#!/usr/bin/env python3
"""
Copyright (c) 2021, ETH Zurich, Computer Engineering Group (TEC)
"""

import numpy as np
import pandas as pd
from collections import Counter, OrderedDict
import itertools
import os
import sys
import glob
from copy import copy
import json
from rocketlogger.data import RocketLoggerData

from bokeh.plotting import figure, show, save, output_file
from bokeh.models import ColumnDataSource, Plot, Span, BoxAnnotation, CrosshairTool, HoverTool, CustomJS, Div, Select, CheckboxButtonGroup, CustomJSHover
from bokeh.models.glyphs import VArea, Line, Circle, Step
from bokeh.models.renderers import GlyphRenderer
from bokeh.models.ranges import DataRange1d
from bokeh.layouts import gridplot, row, column, layout, Spacer
from bokeh.colors.named import red, green, blue, orange, lightskyblue, mediumpurple, mediumspringgreen, grey
from bokeh.events import Tap, DoubleTap, ButtonClick

from .flocklab import FlocklabError
from flocklab import Flocklab
fl = Flocklab()

# ignore bokeh deprecation warning until color.darken in bokeh gets fixed
import warnings
from bokeh.util.warnings import BokehDeprecationWarning
warnings.filterwarnings("ignore", category=BokehDeprecationWarning)

###############################################################################

def addLinkedCrosshairs(plots):
    js_move = '''
        var start_x = plot.x_range.start
        var end_x = plot.x_range.end
        var start_y = plot.y_range.start
        var end_y = plot.y_range.end
        if(cb_obj.x>=start_x && cb_obj.x<=end_x && cb_obj.y>=start_y && cb_obj.y<=end_y) {
            cross.spans.height.computed_location=cb_obj.sx
        }
        else {
            cross.spans.height.computed_location = null
        }
    '''
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
    # repeat and invert
    vInv = [0 if e else 1 for e in v]
    # assume first value is 0 always
    vInv[0] = 0
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
    tNewNew.append(tNew[-1])
    vNewNew.append(vNew[-1])
    tNewNew = np.asarray(tNewNew)
    vNewNew = np.asarray(vNewNew)

    return (tNewNew, vNewNew)

def plotObserverGpio(nodeId, nodeData, prevPlot, absoluteTimeFormatter):
    p = figure(
        title=None,
        x_range=prevPlot.x_range if prevPlot is not None else None,
        y_range=DataRange1d(only_visible=True), # enable auto scaling of plot to visible data instead to all plotted data
        # plot_width=1200,
        plot_height=900,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'reset'],
        active_drag='xbox_zoom', # not working due to bokeh bug https://github.com/bokeh/bokeh/issues/8766
        active_scroll='xwheel_zoom',
        sizing_mode='stretch_both', # full screen
        # output_backend="webgl",
    )
    length = len(nodeData)
    for i, (pin, pinData) in enumerate(nodeData.items()):
        if not 't' in pinData.keys():
            continue
        signalName = '{} (Node {})'.format(pin, nodeId)
        t, v, = trace2series(pinData['t'], pinData['v'])
        source = ColumnDataSource(dict(t=t, y1=np.zeros_like(v)+length-i, y2=v+length-i))
        # plot areas
        vareaGlyph = VArea(x="t", y1="y1", y2="y2", fill_color=colorMapping(pin))
        varea = p.add_glyph(source, vareaGlyph, name=signalName) # name necessary for hover tooltip
        # plot lines (necessary for tooltip/hover and for visibility if zoomed out!)
        lineGlyph = Line(x="t", y="y2", line_color=colorMapping(pin).darken(0.2))
        p.add_glyph(source, lineGlyph, name=signalName) # name necessary for hover tooltip

    hover = p.select(dict(type=HoverTool))
    hover.formatters={"@t": absoluteTimeFormatter}
    hover.tooltips = OrderedDict([
        ('Time (rel)', '@t{0.0000000} s'),
        ('Time (abs)', '@t{withOffset:0.0000000} s'),
        ('Signal', '$name')
    ])

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

    return p

def plotObserverPower(nodeId, nodeData, prevPlot, absoluteTimeFormatter):
    p = figure(
        title=None,
        x_range=prevPlot.x_range if prevPlot is not None else None,
        y_range=DataRange1d(only_visible=True), # enable auto scaling of plot to visible data instead to all plotted data
        # plot_width=1200,
        plot_height=900,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'reset'],
        active_drag='xbox_zoom', # not working due to bokeh bug https://github.com/bokeh/bokeh/issues/8766
        active_scroll='xwheel_zoom',
        sizing_mode='stretch_both', # full screen
        # output_backend="webgl",
    )
    source = ColumnDataSource(dict(
        t=nodeData['t'],
        i=nodeData['i'],
        v=nodeData['v'],
        p=nodeData['v']*nodeData['i'],
    ))
    line_i = Line(x="t", y="i", line_color='blue')
    line_v = Line(x="t", y="v", line_color='red')
    line_p = Line(x="t", y="p", line_color='black')
    p.add_glyph(source, line_i, name='I (Node {})'.format(nodeId), visible=False)
    p.add_glyph(source, line_v, name='V (Node {})'.format(nodeId), visible=False)
    p.add_glyph(source, line_p, name='P (Node {})'.format(nodeId))
    hover = p.select(dict(type=HoverTool))
    hover.formatters={"@t": absoluteTimeFormatter}
    hover.tooltips = OrderedDict([
      ('Time (rel)', '@t{0.00000000} s'),
      ('Time (abs)', '@t{withOffset:0.00000000} s'),
      ('V', '@v{0.000000} V'),
      ('I', '@i{0.000000} mA'),
      ('Power', '@p{0.000000} mW'),
      ('Signal', '$name'),
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

def plotObserverDatatrace(nodeId, nodeData, prevPlot, absoluteTimeFormatter, allVariables):
    p = figure(
        title=None,
        x_range=prevPlot.x_range if prevPlot is not None else None,
        y_range=DataRange1d(only_visible=True), # enable auto scaling of plot to visible data instead to all plotted data
        plot_height=900,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'reset'],
        active_drag='xbox_zoom', # not working due to bokeh bug https://github.com/bokeh/bokeh/issues/8766
        active_scroll='xwheel_zoom',
        sizing_mode='stretch_both', # full screen
        # output_backend="webgl",
    )

    colorMap = ['blue', 'red', 'green', 'black', 'cyan', 'yellowgreen', 'deepskyblue', 'indigo', 'orange', 'yellow']

    for variable, trace in nodeData.items():
        colorIdx = allVariables.index(variable)
        color = colorMap[colorIdx%len(colorMap)]
        source = ColumnDataSource(dict(
          t=trace['t'],
          value=trace['value'],
          access=trace['access'],
          delay_marker=trace['delay_marker'],
        ))
        step = Step(x="t", y="value", line_color=color, mode='after')
        p.add_glyph(source, step, name='{}'.format(variable))
        circle = Circle(x="t", y="value", size=4, line_color=color, fill_color="white", line_width=1)
        p.add_glyph(source, circle, name='{}'.format(variable))
        hover = p.select(dict(type=HoverTool))
        hover.formatters={"@t": absoluteTimeFormatter}
        hover.tooltips = OrderedDict([
          ('Time (rel)', '@t{0.0000000} s'),
          ('Time (abs)', '@t{withOffset:0.0000000} s'),
          ('Value', '@value{0}'),
          ('Access', '@access'),
          ('Delay marker', '@delay_marker'),
          ('Variable', '$name'),
        ])

    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.xaxis.visible = False
    p.yaxis.visible = False

    return p

def plotAll(gpioData, powerData, datatraceData, testNum, absoluteTimeFormatter, interactive=False):
    # determine gpio limits of timestamp value (for vertical lines)
    gpioLimits = None
    if gpioData:
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
        gpioLimits = (minT, maxT)

    ## plot all plots
    allPlots = []

    # plot gpio data
    gpioPlots = OrderedDict()
    p = None
    for nodeId, nodeData in gpioData.items():
        p = plotObserverGpio(nodeId, nodeData, prevPlot=p, absoluteTimeFormatter=absoluteTimeFormatter)
        gpioPlots.update( {nodeId: p} )
    allPlots += list(gpioPlots.values())

    # plot power data
    powerPlots = OrderedDict()
    p = allPlots[-1] if allPlots else None
    for nodeId, nodeData in powerData.items():
        p = plotObserverPower(nodeId, nodeData, prevPlot=p, absoluteTimeFormatter=absoluteTimeFormatter)
        powerPlots.update( {nodeId: p} )
    allPlots += list(powerPlots.values())

    # plot datatrace data
    datatracePlots = OrderedDict()
    p = allPlots[-1] if allPlots else None
    allVariables = sorted(list(set(list(itertools.chain.from_iterable([nodeData.keys() for nodeId, nodeData in datatraceData.items()])))))
    for nodeId, nodeData in datatraceData.items():
        p = plotObserverDatatrace(nodeId, nodeData, prevPlot=p, absoluteTimeFormatter=absoluteTimeFormatter, allVariables=allVariables)
        datatracePlots.update( {nodeId: p} )
    allPlots += list(datatracePlots.values())

    ## time scale axis: create linked dummy plot to get shared x axis without scaling height of bottom most plot
    # figure out last plot for linking x-axis
    p = allPlots[-1] if allPlots else None
    timePlot = figure(
        title=None,
        x_range=p.x_range,
        plot_height=0,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'reset'],
        active_drag='xbox_zoom', # not working due to bokeh bug https://github.com/bokeh/bokeh/issues/8766
        active_scroll='xwheel_zoom',
        height_policy='fit',
        width_policy='fit',
        # output_backend="webgl",
    )
    source = ColumnDataSource(dict(x=[0, np.inf], y1=[0, 0], y2=[0, 0]))
    vareaGlyph = VArea(x="x", y1="y1", y2="y2", fill_color='grey')
    timePlot.add_glyph(source, vareaGlyph)
    timePlot.xgrid.grid_line_color = None
    timePlot.ygrid.grid_line_color = None
    timePlot.xaxis.major_label_text_font_size = '10pt'
    timePlot.yaxis.visible = False
    allPlots += [timePlot]

    # arrange all plots in grid and render it
    createAppAndRender(gpioPlots, powerPlots, datatracePlots, timePlot, testNum, gpioLimits, interactive=interactive)

def createAppAndRender(gpioPlots, powerPlots, datatracePlots, timePlot, testNum, gpioLimits, interactive=False):
    '''arrange all plots in grid, add tools, and render it
    '''
    allPlots = list(gpioPlots.values()) + list(powerPlots.values()) + list(datatracePlots.values()) + [timePlot]
    # determine all nodeIds
    allNodeIds = sorted(list(set(list(gpioPlots.keys()) + list(powerPlots.keys()) + list(datatracePlots.keys()))))

    # : handle case where no gpio data is available
    # vertical line for start and end of test
    if gpioLimits is not None:
        vline_start = Span(location=gpioLimits[0], dimension='height', line_color=(25,25,25,0.1), line_width=3)
        vline_end = Span(location=gpioLimits[1], dimension='height', line_color=(25,25,25,0.1), line_width=3)
    # vertical line for quickzoom
    vline_middle = Span(location=0, dimension='height', line_color=(25,25,25,0.4), line_width=2, location_units='screen', render_mode='canvas', visible=False)

    ## measure time: add objects for measuring time with marker lines
    js_click = '''
    function setSpan(spanId, content) {
        var span = document.getElementById(spanId);

        while( span.firstChild ) {
        span.removeChild( span.firstChild );
        }
        span.appendChild( document.createTextNode(content) );
    }

    function calcAndDisplayDiff() {
        box.visible=true
        var timediff = marker_end.location - marker_start.location
        setSpan("marker_diff_span", timediff.toFixed(7) + " s")
    }

    if (document.getElementById('marker1').style.color=='black') {
        var startTime = cb_obj.x
        marker_start.visible=true
        marker_start.location=startTime
        box.left = startTime
        setSpan("marker_start_span", startTime.toFixed(7) + " s")
        if (marker_end.visible) {
            calcAndDisplayDiff();
        }
    } else if (document.getElementById('marker2').style.color=='black') {
        var endTime = cb_obj.x
        marker_end.location=endTime
        marker_end.visible=true
        box.right=endTime
        setSpan("marker_end_span", endTime.toFixed(7) + " s")
        if (marker_start.visible) {
            calcAndDisplayDiff();
        }
    } else {
        marker_start.visible=false
        marker_end.visible=false
        box.visible=false
        setSpan("marker_start_span", "\xa0") // note 0xa0 corresponds to HTML &nbsp (non-breaking space)
        setSpan("marker_end_span", "\xa0")
        setSpan("marker_diff_span", "\xa0")
    }
    '''
    mt_marker_start = Span(location=0, dimension='height', line_color='black', line_dash='dashed', line_width=2)
    mt_marker_start.location = 5
    mt_marker_start.visible = False
    mt_marker_end = Span(location=0, dimension='height', line_color='black', line_dash='dashed', line_width=2)
    mt_marker_end.location = 10
    mt_marker_end.visible = False
    mt_box = BoxAnnotation()
    mt_box.fill_color = 'grey'
    mt_box.fill_alpha = 0.1
    mt_box.visible = False

    ## add tools and utils to all plots
    for p in allPlots:
        # adding vlines
        if gpioLimits is not None:
            p.add_layout(vline_start)
            p.add_layout(vline_end)
        p.add_layout(vline_middle)

        # time measuring
        p.add_layout(mt_marker_start)
        p.add_layout(mt_marker_end)
        p.add_layout(mt_box)
        args = {'marker_start': mt_marker_start, 'marker_end': mt_marker_end, 'box': mt_box, 'p': p}
        p.js_on_event(Tap, CustomJS(args = args, code = js_click))

        # add functionality to reset by double-click
        p.js_on_event(DoubleTap, CustomJS(args=dict(p=p), code='p.reset.emit()'))

    ## add linked vertical selection line to all plots
    addLinkedCrosshairs(allPlots)

    ## arange plots in grid
    gridPlots = []
    for nodeId in allNodeIds:
        labelDiv = Div(
            # text='<div style="display: table-cell; vertical-align: middle", height="100%""><b>{}</b></div>'.format(nodeId),
            text='<b>{}</b>'.format(nodeId),
            style={
                'background-color': 'lightblue',
                'width': '30px',
                'height': '100%',
                'text-align': 'center',
                # 'font-size': '18px',
            },
            # sizing_mode='stretch_both',
            align='center',
            width=30,
            width_policy='fixed',
            height_policy='fit',
        )

        colList = []
        if (nodeId in gpioPlots) :
            colList.append(gpioPlots[nodeId])
        if (nodeId in powerPlots):
            colList.append(powerPlots[nodeId])
        if (nodeId in datatracePlots):
            colList.append(datatracePlots[nodeId])
        if not colList:
            raise Exception("ERROR: No plot for {nodeId} available, even though nodeId is present!".format(nodeId=nodeId))
        plotCol = column(colList, sizing_mode='stretch_both')
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
        width: 300px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 4px;
        padding: 5px 0;
        position: absolute;
        z-index: 1;
        top: 125%;
        left: 50%;
        margin-left: -150px;
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
    gridPlots.append([labelDiv, timePlot])

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
        margin=(0, 5, 0, 5),
        height_policy='min',
        width_policy='fit',
        align='center'
    )
    spaceDiv1 = Div(
        text='<div width="30px"></div>',
        style={'background-color': 'yellow'},
        width=30,
        margin=(0, 5, 0, 5),
        width_policy='fixed',
        height_policy='min',
    )
    spaceDiv2 = Div(
        text='<div width="30px"></div>',
        style={'background-color': 'yellow'},
        width=30,
        margin=(0, 5, 0, 5),
        width_policy='fixed',
        height_policy='min',
    )
    spaceDiv3 = Div(
        text='<div width="30px"></div>',
        style={'background-color': 'yellow'},
        width=30,
        margin=(0, 5, 0, 5),
        width_policy='fixed',
        height_policy='min',
    )
    measureDiv = Div(
        text='''
        <table style="border-collapse: collapse;">
          <tr>
            <td width="100px" align="left" rowspan="2", style="padding: 0; margin: 0;">
              <div class="tooltip" style="vertical-align:middle; cursor:default; color:grey; font-size: 23px; padding: 2px;">&#9432;<span class="tooltiptext"><b>Set marker</b>:<br/>enable &#9312; or &#9313; + click into plot<br/><b>Remove markers</b>:<br/>disable &#9312; and &#9313; + click into plot<br/><b>Reset plot</b>:<br/>double-click inside plot</span></div>
            </td>
            <td width="20px" align="left" style="padding: 0; margin: 0;">
              <span id="marker1" style="padding: 2px; cursor:default; color:grey; font-size: 25px;" onclick="(function() {
                if (document.getElementById('marker1').style.color == 'grey') {
                    document.getElementById('marker1').style.color='black';
                }
                else if (document.getElementById('marker1').style.color == 'black') {
                    document.getElementById('marker1').style.color='grey';
                }
                document.getElementById('marker2').style.color='grey';
                })();">&#9312;</span>
            </td>
            <td width="110px" align="left" style="padding: 0; margin: 0;">
              <span style="text-align: right; border: 2px solid grey; padding: 2px; border-radius: 3px; display: inline-block; width: 100px;" id="marker_start_span">&nbsp</span>
            </td>
            <td width="10px" align="left" style="padding: 0; margin: 0;">
              <span style="display: inline-block; width: 10px;">&nbsp;</span>
            </td>
            <td width="20px" align="left" rowspan="2" style="padding: 0; margin: 0;">
              <span style="padding: 2px; cursor:default; color:grey; font-size: 25px;">&#916;</span>
            </td>
            <td width="110px" align="left" rowspan="2" style="padding: 0; margin: 0;">
              <span style="text-align: right; border: 2px solid grey; padding: 2px; border-radius: 3px; display: inline-block; width: 100px;" id="marker_diff_span">&nbsp</span>
            </td>
          </tr>
          <tr>
            <td width="20px" align="left" style="padding: 0; margin: 0;">
              <span id="marker2" style="padding: 2px; cursor:default; color:grey; font-size: 25px;"  onclick="(function() {
                if (document.getElementById('marker2').style.color == 'grey') {
                    document.getElementById('marker2').style.color='black';
                }
                else if (document.getElementById('marker2').style.color == 'black') {
                    document.getElementById('marker2').style.color='grey';
                }
                document.getElementById('marker1').style.color='grey';
                })();">&#9313;</span>
            </td>
            <td width="110px" align="left" style="padding: 0; margin: 0;">
              <span style="text-align: right; border: 2px solid grey; padding: 2px; border-radius: 3px; display: inline-block; width: 100px;" id="marker_end_span">&nbsp</span>
            </td>
          </tr>
        </table>''' + '{}'.format(tooltipStyle),
        # style={'background-color': 'yellow'},
        align='center',
        margin=(0, 5, 0, 5),
        width_policy='min',
        height_policy='min',
    )

    zoomLut = OrderedDict([
        ('Quick Zoom', None),
        ('toggle centerline', None),
        ('fit trace', None),
        ('1h', 3600),
        ('10m', 600),
        ('1m', 60),
        ('10s', 10),
        ('1s', 1),
        ('100ms', 100e-3),
        ('10ms', 10e-3),
        ('1ms', 1e-3),
        ('100us', 100e-6),
        ('10us', 10e-6),
        ('1us', 1e-6),
    ])
    quickzoomSelect = Select(
        options=list(zoomLut.keys()),
        align='center',
        max_width=120,
        margin=(0, 5, 0, 5),
        width_policy='fit',
        height_policy='min',
    )
    quickzoomSelectCallback = CustomJS(
        args={
            'zoomLut': zoomLut,
            'resetStr': list(zoomLut.keys())[0],
            'toggleCenterLineStr': list(zoomLut.keys())[1],
            'fitTraceStr': list(zoomLut.keys())[2],
            'p': timePlot,
            'quickzoomSelect': quickzoomSelect,
            'vSpanMiddle': vline_middle,
        },
        code="""
            // console.log(quickzoomSelect, cb_obj.value);
            vSpanMiddle.location = 1/2*(p.inner_width);
            if (cb_obj.value == resetStr) {
                // do nothing
            } else if (cb_obj.value == toggleCenterLineStr) {
                vSpanMiddle.visible = !vSpanMiddle.visible;
            } else if (cb_obj.value == fitTraceStr) {
                p.reset.emit();
            } else {
                var middle = 1/2*(p.x_range.getv('end') + p.x_range.getv('start'));
                var start = middle - 1/2*zoomLut[cb_obj.value];
                var end = middle + 1/2*zoomLut[cb_obj.value];
                p.x_range.setv({"start": start, "end": end});
            }
            // reset drop-down
            quickzoomSelect.value = resetStr;
        """,
    )
    quickzoomSelect.js_on_change('value', quickzoomSelectCallback)

    # prepare title list elements
    titleElementsList = [titleDiv, spaceDiv1, measureDiv, spaceDiv2, quickzoomSelect, spaceDiv3]

    ## checkboxes for services
    serviceNames = []
    if gpioPlots:
        serviceNames.append("GPIO")
    if powerPlots:
        serviceNames.append("PWR")
    if datatracePlots:
        serviceNames.append("DT")
    serviceMap = dict([(name, serviceNames.index(name)) for name in serviceNames])
    checkboxServices = CheckboxButtonGroup(
        labels=serviceNames,
        active=list(range(len(serviceNames))),
        margin=(0, 5, 0, 5),
        # max_height=25,
        width_policy='min',
        height_policy='min',
    )
    checkboxServices.js_on_change('active', CustomJS(
        args={
            'gpioPlots': gpioPlots,
            'powerPlots': powerPlots,
            'datatracePlots': datatracePlots,
            'serviceMap': serviceMap,
        },
        code="""
            // GPIO plots
            if ('GPIO' in serviceMap) {
                for (var nodeId in gpioPlots) {
                    gpioPlots[nodeId].visible = this.active.includes(serviceMap['GPIO']);
                }
            }
            // Power plots
            if ('PWR' in serviceMap) {
                for (var nodeId in powerPlots) {
                    powerPlots[nodeId].visible = this.active.includes(serviceMap['PWR']);
                }
            }
            // Datatrace plots
            if ('DT' in serviceMap) {
                for (var nodeId in datatracePlots) {
                    datatracePlots[nodeId].visible = this.active.includes(serviceMap['DT']);
                }
            }
        """
    ))

    # checkboxes for nodes
    checkboxNodes = CheckboxButtonGroup(
        labels=[str(nodeId) for nodeId in allNodeIds],
        active=list(range(len(allNodeIds))),
        # max_height=25,
        margin=(0, 5, 0, 5),
        width_policy='min',
        height_policy='min',
    )
    checkboxNodes.js_on_change('active', CustomJS(
        args={
            'nodeIds': allNodeIds,
            'gridPlots': gridPlots,
        },
        code="""
            // console.log('checkboxNodes changed:', this.active);
            for (var i=0; i<nodeIds.length; i++) {
                gridPlots[i][0].visible = this.active.includes(i);
                gridPlots[i][1].visible = this.active.includes(i);
            }
        """
    ))

    # checkbox general row
    checkboxGeneralRow = row(
        [checkboxServices, checkboxNodes],
        width_policy='min',
        height_policy='min',
    )

    ## cheboxes for signals
    checkboxSignalsList = []

    # checkboxes for GPIO pins
    # FIXME: if gpio pin in the middle is disabled, space remains reserved and is not available for rest of the plot
    if gpioPlots:
        renderObjs = list(itertools.chain.from_iterable([p.select(GlyphRenderer) for p in gpioPlots.values()]))
        gpioPins = sorted(list(set([g.name.split(' ')[0] for g in renderObjs])))
        renderObjsDict = {}
        for pin in gpioPins:
            renderObjsDict[pin] = [r for r in renderObjs if pin == r.name.split(' ')[0]]
        checkboxGpio = CheckboxButtonGroup(
            labels=gpioPins,
            active=list(range(len(gpioPins))),
            width_policy='min',
        )
        checkboxGpio.js_on_change('active', CustomJS(
            args={
                'gpioPins': gpioPins,
                'renderObjs': renderObjsDict,
            },
            code="""
                for (var i=0; i<gpioPins.length; i++) {
                    for (var k=0; k<renderObjs[gpioPins[i]].length; k++) {
                        renderObjs[gpioPins[i]][k].visible = this.active.includes(i);
                    }
                }
            """
        ))
        checkboxSignalsList.append(checkboxGpio)

    # checkboxes for Power signals (I, V, P)
    if powerPlots:
        renderObjs = list(itertools.chain.from_iterable([p.select(GlyphRenderer) for p in powerPlots.values()]))
        powerSignals = ['V', 'I', 'P']
        renderObjsDict = {}
        for signal in powerSignals:
            renderObjsDict[signal] = [r for r in renderObjs if signal == r.name.split(' ')[0]]
        checkboxPower = CheckboxButtonGroup(
            labels=powerSignals,
            active=[powerSignals.index('P')],
            width_policy='min',
        )
        checkboxPower.js_on_change('active', CustomJS(
            args={
                'powerSignals': powerSignals,
                'renderObjs': renderObjsDict,
            },
            code="""
                for (var i=0; i<powerSignals.length; i++) {
                    for (var k=0; k<renderObjs[powerSignals[i]].length; k++) {
                        renderObjs[powerSignals[i]][k].visible = this.active.includes(i);
                    }
                }
            """
        ))
        checkboxSignalsList.append(checkboxPower)

    # checkboxes for datatrace variables
    if datatracePlots:
        renderObjs = list(itertools.chain.from_iterable([p.select(GlyphRenderer) for p in datatracePlots.values()]))
        variables = sorted(list(set([g.name for g in renderObjs])))
        renderObjsDict = {}
        for variable in variables:
            renderObjsDict[variable] = [r for r in renderObjs if variable == r.name]
        checkboxDatatrace = CheckboxButtonGroup(
            labels=variables,
            active=list(range(len(variables))),
            width_policy='min',
        )
        checkboxDatatrace.js_on_change('active', CustomJS(
            args={
                'variables': variables,
                'renderObjs': renderObjsDict,
            },
            code="""
                for (var i=0; i<variables.length; i++) {
                    for (var k=0; k<renderObjs[variables[i]].length; k++) {
                        renderObjs[variables[i]][k].visible = this.active.includes(i);
                    }
                }
            """
        ))
        checkboxSignalsList.append(checkboxDatatrace)

    checkboxSignalsRow = row(
        checkboxSignalsList,
        width_policy='min',
        height_policy='min',
    )

    checkboxCol = column(
        [checkboxGeneralRow, checkboxSignalsRow],
        width_policy='min',
        height_policy='min',
    )
    titleElementsList.append(checkboxCol)

    titleElementsRow = row(
        titleElementsList,
        sizing_mode='scale_width',
        align='start',
    )


    # make sure centerline stays in center if window is resized
    updateCenterlineCallback = CustomJS(
        args={
            'p': timePlot,
            'vSpanMiddle': vline_middle,
        },
        code="""
        vSpanMiddle.location = 1/2*(p.inner_width);
        """,
    )
    # FIXME: currently resizing the window with double-clicking the frame (to toggle between fullscreen and windowed) does not trigger a inner_width change
    p.js_on_change('inner_width', updateCenterlineCallback)

    # put together final layout of page
    finalLayout = column(
        [titleElementsRow, grid],
        # [grid],
        sizing_mode='scale_both',
    )

    # render all plots
    if interactive:
        show(finalLayout)
    else:
        save(finalLayout)



def visualizeFlocklabTrace(resultPath, outputDir=None, interactive=False, showPps=False, showRst=False, downsamplingFactor=1):
    '''Plots FlockLab results using bokeh.
    Args:
        resultPath: path to the flocklab results (unzipped)
        outputDir:  directory to store the resulting html file in (default: current working directory)
        interactive: switch to turn on/off automatic display of generated bokeh plot
    '''
    # check if resultPath is not empty
    if resultPath.strip() == '' or resultPath is None:
        raise Exception('ERROR: No FlockLab result directory provided as argument!')

    # check for correct path
    if os.path.isfile(resultPath):
        resultPath = os.path.dirname(resultPath)

    resultPath = os.path.normpath(resultPath) # remove trailing slash if there is one
    testNum = os.path.basename(os.path.abspath(resultPath))

    ## try to read gpio tracing data
    gpioPath = os.path.join(resultPath, 'gpiotracing.csv')
    requiredGpioCols = ['timestamp', 'node_id', 'pin_name', 'value']
    gpioAvailable = False

    if os.path.isfile(gpioPath):
        # Read gpio data csv to pandas dataframe (instruct pandas with float_precision to not sacrifice accuracy for the sake of speed)
        gpioDf = pd.read_csv(gpioPath, float_precision='round_trip')
        # sanity check: column names
        for col in requiredGpioCols:
            if not col in gpioDf.columns:
                raise Exception('ERROR: Required column ({}) in gpiotracing.csv file is missing.'.format(col))

        if len(gpioDf) > 0:
            # sanity check node_id data type
            if not 'int' in str(gpioDf.node_id.dtype):
                raise Exception('ERROR: GPIO trace file (gpiotracing.csv) has wrong format!')

            gpioAvailable = True

    ## try to read power profiling data
    powerPath = os.path.join(resultPath, 'powerprofiling.csv')
    powerRldFiles = glob.glob(os.path.join(resultPath, './powerprofiling*.rld'))
    requiredPowerCols = ['timestamp', 'node_id', 'current_mA', 'voltage_V']
    powerAvailable = False

    if os.path.isfile(powerPath):
        # Read power data csv to pandas dataframe (instruct pandas with float_precision to not sacrifice accuracy for the sake of speed)
        powerDf = pd.read_csv(powerPath, float_precision='round_trip')
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
        powerDfList = []
        for powerRldFile in powerRldFiles:
            sp = os.path.basename(powerRldFile).split('.')
            obsId = int(sp[1])
            nodeId = int(sp[2])
            tempDf = pd.DataFrame()
            rld = RocketLoggerData(powerRldFile)
            rld.merge_channels()
            ts = rld.get_time(time_reference='network')
            tempDf['timestamp'] = ts.astype(np.timedelta64) / np.timedelta64(1, 's')   # convert numpy.datetime64 timestamps into unix timestamps (numpy.float64 in seconds)
            # tempDf['timestamp'] = ts.astype('uint64') / 1e9   # convert numpy.datetime64 timestamps into unix timestamps (numpy.float64 in seconds)
            tempDf['observer_id'] = obsId
            tempDf['node_id'] = nodeId
            tempDf['current_mA'] = rld.get_data('I1') * 1e3 # convert to mA
            tempDf['voltage_V'] = rld.get_data('V2') - rld.get_data('V1') # voltage difference
            powerDfList.append(tempDf)

        powerDf = pd.concat(powerDfList)
        if len(powerDf) > 0:
            powerAvailable = True

    ## try to read datatrace data
    datatracePath = os.path.join(resultPath, 'datatrace.csv')
    requiredDatatraceCols = ['timestamp', 'node_id', 'variable', 'value']
    datatraceAvailable = False

    if os.path.isfile(datatracePath):
        # Read datatrace data csv to pandas dataframe (instruct pandas with float_precision to not sacrifice accuracy for the sake of speed)
        datatraceDf = pd.read_csv(datatracePath, float_precision='round_trip')
        # sanity check: column names
        for col in requiredDatatraceCols:
            if not col in datatraceDf.columns:
                raise Exception('ERROR: Required column ({}) in datatrace.csv file is missing.'.format(col))

        if len(datatraceDf) > 0:
            # sanity check node_id data type
            if not 'int' in str(datatraceDf.node_id.dtype):
                raise Exception('ERROR: GPIO trace file (gpiotracing.csv) has wrong format!')

            datatraceAvailable = True

    # handle case where there is no data to plot
    if (not gpioAvailable) and (not powerAvailable) and (not datatraceAvailable):
        print('ERROR: No data for plotting available!')
        sys.exit(1)

    # determine first timestamp globally (used as reference for relative time)
    refTime = np.inf
    if gpioAvailable:
        refTime = min( refTime, np.min(gpioDf.timestamp) )
    if powerAvailable:
        refTime = min( refTime, np.min(powerDf.timestamp) )
    if datatraceAvailable:
        refTime = min( refTime, np.min(datatraceDf.timestamp) )

    # generate custom hover tooltip formatter for adding absolute time to hover info without adding another series of data (to prevent data duplication)
    absoluteTimeFormatter = CustomJSHover(
        args=dict(offsetSource=ColumnDataSource(dict(offset=[refTime]))),
        code="""
            var numFormatter = Bokeh.require('@bokehjs/core/util/templating').DEFAULT_FORMATTERS.numeral;
            var formatSplit = format.split(':');
            if (formatSplit.length == 2 && formatSplit[0] == 'withOffset') {
                return numFormatter(special_vars.data_x + offsetSource.data.offset[0], formatSplit[1], special_vars);
            } else {
                return numFormatter(special_vars.data_x, format, special_vars)
            }
    """)

    ## prepare gpio data
    gpioData = OrderedDict()
    pinOrdering = ['INT1', 'INT2', 'LED1', 'LED2', 'LED3', 'SIG1', 'SIG2', 'PPS', 'nRST']
    if gpioAvailable:
        gpioDf['timestampRelative'] = gpioDf.timestamp - refTime
        gpioDf.sort_values(by=['node_id', 'pin_name', 'timestamp'], inplace=True)
        # determine global end of gpio trace (for adding edge back to 0 at the end of trace for signals which end with 1)
        tEnd = gpioDf[(gpioDf.pin_name=='nRST') & (gpioDf.value==0)].timestampRelative.to_numpy()[-1]

        # Generate gpioData dict from pandas dataframe
        for nodeId, nodeGrp in gpioDf.groupby('node_id'):
            pinList = copy(pinOrdering)
            nodeData = OrderedDict()
            pinGrps = nodeGrp.groupby('pin_name')
            if not set(pinGrps.groups.keys()).issubset(set(pinOrdering)):
                raise FlocklabError('ERROR: GPIO tracing file contains unknown pin names!')
            if not showRst:
                pinList.remove('nRST')
            if not showPps:
                pinList.remove('PPS')
            for pin in pinList:
                if pin in pinGrps.groups.keys():
                    pinGrp = pinGrps.get_group(pin)
                    # check if pin is ever toggled to 1 in the whole GPIO tracing (all nodes)
                    if (gpioDf[(gpioDf.pin_name==pin)].value==1).any():
                        t = pinGrp.timestampRelative.to_numpy()
                        v = pinGrp.value.to_numpy()
                        if len(v):
                            if v[-1] == 1:
                                t = np.append(t, tEnd)
                                v = np.append(v, 0)
                        trace = {'t': t, 'v': v}
                        nodeData.update({pin: trace})
            gpioData.update({nodeId: nodeData})


    ## prepare power data
    powerData = OrderedDict()
    if powerAvailable:
        powerDf['timestampRelative'] = powerDf.timestamp - refTime
        powerDf.sort_values(by=['node_id', 'timestamp'], inplace=True)

        # Get overview of available data
        powerNodeList = sorted(list(set(powerDf.node_id)))
        # print('powerNodeList:', powerNodeList)

        # Generate powerData dict from pandas dataframe
        for nodeId, nodeGrp in powerDf.groupby('node_id'):
            # print(nodeId)
            trace = {
              't': nodeGrp['timestampRelative'].to_numpy()[::downsamplingFactor],
              'i': nodeGrp['current_mA'].to_numpy()[::downsamplingFactor],
              'v': nodeGrp['voltage_V'].to_numpy()[::downsamplingFactor],
            }
            powerData.update({nodeId: trace})

    ## prepare datatrace data
    datatraceData = OrderedDict()
    if datatraceAvailable:
        datatraceDf['timestampRelative'] = datatraceDf.timestamp - refTime
        datatraceDf.sort_values(by=['node_id', 'variable', 'timestamp'], inplace=True)

        # Generate datatraceData dict from pandas dataframe
        for nodeId, nodeGrp in datatraceDf.groupby('node_id'):
            nodeData = OrderedDict()
            for variableName, variableGrp in nodeGrp.groupby('variable'):
                trace = {
                  't': variableGrp['timestampRelative'].to_numpy(),
                  'value': variableGrp['value'].to_numpy(),
                  'access': variableGrp['access'].to_numpy(),
                  'delay_marker': variableGrp['delay_marker'].to_numpy(),
                }
                addrToVarMap = fl.getDtAddrToVarMap(testConfigFile=resultPath)
                variableNameMapped = addrToVarMap[variableName] if variableName in addrToVarMap else variableName
                nodeData.update({variableNameMapped: trace})
            datatraceData.update({nodeId: nodeData})

    # set output file path
    if outputDir is None:
        output_file(os.path.join(os.getcwd(), "flocklab_plot_{}.html".format(testNum)), title="{}".format(testNum))
    else:
        output_file(os.path.join(outputDir, "flocklab_plot_{}.html".format(testNum)), title="{}".format(testNum))

    # generate plots
    plotAll(
        gpioData=gpioData,
        powerData=powerData,
        datatraceData=datatraceData,
        testNum=testNum,
        absoluteTimeFormatter=absoluteTimeFormatter,
        interactive=interactive,
    )


###############################################################################

if __name__ == "__main__":
    pass
