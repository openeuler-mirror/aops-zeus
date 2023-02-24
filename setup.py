#!/usr/bin/python3
"""
Description: setup up the A-ops manager service.
"""

from setuptools import setup, find_packages


setup(
    name='aops-zeus',
    version='2.0.0',
    packages=find_packages(),
    install_requires=[
        'marshmallow>=3.13.0',
        'Flask',
        'Flask-RESTful',
        'requests',
        'SQLAlchemy',
        'Werkzeug',
        'paramiko',
        "redis"
        ],
    author='cmd-lsw-yyy-zyc',
    data_files=[
        ('/etc/aops', ['conf/zeus.ini']),
        ('/usr/lib/systemd/system', ['aops-zeus.service'])
    ],
    scripts=['aops-zeus'],
    zip_safe=False
)
