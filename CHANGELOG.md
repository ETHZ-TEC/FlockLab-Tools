Copyright (c) 2020, ETH Zurich, Computer Engineering Group (TEC)

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
