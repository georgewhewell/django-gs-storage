from __future__ import unicode_literals

import posixpath, datetime, mimetypes, gzip, os
from io import TextIOBase
from email.utils import parsedate_tz
from contextlib import closing, contextmanager
from tempfile import SpooledTemporaryFile

from boto import gs
from boto.gs.connection import GSResponseError

from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.core.files.base import File
from django.contrib.staticfiles.storage import ManifestFilesMixin
from django.utils.deconstruct import deconstructible
from django.utils import timezone
from django.utils.encoding import force_bytes, filepath_to_uri
from django.utils.six.moves.urllib.parse import urljoin

from django_gs_storage.conf import settings


CONTENT_ENCODING_GZIP = "gzip"


class GSFile(File):

    """
    A file returned from Amazon GS.
    """

    def __init__(self, file, name, storage):
        super(GSFile, self).__init__(file, name)
        self._storage = storage

    def open(self, mode=None):
        if self.closed:
            self.file = self._storage.open(self.name, mode or "rb").file
        return super(GSFile, self).open(mode)


@deconstructible
class GSStorage(Storage):

    """
    An implementation of Django file storage over GS.

    It would be nice to use django-storages for this, but it doesn't support
    Python 3, which is kinda lame.
    """

    def __init__(self, gcp_region=None, gcp_access_key_id=None, gcp_secret_access_key=None, gcp_gs_bucket_name=None, gcp_gs_calling_format=None, gcp_gs_key_prefix=None, gcp_gs_bucket_auth=None, gcp_gs_max_age_seconds=None, gcp_gs_public_url=None, gcp_gs_reduced_redundancy=False, gcp_gs_host=None, gcp_gs_metadata=None, gcp_gs_encrypt_key=None, gcp_gs_gzip=None):
        self.gcp_region = settings.GCP_REGION if gcp_region is None else gcp_region
        self.gcp_access_key_id = settings.GCP_ACCESS_KEY_ID if gcp_access_key_id is None else gcp_access_key_id
        self.gcp_secret_access_key = settings.GCP_SECRET_ACCESS_KEY if gcp_secret_access_key is None else gcp_secret_access_key
        self.gcp_gs_bucket_name = settings.GCP_GS_BUCKET_NAME if gcp_gs_bucket_name is None else gcp_gs_bucket_name
        self.gcp_gs_calling_format = settings.GCP_GS_CALLING_FORMAT if gcp_gs_calling_format is None else gcp_gs_calling_format
        self.gcp_gs_key_prefix = settings.GCP_GS_KEY_PREFIX if gcp_gs_key_prefix is None else gcp_gs_key_prefix
        self.gcp_gs_bucket_auth = settings.GCP_GS_BUCKET_AUTH if gcp_gs_bucket_auth is None else gcp_gs_bucket_auth
        self.gcp_gs_max_age_seconds = settings.GCP_GS_MAX_AGE_SECONDS if gcp_gs_max_age_seconds is None else gcp_gs_max_age_seconds
        self.gcp_gs_public_url = settings.GCP_GS_PUBLIC_URL if gcp_gs_public_url is None else gcp_gs_public_url
        self.gcp_gs_reduced_redundancy = settings.GCP_GS_REDUCED_REDUNDANCY if gcp_gs_reduced_redundancy is None else gcp_gs_reduced_redundancy
        self.gcp_gs_host = settings.GCP_GS_HOST if gcp_gs_host is None else gcp_gs_host
        self.gcp_gs_metadata = settings.GCP_GS_METADATA if gcp_gs_metadata is None else gcp_gs_metadata
        self.gcp_gs_encrypt_key = settings.GCP_GS_ENCRYPT_KEY if gcp_gs_encrypt_key is None else gcp_gs_encrypt_key
        self.gcp_gs_gzip = settings.GCP_GS_GZIP if gcp_gs_gzip is None else gcp_gs_gzip
        # Validate args.
        if self.gcp_gs_public_url and self.gcp_gs_bucket_auth:
            raise ImproperlyConfigured("Cannot use GCP_GS_BUCKET_AUTH with GCP_GS_PUBLIC_URL.")
        # Connect to GS.
        connection_kwargs = {
            "calling_format": self.gcp_gs_calling_format,
        }
        if self.gcp_access_key_id:
            connection_kwargs["gcp_access_key_id"] = self.gcp_access_key_id
        if self.gcp_secret_access_key:
            connection_kwargs["gcp_secret_access_key"] = self.gcp_secret_access_key
        if self.gcp_gs_host:
            connection_kwargs["host"] = self.gcp_gs_host
        self.gs_connection = gs.connect_to_region(self.gcp_region, **connection_kwargs)
        if not self.gcp_gs_bucket_auth:
            self.gs_connection.provider.security_token = ''
        self.bucket = self.gs_connection.get_bucket(self.gcp_gs_bucket_name, validate=False)
        # All done!
        super(GSStorage, self).__init__()

    # Helpers.

    def _get_content_type(self, name):
        """Calculates the content type of the file from the name."""
        content_type, encoding = mimetypes.guess_type(name, strict=False)
        content_type = content_type or "application/octet-stream"
        return content_type

    def _get_cache_control(self):
        """
        Calculates an appropriate cache-control header for files.

        Files in non-authenticated storage get a very long expiry time to
        optimize caching, as well as public caching support.
        """
        if self.gcp_gs_bucket_auth:
            privacy = "private"
        else:
            privacy = "public"
        return "{privacy},max-age={max_age}".format(
            privacy = privacy,
            max_age = self.gcp_gs_max_age_seconds,
        )

    def _get_content_encoding(self, content_type):
        """
        Generates an appropriate content-encoding header for the given
        content type.

        Content types that are known to be compressible (i.e. text-based)
        types, are recommended for gzip.
        """
        family, subtype = content_type.lower().split("/")
        subtype = subtype.split("+")[-1]
        if family == "text" or subtype in ("xml", "json", "html", "javascript"):
            return CONTENT_ENCODING_GZIP
        return None

    def _temporary_file(self):
        """
        Creates a temporary file.

        We need a lot of these, so they are tweaked for efficiency.
        """
        return SpooledTemporaryFile(max_size=1024*1024*10)  # 10 MB.

    @contextmanager
    def _conditional_convert_content_to_bytes(self, name, content):
        """
        Forces the given text-mode file into a bytes-mode file.
        """
        if isinstance(content.file, TextIOBase):
            with self._temporary_file() as temp_file:
                for chunk in content.chunks():
                    temp_file.write(force_bytes(chunk))
                temp_file.seek(0)
                yield File(temp_file, name)
                return
        yield content

    @contextmanager
    def _conditional_compress_file(self, name, content, content_encoding):
        """
        Attempts to compress the given file.

        If the file is larger when compressed, returns the original
        file.

        Returns a tuple of (content_encoding, content).
        """
        if self.gcp_gs_gzip and content_encoding == CONTENT_ENCODING_GZIP:
            # Ideally, we would do some sort of incremental compression here,
            # but boto doesn't support uploading a key from an iterator.
            with self._temporary_file() as temp_file:
                with closing(gzip.GzipFile(name, "wb", 9, temp_file)) as zipfile:
                    for chunk in content.chunks():
                        zipfile.write(chunk)
                # Check if the zipped version is actually smaller!
                if temp_file.tell() < content.tell():
                    temp_file.seek(0)
                    content = File(temp_file, name)
                    yield content, CONTENT_ENCODING_GZIP
                    return
        # Haha! Gzip made it bigger.
        content.seek(0)
        yield content, None

    @contextmanager
    def _process_file_for_upload(self, name, content):
        """
        For a given filename and file, returns a tuple of
        (content_type, content_encoding, content). The content
        may or may not be the same file as the original.
        """
        # The Django file storage API always rewinds the file before saving,
        # therefor so should we.
        content.seek(0)
        # Calculate the content type.
        content_type = self._get_content_type(name)
        content_encoding = self._get_content_encoding(content_type)
        # Convert files opened in text mode to binary mode.
        with self._conditional_convert_content_to_bytes(name, content) as content:
            # Attempt content compression.
            with self._conditional_compress_file(name, content, content_encoding) as (content, content_encoding):
                # Return the calculated headers and file.
                yield content, content_type, content_encoding,

    def get_valid_name(self, name):
        return posixpath.normpath(name.replace(os.sep, "/"))

    def _get_key_name(self, name):
        """
        Builds the key name we use to fetch this file form gs

        Normalises the path at the end as name can be a relative url
        """
        return posixpath.join(self.gcp_gs_key_prefix, name)

    def _generate_url(self, name):
        """
        Generates a URL to the given file.

        Authenticated storage will return a signed URL. Non-authenticated
        storage will return an unsigned URL, which aids in browser caching.
        """
        return self.gs_connection.generate_url(
            method = "GET",
            bucket = self.gcp_gs_bucket_name,
            key = self._get_key_name(name),
            expires_in = self.gcp_gs_max_age_seconds,
            query_auth = self.gcp_gs_bucket_auth,
        )

    def _get_key(self, name, validate=False):
        return self.bucket.get_key(self._get_key_name(name), validate=validate)

    def _get_canned_acl(self):
        return "private" if self.gcp_gs_bucket_auth else "public-read"

    def _get_metadata(self, name):
        return {
            key: value(name) if callable(value) else value
            for key, value
            in self.gcp_gs_metadata.items()
        }

    def _open(self, name, mode="rb"):
        if mode != "rb":
            raise ValueError("GS files can only be opened in read-only mode")
        # Load the key into a temporary file. It would be nice to stream the
        # content, but GS doesn't support seeking, which is sometimes needed.
        key = self._get_key(name)
        content = self._temporary_file()
        try:
            key.get_contents_to_file(content)
        except GSResponseError:
            raise IOError("File {name} does not exist".format(
                name = name,
            ))
        content.seek(0)
        # Un-gzip if required.
        if key.content_encoding == CONTENT_ENCODING_GZIP:
            content = gzip.GzipFile(name, "rb", fileobj=content)
        # All done!
        return GSFile(content, name, self)

    def _save(self, name, content):
        # Calculate the file headers and compression.
        with self._process_file_for_upload(name, content) as (content, content_type, content_encoding):
            # Generate file headers.
            headers = {
                "Content-Type": content_type,
                "Cache-Control": self._get_cache_control(),
            }
            # Try to compress the file.
            if content_encoding is not None:
                headers["Content-Encoding"] = content_encoding
            # Add additional metadata.
            headers.update(self._get_metadata(name))
            # Save the file.
            self._get_key(name).set_contents_from_file(
                content,
                policy = self._get_canned_acl(),
                headers = headers,
                reduced_redundancy = self.gcp_gs_reduced_redundancy,
                encrypt_key = self.gcp_gs_encrypt_key,
            )
            # Return the name that was saved.
            return name

    # Subsiduary storage methods.

    def delete(self, name):
        """
        Deletes the specified file from the storage system.
        """
        self._get_key(name).delete()

    def exists(self, name):
        """
        Returns True if a file referenced by the given name already exists in the
        storage system, or False if the name is available for a new file.
        """
        # We also need to check for directory existence, so we'll list matching
        # keys and return success if any match.
        for _ in self.bucket.list(prefix=self._get_key_name(name), delimiter="/"):
            return True
        return False

    def listdir(self, path):
        """
        Lists the contents of the specified path, returning a 2-tuple of lists;
        the first item being directories, the second item being files.
        """
        path = self._get_key_name(path)
        # Normalize directory names.
        if path and not path.endswith("/"):
            path += "/"
        # Look through the paths, parsing out directories and paths.
        files = set()
        dirs = set()
        for key in self.bucket.list(prefix=path, delimiter="/"):
            key_path = key.name[len(path):]
            if key_path.endswith("/"):
                dirs.add(key_path[:-1])
            else:
                files.add(key_path)
        # All done!
        return list(dirs), list(files)

    def size(self, name):
        """
        Returns the total size, in bytes, of the file specified by name.
        """
        return self._get_key(name, validate=True).size

    def url(self, name):
        """
        Returns an absolute URL where the file's contents can be accessed
        directly by a Web browser.
        """
        if self.gcp_gs_public_url:
            return urljoin(self.gcp_gs_public_url, filepath_to_uri(name))
        return self._generate_url(name)

    def accessed_time(self, name):
        """
        Returns the last accessed time (as datetime object) of the file
        specified by name.

        Since this is not accessible via GS, the modified time is returned.
        """
        return self.modified_time(name)

    def created_time(self, name):
        """
        Returns the creation time (as datetime object) of the file
        specified by name.

        Since this is not accessible via GS, the modified time is returned.
        """
        return self.modified_time(name)

    def modified_time(self, name):
        """
        Returns the last modified time (as datetime object) of the file
        specified by name.
        """
        time_tuple = parsedate_tz(self._get_key(name, validate=True).last_modified)
        timestamp = datetime.datetime(*time_tuple[:6])
        offset = time_tuple[9]
        if offset is not None:
            # Convert to local time.
            timestamp = timezone.make_aware(timestamp, timezone.FixedOffset(offset))
            timestamp = timezone.make_naive(timestamp, timezone.utc)
        return timestamp

    def sync_meta_iter(self):
        """
        Sycnronizes the meta information on all GS files.

        Returns an iterator of paths that have been syncronized.
        """
        def sync_meta_impl(root):
            dirs, files = self.listdir(root)
            for filename in files:
                path = posixpath.join(root, filename)
                key = self._get_key(path, validate=True)
                metadata = key.metadata.copy()
                metadata["Content-Type"] = key.content_type
                if key.content_encoding:
                    metadata["Content-Encoding"] = key.content_encoding
                metadata["Cache-Control"] = self._get_cache_control()
                metadata.update(self._get_metadata(path))
                # Copy the key.
                key.copy(
                    key.bucket,
                    key.name,
                    preserve_acl=False,
                    metadata=metadata,
                    encrypt_key=self.gcp_gs_encrypt_key,
                )
                # Set the ACL.
                key.set_canned_acl(self._get_canned_acl())
                yield path
            for dirname in dirs:
                for path in sync_meta_impl(posixpath.join(root, dirname)):
                    yield path
        for path in sync_meta_impl(""):
            yield path

    def sync_meta(self):
        """
        Sycnronizes the meta information on all GS files.
        """
        for path in self.sync_meta_iter():
            pass


class StaticGSStorage(GSStorage):

    """
    An GS storage for storing static files.

    Initializes the default bucket name frome the `GCP_GS_BUCKET_NAME_STATIC`
    setting, allowing different buckets to be used for static and uploaded
    files.

    By default, bucket auth is off, making file access more efficient and
    cacheable.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("gcp_gs_bucket_name", settings.GCP_GS_BUCKET_NAME_STATIC)
        kwargs.setdefault("gcp_gs_calling_format", settings.GCP_GS_CALLING_FORMAT_STATIC)
        kwargs.setdefault("gcp_gs_key_prefix", settings.GCP_GS_KEY_PREFIX_STATIC)
        kwargs.setdefault("gcp_gs_bucket_auth", settings.GCP_GS_BUCKET_AUTH_STATIC)
        kwargs.setdefault("gcp_gs_max_age_seconds", settings.GCP_GS_MAX_AGE_SECONDS_STATIC)
        kwargs.setdefault("gcp_gs_public_url", settings.GCP_GS_PUBLIC_URL_STATIC)
        kwargs.setdefault("gcp_gs_reduced_redundancy", settings.GCP_GS_REDUCED_REDUNDANCY_STATIC)
        kwargs.setdefault("gcp_gs_host", settings.GCP_GS_HOST_STATIC)
        kwargs.setdefault("gcp_gs_metadata", settings.GCP_GS_METADATA_STATIC)
        kwargs.setdefault("gcp_gs_gzip", settings.GCP_GS_GZIP_STATIC)
        super(StaticGSStorage, self).__init__(**kwargs)


class ManifestStaticGSStorage(ManifestFilesMixin, StaticGSStorage):

    pass
