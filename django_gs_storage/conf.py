from __future__ import unicode_literals

"""
Settings used by django-gs-storage.
"""

from django.conf import settings


class LazySetting(object):

    """
    A proxy to a named Django setting.
    """

    def __init__(self, name, default=""):
        self.name = name
        self.default = default

    def __get__(self, obj, cls):
        if obj is None:
            return self
        return getattr(obj._settings, self.name, self.default)


class LazySettings(object):

    """
    A proxy to gs-specific django settings.

    Settings are resolved at runtime, allowing tests
    to change settings at runtime.
    """

    def __init__(self, settings):
        self._settings = settings

    GCP_REGION = LazySetting(
        name = "GCP_REGION",
        default = "us-east-1",
    )

    GCP_ACCESS_KEY_ID = LazySetting(
        name = "GCP_ACCESS_KEY_ID",
    )

    GCP_SECRET_ACCESS_KEY = LazySetting(
        name = "GCP_SECRET_ACCESS_KEY",
    )

    # Media storage config.

    GCP_GS_BUCKET_NAME = LazySetting(
        name = "GCP_GS_BUCKET_NAME",
    )

    GCP_GS_CALLING_FORMAT = LazySetting(
        name = "GCP_GS_CALLING_FORMAT",
        default = "boto.gs.connection.OrdinaryCallingFormat",
    )

    GCP_GS_HOST = LazySetting(
        name = "GCP_GS_HOST",
    )

    GCP_GS_KEY_PREFIX = LazySetting(
        name = "GCP_GS_KEY_PREFIX",
    )

    GCP_GS_BUCKET_AUTH = LazySetting(
        name = "GCP_GS_BUCKET_AUTH",
        default = True,
    )

    GCP_GS_MAX_AGE_SECONDS = LazySetting(
        name = "GCP_GS_MAX_AGE_SECONDS",
        default = 60 * 60,  # 1 hours.
    )

    GCP_GS_PUBLIC_URL = LazySetting(
        name = "GCP_GS_PUBLIC_URL",
    )

    GCP_GS_REDUCED_REDUNDANCY = LazySetting(
        name = "GCP_GS_REDUCED_REDUNDANCY",
    )

    GCP_GS_METADATA = LazySetting(
        name = "GCP_GS_METADATA",
        default = {},
    )

    GCP_GS_ENCRYPT_KEY = LazySetting(
        name = "GCP_GS_ENCRYPT_KEY",
        default = False,
    )

    GCP_GS_GZIP = LazySetting(
        name = "GCP_GS_GZIP",
        default = True
    )

    # Static storage config.

    GCP_GS_BUCKET_NAME_STATIC = LazySetting(
        name = "GCP_GS_BUCKET_NAME_STATIC",
    )

    GCP_GS_CALLING_FORMAT_STATIC = LazySetting(
        name = "GCP_GS_CALLING_FORMAT_STATIC",
        default = "boto.gs.connection.OrdinaryCallingFormat",
    )

    GCP_GS_HOST_STATIC = LazySetting(
        name = "GCP_GS_HOST_STATIC",
    )

    GCP_GS_KEY_PREFIX_STATIC = LazySetting(
        name = "GCP_GS_KEY_PREFIX_STATIC",
    )

    GCP_GS_BUCKET_AUTH_STATIC = LazySetting(
        name = "GCP_GS_BUCKET_AUTH_STATIC",
        default = False,
    )

    GCP_GS_MAX_AGE_SECONDS_STATIC = LazySetting(
        name = "GCP_GS_MAX_AGE_SECONDS_STATIC",
        default = 60 * 60 * 24 * 365,  # 1 year.
    )

    GCP_GS_PUBLIC_URL_STATIC = LazySetting(
        name = "GCP_GS_PUBLIC_URL_STATIC",
    )

    GCP_GS_REDUCED_REDUNDANCY_STATIC = LazySetting(
        name = "GCP_GS_REDUCED_REDUNDANCY_STATIC",
    )

    GCP_GS_METADATA_STATIC = LazySetting(
        name = "GCP_GS_METADATA_STATIC",
        default = {},
    )

    GCP_GS_ENCRYPT_KEY_STATIC = LazySetting(
        name = "GCP_GS_ENCRYPT_KEY_STATIC",
        default = False,
    )

    GCP_GS_GZIP_STATIC = LazySetting(
        name = "GCP_GS_GZIP_STATIC",
        default = True
    )


settings = LazySettings(settings)
