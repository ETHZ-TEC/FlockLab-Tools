#!/usr/bin/env python3

import numpy as np
import pandas as pd
from collections import Counter, OrderedDict
import itertools
import os

from bokeh.plotting import figure, show, output_file
from bokeh.models import ColumnDataSource, Plot, LinearAxis, Grid, CrosshairTool, HoverTool, CustomJS, Div
from bokeh.models.glyphs import VArea, Line
from bokeh.layouts import gridplot, row, column
from bokeh.models import Legend
from bokeh.colors.named import red, green, blue, orange, lightskyblue, mediumpurple, mediumspringgreen, grey



###############################################################################

def addLinkedCrosshairs(plots):
    js_move = '''   start = fig.x_range.start, end = fig.x_range.end
                    if(cb_obj.x>=start && cb_obj.x<=end && cb_obj.y>=start && cb_obj.y<=end)
                        { cross.spans.height.computed_location=cb_obj.sx }
                    else { cross.spans.height.computed_location = null }
                    if(cb_obj.y>=start && cb_obj.y<=end && cb_obj.x>=start && cb_obj.x<=end)
                        { cross.spans.width.computed_location=cb_obj.sy  }
                    else { cross.spans.width.computed_location=null }'''
    js_leave = '''cross.spans.height.computed_location=null; cross.spans.width.computed_location=null'''

    figures = plots
    for x in plots:
        for plot in x:
            print(plot)
            plot = x[plot]
            print(plot)
            crosshair = CrosshairTool(dimensions = 'height')
            plot.add_tools(crosshair)
            for y in figures:
                for figure in y:
                    figure = y[figure]
                    if figure != plot:
                        args = {'cross': crosshair, 'fig': figure}
                        figure.js_on_event('mousemove', CustomJS(args = args, code = js_move))
                        figure.js_on_event('mouseleave', CustomJS(args = args, code = js_leave))



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
#    t = [e[0] for e in trace]
#    v = [e[1] for e in trace]
    tNew = np.repeat(t, 2, axis=0)
    # repeat invert and interleave
    vInv = [0 if e==1.0 else 1 for e in v]
    # interleave
    vNew = np.vstack((vInv, v)).reshape((-1,),order='F')

    return (tNew, vNew)

def plotObserverGpio(nodeId, nodeData, pOld):
    colors = ['blue', 'red', 'green', 'orange']
    p = figure(
        title=None,
        x_range=pOld.x_range if pOld is not None else None,
        # plot_width=1200,
        plot_height=900,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'save', 'reset', 'hover'],
        active_drag='xbox_zoom',
        active_scroll='xwheel_zoom',
        sizing_mode='stretch_both', # full screen)
    )
    length = len(nodeData)
    vareas = []
    for i, (pin, pinData) in enumerate(nodeData.items()):
        t, v, = trace2series(pinData['t'], pinData['v'])
        # source = ColumnDataSource(dict(x=t, y1=np.zeros_like(v)+length-i, y2=v+length-i))
        source = ColumnDataSource(dict(x=t, y1=np.zeros_like(v)+length-i, y2=v+length-i, desc=[pin for _ in range(len(t))]))
        # plot areas
        vareaGlyph = VArea(x="x", y1="y1", y2="y2", fill_color=colorMapping(pin),name=pin)
        varea = p.add_glyph(source, vareaGlyph)
        vareas += [(pin,[varea])]

        # plot lines
        lineGlyph = Line(x="x", y="y2", line_color=colorMapping(pin).darken(0.2),name=pin)
        x = p.add_glyph(source, lineGlyph)

    legend = Legend(items=vareas, location="center")
    p.add_layout(legend, 'right')

    hover = p.select(dict(type=HoverTool))
    # hover.tooltips = OrderedDict([('Time', '@x'),('Time', '@name')])
    hover.tooltips = OrderedDict([('Time', '@x'),('Name','@desc')])

    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.xaxis.visible = False
    p.yaxis.visible = False
#    p.yaxis.axis_label_orientation = "horizontal" # not working!
#    p.axis.major_label_orientation = 'vertical'

    return p

def plotObserverPower(nodeId, nodeData, pOld):
    p = figure(
        title=None,
        x_range=pOld.x_range if pOld is not None else None,
        # plot_width=1200,
        plot_height=900,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'save', 'reset', 'hover'],
        active_drag='xbox_zoom',
        active_scroll='xwheel_zoom',
        sizing_mode='stretch_both', # full screen)
    )
    source = ColumnDataSource(dict(x=nodeData['t'], y=nodeData['v']))
    lineGlyph = Line(x="x", y="y", line_color='black')
    p.add_glyph(source, lineGlyph)
    hover = p.select(dict(type=HoverTool))
    hover.tooltips = OrderedDict([('Time', '@x'),('Current', '@y')])

    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.xaxis.visible = False
#    p.yaxis.visible = False
#    p.yaxis.axis_label_orientation = "horizontal" # not working!
#    p.axis.major_label_orientation = 'vertical'

    return p

def plotAll(gpioData, powerData):
    # determine max timestamp value
    maxT = 0
    for nodeData in gpioData.values():
        for pinData in nodeData.values():
            pinMax = pinData['t'].max()
            if pinMax > maxT:
                maxT = pinMax

    # plot gpio data
    gpioPlots = OrderedDict()
    p = None
    for nodeId, nodeData in gpioData.items():
        p = plotObserverGpio(nodeId, nodeData, pOld=p)
        gpioPlots.update( {nodeId: p} )
    

    # plot power data
    powerPlots = OrderedDict()
    p = list(gpioPlots.values())[-1]
    for nodeId, nodeData in powerData.items():
        p = plotObserverPower(nodeId, nodeData, pOld=p)
        powerPlots.update( {nodeId: p} )

    # mergedPlots = powerPlots
    addLinkedCrosshairs([gpioPlots, powerPlots])

    # create linked dummy plot to get shared x axis without scaling height of bottom most plot
    allPlots = list(gpioPlots.values())
    pTime = figure(
        title=None,
        x_range=allPlots[-1].x_range,
        # plot_width=1200,
        plot_height=50,
        min_border=0,
        tools=['xpan', 'xwheel_zoom', 'xbox_zoom', 'hover', 'save', 'reset', 'hover'],
        active_drag='xbox_zoom',
        active_scroll='xwheel_zoom',
        sizing_mode='stretch_both', # full screen)
    )
    source = ColumnDataSource(dict(x=[0, maxT], y1=np.zeros_like([0, 60]), y2=[1, 1]))
    vareaGlyph = VArea(x="x", y1="y1", y2="y2", fill_color='grey')
    pTime.add_glyph(source, vareaGlyph)
    pTime.xgrid.grid_line_color = None
    pTime.ygrid.grid_line_color = None
    pTime.yaxis.visible = False

    # arrange all plots in grid
    gridPlots = []
    print(gpioPlots.keys())
    print(powerPlots.keys())
    allNodeIds = sorted(list(set(gpioPlots.keys()).union(set(powerPlots.keys()))))
    for nodeId in allNodeIds:
        labelDiv = column(Div(text='{}'.format(nodeId), style={'float': 'right'}), sizing_mode='fixed')
        print(len(powerPlots))
        if (nodeId in gpioPlots) and (nodeId in powerPlots):
            col = column(gpioPlots[nodeId], powerPlots[nodeId])
        elif (nodeId in gpioPlots):
            col = column(gpioPlots[nodeId])
        elif (nodeId in powerPlots):
            col = column(powerPlots[nodeId])
        else:
            raise Exception("ERROR!")
        gridPlots.append([labelDiv, col])
    gridPlots.append([None, pTime])

    # stack all plots
    grid = gridplot(gridPlots,
                    merge_tools=True,
                    sizing_mode='scale_both',
#                    plot_width=1200,
#                    plot_height=900,
                    )

    # render all plots
    show(grid)



def visualizeFlocklabTrace(resultPath):
    # check for correct path
    if os.path.isfile(resultPath):
        resultPath = os.path.dirname(resultPath)

    gpioPath = os.path.join(resultPath, 'gpiotracing.csv')
    powerPath = os.path.join(resultPath, 'powerprofiling.csv')
    actutationPath = os.path.join(resultPath, 'gpioactuation.csv')
    gpioAvailable = False
    powerAvailable = False

    # figure out which data is available
    if os.path.isfile(gpioPath):
        # Read gpio data csv to pandas dataframe
        gpioDf = pd.read_csv(gpioPath)
        # gpioDf.columns = ['timestamp'] + list(gpioDf.columns[1:])
        gpioDf.rename(columns={'# timestamp': 'timestamp'},inplace=True)

        if len(gpioDf) > 0:
            gpioAvailable = True
    else:
        print('gpiotracing.csv could not be found!')

    # figure out which data is available
    if os.path.isfile(actutationPath):
        # Read gpio data csv to pandas dataframe
        actutationDf = pd.read_csv(actutationPath)
        # actutationDf.columns = ['timestamp'] + list(actutationDf.columns[1:])
        print(actutationDf.head())
        actutationDf.rename(columns={'timestamp_executed': 'timestamp'},inplace=True)
        actutationDf.drop(['# timestamp_planned'], axis=1, inplace=True)
        if gpioAvailable:
            gpioDf = pd.concat([gpioDf, actutationDf])
        elif len(actutationDf) > 0:
            gpioDf = actutationDf
            gpioAvailable = True
        print(gpioDf.head())
    else:
        print('gpioactuation.csv could not be found!')

    if os.path.isfile(powerPath):
        # Read power data csv to pandas dataframe
        powerDf = pd.read_csv(powerPath)
        powerDf.rename(columns={'# timestamp': 'timestamp'},inplace=True)
        if len(powerDf) > 0:
            powerAvailable = True
    else:
        print('powerprofiling.csv could not be found!')

    # if os.path.isfile(sigPath):
    #     # Read power data csv to pandas dataframe
    #     sigDf = pd.read_csv(powerPath)
    #     sigDf.columns = ['timestamp'] + list(sigDf.columns[1:])
    #     if len(sigDf) > 0:
    #         powerAvailable = True
    # else:
    #     print('gpioactuation.csv could be found!')

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
    if gpioAvailable:
        gpioDf['timestampRelative'] = gpioDf.timestamp - minT
        gpioDf.sort_values(by=['node_id', 'pin_name', 'timestamp'], inplace=True)

        # Get overview of available data
        gpioNodeList = sorted(list(set(gpioDf.node_id)))
        gpioPinList = sorted(list(set(gpioDf.pin_name)))
        print('gpioNodeList:', gpioNodeList)
        print('gpioPinList:', gpioPinList)

        # Generate gpioData dict from pandas dataframe
        for nodeId, nodeGrp in gpioDf.groupby('node_id'):
            print(nodeId)
            nodeData = OrderedDict()
            for pin, pinGrp in nodeGrp.groupby('pin_name'):
                print('  {}'.format(pin))
                trace = {'t': pinGrp.timestampRelative.to_numpy(), 'v': pinGrp.value.to_numpy()}
                nodeData.update({pin: trace})
            gpioData.update({nodeId: nodeData})


    # prepare power data
    powerData = OrderedDict()
    if powerAvailable:
        powerDf['timestampRelative'] = powerDf.timestamp - minT
        powerDf.sort_values(by=['node_id', 'timestamp'], inplace=True)

        # Get overview of available data
        powerNodeList = sorted(list(set(powerDf.node_id)))
        print('powerNodeList:', powerNodeList)

        # Generate gpioData dict from pandas dataframe
        for nodeId, nodeGrp in powerDf.groupby('node_id'):
            print(nodeId)
            trace = {'t': nodeGrp.timestampRelative.to_numpy(), 'v': nodeGrp['value_mA'].to_numpy()}
            powerData.update({nodeId: trace})


    # # prepare sig data
    # sigData = OrderedDict()
    # if sigAvailable:
    #     sigDf['timestampRelative'] = sigDf.timestamp - minT
    #     sigDf.sort_values(by=['node_id', 'timestamp'], inplace=True)

    #     # Get overview of available data
    #     powerNodeList = sorted(list(set(sigDf.node_id)))
    #     print('powerNodeList:', powerNodeList)

    #     # Generate gpioData dict from pandas dataframe
    #     for nodeId, nodeGrp in sigDf.groupby('node_id'):
    #         print(nodeId)
    #         trace = {'t': nodeGrp.timestampRelative.to_numpy(), 'v': nodeGrp['value_mA'].to_numpy()}
    #         powerData.update({nodeId: trace})

    output_file(os.path.join(os.getcwd(), "out.html"))
    plotAll(gpioData, powerData)


###############################################################################

if __name__ == "__main__":
    output_file("out.html")

    visualizeFlocklabTrace(path)
