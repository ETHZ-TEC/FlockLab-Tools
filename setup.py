import setuptools
# import os

with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name='flocklab-tools',
    python_requires='>=3.6',
    version='0.1.0',
    author='rtrueb',
    author_email='rtrueb@ethz.ch',
    description='Python support for using the FlockLab testbed (flocklab CLI, creating flocklab xml, visualization).',
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
