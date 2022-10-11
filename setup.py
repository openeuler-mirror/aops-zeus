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
        'ansible>=2.9.0',
        'PyYAML',
        'marshmallow>=3.13.0',
        'Flask',
        'Flask-RESTful',
        'requests',
        'SQLAlchemy',
        'Werkzeug'
        ],
    author='cmd-lsw-yyy-zyc',
    data_files=[
        ('/etc/aops', ['conf/zeus.ini', 'conf/default.json']),
        ('/usr/lib/systemd/system', ['aops-zeus.service']),
    ],
    scripts=['aops-zeus'],
    zip_safe=False
)
