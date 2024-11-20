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
from collections import defaultdict
from threading import current_thread

import numpy as np
from loguru import logger

from quark import connect
from quark.proxy import Task

from ._data import (get_config_by_tid, get_dataset_by_tid,
                    get_record_by_rid, get_record_by_tid, sql)

sp = {}  # defaultdict(lambda: connect('QuarkServer', host, port))
_vs = connect('QuarkViewer', port=2086)


def signup(user: str, system: str, **kwds):
    """register a new **user** on the **system**

    Args:
        user (str): name of the user
        system (str): name of the system(i.e. the name of the cfg file)
    """
    s = login()
    logger.info(s.adduser(user, system, **kwds))
    s.login(user)  # relogin


def login(user: str = 'baqis', host: str = '127.0.0.1', verbose: bool = True):
    """login to the server as **user**

    Args:
        user (str, optional): name of the user(same as signup). Defaults to 'baqis'.
        verbose (bool, optional): print login info if True. Defaults to True.

    Returns:
        _type_: a connection to the server
    """
    try:
        return sp[current_thread().name]
    except KeyError as e:
        s = sp[current_thread().name] = connect('QuarkServer', host, 2088)
        m = s.login(user)
        if verbose:
            logger.info(m)
        return s


def submit(task: dict, block: bool = False, preview: list = [], **kwds):
    """submit a task to a backend

    Args:
        task (dict): description of a task
        block (bool, optional): block until the task is done if True
        preview (list, optional): real time display of the waveform

    Keyword Arguments: Kwds
        plot (bool): plot the result in the QuarkStudio if True(1D or 2D), defaults to False.
        backend (connection): connection to a backend, defaults to local machine.

    Raises:
        TypeError: _description_

    Example: description of a task
        ``` {.py3 linenums="1"}
        {
            'meta': {'name': f'{filename}: /s21',  # s21 is the name of the dataset
                     # extra arguments for compiler and others
                     'other': {'shots': 1234, 'signal': 'iq', 'autorun': False}},
            'body': {'step': {'main': ['WRITE', ('freq', 'offset', 'power')],  # main is reserved
                              'step2': ['WRITE', 'trig'],
                              'step3': ['WAIT', 0.8101],  # wait for some time in the unit of second
                              'READ': ['READ', 'read'],
                              'step5': ['WAIT', 0.202]},
                     'init': [('Trigger.CHAB.TRIG', 0, 'any')],  # initialization of the task
                     'post': [('Trigger.CHAB.TRIG', 0, 'any')],  # reset of the task
                     'cirq': ['cc'],  # list of circuits in the type of qlisp
                     'rule': ['<gate.Measure.Q1.params.frequency> = <Q0.setting.LO>+<Q2.setting.LO> +1250'],
                     'loop': {'freq': [('Q0.setting.LO', np.linspace(0, 10, 2), 'Hz'),
                                       ('gate.Measure.Q1.index',  np.linspace(0, 1, 2), 'Hz')],
                              'offset': [('M0.setting.TRIGD', np.linspace(0, 10, 1), 'Hz'),
                                         ('Q2.setting.LO', np.linspace(0, 10, 1), 'Hz')],
                              'power': [('Q3.setting.LO', np.linspace(0, 10, 15), 'Hz'),
                                        ('Q4.setting.POW', np.linspace(0, 10, 15), 'Hz')],
                              'trig': [('Trigger.CHAB.TRIG', 0, 'any')],
                              'read': ['NA10.CH1.TraceIQ', 'M0.setting.POW']
                            }
                    },
        }
        ```

    Todo: fixes
        * `bugs`
    """

    if 'backend' in kwds:  # from master
        ss = kwds['backend']
        trig = []
    else:
        ss = login(verbose=False)
        trig = [(t, 0, 'au') for t in ss.query('station.triggercmds')]

    # if preview:
    ss.update('etc.canvas.filter', preview)  # waveforms to be previewed

    task['body']['loop']['trig'] = trig
    t = Task(task)
    t.server = ss
    t.plot = plot if kwds.get('plot', False) else False
    t.timeout = 1e9 if block else None
    t.run()
    return t


def rollback(tid: int):
    """rollback the parameters with given task id and checkpoint name

    Args:
        tid (int): task id
    """
    _s = login(verbose=False)

    try:
        config = get_config_by_tid(tid)
        _s.clear()
        for k, v in config.items():
            _s.create(k, v)
    except Exception as e:
        logger.error(f'Failed to rollback: {e}')


def get_data_by_tid(tid: int, signal: str, shape: tuple | list = [], **kwds) -> dict:
    """load data with given **task id(tid)** and **signal**

    Args:
        tid (int): task id
        signal (str): signal of the data
        shape (tuple|list): data shape like (*sweeps, *(shots, qubits))

    Keyword Arguments: Kwds
        plot (bool, optional): plot the result in QuarkStudio after the data is loaded(1D or 2D).

    Returns:
        dict: data、metainfo
    """
    info, data = get_dataset_by_tid(tid, signal, shape)

    if kwds.get('plot', False) and signal:
        task = Task({'meta': info['meta']})
        task.meta = info['meta']
        task.data = {signal: data[signal]}
        task.index = len(data[signal]) + 1
        plot(task)

    return {'data': data, 'meta': info['meta']}


def update_remote_wheel(filenames: list[str], host: str = '127.0.0.1'):
    """update the package on remote device

    Args:
        filenames (list[str]): packages (downloaded from PyPI) location
        host (str, optional): IP address of remote device. Defaults to '127.0.0.1'.
    """
    wheel = {}
    for filename in filenames:
        with open(filename, 'rb') as f:
            wheel[filename] = f.read()
    rs = connect('QuarkRemote', host=host, port=2087)
    logger.info(rs.install(wheel))

    for alias, info in rs.info().items():
        if isinstance(info, dict):
            rs.reopen(alias, info)
            logger.warning(f'{alias} restarted!')
    return rs


def plot(task: Task, append: bool = False):
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
        raw = np.abs(raw)

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
            _vs.clear()  # clear the canvas
            task.counter.clear()  # clear the task history
        else:
            task.counter[uname] += 1
        _vs.info(task.task)

    col = task.column if hasattr(task, 'column') else 4
    div, mod = divmod(raw.shape[-1], col)
    row = div if mod == 0 else div+1
    time.sleep(0.1)  # reduce the frame rate per second for better performance
    try:
        data = []  # outter list
        for r in range(row):
            rd = []  # inner list
            for c in range(col):
                idx = r*col+c

                try:
                    _name = task.app.name.split('.')[-1]
                    rid = task.app.record_id
                    _title = f'{_name}_{rid}_{task.title[idx][1]}'
                except Exception as e:
                    _title = f'{r}_{c}'

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
                        line['xdata'] = xdata[..., idx].squeeze()
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
                            line['xdata'] = xdata[..., idx]
                            line['ydata'] = ydata[..., idx]
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

                rd.append(cell)
            data.append(rd)
        if not append:
            _vs.plot(data)  # create a new canvas
        else:
            _vs.append(data)  # append new data to the canvas
    except Exception as e:
        logger.error(f'Failed to update viewer: {e}')


def translate(circuit: list = [(('Measure', 0), 'Q1001')], cfg: dict = {}, tid: int = 0, **kwds) -> tuple:
    """translate circuit to executable commands(i.e., waveforms or settings)

    Args:
        circuit (list, optional): qlisp circuit. Defaults to [(('Measure', 0), 'Q1001')].
        cfg (dict, optional): parameters of qubits in the circuit. Defaults to {}.
        tid (int, optional): task id used to load cfg. Defaults to 0.

    Returns:
        tuple: context that contains cfg, translated result
    """
    from quark.runtime import ccompile, initialize
    ctx = initialize(cfg if cfg else get_config_by_tid(tid))
    return ctx, ccompile(0, {}, circuit, signal='iq', prep=True, **kwds)


def preview(cmds: dict, keys: tuple[str] = ('',), calibrate: bool = False,
            start: float = 0, stop: float = 100e-6, srate: float = 0,
            unit: float = 1e-6, offset: float = 0, space: float = 0):
    import matplotlib.pyplot as plt
    from waveforms import Waveform

    from quark.runtime import calculate

    plt.figure()
    wf, index = {}, 0
    for target, value in cmds.items():
        if isinstance(value[1], Waveform):
            _target = value[-1]['target']  # .split('.')[0]
            if _target.startswith(tuple(keys)):
                if srate:
                    value[-1]['srate'] = srate
                else:
                    srate = value[-1]['srate']
                value[-1]['start'] = start
                value[-1]['LEN'] = stop
                value[-1]['filter'] = []
                if not calibrate:
                    for ch, val in value[-1]['calibration'].items():
                        try:
                            val['delay'] = 0
                        except Exception as e:
                            logger.error(f'{target, ch, val, e}')

                xt = np.arange(start, stop, 1/srate)/unit
                (_, _, cmd), _ = calculate('main', target, value)
                wf[_target] = cmd[1]+index*offset
                index += 1

                plt.plot(xt, wf[_target])
                plt.text(xt[-1], np.mean(wf[_target]), _target, va='center')
                plt.xlim(xt[0]-space, xt[-1]+space)
                # print(xt[0], _target)
    # plt.axis('off')
    # plt.legend(tuple(wf))
    return wf


def network():
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
def plotdemo():
    """demo for plot

    Example: iq scatter
        ``` {.py3 linenums="1"}
        _vs.clear()
        iq = np.random.randn(1024)+np.random.randn(1024)*1j
        _vs.plot([[
                {'i':{'xdata':iq.real-3,'ydata':iq.imag,'linestyle':'none','marker':'o','markersize':15,'markercolor':'b'},
                'q':{'xdata':iq.real+3,'ydata':iq.imag,'linestyle':'none','marker':'o','markersize':5,'markercolor':'r'},
                'hist':{'xdata':np.linspace(-3,3,1024),'ydata':iq.imag,"fillvalue":0, 'fillcolor':'r'}
                }
                ]]
                )
        ```

    Example: hist
        ``` {.py3 linenums="1"}
        _vs.clear()
        vals = np.hstack([np.random.normal(size=500), np.random.normal(size=260, loc=4)])
        # compute standard histogram, len(y)+1 = len(x)
        y,x = np.histogram(vals, bins=np.linspace(-3, 8, 40))
        data = [[{'hist':{'xdata':x,'ydata':y,'step':'center','fillvalue':0,'fillcolor':'g','linewidth':0}}]]
        _vs.plot(data)
        ```
    """
    row = 3  # row number
    col = 3  # column number
    # _vs.clear() # clear canvas
    for i in range(10):  # step number
        time.sleep(.2)
        try:
            data = []
            for r in range(row):
                rd = []
                for c in range(col):
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
                        line['title'] = f'aabb{r}_{c}'
                        line['legend'] = 'test'
                        line['xlabel'] = f'add'
                        line['ylabel'] = f'yddd'
                        # random.choice(['r', 'g', 'b', 'k', 'c', 'm', 'y', (31, 119, 180)])
                        line['linecolor'] = (31, 119, 180)
                        cell[f'test{j}2'] = line
                    rd.append(cell)
                data.append(rd)
            if i == 0:
                _vs.plot(data)
            else:
                _vs.append(data)
        except Exception as e:
            logger.error(e)
