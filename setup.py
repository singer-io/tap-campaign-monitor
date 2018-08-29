#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='tap-campaign-monitor',
    version='0.1.1',
    description=(
        'Singer.io tap for extracting data from the '
        'Campaign Monitor API'
    ),
    author='Fishtown Analytics',
    url='http://fishtownanalytics.com',
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    install_requires=[
        'tap-framework==0.0.4'
    ],
    entry_points='''
        [console_scripts]
        tap-campaign-monitor=tap_campaign_monitor:main
    ''',
    packages=find_packages(),
    package_data={
        'tap_campaign_monitor': [
            'schemas/*.json'
        ]
    }
)
