# MIT License

# Copyright (c) 2021 YL Feng

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


"""
Abstract: about app
    usefull functions for users to interact with `QuarkServer` and database
"""

import time

import numpy as np
from loguru import logger
from srpc import connect

from quark.proxy import Task

_vs = {'viewer': connect('QuarkViewer', port=2086),
       'studio': connect('QuarkViewer', port=1086)}


def plot(task: Task, append: bool = False, backend: str = 'viewer'):
    """real time display of the result

    Args:
        append (bool, optional): append new data to the canvas if True

    Note: for better performance
        - subplot number should not be too large(6*6 at maximum) 
        - data points should not be too many(5000 at maxmum)

    Tip: data structure of plot
        - [[dict]], namely a 2D list whose element is a dict
        - length of the outter list is the row number of the subplot
        - length of the inner list is the column number of the subplot
        - each element(the dict) stores the data, 1D(multiple curves is allowed) or 2D
        - the attributes of the lines or image(line color/width and so on) is the same as those in matplotlib **in most cases**
    """

    viewer = _vs[backend]
    if backend == 'studio':
        viewer.clear()

    if 'population' in str(task.meta['other']['signal']):
        signal = 'population'
    else:
        signal = str(task.meta['other']['signal']).split('.')[-1]
    raw = np.asarray(task.data[signal][task.last:task.index])

    if signal == 'iq':
        state = {0: 'b', 1: 'r', 2: 'g'}  # color for state 0,1,2
        label = []
        xlabel, ylabel = 'real', 'imag'
        append = False
    else:
        # raw = np.abs(raw)

        axis = task.meta['axis']
        label = tuple(axis)
        if len(label) == 1:
            xlabel, ylabel = label[0], 'Any'
            # xdata = axis[xlabel][xlabel][task.last:task.index]
            if not hasattr(task, 'xdata'):
                task.xdata = np.asarray(list(axis[xlabel].values())).T
            xdata = task.xdata[task.last:task.index]
            ydata = raw
        elif len(label) == 2:
            xlabel, ylabel = label
            # xdata = axis[xlabel][xlabel]
            if not hasattr(task, 'xdata'):
                task.xdata = np.asarray(list(axis[xlabel].values())).T
                task.ydata = np.asarray(list(axis[ylabel].values())).T
            # ydata = axis[ylabel][ylabel]
            xdata = task.xdata
            ydata = task.ydata
            zdata = raw
        if len(label) > 3:  # 2D image at maximum
            return

    uname = f'{task.name}_{xlabel}'
    if task.last == 0:
        if uname not in task.counter or len(label) == 2 or signal == 'iq':
            viewer.clear()  # clear the canvas
            task.counter.clear()  # clear the task history
        else:
            task.counter[uname] += 1
        viewer.info(task.task)

    time.sleep(0.1)  # reduce the frame rate per second for better performance
    try:
        data = []
        for idx in range(raw.shape[-1]):

            try:
                _name = task.app.name.split('.')[-1]
                rid = task.app.record_id
                _title = f'{_name}_{rid}_{task.title[idx][1]}'
            except Exception as e:
                _title = f'{idx}'

            # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            cell = {}  # one of the subplot
            line = {}

            if signal == 'iq':  # scatter plot
                try:
                    for i, iq in enumerate(raw[..., idx]):
                        si = i + task.last
                        cell[si] = {'xdata': iq.real.squeeze(),
                                    'ydata': iq.imag.squeeze(),
                                    'xlabel': xlabel,
                                    'ylabel': ylabel,
                                    'title': _title,
                                    'linestyle': 'none',
                                    'marker': 'o',
                                    'markersize': 5,
                                    'markercolor': state[si]}
                except Exception as e:
                    continue

            if len(label) == 1:  # 1D curve
                try:
                    try:
                        line['xdata'] = xdata[..., idx].squeeze()
                    except Exception as e:
                        line['xdata'] = xdata[..., 0].squeeze()
                    line['ydata'] = ydata[..., idx].squeeze()
                    if task.last == 0:
                        line['linecolor'] = 'r'  # line color
                        line['linewidth'] = 2  # line width
                        line['fadecolor'] = (  # RGB color, hex to decimal
                            int('5b', 16), int('b5', 16), int('f7', 16))
                except Exception as e:
                    continue

            if len(label) == 2:  # 2D image
                try:
                    if task.last == 0:
                        try:
                            line['xdata'] = xdata[..., idx].squeeze()
                            line['ydata'] = ydata[..., idx]
                        except Exception as e:
                            line['xdata'] = xdata[..., 0].squeeze()
                            line['ydata'] = ydata[..., 0]
                        # colormap of the image, see matplotlib
                        line['colormap'] = 'RdBu'
                    line['zdata'] = zdata[..., idx]
                except Exception as e:
                    continue

            if task.last == 0:
                line['title'] = _title
                line['xlabel'] = xlabel
                line['ylabel'] = ylabel
            cell[f'{uname}{task.counter[uname]}'] = line
            # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            data.append(cell)
        if not append:
            viewer.plot(data)  # create a new canvas
        else:
            viewer.append(data)  # append new data to the canvas
    except Exception as e:
        logger.error(f'Failed to update viewer: {e}')


def graph():
    nodes = {}
    for i in range(5):
        for j in range(6):
            nodes[f'{i+1:02d}{j+1:02d}'] = {'index': (i*3, j*3),
                                            'color': (0, 255, 255, 255),
                                            'size': 2,
                                            'value': np.random.random(1)[0]+5}
    edges = {(i, i+1): (255, 0, 255, 180, 21) for i in range(24)}

    _vs.graph(dict(nodes=nodes, edges=edges))


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def demo():
    """demo for plot

    Example: iq scatter
        ``` {.py3 linenums="1"}
        _vs.clear()
        iq = np.random.randn(1024)+np.random.randn(1024)*1j
        _vs.plot([
                {'i':{'xdata':iq.real-3,'ydata':iq.imag,'linestyle':'none','marker':'o','markersize':15,'markercolor':'b'},
                'q':{'xdata':iq.real+3,'ydata':iq.imag,'linestyle':'none','marker':'o','markersize':5,'markercolor':'r'},
                'hist':{'xdata':np.linspace(-3,3,1024),'ydata':iq.imag,"fillvalue":0, 'fillcolor':'r'}
                }
                ]
                )
        ```

    Example: hist
        ``` {.py3 linenums="1"}
        _vs.clear()
        vals = np.hstack([np.random.normal(size=500), np.random.normal(size=260, loc=4)])
        # compute standard histogram, len(y)+1 = len(x)
        y,x = np.histogram(vals, bins=np.linspace(-3, 8, 40))
        data = [{'hist':{'xdata':x,'ydata':y,'step':'center','fillvalue':0,'fillcolor':'g','linewidth':0}}]
        _vs.plot(data)
        ```
    """
    viewer = _vs['studio']

    n = 3  # number of subplots
    # _vs.clear() # clear canvas
    for i in range(10):  # step number
        time.sleep(.2)
        try:
            data = []
            for r in range(n):
                cell = {}
                for j in range(1):
                    line = {}
                    line['xdata'] = np.arange(i, i+1)*1e8
                    line['ydata'] = np.random.random(1)*1e8

                    # line['xdata'] = np.arange(-9,9)*1e-6
                    # line['ydata'] = np.arange(-10,10)*1e-8
                    # line['zdata'] = np.random.random((18,20))

                    line['linewidth'] = 2
                    line['marker'] = 'o'
                    line['fadecolor'] = (255, 0, 255)
                    line['title'] = f'aabb{r}'
                    line['legend'] = 'test'
                    line['xlabel'] = f'add'
                    line['ylabel'] = f'yddd'
                    # random.choice(['r', 'g', 'b', 'k', 'c', 'm', 'y', (31, 119, 180)])
                    line['linecolor'] = (31, 119, 180)
                    cell[f'test{j}2'] = line
                data.append(cell)
            if i == 0:
                viewer.plot(data)
            else:
                viewer.append(data)
        except Exception as e:
            logger.error(e)
