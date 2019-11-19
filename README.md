# FlockLab Tools

This python package provides:
* Python API for managing FlockLab tests
* Command-line interface (CLI) for Interfacing with FlockLab
* Programmatic creation of FlockLab test xml files (in python)
* Visualization of FlockLab test results

## Installation

Dependencies:
* `python3.6+`
* `pip`

Install with
```sh
python -m pip install flocklab-tools
```

## Uninstall
```python
python3 -m pip uninstall flocklab-tools
```


## Usage

### Command Line Interface (CLI)
System wide command:
```sh
flocklab -h
```

Alternative (using the python module):
```sh
python3 -m flocklab -h
```

#### Command Line Options:
```sh
-h, --help            show this help message and exit
-v <testconfig.xml>, --validate <testconfig.xml>
                      validate test config
-c <testconfig.xml>, --create <testconfig.xml>
                      create / schedule new test
-a <testid>, --abort <testid>
                      abort test
-d <testid>, --delete <testid>
                      delete test
-g <testid>, --get <testid>
                      get test results (via https)
-f <testid>, --fetch <testid>
                      fetch test results (via webdav) [NOT IMPLEMENTED YET!]
-o <platform>, --observers <platform>
                      get a list of the currently available (online)
                      observers
-p, --platforms       get a list of the available platforms
-x <result directory>, --visualize <result directory>
                      Visualize FlockLab result data

```

#### Visualization of FlockLab Results

```sh
flocklab -x <result directory>
```


### Python Support
Example 
```python
from flocklab import Flocklab as fl
from flocklab import *

testId = 0
fl.getResults(testId)

fc = FlocklabXmlConfig()
fc.generalConf.name = 'Example Test'
fc.generalConf.description = 'Description of example test'
fc.generalConf.duration = 60 # duration in seconds
# ...
```

## Development

#### Bug Reports / Feature Requests
Please send bug reports and feature requests to rtrueb@ethz.ch. 

#### Installation for Development 

Clone this repository and run the following from inside the root folder of the project (where `setup.py` is located):

```sh
python -m pip install -e .
```

You can edit the source files and the module will reflect the changes automatically (the `-e` option which means _editable install_).
