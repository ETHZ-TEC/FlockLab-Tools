#!/usr/bin/env python3

import numpy as np
import pandas as pd
from collections import Counter, OrderedDict
import itertools
import datetime
import os

from . import Flocklab



###############################################################################

class FlocklabXmlConfig():
    xmlStart = \
    '''<?xml version="1.0" encoding="UTF-8"?>

    <testConf xmlns="http://www.flocklab.ethz.ch" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.flocklab.ethz.ch xml/flocklab.xsd">
    '''

    xmlEnd = \
    '''
    </testConf>
    '''

    def __init__(self):
        self.generalConf = GeneralConf()
        self.configList = [self.generalConf]

    def generateXml(self, xmlPath):
        '''Generate FlockLab xml config for runnnig a test on FlockLab. Output file is written to 'out.xml'.
        Args:
            xmlPath: path to file where xml config is written to
        Returns:
            (-)
        '''

        # TODO: Set obsIds for elements which do not have obsIds specified (autocomplete test config)
        # TODO: make sure that at least one image is provided in any of the imageConf


        allNodes = []
        for config in self.configList:
            if type(config) == TargetConf:
                allNodes += config.obsIds
                print('== {}: {} =='.format(type(config).__name__, config.imageId))
                print('Selected nodes: {}'.format(config.obsIds))
            elif type(config) == ImageConf:
                print('== {}: {} =='.format(type(config).__name__, config.imageId))
                if config.imagePath == '':
                    print('Image last modified:- (data empty)')
                else:
                    print('Image last modified: {}'.format(datetime.datetime.fromtimestamp(os.path.getmtime(config.imagePath))))

        print('Used nodes (all): {}'.format(list(set(allNodes))))


        with open(xmlPath, "w") as f:
            f.write(FlocklabXmlConfig.xmlStart)

            for config in self.configList:
                print(type(config))
                f.write(config.config2Str())

            f.write(FlocklabXmlConfig.xmlEnd)

class GeneralConf():
    # name, description, duration
    generalConf = \
    '''
    <!-- General configuration -->
    <generalConf>
    <name>{name}</name>
    <description>{description}</description>
    <scheduleAsap>
        <durationSecs>{duration}</durationSecs>
    </scheduleAsap>
    <emailResults>no</emailResults>
    </generalConf>
    '''

    def __init__(self):
        self.name = None
        self.description = None
        self.duration = None

    def config2Str(self):
        assert self.name is not None
        assert self.description is not None
        assert self.duration is not None
        return GeneralConf.generalConf.format(
            name=self.name,
            description=self.description,
            duration=self.duration
        )

class TargetConf():
    # obsIds, imageId
    targetConf = \
    '''
    <!-- Target configuration -->
    <targetConf>
    <obsIds>{obsIds}</obsIds>
    <voltage>{voltage}</voltage>
    <embeddedImageId>{imageId}</embeddedImageId>
    </targetConf>
    '''

    def __init__(self):
        self.obsIds = None
        self.voltage = 3.3
        self.imageId = None

    def config2Str(self):
        assert self.obsIds is not None
        assert self.voltage is not None
        assert self.imageId is not None
        return TargetConf.targetConf.format(
            obsIds=Flocklab.formatObsIds(self.obsIds),
            imageId=self.imageId,
            voltage=self.voltage
        )

class GpioTracingConf():
    # obsIds
    gpioTracingConf = \
    '''
    <!-- GPIO Tracing Service configuration -->
    <gpioTracingConf>
    <obsIds>{obsIds}</obsIds>
    <pinConf>
        <pin>INT1</pin>
        <edge>both</edge>
        <mode>continuous</mode>
    </pinConf>
    <pinConf>
        <pin>INT2</pin>
        <edge>both</edge>
        <mode>continuous</mode>
    </pinConf>
    <pinConf>
        <pin>LED1</pin>
        <edge>both</edge>
        <mode>continuous</mode>
    </pinConf>
    <pinConf>
        <pin>LED2</pin>
        <edge>both</edge>
        <mode>continuous</mode>
    </pinConf>
    <pinConf>
        <pin>LED3</pin>
        <edge>both</edge>
        <mode>continuous</mode>
    </pinConf>
    </gpioTracingConf>
    '''

    def __init__(self):
        self.obsIds = None

    def config2Str(self):
        assert self.obsIds is not None
        return GpioTracingConf.gpioTracingConf.format(
            obsIds=Flocklab.formatObsIds(self.obsIds),
        )

class GpioActuationConf():
    gpioActuationConf = \
    '''
    <!-- GPIO Actuation Service configuration -->
    <gpioActuationConf>
        <obsIds>{obsIds}</obsIds>
        <pinConf>
            <pin>SIG1</pin>
            <level>{levelSig1}</level>
            <relativeTime>
                <offsetSecs>0</offsetSecs>
            </relativeTime>
        </pinConf>
        <pinConf>
            <pin>SIG2</pin>
            <level>{levelSig2}</level>
            <relativeTime>
                <offsetSecs>0</offsetSecs>
            </relativeTime>
        </pinConf>
    </gpioActuationConf>
    '''

    def __init__(self):
        self.obsIds = None
        self.levelSig1 = None
        self.levelSig2 = None

    def config2Str(self):
        assert self.obsIds is not None
        assert self.levelSig1 is not None
        assert self.levelSig2 is not None
        return GpioActuationConf.gpioActuationConf.format(
            obsIds=Flocklab.formatObsIds(self.obsIds),
            levelSig1=self.levelSig1,
            levelSig2=self.levelSig2,
        )

class SerialConf():
    # obsIds
    serialConf = \
    '''
    <!-- Serial Service configuration -->
    <serialConf>
    <obsIds>{obsIds}</obsIds>
        <port>serial</port>
        <baudrate>115200</baudrate>
        <mode>ascii</mode>
        <remoteIp>0.0.0.0</remoteIp>
    </serialConf>
    '''

    def __init__(self):
        self.obsIds = None

    def config2Str(self):
        assert self.obsIds is not None
        return SerialConf.serialConf.format(
            obsIds=Flocklab.formatObsIds(self.obsIds),
        )


class PowerProfilingConf():
    # obsIds, duration
    powerProfilingConf = \
    '''
    <!-- Power Profiling Service configuration -->
    <powerProfilingConf>
        <obsIds>{obsIds}</obsIds>
        <profConf>
            <durationMillisecs>{duration}</durationMillisecs>
            <relativeTime>
                <offsetSecs>0</offsetSecs>
                <offsetMicrosecs>0</offsetMicrosecs>
            </relativeTime>
            <samplingDivider>56</samplingDivider>
        </profConf>
    </powerProfilingConf>
    '''

    def __init__(self):
        self.obsIds = None
        self.duration = None

    def config2Str(self):
        assert self.obsIds is not None
        assert self.duration is not None
        return PowerProfilingConf.powerProfilingConf.format(
            obsIds=Flocklab.formatObsIds(self.obsIds),
            duration=self.duration*1000, # convert seconds to milliseconds
        )

class ImageConf():
    # imageId, imageName, imageDescription, imagePlatform, imageString
    imageConf = \
    '''
    <!-- Image configuration -->
    <imageConf>
        <embeddedImageId>{imageId}</embeddedImageId>
        <name>{imageName}</name>
        <description>{imageDescription}</description>
        <platform>{imagePlatform}</platform>
        <os>other</os>
        <data>
{imageString}
        </data>
    </imageConf>
    '''

    def __init__(self):
        self.imageId = None
        self.imageName = None
        self.imageDescription = None
        self.imagePlatform = None
        self.imagePath = None

    def config2Str(self):
        assert self.imageId is not None
        assert self.imageName is not None
        assert self.imageDescription is not None
        assert self.imagePlatform is not None
        assert self.imagePath is not None

        if self.imagePath == '':
            '''No image provided -> flocklab will take image of other image conf'''
            self.imageString = ''
        else:
            '''Read image from file'''
            self.imageString = Flocklab.getImageAsBase64(self.imagePath)


        return ImageConf.imageConf.format(
            imageId=self.imageId,
            imageName=self.imageName,
            imageDescription=self.imageDescription,
            imagePlatform=self.imagePlatform,
            imageString=self.imageString,
        )

###############################################################################

if __name__ == "__main__":
    pass
