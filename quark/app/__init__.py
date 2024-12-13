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

import sys
import time
from collections import defaultdict
from pathlib import Path
from threading import current_thread

import numpy as np
from loguru import logger

from quark import connect
from quark.proxy import Task

# get_record_by_rid, get_record_by_tid, sql
from ._data import get_config_by_tid

_sp = {}  # defaultdict(lambda: connect('QuarkServer', host, port))


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
        s = _sp[current_thread().name]
    except KeyError as e:
        s = _sp[current_thread().name] = connect('QuarkServer', host, 2088)

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

    from ._view import plot

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


def get_data_by_tid(tid: int, signal: str = '', **kwds) -> dict:
    """load data with given **task id(tid)** and **signal**

    Args:
        tid (int): task id
        signal (str): signal of the data

    Keyword Arguments: Kwds
        plot (bool, optional): plot the result in QuarkStudio after the data is loaded(1D or 2D).

    Returns:
        dict: data、metainfo
    """
    from ._data import get_dataset_by_tid
    from ._view import plot

    info, data = get_dataset_by_tid(tid, signal)

    signal = info['meta']['other']['signal']

    if kwds.get('plot', False) and signal:
        task = Task({'meta': info['meta']})
        task.meta = info['meta']
        task.data = {signal: data[signal]}
        task.index = len(data[signal]) + 1
        task.column = kwds.get('column', 4)
        plot(task, backend=kwds.get('backend', 'studio'))

    return {'data': data, 'meta': info['meta']}


def update_remote_wheel(wheel: str, index: str | Path, host: str = '127.0.0.1', sudo: bool = False):
    """update the package on remote device

    Args:
        wheel (str): package to be installed.
        index (str): location of required packages (downloaded from PyPI).
        host (str, optional): IP address of remote device. Defaults to '127.0.0.1'.
    """
    if sudo:
        assert sys.platform != 'win32', 'sudo can not be used on windows'

    links = {}
    for filename in Path(index).glob('*.whl'):
        with open(filename, 'rb') as f:
            print(f'{filename} will be installed!')
            links[filename.parts[-1]] = f.read()
    rs = connect('QuarkRemote', host=host, port=2087)
    logger.info(rs.install(wheel, links, sudo))

    for alias, info in rs.info().items():
        rs.reopen(alias)
        logger.warning(f'{alias} restarted!')
    return rs


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
