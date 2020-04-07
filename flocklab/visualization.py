#!/usr/bin/env python3
"""
Copyright (c) 2020, ETH Zurich, Computer Engineering Group (TEC)
"""

import numpy as np
import pandas as pd
from collections import Counter, OrderedDict
import itertools
import os
import sys
import glob

from bokeh.plotting import figure, show, save, output_file
from bokeh.models import ColumnDataSource, Plot, LinearAxis, Grid, CrosshairTool, HoverTool, CustomJS, Div
from bokeh.models.glyphs import VArea, Line
from bokeh.layouts import gridplot, row, column, layout, Spacer
from bokeh.models import Legend, Span, Label, BoxAnnotation
from bokeh.colors.named import red, green, blue, orange, lightskyblue, mediumpurple, mediumspringgreen, grey
from bokeh.events import Tap, DoubleTap, ButtonClick


###############################################################################

def addLinkedCrosshairs(plots):
    js_move = '''   start_x = plot.x_range.start
                    end_x = plot.x_range.end
                    start_y = plot.y_range.start
                    end_y = plot.y_range.end
                    if(cb_obj.x>=start_x && cb_obj.x<=end_x && cb_obj.y>=start_y && cb_obj.y<=end_y) {
                        cross.spans.height.computed_location=cb_obj.sx
                    }
                    else {
                        cross.spans.height.computed_location = null
                    }'''
                    # if(cb_obj.y>=start && cb_obj.y<=end && cb_obj.x>=start && cb_obj.x<=end)
                    #     { cross.spans.width.computed_location=cb_obj.sy  }
                    # else { cross.spans.width.computed_location=null }
                    # '''
    js_leave = '''cross.spans.height.computed_location=null; cross.spans.width.computed_location=null'''

    for currPlot in plots:
        crosshair = CrosshairTool(dimensions = 'height')
        currPlot.add_tools(crosshair)
        for plot in plots:
            if plot != currPlot:
                args = {'cross': crosshair, 'plot': plot}
                plot.js_on_event('mousemove', CustomJS(args = args, code = js_move))
                plot.js_on_event('mouseleave', CustomJS(args = args, code = js_leave))



def colorMapping(pin):
    if pin == 'LED1': return red
    elif pin == 'LED2': return green
    elif pin == 'LED3': return blue
    elif pin == 'INT1': return orange
    elif pin == 'INT2': return lightskyblue
    elif pin == 'SIG1': return mediumspringgreen
    elif pin == 'SIG2': return mediumpurple
    else: return grey

def trace2series(t, v):
    tNew = np.repeat(t, 2, axis=0)
    # repeat invert and interleave
    vInv = [0 if e==1.0 else 1 for e in v]
    # interleave
    vNew = np.vstack((vInv, v)).reshape((-1,),order='F')

    # insert gaps (np.nan) where signal is LOW (to prevent long unnecessary lines in plots)
    tNewNew = []
    vNewNew = []
    assert len(tNew) == len(vNew)
    for i in range(len(tNew)-1):
        tNewNew.append(tNew[i])
        vNewNew.append(vNew[i])
        if (vNew[i] == 0 and vNew[i+1] == 0):
            tNewNew.append(tNew[i])
            vNewNew.append(np.nan)
    tNewNew = np.asarray(tNewNew)
    vNewNew = np.asarray(vNewNew)

    return (tNewNew, vNewNew)

def plotObserverGpio(nodeId, nodeData, pOld):
    colors = ['blue', 'red', 'green', 'orange']
    p = figure(
        title=None,
        x_range=pOld.x_range if pOld is not None else None,
        # plot_width=1200,
        plot_height=900,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'save', 'reset'],
        active_drag='xbox_zoom', # not working due to bokeh bug https://github.com/bokeh/bokeh/issues/8766
        active_scroll='xwheel_zoom',
        sizing_mode='stretch_both', # full screen
    )
    length = len(nodeData)
    vareas = []
    for i, (pin, pinData) in enumerate(nodeData.items()):
        if not 't' in pinData.keys():
            continue
        signalName = '{} (Node {})'.format(pin, nodeId)
        t, v, = trace2series(pinData['t'], pinData['v'])
        source = ColumnDataSource(dict(x=t, y1=np.zeros_like(v)+length-i, y2=v+length-i))
        # plot areas
        vareaGlyph = VArea(x="x", y1="y1", y2="y2", fill_color=colorMapping(pin))
        varea = p.add_glyph(source, vareaGlyph, name=signalName)
        vareas += [(pin,[varea])]

        # plot lines (necessary for tooltip/hover and for visibility if zoomed out!)
        lineGlyph = Line(x="x", y="y2", line_color=colorMapping(pin).darken(0.2))
        x = p.add_glyph(source, lineGlyph, name=signalName)

    # legend = Legend(items=vareas, location="center")
    # p.add_layout(legend, 'right')


    hover = p.select(dict(type=HoverTool))
    hover.tooltips = OrderedDict([('Time', '@x{0.0000000} s'),('Signal','$name')])

    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.xaxis.visible = False
    p.yaxis.visible = False


    p.xaxis.major_tick_line_color = None  # turn off x-axis major ticks
    p.xaxis.minor_tick_line_color = None  # turn off x-axis minor ticks

    p.yaxis.major_tick_line_color = None  # turn off y-axis major ticks
    p.yaxis.minor_tick_line_color = None  # turn off y-axis minor ticks

    p.xaxis.major_label_text_font_size = '0pt'  # turn off x-axis tick labels
    p.yaxis.major_label_text_font_size = '0pt'  # turn off y-axis tick labels
    # p.xaxis.axis_label = "GPIO Traces"
    # p.xaxis.axis_label_text_color = "#aa6666"
    # p.xaxis.axis_label_standoff = 30

    # p.yaxis.axis_label = f"{nodeId}"
    # p.yaxis.axis_label = f"Node {nodeId}\n GPIO Traces"
    # p.yaxis.axis_label_text_font_style = "italic"

    return p

def plotObserverPower(nodeId, nodeData, pOld):
    p = figure(
        title=None,
        x_range=pOld.x_range if pOld is not None else None,
        # plot_width=1200,
        plot_height=900,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'save', 'reset'],
        active_drag='xbox_zoom', # not working due to bokeh bug https://github.com/bokeh/bokeh/issues/8766
        active_scroll='xwheel_zoom',
        sizing_mode='stretch_both', # full screen
    )
    source = ColumnDataSource(dict(
      t=nodeData['t'],
      i=nodeData['i'],
      v=nodeData['v'],
      p=nodeData['v']*nodeData['i'],
    ))
    line_i = Line(x="t", y="i", line_color='blue')
    # line_v = Line(x="t", y="v", line_color='red')
    line_p = Line(x="t", y="p", line_color='black')
    # p.add_glyph(source, line_i, name='{}'.format(nodeId))
    # p.add_glyph(source, line_v, name='{}'.format(nodeId))
    p.add_glyph(source, line_p, name='{}'.format(nodeId))
    hover = p.select(dict(type=HoverTool))
    hover.tooltips = OrderedDict([
      ('Time', '@t{0.00000000} s'),
      ('V', '@v{0.000000} V'),
      ('I', '@i{0.000000} mA'),
      ('Power', '@p{0.000000} mW'),
      ('Node','$name'),
    ])

    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.xaxis.visible = False
    p.yaxis.visible = False
#    p.yaxis.axis_label_orientation = "horizontal" # not working!
#    p.axis.major_label_orientation = 'vertical'

    # p.yaxis.axis_label = f"Node {nodeId}\n Current [mA]"
    # p.yaxis.axis_label_text_font_style = "italic"

    return p

def plotAll(gpioData, powerData, testNum, interactive=False):
    # determine max timestamp value
    maxT = 0
    minT = np.inf
    for nodeData in gpioData.values():
        for pinData in nodeData.values():
            if not 't' in pinData.keys():
                continue
            pinMax = pinData['t'].max()
            pinMin = pinData['t'].min()
            if pinMax > maxT:
                maxT = pinMax
            if pinMin < minT:
                minT = pinMin


    vline_start = Span(location=minT, dimension='height', line_color=(25,25,25,0.1), line_width=3)
    vline_end = Span(location=maxT, dimension='height', line_color=(25,25,25,0.1), line_width=3)

    # time measuring with marker lines
    js_click = '''
    function setSpan(spanId, content) {
        var span = document.getElementById(spanId);

        while( span.firstChild ) {
        span.removeChild( span.firstChild );
        }
        span.appendChild( document.createTextNode(content) );
    }

    if (num_clicked_label.x==0) {
    marker_start.visible=true
    marker_start.location=cb_obj.x
    box.left = cb_obj.x
    setSpan("marker_start_span", cb_obj.x.toFixed(7) + " s")
} else if (num_clicked_label.x==1) {
    marker_end.location=cb_obj.x
    marker_end.visible=true
    box.right=cb_obj.x
    box.visible=true
    timediff = cb_obj.x - marker_start.location
    setSpan("marker_end_span", cb_obj.x.toFixed(7) + " s")
    setSpan("marker_diff_span", timediff.toFixed(7) + " s")
} else if (num_clicked_label.x==2) {
    marker_start.visible=false
    marker_end.visible=false
    box.visible=false
    setSpan("marker_start_span", "   ")
    setSpan("marker_end_span", "   ")
    setSpan("marker_diff_span", "   ")
}
num_clicked_label.x = (num_clicked_label.x + 1) % 3
    '''
    marker_start = Span(location=0, dimension='height', line_color='black', line_dash='dashed', line_width=2)
    marker_start.location = 5
    marker_start.visible = False
    marker_end = Span(location=0, dimension='height', line_color='black', line_dash='dashed', line_width=2)
    marker_end.location = 10
    marker_end.visible = False
    box = BoxAnnotation()
    box.fill_color = 'grey'
    box.fill_alpha = 0.1
    box.visible = False
    # dummy label for counting number of clicks (simple int or list does not work since state is not kept or state is not shared between plots)
    num_clicked_label = Label()
    num_clicked_label.x = 0
    num_clicked_label.visible = False

    # plot gpio data
    gpioPlots = OrderedDict()
    p = None
    for nodeId, nodeData in gpioData.items():
        p = plotObserverGpio(nodeId, nodeData, pOld=p)

        # adding a start and end line
        p.add_layout(vline_start)
        p.add_layout(vline_end)

        # time measuring
        p.add_layout(marker_start)
        p.add_layout(marker_end)
        p.add_layout(box)
        args = {'marker_start': marker_start, 'marker_end': marker_end, 'box': box, 'num_clicked_label': num_clicked_label}
        p.js_on_event(Tap, CustomJS(args = args, code = js_click))

        # add functionality to reset by double-click
        p.js_on_event(DoubleTap, CustomJS(args=dict(p=p), code='p.reset.emit()'))

        gpioPlots.update( {nodeId: p} )


    # plot power data
    if len(gpioPlots):
        p = list(gpioPlots.values())[-1]
    else:
        p = None

    powerPlots = OrderedDict()
    for nodeId, nodeData in powerData.items():
        p = plotObserverPower(nodeId, nodeData, pOld=p)

        # adding a start and end line
        p.add_layout(vline_start)
        p.add_layout(vline_end)

        # time measuring
        p.add_layout(marker_start)
        p.add_layout(marker_end)
        p.add_layout(box)
        args = {'marker_start': marker_start, 'marker_end': marker_end, 'box': box, 'p': p, 'num_clicked_label': num_clicked_label}
        p.js_on_event(Tap, CustomJS(args = args, code = js_click))

        # add functionality to reset by double-click
        p.js_on_event(DoubleTap, CustomJS(args=dict(p=p), code='p.reset.emit()'))

        powerPlots.update( {nodeId: p} )

    # figure out last plot for linking x-axis
    if len(powerPlots) > 0:
        lastPlot = list(powerPlots.values())[-1]
    elif len(gpioPlots) > 0:
        lastPlot = list(gpioPlots.values())[-1]
    else:
        lastPlot = None
    # lastPlot.xaxis.visible = True # used if no dummy plot is used for x-axis

    ## create linked dummy plot to get shared x axis without scaling height of bottom most plot
    pTime = figure(
        title=None,
        x_range=lastPlot.x_range,
        plot_height=0,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'save', 'reset'],
        active_drag='xbox_zoom', # not working due to bokeh bug https://github.com/bokeh/bokeh/issues/8766
        active_scroll='xwheel_zoom',
        height_policy='fit',
        width_policy='fit',
    )
    source = ColumnDataSource(dict(x=[0, maxT], y1=[0, 0], y2=[0, 0]))
    vareaGlyph = VArea(x="x", y1="y1", y2="y2", fill_color='grey')
    pTime.add_glyph(source, vareaGlyph)
    pTime.xgrid.grid_line_color = None
    pTime.ygrid.grid_line_color = None
    pTime.yaxis.visible = False

    addLinkedCrosshairs( list(gpioPlots.values()) + list(powerPlots.values()) + [pTime] )

    # arrange all plots in grid
    gridPlots = []
    # print(gpioPlots.keys())
    # print(powerPlots.keys())
    allNodeIds = sorted(list(set(gpioPlots.keys()).union(set(powerPlots.keys()))))
    for nodeId in allNodeIds:
        labelDiv = Div(
            # text='<div style="display: table-cell; vertical-align: middle", height="100%""><b>{}</b></div>'.format(nodeId),
            text='<b>{}</b>'.format(nodeId),
            style={
                'background-color': 'lightblue',
                'width': '30px',
                'height': '100%',
                'text-align': 'center',
            },
            # sizing_mode='stretch_both',
            align='center',
            width=30,
            width_policy='fixed',
        )
        spacer = Spacer(
            height_policy='fixed',
            height=10,
        )
        # print(len(powerPlots))
        if (nodeId in gpioPlots) and (nodeId in powerPlots):
            colList = [gpioPlots[nodeId], powerPlots[nodeId]]
        elif (nodeId in gpioPlots):
            colList = [gpioPlots[nodeId]]
        elif (nodeId in powerPlots):
            colList = [powerPlots[nodeId]]
        else:
            raise Exception("ERROR: No plot for {nodeId} available, even though nodeId is present!".format(nodeId=nodeId))
        plotCol = column(colList, sizing_mode='stretch_both')
        # plotCol = column(colList + [spacer], sizing_mode='stretch_both')
        # labelCol = column([labelDiv, spacer], sizing_mode='fixed')
        gridPlots.append([labelDiv, plotCol])

    tooltipStyle = '''
    <style>
  .tooltip {
    font-size: 18px;
    position: relative;
    display: inline-block;
  }

  .tooltip .tooltiptext {
    visibility: hidden;
    width: 220px;
    background-color: #555;
    color: #fff;
    text-align: center;
    border-radius: 4px;
    padding: 5px 0;
    position: absolute;
    z-index: 1;
    top: 125%;
    left: 50%;
    margin-left: -110px;
    opacity: 0;
    transition: opacity 0.3s;
  }

  .tooltip .tooltiptext::after {
    content: "";
    position: absolute;
    bottom: 100%;
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: transparent transparent #555 transparent;
  }

  .tooltip:hover .tooltiptext {
    visibility: visible;
    font-size: 16px;
    opacity: 1;
  }
  </style>
    '''

    ## add plot for time scale
    labelDiv = Div(
        align='center',
        width=30,
        width_policy='fixed',
        height_policy='fit',
    )
    gridPlots.append([labelDiv, pTime])

    # stack all plots
    grid = gridplot(
        gridPlots,
        merge_tools=True,
        # sizing_mode='stretch_both',
        sizing_mode='scale_both',
    )
    # Add title
    titleDiv = Div(
        text='<h2 style="margin:0">FlockLab Test {testNum}</h2>'.format(testNum=testNum),
        # style={'background-color': 'yellow',},
        height_policy='fit',
        width_policy='fit',
        align='center'
    )
    spaceDiv = Div(
        text='<div width="30px"></div>',
        style={'background-color': 'yellow'},
        width=60,
        width_policy='fixed',
        height_policy='fit',
    )
    measureDiv = Div(
        text='''
        <table>
          <tr>
            <th width="180px" align="left"><span style="padding: 2px;">&#9312;</span><span style="border: 2px solid grey; padding: 2px; border-radius: 3px;" id="marker_start_span">   </span></th>
            <th width="180px" align="left"><span style="padding: 2px;">&#9313;</span><span style="border: 2px solid grey; padding: 2px; border-radius: 3px;" id="marker_end_span">   </span></th>
            <th width="180px" align="left"><span style="padding: 2px;">&#916;</span><span style="border: 2px solid grey; padding: 2px; border-radius: 3px;" id="marker_diff_span">   </span></th>
          </tr>
        </table>
        ''',
        # style={'background-color': 'yellow'},
        width=550,
        width_policy='fixed',
        height_policy='fit',
    )
    infoDiv = Div(
        text='<div class="tooltip">&#9432;<span class="tooltiptext"><b>click</b>: time measure tool <br/>(set &#9312;/set &#9313;/clear)<br/><b>double-click</b>: reset plot</span></div>'+tooltipStyle,
        # style={'background-color': 'yellow'},
        width=30,
        width_policy='fixed',
        height_policy='fit',
    )
    titleLine = row(
        [titleDiv, spaceDiv, measureDiv, infoDiv],
        sizing_mode='scale_width',
        align='start',
        # align='center',
    )
    # put together final layout of page
    finalLayout = column(
        [titleLine, grid],
        # [grid],
        sizing_mode='scale_both',
    )

    # render all plots
    if interactive:
        show(finalLayout)
    else:
        save(finalLayout)



def visualizeFlocklabTrace(resultPath, outputDir=None, interactive=False):
    '''Plots FlockLab results using bokeh.
    Args:
        resultPath: path to the flocklab results (unzipped)
        outputDir:  directory to store the resulting html file in (default: current working directory)
        interctive: switch to turn on/off automatic display of generated bokeh plot
    '''
    # check if resultPath is not empty
    print(resultPath)
    if resultPath.strip() == '' or resultPath is None:
        raise Exception('ERROR: No FlockLab result directory provided as argument!')

    # check for correct path
    if os.path.isfile(resultPath):
        resultPath = os.path.dirname(resultPath)

    resultPath = os.path.normpath(resultPath) # remove trailing slash if there is one
    testNum = os.path.basename(os.path.abspath(resultPath))

    # try to read gpio tracing data
    gpioPath = os.path.join(resultPath, 'gpiotracing.csv')
    requiredGpioCols = ['timestamp', 'node_id', 'pin_name', 'value']
    gpioAvailable = False

    if os.path.isfile(gpioPath):
        # Read gpio data csv to pandas dataframe
        gpioDf = pd.read_csv(gpioPath)
        # sanity check: column names
        for col in requiredGpioCols:
            if not col in gpioDf.columns:
                raise Exception('ERROR: Required column ({}) in gpiotracing.csv file is missing.'.format(col))

        if len(gpioDf) > 0:
            # sanity check node_id data type
            if not 'int' in str(gpioDf.node_id.dtype):
                raise Exception('ERROR: GPIO trace file (gpiotracing.csv) has wrong format!')

            gpioAvailable = True
    else:
        print('gpiotracing.csv could not be found!')

    # try to read power profiling data
    powerPath = os.path.join(resultPath, 'powerprofiling.csv')
    powerRldFiles = glob.glob(os.path.join(resultPath, './powerprofiling*.rld'))
    requiredPowerCols = ['timestamp', 'node_id', 'current_mA', 'voltage_V']
    powerAvailable = False

    if os.path.isfile(powerPath):
        # Read power data csv to pandas dataframe
        powerDf = pd.read_csv(powerPath)
        # sanity check: column names
        for col in requiredPowerCols:
            if not col in powerDf.columns:
                raise Exception('ERROR: Required column ({}) in powerprofiling.csv file is missing.'.format(col))

        if len(powerDf) > 0:
            # sanity check node_id data type
            if not 'int' in str(powerDf.node_id.dtype):
                raise Exception('ERROR: GPIO trace file (gpiotracing.csv) has wrong format!')

            powerAvailable = True
    elif powerRldFiles:
        from rocketlogger.data import RocketLoggerData

        powerDfList = []
        for powerRldFile in powerRldFiles:
            sp = os.path.basename(powerRldFile).split('.')
            obsId = int(sp[1])
            nodeId = int(sp[2])
            tempDf = pd.DataFrame()
            rld = RocketLoggerData(powerRldFile)
            rld.merge_channels()
            ts = rld.get_time(absolute_time=True, time_reference='network')
            tempDf['timestamp'] = ts.astype('uint64') / 1e9   # convert to s
            tempDf['observer_id'] = obsId
            tempDf['node_id'] = nodeId
            tempDf['current_mA'] = rld.get_data('I1') * 1e3 # convert to mA
            tempDf['voltage_V'] = rld.get_data('V2') - rld.get_data('V1') # voltage difference
            powerDfList.append(tempDf)

        powerDf = pd.concat(powerDfList)
        # import pdb
        # pdb.set_trace()
        if len(powerDf) > 0:
            powerAvailable = True
    else:
        print('powerprofiling data (\'.csv\' or \'.rld\') could not be found!')

    # handle case where there is no data to plot
    if (not gpioAvailable) and (not powerAvailable):
        print('ERROR: No data for plotting available!')
        sys.exit(1)

    # determine first timestamp (globally)
    minT = None
    if gpioAvailable and powerAvailable:
        minT = min( np.min(gpioDf.timestamp), np.min(powerDf.timestamp) )
    elif gpioAvailable:
        minT = np.min(gpioDf.timestamp)
    elif powerAvailable:
        minT = np.min(powerDf.timestamp)

    # prepare gpio data
    gpioData = OrderedDict()
    pinOrdering = ['INT1', 'INT2', 'LED1', 'LED2', 'LED3', 'SIG1', 'SIG2']
    if gpioAvailable:
        gpioDf['timestampRelative'] = gpioDf.timestamp - minT
        gpioDf.sort_values(by=['node_id', 'pin_name', 'timestamp'], inplace=True)

        # Get overview of available data
        gpioNodeList = sorted(list(set(gpioDf.node_id)))
        gpioPinList = sorted(list(set(gpioDf.pin_name)))
        # print('gpioNodeList:', gpioNodeList)
        # print('gpioPinList:', gpioPinList)

        # Generate gpioData dict from pandas dataframe
        for nodeId, nodeGrp in gpioDf.groupby('node_id'):
            # print(nodeId)
            nodeData = OrderedDict()
            pinGrps = nodeGrp.groupby('pin_name')
            pinList = pinOrdering + list(set(pinGrps.groups.keys()) - set(pinOrdering))
            # TODO: test with gpio tracing file with missin  pin
            for pin in pinList:
                if pin in pinGrps.groups.keys():
                    pinGrp = pinGrps.get_group(pin)
                    trace = {'t': pinGrp.timestampRelative.to_numpy(), 'v': pinGrp.value.to_numpy()}
                    nodeData.update({pin: trace})
                else:
                    nodeData.update({pin: {}})
            gpioData.update({nodeId: nodeData})


    # prepare power data
    powerData = OrderedDict()
    if powerAvailable:
        powerDf['timestampRelative'] = powerDf.timestamp - minT
        powerDf.sort_values(by=['node_id', 'timestamp'], inplace=True)

        # Get overview of available data
        powerNodeList = sorted(list(set(powerDf.node_id)))
        # print('powerNodeList:', powerNodeList)

        # Generate powerData dict from pandas dataframe
        for nodeId, nodeGrp in powerDf.groupby('node_id'):
            # print(nodeId)
            trace = {
              't': nodeGrp.timestampRelative.to_numpy(),
              'i': nodeGrp['current_mA'].to_numpy(),
              'v': nodeGrp['voltage_V'].to_numpy(),
            }
            powerData.update({nodeId: trace})

    if outputDir is None:
        output_file(os.path.join(os.getcwd(), "flocklab_plot_{}.html".format(testNum)), title="{}".format(testNum))
    else:
        output_file(os.path.join(outputDir, "flocklab_plot_{}.html".format(testNum)), title="{}".format(testNum))
    plotAll(gpioData, powerData, testNum=testNum, interactive=interactive)


###############################################################################

if __name__ == "__main__":
    pass
