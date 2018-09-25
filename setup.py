#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='tap-campaign-monitor',
    version='1.0.0',
    description=(
        'Singer.io tap for extracting data from the '
        'Campaign Monitor API'
    ),
    author='Stitch Data, Fishtown Analytics',
    url='https://www.stitchdata.com, http://fishtownanalytics.com',
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    install_requires=[
        'tap-framework==0.0.5'
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
