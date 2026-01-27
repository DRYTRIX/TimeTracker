"""
Setup configuration for TimeTracker application.
This allows the app to be installed as a package for testing.
"""

from setuptools import setup, find_packages

setup(
    name='timetracker',
    version='4.14.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Core requirements are in requirements.txt
        # This file is mainly for making the app importable during testing
    ],
    python_requires='>=3.11',
)

