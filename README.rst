django-gs-storage
=================

**django-gs-storage** provides a Django Amazon GS file storage.


Features
--------

- Django file storage for Amazon GS.
- Django static file storage for Amazon GS.
- Works in Python 3!


Installation
------------

1. Install using ``pip install django-gs-storage``.
2. Add ``'django_gs_storage'`` to your ``INSTALLED_APPS`` setting.
3. Set your ``DEFAULT_FILE_STORAGE`` setting to ``"django_gs_storage.storage.GSStorage"``.
4. Set your ``STATICFILES_STORAGE`` setting to ``"django_gs_storage.storage.StaticGSStorage"`` or ``"django_gs_storage.storage.ManifestStaticGSStorage"``.
5. Configure your Amazon GS settings (see Available settings, below).


Available settings
------------------

.. code:: python

    # The region to connect to when storing files.
    GCP_REGION = "us-east-1"

    # The GCP access key used to access the storage buckets.
    GCP_ACCESS_KEY_ID = ""

    # The GCP secret access key used to access the storage buckets.
    GCP_SECRET_ACCESS_KEY = ""

    # The GS bucket used to store uploaded files.
    GCP_GS_BUCKET_NAME = ""

    # The GS calling format to use to connect to the bucket.
    GCP_GS_CALLING_FORMAT = "boto.gs.connection.OrdinaryCallingFormat"

    # The host to connect to (only needed if you are using a non-GCP host)
    GCP_GS_HOST = ""

    # A prefix to add to the start of all uploaded files.
    GCP_GS_KEY_PREFIX = ""

    # Whether to enable querystring authentication for uploaded files.
    GCP_GS_BUCKET_AUTH = True

    # The expire time used to access uploaded files.
    GCP_GS_MAX_AGE_SECONDS = 60*60  # 1 hour.

    # A custom URL prefix to use for public-facing URLs for uploaded files.
    GCP_GS_PUBLIC_URL = ""

    # Whether to set the storage class of uploaded files to REDUCED_REDUNDANCY.
    GCP_GS_REDUCED_REDUNDANCY = False

    # A dictionary of additional metadata to set on the uploaded files.
    # If the value is a callable, it will be called with the path of the file on GS.
    GCP_GS_METADATA = {}

    # Whether to enable gzip compression for uploaded files.
    GCP_GS_GZIP = True

    # The GS bucket used to store static files.
    GCP_GS_BUCKET_NAME_STATIC = ""

    # The GS calling format to use to connect to the static bucket.
    GCP_GS_CALLING_FORMAT_STATIC = "boto.gs.connection.OrdinaryCallingFormat"

    # The host to connect to for static files (only needed if you are using a non-GCP host)
    GCP_GS_HOST_STATIC = ""

    # Whether to enable querystring authentication for static files.
    GCP_GS_BUCKET_AUTH_STATIC = False

    # A prefix to add to the start of all static files.
    GCP_GS_KEY_PREFIX_STATIC = ""

    # The expire time used to access static files.
    GCP_GS_MAX_AGE_SECONDS_STATIC = 60*60*24*365  # 1 year.

    # A custom URL prefix to use for public-facing URLs for static files.
    GCP_GS_PUBLIC_URL_STATIC = ""

    # Whether to set the storage class of static files to REDUCED_REDUNDANCY.
    GCP_GS_REDUCED_REDUNDANCY_STATIC = False

    # A dictionary of additional metadata to set on the static files.
    # If the value is a callable, it will be called with the path of the file on GS.
    GCP_GS_METADATA_STATIC = {}

    # Whether to enable gzip compression for static files.
    GCP_GS_GZIP_STATIC = True


**Important:** If you change any of the ``GCP_GS_BUCKET_AUTH`` or ``GCP_GS_MAX_AGE_SECONDS`` settings, you will need
to run ``./manage.py gs_sync_meta path.to.your.storage`` before the changes will be applied to existing media files.


How it works
------------

By default, uploaded user files are stored on Amazon GS using the private access control level. When a URL for the file
is generated, querystring auth with a timeout of 1 hour is used to secure access to the file.

By default, static files are stored on Amazon GS using the public access control level and aggressive caching.

Text-based files, such as HTML, XML and JSON, are stored using gzip to save space and improve download
performance.

At the moment, files stored on GS can only be opened in read-only mode.


Optimizing media file caching
-----------------------------

The default settings assume that user-uploaded file are private. This means that
they are only accessible via GS authenticated URLs, which is bad for browser caching.

To make user-uploaded files public, and enable aggressive caching, make the following changes to your ``settings.py``.

.. code:: python

    GCP_GS_BUCKET_AUTH = False

    GCP_GS_MAX_AGE_SECONDS = 60*60*24*365  # 1 year.

**Important:** By making these changes, all user-uploaded files will be public. Ensure they do not contain confidential information.

**Important:** If you change any of the ``GCP_GS_BUCKET_AUTH`` or ``GCP_GS_MAX_AGE_SECONDS`` settings, you will need
to run ``./manage.py gs_sync_meta path.to.your.storage`` before the changes will be applied to existing media files.


Management commands
-------------------

`gs_sync_meta`
~~~~~~~~~~~~~~

Syncronizes the meta information on GS files.

If you change any of the ``GCP_GS_BUCKET_AUTH``, ``GCP_GS_MAX_AGE_SECONDS``, or ``GCP_GS_METADATA`` settings, you will need
to run this command before the changes will be applied to existing media files.

Example usage: ``./manage.py gs_sync_meta django.core.files.storage.default_storage``


How does django-gs-storage compare with django-storages?
--------------------------------------------------------

The `django-storages-redux <https://github.com/jschneier/django-storages>`_ fork of django-storages appears to be
the most widely used GS storage backend for Django. It also supports a variety of other storage backends.

django-gs-storage provides similar features, but only supports GS. It was originally written to support Python 3
at a time when the future of django-storages was unclear. It's a small, well-tested and self-contained library
that aims to do one thing very well.

The author of django-gs-storage is not aware of significant differences in functionality with django-storages-redux.
If you notice some differences, please file an issue!

Migration from django-storages(non-redux)
-----------------------------------------

If your are updating a project that used `django-storages <https://pypi.python.org/pypi/django-storages/1.1.8>`_ just for GS file storage, migration is trivial.

Follow the installation instructions, replacing 'storages' in ``INSTALLED_APPS``. Be sure to scrutinize the rest of your settings file for changes, most notably ``GCP_GS_BUCKET_NAME`` for ``GCP_STORAGE_BUCKET_NAME``.

Build status
------------

This project is built on every push using the Travis-CI service.

.. image:: https://travis-ci.org/etianen/django-gs-storage.svg?branch=master
    :target: https://travis-ci.org/etianen/django-gs-storage


Support and announcements
-------------------------

Downloads and bug tracking can be found at the `main project
website <http://github.com/etianen/django-gs-storage>`_.


More information
----------------

The django-gs-storage project was developed by Dave Hall. You can get the code
from the `django-gs-storage project site <http://github.com/etianen/django-gs-storage>`_.

Dave Hall is a freelance web developer, based in Cambridge, UK. You can usually
find him on the Internet in a number of different places:

-  `Website <http://www.etianen.com/>`_
-  `Twitter <http://twitter.com/etianen>`_
-  `Google Profile <http://www.google.com/profiles/david.etianen>`_
