# FlockLab Tools

This python package provides support for
* Interfacing with FlockLab via a CLI
* Creating FlockLab test xml programmatically (Python wrapper)
* Visualizing FlockLab test results



## Usage

### Command Line Interface (CLI)
System wide command:
```sh
flocklab -h
```

Alternative (using the module):
```sh
python3 -m flocklab -h
```

### Python support
Example 
```python
from flocklab import Flocklab as fl
from flocklab import *

testId = 0
fl.getResults(testId)

flConfig = FlocklabXmlConfig()
flConfig.generalConf.name = 'Example Test'
flConfig.generalConf.description = 'Description of example test'
flConfig.generalConf.duration = 60 # duration in seconds

# ...
```

## Installation for Development 

Clone this repository and run the following from inside the root folder of the project (where `setup.py` is located):

```sh
python -m pip install -e .
```

You can edit the source files and the module will reflect the changes automatically (ue to the `-e` option which means _editable install_).

## Installation (not yet working!)

Install `python3.6+` and `pip`. Then run:

```sh
python -m pip install flocklab_tools
```

## Uninstall
```python
python3 -m pip uninstall flocklab_tools
```
