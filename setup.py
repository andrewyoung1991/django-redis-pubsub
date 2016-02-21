import os
import sys
from setuptools import setup, find_packages


version = sys.version_info.major, sys.version_info.minor
assert version >= (3, 4), "Requires Python 3.4 or later"

install_requires = [
    "aioredis==0.2.4",
    "Django>=1.7",
    "redis==2.10.5",
    "hiredis==0.2.0",
    ]

websockets_require = install_requires + [
    "aiohttp==0.20.2",
    "chardet==2.3.0",
    ]

tests_requires = websockets_require + [
    "PyJWT==1.4.0",
    "djangorestframework==3.3.2",
    "djangorestframework-jwt==1.7.2",
    "model-mommy==1.2.6",
    "coverage==4.0.3",
    "six==1.10.0",
    "psycopg2==2.6.1",
    "py==1.4.31",
    "pytest==2.8.7",
    "pytest-cov==2.2.1",
    "pytest-django==2.9.1",
    ]

def read(filename):
    data = None
    with open(os.path.join(os.path.dirname(__file__), filename)) as file_:
        data = file_.read()
    return data

setup(
    name="django-redis-pubsub",
    version="1.0",
    author="Andrew Young",
    description="asyncronous pubsub in django using redis",
    license="BSD",
    long_description=read("README.rst"),
    packages=find_packages(exclude=["tests", "testapp"]),
    install_requires=install_requires,
    tests_require=tests_requires,
    extras_require={"websockets": websockets_require},
    url="https://github.com/andrewyoung1991/django-redis-pubsub",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Environment :: Web Environment",
        "Framework :: Django",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        ]
    )
