Copyright (c) 2021, ETH Zurich, Computer Engineering Group (TEC)

# CHANGELOG - FlockLab Tools

## Version 0.1.0 (19.11.2019)
Initial version

## Version 0.1.1 (06.12.2019)
* Added copyright notice
* Improved visualization (removed unnecessary lines of GPIO traces, hover tooltip more efficient, html title)

## Version 0.2.0 (23.03.2020)
* support for FlockLab 2
* CLI
  * added option to display version number to CLI 
* xml config
  * use xml.etree for xml generation
* visualization
  * improved plotting (separate time scale, removed legend)
  * added all measured values to power plot hover
  * added rudimentary time measurement tool
  * extended visualizeFlocklabTrace for non-interactive use
* bug fixes

## Version 0.2.1 (07.04.2020)
* xml config
  * added support for gpio actuation
* visualization
  * improved behavior of time measure tool
  * tooltip for click actions
* bug fixes (creation of .flocklabauth file)

## Version 0.2.2 (28.04.2020)
* added getTestInfo() function
* added createTestWithInfo() function
* CLI
  * set file permissions for auth file
  * added test start time to output of create test CLI command
* visualization
  * explicitly declare javascript variables (bokeh applies "use_strict" starting with version 2.0.0)
  * improved time measure feature (set marker after selecting)
  * assume initial state of all GPIO signals to be 0 (this removes the infinitely short spike at the beginning of the plot)
  * fixed missing edge and hover on last signal edge
* xml config
  * updated xml generation to latest FlockLab 2 interface (schedule block)

## Version 0.2.3 (11.05.2020)
* visualization
  * fix: instruct pandas to not sacrifice accuracy for the sake of speed
  * disabled plotting of nRST and PPS signal by default & added CLI option (-y) to plot it anyway
  * omitting plotting of GPIO signals which are never HIGH in the whole test on all nodes

## Version 0.2.4 (08.10.2020)
* visualization
  * added absolute time to hover info of gpio plots
  * added Quick Zoom functionality (select zoom level from drop-down)
* xmlValidate now returns value (string) if execution fails
* CLI
  * return exit status 1 if command failed
* xml config
  * added support for dataTraceConf
  * added support for cpuSpeed element in serial config (required for swo mode in serial tracing)
  * automatically ceil duration of generalConf since only integers are allowed
  * fixed error message for gdbPort

## Version 0.2.5 (30.10.2020)
* visualization
  * quickzoom: changed zoom center to the middle of the plot, added centerline option
  * added buttons to enable/disable plots (services, nodes, GPIO pins, power signals, datatrace variables)
  * added support for plotting datatrace data
  * added absolute time to hover info of all plots using CustomJSHover
  * mapping of datatrace addr to variables based on content in custom tag of testconfig.xml

## Version 0.2.6 (11.12.2020)
* fix slow download of test results (prevent guessing of encoding for gzip responses)
* fix serial2Df() function
* visualization
  * added option to downsample powerprofiling in visualization
  * reordered UI elements to save horizontal space

## Version 0.2.7 (11.03.2021)
* added readCustomField() function
* fixed serial2Df (use correct path & properly handle serial logs which contain carriage returns)
* added functions to read and write symbol values in ELF files (binary patching)
* added option to specify download directory for getResults()
* xml config
  * no longer add `remoteIp` field in xml if no value specified (to improve serial logging performance)

## Version 0.2.8 (30.11.2021)
* CLI
  * removed unimplemented option to fetch test results via webdav
* convert timestamp to float in serial2Df()
* adding support to read from file pointer (file path, file pointer, or path to results dir is accepted as input to getCustomField, getDtAddrToVarMap, serial2Df)
* visualization
  * adjusted font size of axis labels
  * added workaround to disable rocketlogger printout
* explicitly specify version numbers of dependencies in package metadata
* added license info to package metadata
