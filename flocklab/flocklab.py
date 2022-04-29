#!/usr/bin/env python3
"""
Copyright (c) 2021, ETH Zurich, Computer Engineering Group (TEC)
"""

import base64
import os
import stat
import sys
import time
import requests
import json
import re
import datetime
import argparse
import tarfile
from collections import OrderedDict
import numpy as np
import pandas as pd
import appdirs
from getpass import getpass
from xml.etree import ElementTree as et
import io
from elftools.elf.elffile import ELFFile   # requires package "pyelftools"
import struct

################################################################################


class FlocklabError(Exception):
    """Exception raised for errors from flocklab

    Attributes:
        message -- explanation of the error
    """

    def __init__(self,  message):
        self.message = message


class Flocklab:
    def __init__(self, apiBaseAddr=None):
        if apiBaseAddr is None:
            self.apiBaseAddr = 'https://flocklab.ethz.ch/user/'
        else:
            self.apiBaseAddr = apiBaseAddr
        self.sslVerify = True

    def setApiBaseAddr(self, addr):
        self.apiBaseAddr = addr

    def getCredentials(self):
        '''Feteches FlockLab credentials stored in .flocklabauth file
        Returns:
            Username & Password
        '''
        # get username and pw from config file
        flConfigPath = os.path.join(appdirs.AppDirs("flocklab_tools", "flocklab_tools").user_config_dir,'.flocklabauth')
        flConfigDir = os.path.dirname(flConfigPath)
        # check if flocklab auth file exists
        if not os.path.exists(flConfigPath):
            print('The required FlockLab authentication file ({}) is not available!'.format(flConfigPath))
            # offer user to create flocklab auth file
            inp = input("Would you like to create the .flocklabauth file? [y/N]: ")
            if inp == 'y':
                # check if config folder exists & create it if necessary
                if not os.path.exists(flConfigDir):
                    os.makedirs(flConfigDir)
                usr = input("Username: ")
                pwd = getpass(prompt='Password: ', stream=None)
                # Test whether credentials are working
                if self.getPlatforms(username=usr, password=pwd) is not None:
                    with open(flConfigPath, 'w') as f:
                        f.write('USER={}\n'.format(usr))
                        f.write('PASSWORD={}\n'.format(pwd))
                    os.chmod(flConfigPath, stat.S_IRUSR | stat.S_IWUSR)
                    print("FlockLab authentication file successfully created!")
                else:
                    print("ERROR: FlockLab authentication information seems wrong. No \'.flocklabauth\' file created!")
                    sys.exit(1)

        try:
            with open(flConfigPath, "r") as configFile:
                text = configFile.read()
                username = re.search(r'USER=(.+)', text).group(1)
                password = re.search(r'PASSWORD=(.+)', text).group(1)
                return {'username': username, 'password': password}
        except:
            print("ERROR: Failed to read flocklab auth info from %s \n"
                  "Please create the file and provide at least one line with USER=your_username and one line with PASSWORD=your_password \n"
                  "See https://gitlab.ethz.ch/tec/public/flocklab/wikis/flocklab-cli#setting-it-up for more info!"%flConfigPath)

    @staticmethod
    def formatObsIds(obsList):
        '''
        Args:
            obsList: list of integers correpsonding to observer IDs
        Returns:
            String which concatenates all observer IDs and formats them according to the FlockLab xml config file requirements
        '''
        obsList = ['{:d}'.format(e) for e in obsList]
        return ' '.join(obsList)

    @staticmethod
    def apiStr2int(apiStr):
        '''
        Args:
            apiStr: string to be converted to int or None
        Returns:
            object of converted string (int)
        '''
        if apiStr is None:
            ret = None
        else:
            if apiStr.isnumeric():
                ret = int(apiStr)
            else:
                ret = None
        return ret


    @staticmethod
    def getImageAsBase64(imagePath):
        '''
        Args:
            imagePath: path to image file (.elf)
        Returns:
            image as base64 encoded string
        '''
        try:
            with open(imagePath, "rb") as elf_file:
                encoded_string = base64.b64encode(elf_file.read()).decode('ascii')

                # insert newlines
                every = 128
                encoded_string = '\n'.join(encoded_string[i:i + every] for i in range(0, len(encoded_string), every))

                return encoded_string
        except FileNotFoundError:
            print("ERROR: Failed to read and convert image!")

    def xmlValidate(self, xmlPath):
        '''Validate FlockLab config xml by using the web api
        Args:
            xmlPath: path to FlockLab config xml file
        Returns:
            Result of validation as string
        '''
        creds = self.getCredentials()

        try:
            files = {
                'username': (None, creds['username']),
                'password': (None, creds['password']),
                'first': (None, 'no'),
                'xmlfile': (os.path.basename(xmlPath), open(xmlPath, 'rb').read(), 'text/xml', {}),
            }
            req = requests.post(self.apiBaseAddr + 'xmlvalidate.php', files=files, verify=self.sslVerify)
            if '<p>The file validated correctly.</p>' in req.text:
                info = 'The file validated correctly.'
            else:
                info = re.search(r'<!-- cmd -->(.*)<!-- cmd -->', req.text).group(1)
        except Exception as e:
            info = "{}\nERROR: Failed to contact the FlockLab API!".format(e)
        return info

    def createTest(self, xmlPath):
        '''Create a FlockLab test by using the web api
        Args:
            xmlPath: path to FlockLab config xml file
        Returns:
            testId: Test ID returned from flocklab if successful, None otherwise
            info: Result of test creation as string
        '''
        creds = self.getCredentials()

        try:
            files = {
                'username': (None, creds['username']),
                'password': (None, creds['password']),
                'first': (None, 'no'),
                'xmlfile': (os.path.basename(xmlPath), open(xmlPath, 'rb').read(), 'text/xml', {}),
            }
            req = requests.post(self.apiBaseAddr + 'newtest.php', files=files, verify=self.sslVerify)
            ret = re.search('<!-- cmd --><p>(Test \(Id ([0-9]*)\) successfully added.)</p>', req.text)
            if ret is not None:
                info = ret.group(1)
                testId = ret.group(2)
            else:
                info = re.search(r'<!-- cmd -->(.*)<!-- cmd -->', req.text).group(1)
                testId = None
        except Exception as e:
            print(e)
            info = 'ERROR: Failed to contact the FlockLab API!'
            testId = None

        return testId, info

    def createTestWithInfo(self, xmlPath):
        '''Create a FlockLab test by using the web api and return a string with info about test start and ID
        Args:
            xmlPath: path to FlockLab config xml file
        Returns:
            info: Test ID and start date or info about failure
        '''
        testId, info = self.createTest(xmlPath)
        if not testId:
            ret = 'ERROR: Creation of test failed!\n{}'.format(info)
        else:
            try:
                testinfo = self.getTestInfo(testId=testId)
                ret = 'Test {} was successfully added and is scheduled to start at {} (local time)'.format(testId, datetime.datetime.fromtimestamp((testinfo['start_planned'])))
            except Exception as e:
                ret = 'Test {} was successfully added. (Test start time could not be fetched.)'.format(testId)
        return ret

    def abortTest(self, testId):
        '''Abort a FlockLab test if it is running.
        Args:
            testId: ID of the test which should be aborted
        Returns:
            Result of abortion as string
        '''
        creds = self.getCredentials()

        try:
            files = {
                'username': (None, creds['username']),
                'password': (None, creds['password']),
                'removeit': (None, 'Remove test'),
                'testid': (None, '{}'.format(testId)),
            }
            req = requests.post(self.apiBaseAddr + 'test_abort.php', files=files, verify=self.sslVerify)
            reg = re.search('<!-- cmd --><p>(The test has been aborted.)</p><!-- cmd -->', req.text)
            if reg is not None:
                return reg.group(1)
            else:
                return re.search(r'<!-- cmd -->(.*)<!-- cmd -->', req.text).group(1)
        except Exception as e:
            print(e)
            print("ERROR: Failed to contact the FlockLab API!")

    def deleteTest(self, testId):
        '''Delete a FlockLab test.
        Args:
            testId: ID of the test which should be delted
        Returns:
            Result of deletion as string
        '''
        creds = self.getCredentials()

        try:
            files = {
                'username': (None, creds['username']),
                'password': (None, creds['password']),
                'removeit': (None, 'Remove test'),
                'testid': (None, '{}'.format(testId)),
            }
            req = requests.post(self.apiBaseAddr + 'test_delete.php', files=files, verify=self.sslVerify)
            reg = re.search('<!-- cmd --><p>(The test has been removed.)</p><!-- cmd -->', req.text)
            if reg is not None:
                return reg.group(1)
            else:
                return re.search(r'<!-- cmd -->(.*)<!-- cmd -->', req.text).group(1)
        except Exception as e:
            print(e)
            print("ERROR: Failed to contact the FlockLab API!")

    def getResults(self, testId, outDir='./', extract=True):
        '''Download FlockLab test results via https.
        Args:
            testId: ID of the test which should be downloaded
            outDir: Download directory (default: current working path)
        Returns:
            Success of download as string.
        '''
        creds = self.getCredentials()
        req = None

        # download test result archive
        print("downloading ...")
        try:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            data = {
                  'testid': '{}'.format(testId),
                  'query': 'get',
                  'username': creds['username'],
                  'password': creds['password']
            }
            req = requests.post(self.apiBaseAddr + 'result_download_archive.php', headers=headers, data=data, verify=self.sslVerify)
        except requests.exceptions.RequestException as e:
            print(e)
            print("ERROR: Failed to contact the FlockLab API!")

        if req:
            if req.status_code != 200:
                raise FlocklabError('Downloading testresults failed (status code: {})'.format(req.status_code))

            # encoding is required to decode when accessing data with req.text -> currently guessing is ok since it is only required if content-type is text/html
            # req.encoding = 'utf-8' # explicitly set expected encoding since automatic detection ("encoding will be guessed using chardet") is very slow, especially with large files!
            if 'text/html' in req.headers['content-type']: # NOTE: full contenty-type string is usually 'text/html; charset=UTF-8'
                output = json.loads(req.text)["output"]
                raise FlocklabError('FlockLab API Error: {}'.format(output))
            elif 'application/x-gzip' in req.headers['content-type']:
                with open(os.path.join(outDir, 'flocklab_testresults_{}.tar.gz'.format(testId)), 'wb') as f:
                    f.write(req.content)
            else:
                raise FlocklabError('Server response contains unexpected response content-type: {}'.format(req.headers['content-type']))

            if extract:
                print("extracting archive ...")
                with tarfile.open(os.path.join(outDir, 'flocklab_testresults_{}.tar.gz'.format(testId))) as tar:
                    tar.extractall(path=outDir)
                return 'Successfully downloaded & extracted: flocklab_testresults_{}.tar.gz & {}'.format(testId, testId)
            else:
                return 'Successfully downloaded flocklab_testresults_{}.tar.gz'.format(testId)

    def getTestInfo(self, testId):
        '''Get information for an existing FlockLab test.
        Args:
            testId: ID of the test which should be delted
        Returns:
            Test info as a dict.
        '''
        creds = self.getCredentials()

        # get observer list from server
        try:
            files = {
                'username': (None, creds['username']),
                'password': (None, creds['password']),
                'q': (None, 'testinfo'),
                'id': (None, testId),
            }
            req = requests.post(self.apiBaseAddr + 'api.php', files=files, verify=self.sslVerify)
            output = json.loads(req.text)["output"]
            # convert timestamps to int
            output['start_planned'] = Flocklab.apiStr2int(output['start_planned'])
            output['start'] = Flocklab.apiStr2int(output['start'])
            output['end_planned'] = Flocklab.apiStr2int(output['end_planned'])
            output['end'] = Flocklab.apiStr2int(output['end'])
        except Exception as e:
            print(e)
            print("ERROR: Failed to fetch test info from FlockLab API!")
            output = None

        return output

    def getObsIds(self, platform='dpp2lora'):
        '''Get currently available observer IDs (depends on user role!)
        Args:
            platform: Flocklab platform
        Returns:
            List of accessible FlockLab observer IDs
        '''
        creds = self.getCredentials()

        # get observer list from server
        try:
            files = {
                'username': (None, creds['username']),
                'password': (None, creds['password']),
                'q': (None, 'obs'),
                'platform': (None, platform),
            }
            req = requests.post(self.apiBaseAddr + 'api.php', files=files, verify=self.sslVerify)
            output = json.loads(req.text)["output"]
            if len(output) > 0:
                obsList = output.split(' ')
                obsList = [int(e) for e in obsList]
                return obsList
            else:
                return []
        except Exception as e:
            print(e)
            print("ERROR: Failed to fetch active observers from FlockLab API!")

    def getPlatforms(self, username=None, password=None):
        '''Get currently available observer IDs (depends on user role!)
        Args:
            username: FlockLab username (useful for testing flocklab authentication info)
            password: Flocklab password (useful for testing flocklab authentication info)
        Returns:
            List of available platforms on FlockLab
        '''
        if username is None or password is None:
            creds = self.getCredentials()
        else:
            creds = {'username': username, 'password': password}

        # get observer list from server
        try:
            files = {
                'username': (None, creds['username']),
                'password': (None, creds['password']),
                'q': (None, 'platform'),
            }
            req = requests.post(self.apiBaseAddr + 'api.php', files=files, verify=self.sslVerify)
            platformList = json.loads(req.text)["output"].split(' ')
            return platformList
        except Exception as e:
            if username is None and password is None:
                # print(e)
                print("ERROR: Failed to fetch platforms from FlockLab API!")
            return None


    @staticmethod
    def serial2Df(serialFile, error='replace', fileName='serial.csv'):
        '''Read a serial trace from a flocklab test result and convert it to a pandas dataframe.
        Args:
            serialFile: File path or file pointer (binary read mode, 'rb') to serial logging file, or path to FockLab result directory containing the serial logging file
            error:      How to handle binary to string decoding errors
            fileName:   File name of the FlockLab serial logging file; used in case a string pointing to a test result directory is passed to serialFile (default: serial.csv)
        Returns:
            serial log as pandas dataframe
        '''
        f = None
        if type(serialFile)==str:
            if os.path.isdir(serialFile):
                serialFile = os.path.join(serialFile, fileName)
            if not os.path.isfile(serialFile):
                raise Exception('The file does not exist: {}'.format(serialFile))
            f = open(serialFile, 'rb')
        else:
            f = serialFile

        buf = f.read()
        # replace carriage returns (e.g. contained in corrupted radio messages) as they are interpreted as newline by readlines(), flocklab serial output does never contain carriage return for line break as flocklab converts all CRLF into LF (\r\n -> \n)
        buf = buf.replace(bytes(u'\r', encoding='utf8'), bytes(u'', encoding='utf8')) # removes all carriage returns ('\r' or u'\u000d')
        f2 = io.StringIO(buf.decode(encoding='utf-8', errors='replace'))
        # read data into dataframe
        ll = []
        header_processed = False
        for line in f2.readlines():
            if not header_processed:
                cols = line.rstrip().split(',')
                assert len(cols) == 5
                header_processed = True
                continue
            parts = line.rstrip().split(',')
            if len(parts) >= 5:
                ll.append(OrderedDict([
                  (cols[0], float(parts[0])),          # timestamp
                  (cols[1], int(parts[1])),            # observer_id
                  (cols[2], int(parts[2])),            # node_id
                  (cols[3], parts[3]),                 # direction
                  (cols[4], ','.join(parts[4:])),      # output
                ]))
            else:
                raise Exception('ERROR: line does not contain enough columns: {}'.format(line))

        if type(serialFile)==str:
            f.close()

        df = pd.DataFrame.from_dict(ll)
        df.columns
        return df

    @staticmethod
    def getCustomField(testConfigFile, testConfigFileName='testconfig.xml'):
        '''Tries to read info from xml field `custom`.
        Args:
            testConfigFile:      File path as string or file pointer of the FlockLab test config file, or file path (string) of a FlockLab test result directory
            testConfigFileName:  File name of the FlockLab test config file; used in case a string pointing to a test result directory is passed to testConfigFile (default: testconfig.xml)
        Returns:
            Content of custom field in testconfig.xml as string.
        '''
        if type(testConfigFile)==str and os.path.isdir(testConfigFile):
            testConfigFile = os.path.join(testConfigFile, testConfigFileName)

        try:
            # read custom field in testconfig xml
            ns = {'dummy': 'http://www.flocklab.ethz.ch'}
            tree = et.parse(testConfigFile)
            ret = tree.findall('.//dummy:custom', namespaces=ns)
            assert len(ret) == 1
        except Exception as e:
            return None
        else:
            return ret[0].text

    @staticmethod
    def getDtAddrToVarMap(testConfigFile, testConfigFileName='testconfig.xml'):
        '''Tries to read datatrace specific info from xml field `custom`. Always returns a dict (even if empty).
        Args:
            testConfigFile:      File path as string or file pointer of the FlockLab test config file, or file path (string) of a FlockLab test result directory
            testConfigFileName:  File name of the FlockLab test config file; used in case a string pointing to a test result directory is passed to testConfigFile (default: testconfig.xml)
        Returns:
            Dictionary with mapping of datatrace addresses to variables
        '''
        try:
            custom = Flocklab.getCustomField(testConfigFile, testConfigFileName)
            d = json.loads(custom)
            d = d['datatrace']['var_to_addr_map']
            # reverse dict
            d = {v:k for k,v in d.items()}
        except Exception as e:
            # we ignore any error since info is not essential, nevertheless it is important to return a dict() such that the mapping does not fail
            return dict()
        else:
            return d

    @staticmethod
    def structSizeMap(numBytes):
        if numBytes == 1: return 'B'
        elif numBytes == 2: return 'H'
        elif numBytes == 4: return 'I'
        elif numBytes == 8: return 'Q'
        else: raise Exception('Undefined number of bytes!')

    @staticmethod
    def getSymbolAddress(elfPath, symbName):
        '''Get the address of the symbol with name symbName from ELF file elfPath.
        Args:
            elfPath:  Path to the elf file
            symbName: Name of the symbol
        Returns:
            Address
        '''
        with open(elfPath, 'rb') as f:
            elf = ELFFile(f)
            symtab = elf.get_section_by_name('.symtab')
            if not symtab:
                raise Exception('ELF file does not contain a symbol table!')
            sym = symtab.get_symbol_by_name(varname)

            if sym is None or len(sym) == 0:
                raise Exception('Symbol "{}" not found!'.format(symbName))
            elif len(sym) > 1:
                raise Exception('Found multiple entries for Symbol "{}"!'.format(symbName))
            return sym[0]['st_value']

    @staticmethod
    def getSymbolFileOffsetAndSize(elfPath, symbName):
        '''Get the file offset (in bytes) and the size of the symbol with name symbName from ELF file elfPath.
        Args:
            elfPath:  Path to the elf file
            symbName: Name of the symbol
        Returns:
            File offset (in bytes)
        '''
        fileOffset = None
        symbSize = None

        with open(elfPath, 'rb') as f:
            elf = ELFFile(f)

            # read symbol table
            symtab = elf.get_section_by_name('.symtab')
            if not symtab:
                raise Exception('ELF file does not contain a symbol table!')

            # get symbol & symbol size
            symList = symtab.get_symbol_by_name(symbName)
            if not symList:
                raise Exception('Symbol "{}" not found!'.format(symbName))
            sym = symList[0]
            symbAddr = sym['st_value']
            symbSize = sym['st_size']

            # get file offset
            fileOffset = next(elf.address_offsets(symbAddr), None)

            if not fileOffset:
                raise Exception('Could not determine file offset!')

        return fileOffset, symbSize

    @staticmethod
    def readSymbolValue(elfPath, symbName, signed=False):
        '''Read value of symbol symbName from elf file elfPath.
        Args:
            elfPath:  Path to the elf file in which the symbol will be replaced
            symbName: Name of the symbol
            signed:   If True, the symbol is assumed to be a signed integer, otherwise the symbol is assumed to be an unsigned integer (default: False)
        Returns:
            Value of symbol
        '''
        value = None

        with open(elfPath, 'rb') as f:
            elf = ELFFile(f)
            fileOffset, symbSize = Flocklab.getSymbolFileOffsetAndSize(elfPath, symbName)
            elf.stream.seek(fileOffset)
            if signed:
                value = struct.unpack(Flocklab.structSizeMap(symbSize).lower(), elf.stream.read(symbSize))[0]
            else:
                value = struct.unpack(Flocklab.structSizeMap(symbSize), elf.stream.read(symbSize))[0]

        return value

    @staticmethod
    def writeSymbolValue(elfPath, symbName, symbReplace, signed=False):
        '''Searches symbol symbName in ELF file elfPath and replaces its value with symbReplace.
        Args:
            elfPath:        Path to the elf file in which the symbol will be replaced
            symbName:       Name of the symbol whose value will be replaced
            symbReplace:    Replacement value (int)
            signed:         If True, the symbol is assumed to be a signed integer, otherwise the symbol is assumed to be an unsigned integer (default: False)
        '''
        symbFileOffset, symbSize = Flocklab.getSymbolFileOffsetAndSize(elfPath, symbName)

        with open(elfPath, 'rb+') as f:
            f.seek(symbFileOffset)
            if signed:
                replaceBytes = struct.pack(Flocklab.structSizeMap(symbSize).lower(), symbReplace)
            else:
                replaceBytes = struct.pack(Flocklab.structSizeMap(symbSize), symbReplace)
            f.write(replaceBytes)
            f.close()


################################################################################

if __name__ == "__main__":
    pass
