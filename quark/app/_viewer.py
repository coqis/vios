# MIT License

# Copyright (c) 2021 YL Feng <fengyulong@pku.org.cn>

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


import time

import numpy as np
from loguru import logger
from srpc import connect

from . import ping
from ._task import Task

_vs = {'viewer': connect('QuarkViewer', port=2086),
       'studio': connect('QuarkViewer', port=1086)}


class Figure(object):
    def __init__(self):
        self.__backend = _vs['viewer']
        self.data = []
        self.axes = []

    @property
    def backend(self):
        return self.__backend

    @backend.setter
    def backend(self, name: str):
        assert name in _vs, 'wrong name!'
        self.__backend = _vs[name]

    def __enter__(self):
        self.clear()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.show()

    def clear(self, backend: str = 'viewer'):
        self.data.clear()
        self.axes.clear()
        if backend in _vs:
            self.backend.clear()

    def subplot(self, length: int):
        for i in range(length):
            ax = Axes(self)
            self.axes.append(ax)
            self.data.append(ax.raw)
        return self.axes

    def show(self):
        self.backend.plot(self.data)


class Axes(object):
    def __init__(self, fig: Figure):
        self.fig = fig
        self.raw = {}

    def plot(self, ydata: np.ndarray | list, xdata: np.ndarray | list = [], **kwds):
        line = {'ydata': np.asarray(ydata)}

        xdata = np.arange(len(ydata)) if not len(xdata) else xdata
        assert len(xdata) == len(ydata), 'x and y must have same dimension'
        line['xdata'] = np.asarray(xdata)

        line['linestyle'] = kwds.get('linestyle', 2)
        line['linewidth'] = kwds.get('linewidth', 2)
        line['linecolor'] = kwds.get('linecolor', 'r')
        line['marker'] = kwds.get('marker', 'o')
        line['markersize'] = kwds.get('markersize', 5)
        line['markercolor'] = kwds.get('markercolor', 'r')
        self.style(line, **kwds)

    def scatter(self, ydata: np.ndarray | list, xdata: np.ndarray | list = [], **kwds):
        self.plot(ydata, xdata=xdata, **(kwds | {'linestyle': 'none'}))

    def imshow(self, zdata: np.ndarray | list, xdata: np.ndarray | list = [], ydata: np.ndarray | list = [], **kwds):
        line = {'zdata': np.asarray(zdata)}
        shape = line['zdata'].shape

        xdata = np.arange(shape[0]) if not len(xdata) else xdata
        assert len(xdata) == shape[0], 'x and z(x) must have same dimension'
        line['xdata'] = np.asarray(xdata)

        ydata = np.arange(shape[1]) if not len(ydata) else ydata
        assert len(ydata) == shape[1], 'y and z(y) must have same dimension'
        line['ydata'] = np.asarray(ydata)

        line['colormap'] = kwds.get('colormap', 'RdBu')
        self.style(line, **kwds)

    def style(self, line: dict, **kwds):
        line['title'] = kwds.get('title', 'title')
        line['xlabel'] = kwds.get('xlabel', 'xlabel')
        line['ylabel'] = kwds.get('ylabel', 'ylabel')
        self.raw[len(self.raw) + 1] = line


fig = Figure()


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

    if backend:
        viewer = _vs[backend]
        if backend == 'studio':
            viewer.clear()

        if not ping(viewer):
            task.plot = False
            return

    if 'population' in str(task.meta['other']['signal']):
        signal = 'population'
    else:
        signal = str(task.meta['other']['signal']).split('.')[-1]
    raw = np.asarray(task.data[signal][task.last:task.index])

    try:
        if signal == 'iq' and task.progress.total >= 5:
            raw = raw.mean(-2)
            signal = 'iq_avg'
    except Exception as e:
        logger.warning(f'Failed to average iq: {e}')

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
                if raw.shape[-1] + 1 == task.xdata.shape[-1]:
                    task.xdata = task.xdata[:, 1:]
            xdata = task.xdata[task.last:task.index]
            ydata = raw
        elif len(label) == 2:
            xlabel, ylabel = label
            # xdata = axis[xlabel][xlabel]
            if not hasattr(task, 'xdata'):
                task.xdata = np.asarray(list(axis[xlabel].values())).T
                if raw.shape[-1] + 1 == task.xdata.shape[-1]:
                    task.xdata = task.xdata[:, 1:]
                task.ydata = np.asarray(list(axis[ylabel].values())).T
                if raw.shape[-1] + 1 == task.ydata.shape[-1]:
                    task.ydata = task.ydata[:, 1:]
            # ydata = axis[ylabel][ylabel]
            xdata = task.xdata
            ydata = task.ydata
            zdata = np.abs(raw)
        if len(label) > 3:  # 2D image at maximum
            return

    uname = f'{task.name}_{xlabel}'
    if backend and task.last == 0:
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
                        except Exception as e:
                            line['xdata'] = xdata[..., 0].squeeze()

                        try:
                            line['ydata'] = ydata[..., idx].squeeze()
                        except Exception as e:
                            line['ydata'] = ydata[..., 0].squeeze()
                        # colormap of the image, see matplotlib
                        line['colormap'] = 'RdBu'
                    line['zdata'] = zdata[..., idx].squeeze()
                except Exception as e:
                    continue

            if task.last == 0:
                line['title'] = _title
                line['xlabel'] = xlabel
                line['ylabel'] = ylabel
            cell[f'{uname}{task.counter[uname]}'] = line
            # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            data.append(cell)

        if not backend:
            return data
        if not append:
            viewer.plot(data)  # create a new canvas
        else:
            viewer.append(data)  # append new data to the canvas
    except Exception as e:
        logger.error(f'Failed to update viewer: {e}')


def network():
    nodes = {}
    edges = {}
    for i in range(12):
        r, c = divmod(i, 3)
        nodes[f'Q{i}'] = {
            # 'name': f'Q{i}',
            # 'id': i,
            'pos': (r * 3, c * 3),
            'pen': (35, 155, 75, 255, 2),
            'value': {
                "probe": "M1",
                "couplers": [
                    "C0"
                ],
                "waveform": {
                    "SR": 6000000000.0,
                    "LEN": 8e-05,
                    "DDS_LO": 6000000000.0,
                    "RF": "zero()",
                    "DDS": "zero()"
                },
                "channel": {
                    "DDS": "ZW_AWG_13.CH2"
                },
                "calibration": {
                    "DDS": {
                        "delay": 3.05e-08
                    }
                }}}

        if i > 10:
            break
        edges[(f'Q{i}', f'Q{i + 1}')] = {'name': f'C{i}',
                                         'pen': (55, 123, 255, 180, 21),
                                         'value': {'b': np.random.random(1)[0] + 5, 'c': {'e': 134}, 'f': [(1, 2, 34)]}
                                         }
    _vs.graph(dict(nodes=nodes, edges=edges))


try:
    import ipywidgets as widgets
    from IPython.display import display

    class PagedTable(object):
        def __init__(self, data, page_size=10):
            self.data = data
            self.page_size = page_size
            self.total_pages = (len(data) + page_size - 1) // page_size
            self.current_page = 1

            # 创建控件
            self.prev_btn = widgets.Button(description="上一页")
            self.next_btn = widgets.Button(description="下一页")
            self.page_slider = widgets.IntSlider(
                value=1,
                min=1,
                max=self.total_pages,
                description='页码:'
            )
            self.output = widgets.Output()

            # 绑定事件
            self.prev_btn.on_click(self.prev_page)
            self.next_btn.on_click(self.next_page)
            self.page_slider.observe(self.slider_changed, names='value')

            # 初始显示
            self.update_display()

        def get_page_data(self):
            start = (self.current_page - 1) * self.page_size
            end = start + self.page_size
            return self.data.iloc[start:end]

        def update_display(self):
            self.output.clear_output(wait=True)
            with self.output:
                display(self.get_page_data())

            # 更新按钮状态
            self.prev_btn.disabled = (self.current_page == 1)
            self.next_btn.disabled = (self.current_page == self.total_pages)
            self.page_slider.value = self.current_page

        def prev_page(self, btn):
            self.current_page = max(1, self.current_page - 1)
            self.update_display()

        def next_page(self, btn):
            self.current_page = min(self.total_pages, self.current_page + 1)
            self.update_display()

        def slider_changed(self, change):
            self.current_page = change['new']
            self.update_display()

        def show(self):
            # 布局控件
            controls = widgets.HBox([
                self.prev_btn,
                self.next_btn,
                self.page_slider
            ])
            display(widgets.VBox([controls, self.output]))

except Exception as e:
    logger.error(f'{e}')


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def demo(dim: int = 1):
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
    viewer.clear()  # clear canvas
    for i in range(10):  # step number
        time.sleep(.2)
        try:
            data = []
            for r in range(n):
                cell = {}
                for j in range(1):
                    line = {}
                    if dim == 1:
                        line['xdata'] = np.arange(i, i + 1) * 1e8
                        line['ydata'] = np.random.random(1) * 1e8
                        line['linewidth'] = 2
                        line['marker'] = 'o'
                        line['fadecolor'] = (255, 0, 255)

                    if dim == 2:
                        if i == 0:
                            line['xdata'] = np.arange(-9, 9) * 1e-6
                            line['ydata'] = np.arange(-10, 10) * 1e-8
                        line['zdata'] = np.random.random((36,))

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
            print(e)
