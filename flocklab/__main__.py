#!/usr/bin/env python3
"""
Copyright (c) 2021, ETH Zurich, Computer Engineering Group (TEC)
"""

import base64
import os
import sys
import requests
import json
import re
from datetime import datetime
import argparse
import tarfile
from collections import OrderedDict
import numpy as np
import pandas as pd
import appdirs

from ._version import __version__
from .visualization import visualizeFlocklabTrace
from .flocklab import Flocklab


################################################################################
def main():
    description = '''FlockLab CLI
    Default config file location: {}
    '''.format(os.path.join(appdirs.AppDirs("flocklab_tools", "flocklab_tools").user_config_dir,'.flocklabauth'))
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--validate', metavar='<testconfig.xml>', help='validate test config')
    parser.add_argument('-c', '--create', metavar='<testconfig.xml>', help='create / schedule new test')
    parser.add_argument('-a', '--abort', metavar='<testid>', help='abort test')
    parser.add_argument('-d', '--delete', metavar='<testid>', help='delete test')
    parser.add_argument('-i', '--info', metavar='<testid>', help='get test info')
    parser.add_argument('-g', '--get', metavar='<testid>', help='get test results')
    parser.add_argument('-o', '--observers', metavar='<platform>', help='get a list of the currently available (online) observers')
    parser.add_argument('-p', '--platforms', help='get a list of the available platforms', action='store_true', default=False)
    parser.add_argument('-x', '--visualize', metavar='<result directory>', help='Visualize FlockLab result data', type=str, nargs='?') # default unfortunately does not work properly together with nargs
    parser.add_argument('-s', '--downsampling', metavar='<factor>', help='downsampling factor for power profiling data in visualization', type=int, default=1)
    parser.add_argument('-y', '--develop', help='Enable develop output (incl. develop signals (nRST, PPS) in visualization)', action='store_true', default=False)
    parser.add_argument('-V', '--version', help='Print version number', action='store_true', default=False)


    args = parser.parse_args()

    fl = Flocklab()
    ret = ''
    if args.validate is not None:
        ret = fl.xmlValidate(args.validate)
    elif args.create is not None:
        ret = fl.createTestWithInfo(args.create)
    elif args.abort is not None:
        ret = fl.abortTest(args.abort)
    elif args.delete is not None:
        ret = fl.deleteTest(args.delete)
    elif args.info is not None:
        ret = fl.getTestInfo(args.info)
    elif args.get is not None:
        ret = fl.getResults(args.get)
    elif args.observers is not None:
        ret = fl.getObsIds(args.observers)
    elif args.platforms:
        ret = fl.getPlatforms()
    elif args.visualize is not None:
        visualizeFlocklabTrace(resultPath=args.visualize, interactive=True, showPps=args.develop, showRst=args.develop, downsamplingFactor=args.downsampling)
    elif args.version:
        ret = __version__
    else:
        parser.print_help()

    if type(ret) == str:
        if ret != '':
            print(ret)
            if 'ERROR' in ret:
                sys.exit(1)
            else:
                sys.exit(0)
    else:
        print(ret)

################################################################################

if __name__ == "__main__":
    main()
