# FlockLab Python Support

This python package provides support for
* Interfacing with FlockLab via a CLI
* Creating FlockLab test xml programmatically (Python wrapper)
* Visualizing FlockLab test results

# Installation

Install `python3.6+` and `pip`. Then run (not yet working!):

```sh
python -m pip install flocklab
```

### Run the Script ###

Use 

```sh
python -m flocklab
```

or just

```
flocklab -h
```

### Development ### 

Do not install the Python package from PyPi, but rather clone this repository and run the following from inside the top folder (where `setup.py` is located):

```sh
python -m pip install -e .
```

You can edit the source files and the module will reflect the changes automatically (`-e` means editable install).
