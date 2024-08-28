#!/usr/bin/python3
"""
Description: setup up the A-ops manager service.
"""
import os
from setuptools import find_packages, setup
from distutils.sysconfig import get_python_lib

TEMPLATE = os.path.join(get_python_lib(), "zeus", "operation_service", "templates")
setup(
    name='zeus-operation',
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
        ('/etc/aops/conf.d', ['zeus-operation.yml']),
        ('/usr/lib/systemd/system', ["zeus-operation.service"]),
        ("/opt/aops/database", ["zeus/operation_service/database/zeus-operation.sql"]),
        (TEMPLATE, ["zeus/operation_service/templates/workflow_template.yml"]),
    ],
    zip_safe=False,
)
