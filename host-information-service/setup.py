#!/usr/bin/python3
"""
Description: setup up the A-ops manager service.
"""

from setuptools import find_packages, setup

setup(
    name='zeus-host-information',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'marshmallow>=3.13.0',
        'Flask',
        'Flask-RESTful',
        'requests',
        'SQLAlchemy',
        'paramiko>=2.11.0',
        "redis",
        'gevent',
        "retrying",
    ],
    data_files=[
        ('/etc/aops/conf.d', ['zeus-host-information.yml']),
        ('/usr/lib/systemd/system', ["zeus-host-information.service"]),
        ("/opt/aops/database", ["zeus/host_information_service/database/zeus-host-information.sql"]),
    ],
    zip_safe=False,
)
