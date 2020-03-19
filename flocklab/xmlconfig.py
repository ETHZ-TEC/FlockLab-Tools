#!/usr/bin/env python3
"""
Copyright (c) 2020, ETH Zurich, Computer Engineering Group (TEC)
"""

import numpy as np
import pandas as pd
from collections import Counter, OrderedDict
import itertools
import datetime
import os
from xml.etree import ElementTree as et

from . import Flocklab



###############################################################################

class FlocklabXmlConfig():
    def xmlPrettify(elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                FlocklabXmlConfig.xmlPrettify(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def addSubElement(parent, tag, text=None):
        e = et.SubElement(parent, tag)
        if text is not None:
            e.text = text
        return e

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

        x = et.Element('testConf')
        x.set('xmlns', "http://www.flocklab.ethz.ch")
        x.set('xmlns:xsi', "http://www.w3.org/2001/XMLSchema-instance")
        x.set('xsi:schemaLocation', "http://www.flocklab.ethz.ch xml/flocklab.xsd")


        # TODO: Set obsIds for elements which do not have obsIds specified (autocomplete test config)
        # TODO: make sure that at least one image is provided in any of the imageConf

        # print info and do sanity checks
        allNodes = []
        for config in self.configList:
            if type(config) == TargetConf:
                allNodes += config.obsIds
                print('== {}: {} =='.format(type(config).__name__, config.embeddedImageId))
                print('Selected nodes: {}'.format(config.obsIds))
            elif type(config) == ImageConf:
                print('== {}: {} =='.format(type(config).__name__, config.embeddedImageId))
                if config.imagePath == '':
                    print('Image last modified:- (data empty)')
                else:
                    print('Image last modified: {}'.format(datetime.datetime.fromtimestamp(os.path.getmtime(config.imagePath))))

        print('Used nodes (all): {}'.format(list(set(allNodes))))

        # concatenate config sections
        for config in self.configList:
            print(type(config).__name__)
            x = config.config2Et(x)

        # generate formatted xml
        type(self).xmlPrettify(x)
        xml = et.tostring(x, encoding="unicode")

        # write FlockLab xml config file
        with open(xmlPath, "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(xml)

class GeneralConf():
    def __init__(self, name=None, description=None, custom=None, duration=None, startTime=None, emailResults=None):
        self.name = name
        self.description = description
        self.custom = custom               # must be of type str
        self.duration = duration           # in secs
        self.startTime = startTime         # datetime in UTC time; if None -> test will be scheduled using asap
        self.emailResults = emailResults   # boolean, will be converted

    def config2Et(self, x):
        if self.name is None:
            raise Exception('ERROR: name of GeneralConf needs to be set!')
        if self.duration is None:
            raise Exception('ERROR: ndurationame of GeneralConf needs to be set!')

        x.append(et.Comment('General configuration'))
        gc = FlocklabXmlConfig.addSubElement(x, 'generalConf')
        FlocklabXmlConfig.addSubElement(gc, 'name', text=self.name)
        if self.description is not None:
            FlocklabXmlConfig.addSubElement(gc, 'description', text=self.description)
        if self.custom is not None:
            if type(self.custom) != str:
                raise Exception('ERROR: type of custom of generalConf must be of type str!')
            FlocklabXmlConfig.addSubElement(gc, 'custom', text=self.custom)
        if self.startTime is None:
            scheduleAsap = FlocklabXmlConfig.addSubElement(gc, 'scheduleAsap')
            FlocklabXmlConfig.addSubElement(scheduleAsap, 'durationSecs', text='{}'.format(self.duration))
        else:
            if type(self.startTime) != datetime.datetime:
                raise Exception('ERROR: startTime of generalConf must be of type datetime.datetime!')
            endTime = self.startTime + datetime.timedelta(seconds=self.duration)
            scheduleAbsolute = FlocklabXmlConfig.addSubElement(gc, 'scheduleAbsolute')
            # format YYYY-mm-ddTHH:MM:SSZ
            format = "%Y-%m-%dT%H:%M:%SZ"
            FlocklabXmlConfig.addSubElement(scheduleAbsolute, 'start', text=self.startTime.strftime(format))
            FlocklabXmlConfig.addSubElement(scheduleAbsolute, 'end', text=endTime.strftime(format))
        if self.emailResults is not None:
            FlocklabXmlConfig.addSubElement(gc, 'emailResults', text='yes' if self.emailResults else 'no')
        return x

class TargetConf():
    def __init__(self, obsIds=None, targetIds=None, voltage=3.3, dbImagId=None, embeddedImageId=None):
        self.obsIds = obsIds
        self.targetIds = targetIds
        self.voltage = voltage
        self.dbImagId = dbImagId
        self.embeddedImageId = embeddedImageId

    def config2Et(self, x):
        if self.obsIds is None:
            raise Exception('ERROR: obsIds of TargetConf needs to be set!')
        if self.dbImagId is None and self.embeddedImageId is None:
            raise Exception('ERROR: Either dbImagId or embeddedImageId of TargetConf needs to be set!')
        if self.dbImagId is not None and self.embeddedImageId is not None:
            raise Exception('ERROR: Only one image can be specified per TargetConf object (dbImagId OR embeddedImageId)!')

        x.append(et.Comment('Target configuration'))
        tc = FlocklabXmlConfig.addSubElement(x, 'targetConf')
        FlocklabXmlConfig.addSubElement(tc, 'obsIds', text=Flocklab.formatObsIds(self.obsIds))
        if self.targetIds is not None:
            FlocklabXmlConfig.addSubElement(tc, 'targetIds', text=Flocklab.formatObsIds(self.targetIds))
        if self.voltage is not None:
            FlocklabXmlConfig.addSubElement(tc, 'voltage', text='{:.1f}'.format(self.voltage))
        if self.dbImagId is not None:
            FlocklabXmlConfig.addSubElement(tc, 'dbImageId', text=self.dbImageId)
        if self.embeddedImageId is not None:
            FlocklabXmlConfig.addSubElement(tc, 'embeddedImageId', text=self.embeddedImageId)
        return x

class SerialConf():
    def __init__(self, obsIds=None, port='serial', baudrate=115200, remoteIp=None):
        self.obsIds = obsIds
        self.port = port
        self.baudrate = baudrate
        self.remoteIp = remoteIp

    def config2Et(self, x):
        if self.obsIds is None:
            raise Exception('ERROR: obsIds of SerialConf needs to be set!')
        if self.remoteIp is None:
            self.remoteIp = '0.0.0.0' # useless for forwarding but prevents problems with gpiotracing if by default an IPv6 address is set

        x.append(et.Comment('Serial Service configuration'))
        sc = FlocklabXmlConfig.addSubElement(x, 'serialConf')
        FlocklabXmlConfig.addSubElement(sc, 'obsIds', text=Flocklab.formatObsIds(self.obsIds))
        if self.port is not None:
            FlocklabXmlConfig.addSubElement(sc, 'port', text='{}'.format(self.port))
        if self.baudrate is not None:
            FlocklabXmlConfig.addSubElement(sc, 'baudrate', text='{}'.format(self.baudrate))
        FlocklabXmlConfig.addSubElement(sc, 'remoteIp', text=self.remoteIp)
        return x

class GpioTracingConf():
    def __init__(self, obsIds=None, pinList=['INT1', 'INT2', 'LED1', 'LED2', 'LED3']):
        self.obsIds = obsIds
        self.pinList = pinList

    def config2Et(self, x):
        if self.obsIds is None:
            raise Exception('ERROR: obsIds of GpioTracingConf needs to be set!')
        if self.pinList is None:
            raise Exception('ERROR: pinList of GpioTracingConf needs to be set!')

        x.append(et.Comment('Target configuration'))
        gtc = FlocklabXmlConfig.addSubElement(x, 'gpioTracingConf')
        FlocklabXmlConfig.addSubElement(gtc, 'obsIds', text=Flocklab.formatObsIds(self.obsIds))
        FlocklabXmlConfig.addSubElement(gtc, 'pins', text=' '.join(self.pinList))
        return x

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

    def __init__(self, obsIds=None, levelSig1=None, levelSig2=None):
        self.obsIds = obsIds
        self.levelSig1 = levelSig1
        self.levelSig2 = levelSig2

    def config2Et(self, x):
        # TODO
        return x

class ImageConf():
    def __init__(self, embeddedImageId=None, imageName=None, imageDescription=None, imagePlatform=None, imagePath=None, core=None):
        self.embeddedImageId = embeddedImageId
        self.name = imageName
        self.description = imageDescription
        self.platform = imagePlatform
        self.imagePath = imagePath
        self.core = core

    def config2Et(self, x):
        if self.embeddedImageId is None:
            raise Exception('ERROR: imageId of ImageConf needs to be set!')
        if self.name is None:
            raise Exception('ERROR: imageName of ImageConf needs to be set!')
        if self.platform is None:
            raise Exception('ERROR: imagePlatform of ImageConf needs to be set!')
        if self.imagePath is None:
            raise Exception('ERROR: imagePath of ImageConf needs to be set!')

        if self.imagePath == '':
            # No image provided -> flocklab will take image of other image conf
            self.imageString = ''
        else:
            # Read image from file
            self.imageString = Flocklab.getImageAsBase64(self.imagePath)

        x.append(et.Comment('Image configuration'))
        ic = FlocklabXmlConfig.addSubElement(x, 'imageConf')
        FlocklabXmlConfig.addSubElement(ic, 'embeddedImageId', text='{}'.format(self.embeddedImageId))
        FlocklabXmlConfig.addSubElement(ic, 'name', text='{}'.format(self.name))
        if self.description is not None:
            FlocklabXmlConfig.addSubElement(ic, 'description', text='{}'.format(self.description))
        FlocklabXmlConfig.addSubElement(ic, 'platform', text='{}'.format(self.platform))
        if self.core is not None:
            FlocklabXmlConfig.addSubElement(ic, 'core', text='{}'.format(self.core))
        FlocklabXmlConfig.addSubElement(ic, 'data', text='\n{}\n  '.format(self.imageString))
        return x

class PowerProfilingConf():
    def __init__(self, obsIds=None, offset=0, duration=None, samplingRate=1000, fileFormat='csv'):
        self.obsIds = obsIds
        self.offset = offset
        self.duration = duration
        self.samplingRate = samplingRate
        self.fileFormat = fileFormat

    def config2Et(self, x):
        if self.obsIds is None:
            raise Exception('ERROR: obsIds of PowerProfilingConf needs to be set!')
        if self.duration is None:
            raise Exception('ERROR: duration of PowerProfilingConf needs to be set!')

        x.append(et.Comment('Power Profiling Service configuration'))
        pc = FlocklabXmlConfig.addSubElement(x, 'powerProfilingConf')
        FlocklabXmlConfig.addSubElement(pc, 'obsIds', text=Flocklab.formatObsIds(self.obsIds))
        FlocklabXmlConfig.addSubElement(pc, 'offset', text='{}'.format(self.offset))
        FlocklabXmlConfig.addSubElement(pc, 'duration', text='{}'.format(self.duration))
        FlocklabXmlConfig.addSubElement(pc, 'samplingRate', text='{}'.format(self.samplingRate))
        FlocklabXmlConfig.addSubElement(pc, 'fileFormat', text='{}'.format(self.fileFormat))
        return x

class DebugConf():
    def __init__(self, obsIds=None, gdbPort=2331):
        self.obsIds = obsIds
        self.gdbPort = gdbPort

    def config2Et(self, x):
        if self.obsIds is None:
            raise Exception('ERROR: obsIds of DebugConf needs to be set!')

        x.append(et.Comment('Debug configuration'))
        dc = FlocklabXmlConfig.addSubElement(x, 'debugConf')
        FlocklabXmlConfig.addSubElement(dc, 'obsIds', text=Flocklab.formatObsIds(self.obsIds))
        FlocklabXmlConfig.addSubElement(dc, 'gdbPort', text='{}'.format(self.gdbPort))
        return x

###############################################################################

if __name__ == "__main__":
    pass
