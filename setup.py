#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='tap-campaign-monitor',
    version='1.2.0',
    description=(
        'Singer.io tap for extracting data from the '
        'Campaign Monitor API'
    ),
    author='Stitch Data, Fishtown Analytics',
    url='https://www.stitchdata.com',
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    install_requires=[
        'singer-python==6.8.0',
        'requests==2.32.5',
        'backoff==2.2.1',
    ],
    extras_require={
      "dev": [
        "pylint",
        "ipdb",
        "nose",
        "parameterized",
      ],
    },
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
