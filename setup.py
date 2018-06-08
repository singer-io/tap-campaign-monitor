#!/usr/bin/env python

from setuptools import setup, find_packages
import os.path

setup(name='tap-campaign-monitor',
      version='0.0.1',
      description='Singer.io tap for extracting data from the Campaign Monitor API',
      author='Fishtown Analytics',
      url='http://fishtownanalytics.com',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_campaign_monitor'],
      install_requires=[
          'singer-python==5.0.12',
          'backoff==1.3.2',
          'requests==2.18.4',
          'requests-oauthlib==0.8.0',
          'funcy==1.10.1',
      ],
      entry_points='''
          [console_scripts]
          tap-campaign-monitor=tap_campaign_monitor:main
      ''',
      packages=['tap_campaign_monitor'])
