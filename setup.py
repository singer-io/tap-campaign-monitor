#!/usr/bin/env python

from setuptools import setup, find_packages
import os.path

setup(name='tap-campaign-monitor',
      version='0.1.0',
      description='Singer.io tap for extracting data from the Campaign Monitor API',
      author='Fishtown Analytics',
      url='http://fishtownanalytics.com',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_campaign_monitor'],
      install_requires=[
          'tap-framework==0.0.4'
      ],
      entry_points='''
          [console_scripts]
          tap-campaign-monitor=tap_campaign_monitor:main
      ''',
      packages=['tap_campaign_monitor'])
