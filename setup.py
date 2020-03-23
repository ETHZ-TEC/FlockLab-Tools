#!/usr/bin/env python3
"""
Copyright (c) 2020, ETH Zurich, Computer Engineering Group (TEC)
"""

import setuptools
import re

# Version number (set in '_version.py'!)
VERSIONFILE="flocklab/_version.py"
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    verstr = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))

# README
with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name='flocklab-tools',
    python_requires='>=3.6',
    version=verstr,
    author='Computer Engineering Group, ETH Zurich',
    author_email='rtrueb@ethz.ch',
    description='Python support for using the FlockLab 2 testbed (flocklab CLI, creating flocklab xml, visualization).',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://flocklab.ethz.ch/',
    packages=setuptools.find_packages(),
    install_requires=[
        'setuptools',
        'numpy',
        'pandas',
        'bokeh',
        'requests',
        'appdirs',
    ],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    entry_points={
        'console_scripts': [
            'flocklab = flocklab.__main__:main'
        ]
    },
)
