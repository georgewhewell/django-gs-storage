from setuptools import setup, find_packages

from django_gs_storage import __version__


version_str = ".".join(str(n) for n in __version__)


setup(
    name = "django-gs-storage",
    version = version_str,
    license = "BSD",
    description = "Django Amazon GS file storage.",
    author = "Dave Hall",
    author_email = "dave@etianen.com",
    url = "https://github.com/etianen/django-gs-storage",
    packages = find_packages(),
    install_requires = [
        "django>=1.7",
        "boto>=2.35",
    ],
    extras_require = {
        "test": [
            "coverage",
            "requests",
        ],
    },
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Framework :: Django",
    ],
)
