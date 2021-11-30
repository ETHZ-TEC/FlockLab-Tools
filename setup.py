#!/usr/bin/env python3
"""
Copyright (c) 2021, ETH Zurich, Computer Engineering Group (TEC)
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
    license='BSD 3-Clause',
    license_files = ('LICENSE',),
    description='Python support for using the FlockLab 2 testbed (flocklab CLI, creating flocklab xml, visualization).',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://flocklab.ethz.ch/',
    packages=setuptools.find_packages(),
    install_requires=[
        'setuptools>=50.3.0',
        'numpy>=1.19.1,<2.0',
        'pandas>=1.1.1,<2.0',
        'bokeh>=2.1.1,<3.0',
        'requests>=2.22.0,<3.0',
        'appdirs>=1.4.3,<1.5',
        'rocketlogger>=2.0,<3.0',
        'pyelftools>=0.26,<1.0',
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
