#!/usr/bin/env python3
"""
Copyright (c) 2020, ETH Zurich, Computer Engineering Group (TEC)
"""

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
import appdirs
from getpass import getpass

################################################################################


class FlocklabError(Exception):
    """Exception raised for errors from flocklab

    Attributes:
        message -- explanation of the error
    """

    def __init__(self,  message):
        self.message = message


class Flocklab:
    def __init__(self):
        self.apiBaseAddr = 'https://flocklab.ethz.ch/user/'
        self.sslVerify = True

    def setApiBaseAddr(self, addr):
        self.apiBaseAddr = addr

    @staticmethod
    def getCredentials():
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
                if Flocklab.getPlatforms(username=usr, password=pwd) is not None:
                    with open(flConfigPath, 'w') as f:
                        f.write('USER={}\n'.format(usr))
                        f.write('PASSWORD={}\n'.format(pwd))
                    print("FlockLab authentication file successfully created!")
                else:
                    print("WARNING: FlockLab authentication information seems wrong. No .flocklabauth file created!")

        try:
            with open(flConfigPath, "r") as configFile:
                text = configFile.read()
                username = re.search(r'USER=(.+)', text).group(1)
                password = re.search(r'PASSWORD=(.+)', text).group(1)
                return {'username': username, 'password': password}
        except:
            print("Failed to read flocklab auth info from %s \n"
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
            print("Failed to read and convert image!")

    def xmlValidate(self, xmlPath):
        '''Validate FlockLab config xml by using the web api
        Args:
            xmlPath: path to FlockLab config xml file
        Returns:
            Result of validation as string
        '''
        creds = Flocklab.getCredentials()

        try:
            files = {
                'username': (None, creds['username']),
                'password': (None, creds['password']),
                'first': (None, 'no'),
                'xmlfile': (os.path.basename(xmlPath), open(xmlPath, 'rb').read(), 'text/xml', {}),
            }
            req = requests.post(self.apiBaseAddr + 'xmlvalidate.php', files=files, verify=self.sslVerify)
            if '<p>The file validated correctly.</p>' in req.text:
                return 'The file validated correctly.'
            else:
                return re.search(r'<!-- cmd -->(.*)<!-- cmd -->', req.text).group(1)
        except Exception as e:
            print(e)
            print("Failed to contact the FlockLab API!")

    def createTest(self, xmlPath):
        '''Create a FlockLab test by using the web api
        Args:
            xmlPath: path to FlockLab config xml file
        Returns:
            Result of test creation as string
        '''
        creds = Flocklab.getCredentials()

        try:
            files = {
                'username': (None, creds['username']),
                'password': (None, creds['password']),
                'first': (None, 'no'),
                'xmlfile': (os.path.basename(xmlPath), open(xmlPath, 'rb').read(), 'text/xml', {}),
            }
            req = requests.post(self.apiBaseAddr + 'newtest.php', files=files, verify=self.sslVerify)
            # FIXME: success is not correctly detected
            ret = re.search('<!-- cmd --><p>(Test (Id [0-9]*) successfully added.)</p>', req.text)
            if ret is not None:
                print('success')
                return ret.group(1)
            else:
                return re.search(r'<!-- cmd -->(.*)<!-- cmd -->', req.text).group(1)
        except Exception as e:
            print(e)
            print("Failed to contact the FlockLab API!")

    def abortTest(self, testId):
        '''Abort a FlockLab test if it is running.
        Args:
            testId: ID of the test which should be aborted
        Returns:
            Result of abortion as string
        '''
        creds = Flocklab.getCredentials()

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
            print("Failed to contact the FlockLab API!")

    def deleteTest(self, testId):
        '''Delete a FlockLab test.
        Args:
            testId: ID of the test which should be delted
        Returns:
            Result of deletion as string
        '''
        creds = Flocklab.getCredentials()

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
            print("Failed to contact the FlockLab API!")

    def getResults(self, testId):
        '''Download FlockLab test results via https.
        Args:
            testId: ID of the test which should be downloaded
        Returns:
            Success of download as string.
        '''
        creds = Flocklab.getCredentials()

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
            if req.status_code == 200:
                if '"error"' in req.text:
                    output = json.loads(req.text)["output"]
                    raise FlocklabError('Failed: {}'.format(output))
                else:
                    with open('flocklab_testresults_{}.tar.gz'.format(testId), 'wb') as f:
                        f.write(req.content)
                    with tarfile.open('flocklab_testresults_{}.tar.gz'.format(testId)) as tar:
                        tar.extractall()
                    return 'Successfully downloaded & extracted: flocklab_testresults_{}.tar.gz & {}'.format(testId, testId)
            else:
                raise FlocklabError('Downloading testresults failed (status code: {})'.format(req.status_code))
        except requests.exceptions.RequestException as e:
            print(e)
            print("Failed to contact the FlockLab API!")

    def getObsIds(self, platform='dpp2lora'):
        '''Get currently available observer IDs (depends on user role!)
        Args:
            platform: Flocklab platform
        Returns:
            List of accessible FlockLab observer IDs
        '''
        creds = Flocklab.getCredentials()

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
            print("Failed to fetch active observers from FlockLab API!")

    def getPlatforms(self, username=None, password=None):
        '''Get currently available observer IDs (depends on user role!)
        Args:
            username: FlockLab username (useful for testing flocklab authentication info)
            password: Flocklab password (useful for testing flocklab authentication info)
        Returns:
            List of available platforms on FlockLab
        '''
        if username is None or password is None:
            creds = Flocklab.getCredentials()
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
            print(e)
            print("Failed to fetch active observers from FlockLab API!")
            return None



    @staticmethod
    def serial2Df(serialPath, error='replace', serialFilename='serial.csv'):
        '''Read a serial trace from a flocklab test result and convert it to a pandas dataframe.
        Args:
            serialPath: path to serial trace result file (or flocklab result directory)
        Returns:
            serial log as pandas dataframe
        '''
        if os.path.isdir(serialPath):
            serialFilename = os.path.join(serialPath, serialFilename)
        else:
            raise RuntimeError('The provided path is not valid: %s'%serialPath)

        if not os.path.isfile(serialFilename):
            raise RuntimeError('The file not exist : %s'%serialFilename)

        with open(serialFilename, 'r', encoding='utf-8', errors='replace') as f:
            ll = []
            for line in f.readlines():
                print(line)
                if line[0] == '#': # special processing of header
                    cols = line[2:].rstrip().split(',')
                    assert len(cols) == 5
                    continue
                parts = line.rstrip().split(',')
                if len(parts) > 0:
                    ll.append(OrderedDict([
                      (cols[0], parts[0]),                  # timestamp
                      (cols[1], int(parts[1])),             # observer_id
                      (cols[2], int(parts[2])),            # node_id
                      (cols[3], parts[3]),                 # direction
                      (cols[4], ','.join(parts[4:])),      # output
                    ]))
        df = pd.DataFrame.from_dict(ll)
        df.columns
        return df


################################################################################

if __name__ == "__main__":
    pass
