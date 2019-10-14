#!/usr/bin/env python3

import base64
import os
import requests
import json
import re
import datetime
import argparse
import tarfile
from collections import OrderedDict
import numpy as np
import pandas as pd

from .visualization import visualizeFlocklabTrace
from .flocklab import Flocklab


################################################################################
def main():
    parser = argparse.ArgumentParser(description='FlockLab CLI')
    parser.add_argument('-v', '--validate', metavar='<testconfig.xml>', help='validate test config')
    parser.add_argument('-c', '--create', metavar='<testconfig.xml>', help='create / schedule new test')
    parser.add_argument('-a', '--abort', metavar='<testid>', help='abort test')
    parser.add_argument('-d', '--delete', metavar='<testid>', help='delete test')
    parser.add_argument('-g', '--get', metavar='<testid>', help='get test results (via https)')
    parser.add_argument('-f', '--fetch', metavar='<testid>', help='fetch test results (via webdav)')
    parser.add_argument('-o', '--observers', metavar='<platform>', help='get a list of the currently available (online) observers')
    parser.add_argument('-p', '--platforms', help='get a list of the available platforms', action='store_true', default=False)
    parser.add_argument('-x', '--xml', metavar='<image.elf>', help='Generate FlockLab xml config')
    parser.add_argument('--power', action='store_true', default=False, help='Enable power profiling (for FlockLab xml config generation)')
    parser.add_argument('-z', '--visualize', metavar='<result directory>', help='Visualize FlockLab result data')


    args = parser.parse_args()
    # assertions
    if args.power:
        assert args.xml is not None

    if args.validate is not None:
        print(Flocklab.xmlValidate(args.validate))
    elif args.create is not None:
        print(Flocklab.createTest(args.create))
    elif args.abort is not None:
        print(Flocklab.abortTest(args.abort))
    elif args.delete is not None:
        print(Flocklab.deleteTest(args.delete))
    elif args.get is not None:
        print(Flocklab.getResults(args.get))
    elif args.fetch is not None:
        # print(Flocklab.festResults(args.fetch))
        print('Sorry, this feature is not yet implemented!')
    elif args.observers is not None:
        print(Flocklab.getObsIds(args.observers))
    elif args.platforms:
        print(Flocklab.getPlatforms())
    elif args.xml is not None:
        Flocklab.generateXmlConfig(args.xml, powerProfiling=args.power)
    elif args.visualize is not None:
        visualizeFlocklabTrace(args.visualize)

################################################################################

if __name__ == "__main__":
    main()
