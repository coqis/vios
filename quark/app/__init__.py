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
from functools import wraps
from importlib import import_module, reload
from pathlib import Path
from threading import current_thread
from typing import Callable

import numpy as np
from loguru import logger
from srpc import connect, loads
from zee import flatten_dict

from quark.proxy import Task

# get_record_by_rid, get_record_by_tid, sql
from ._db import get_tid_by_rid
from ._recipe import Recipe


class Super(object):
    def __init__(self):
        pass

    def login(self, user: str = 'baqis', host: str = '127.0.0.1'):
        ss = login(user, host)

        if hasattr(self, 'update'):
            return

        for mth in ['start', 'query', 'write', 'read']:
            setattr(self, mth, getattr(ss, mth))

        for name in ['signup', 'update']:
            setattr(self, name, globals()[name])


_sp = {}  # defaultdict(lambda: connect('QuarkServer', host, port))

s = Super()


def signup(user: str, system: str, **kwds):
    """register a new **user** on the **system**

    Args:
        user (str): name of the user
        system (str): name of the system(i.e. the name of the cfg file)
    """
    ss = login()
    logger.info(ss.adduser(user, system, **kwds))
    ss.login(user)  # relogin


def login(user: str = 'baqis', host: str = '127.0.0.1', verbose: bool = True):
    """login to the server as **user**

    Args:
        user (str, optional): name of the user(same as signup). Defaults to 'baqis'.
        verbose (bool, optional): print login info if True. Defaults to True.

    Returns:
        _type_: a connection to the server
    """
    try:
        ss = _sp[current_thread().name]
    except KeyError as e:
        ss = _sp[current_thread().name] = connect('QuarkServer', host, 2088)

    m = ss.login(user)
    if verbose:
        logger.info(m)
    return ss


def submit(task: dict, block: bool = False, **kwds):
    """submit a task to a backend

    Args:
        task (dict): description of a task
        block (bool, optional): block until the task is done if True

    Keyword Arguments: Kwds
        preview (list): real time display of the waveform
        plot (bool): plot the result if True(1D or 2D), defaults to False.
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
                     'rule': ['⟨gate.Measure.Q1.params.frequency⟩ = ⟨Q0.setting.LO⟩+⟨Q2.setting.LO⟩+1250'],
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
    else:
        ss = login(verbose=False)

        trigger: list[str] = ss.query('station.triggercmds')
        task['body']['loop']['trig'] = [(t, 0, 'au') for t in trigger]

        # shots = task['meta']['other']['shots']
        # [ss.write(f'{t.rsplit(".", 1)[0]}.Shot', shots) for t in trigger]

        # waveforms to be previewed
        ss.update('etc.canvas.filter', kwds.get('preview', []))

    t = Task(task,
             timeout=1e9 if block else None,
             plot=plot if kwds.get('plot', False) else False)
    t.server = ss
    t.run()
    return t


def update(path: str, value, failed: list = []):
    ss = login(verbose=False)
    rs: str = ss.update(path, value)
    if rs.startswith('Failed'):
        if 'root' in rs:
            ss.create(path, {})
        else:
            path, _f = path.rsplit('.', 1)
            failed.append((_f, value))
            update(path, {}, failed)

    while failed:
        _f, v = failed.pop()
        path = f'{path}.{_f}'
        ss.update(path, v)


def diff(rida: int, ridb: int = 0, fmt: str = 'dict'):

    if fmt == 'dict':
        fda = flatten_dict(get_config_by_rid(rida))
        fdb = flatten_dict(get_config_by_rid(ridb))
        changes = {}
        for k in set(fda) | set(fdb):
            if k.startswith('usr') or k.endswith('pid'):
                continue

            if k in fda and k in fdb:
                try:
                    if isinstance(fda[k], np.ndarray) and isinstance(fdb[k], np.ndarray):
                        if not np.all(fda[k] == fdb[k]):
                            changes[k] = f'🔄 <{fdb[k]}> ⟼ <{fda[k]}>'
                    elif fda[k] != fdb[k]:
                        changes[k] = f'🔄 <{fdb[k]}> ⟼ <{fda[k]}>'
                except Exception as e:
                    print(e)
                    changes[k] = f'🔄 <{fdb[k]}> ⟼ <{fda[k]}>'
            elif k in fda and k not in fdb:
                changes[k] = f'✅ <> ⟼ <{fda[k]}>'
            elif k not in fda and k in fdb:
                changes[k] = f'❎ <{fdb[k]}> ⟼ <>'

        return changes
    elif fmt == 'git':
        from ._db import get_commit_by_tid

        cma, filea = get_commit_by_tid(get_tid_by_rid(rida))
        cmb, fileb = get_commit_by_tid(get_tid_by_rid(ridb))
        msg = ''
        for df in cma.diff(cmb, create_patch=True):
            # msg = str([0])
            if filea.name == df.a_path and fileb.name == df.b_path:
                msg = df.diff.decode('utf-8')

        return msg


def rollback(rid: int = 0, tid: int = 0):
    """rollback the parameters with given task id and checkpoint name

    Args:
        tid (int): task id
    """
    _s = login(verbose=False)

    try:
        if rid:
            config = get_config_by_rid(rid)
        elif tid:
            config = get_config_by_tid(tid)
        else:
            raise ValueError('one of rid and tid must be given!')
        _s.clear()
        for k, v in config.items():
            _s.create(k, v)
    except Exception as e:
        logger.error(f'Failed to rollback: {e}')


def lookup(start: str = '', end: str = '', name: str = '', fmt: str = '%Y-%m-%d-%H-%M-%S'):
    import pandas as pd

    from ._db import get_record_list_by_name
    from ._view import PagedTable

    days = time.time()-14*24*60*60
    start = time.strftime(fmt, time.localtime(days)) if not start else start
    end = time.strftime(fmt) if not end else end

    rs = get_record_list_by_name(name, start, end)[::-1]

    df = pd.DataFrame(rs)[[0, 1, 2, 6]]
    df.columns = ['rid', 'tid', 'name', 'status']

    paged_table = PagedTable(df, page_size=10)
    paged_table.show()

    # -------------------------------------------------------------------------
    # items_per_page = 10
    # total_pages = (len(df) + items_per_page - 1) // items_per_page
    # setting = {'current': 1}

    # output = widgets.Output()
    # prev_button = widgets.Button(description="Previous")
    # next_button = widgets.Button(description="Next")
    # page_label = widgets.Label(value=f"Page 1 of {total_pages}")

    # def display_table(page):
    #     setting['current'] = page
    #     current_page = setting['current']

    #     start_idx = (current_page - 1) * items_per_page
    #     end_idx = start_idx + items_per_page

    #     with output:
    #         output.clear_output()
    #         display(df.iloc[start_idx:end_idx])

    #     page_label.value = f"Page {current_page} of {total_pages}"

    # def on_prev_clicked(b):
    #     current_page = setting['current']
    #     if current_page > 1:
    #         display_table(current_page - 1)

    # def on_next_clicked(b):
    #     current_page = setting['current']
    #     if current_page < total_pages:
    #         display_table(current_page + 1)

    # prev_button.on_click(on_prev_clicked)
    # next_button.on_click(on_next_clicked)

    # display_table(setting['current'])

    # display(widgets.HBox([prev_button, next_button, page_label]))
    # display(output)


def get_config_by_rid(rid: int):
    return get_config_by_tid(get_tid_by_rid(rid))


def get_config_by_tid(tid: int) -> dict:
    # git config --global --add safe.directory path/to/cfg
    from ._db import get_commit_by_tid
    try:
        commit, file = get_commit_by_tid(tid)

        return loads(commit.tree[file.name].data_stream.read().decode())
    except Exception as e:
        logger.error(f'Failed to get config: {e}')
        return {}


def get_data_by_rid(rid: int, **kwds):
    return get_data_by_tid(get_tid_by_rid(rid), **kwds)


def get_data_by_tid(tid: int, **kwds) -> dict:
    """load data with given **task id(tid)**

    Args:
        tid (int): task id

    Keyword Arguments: Kwds
        plot (bool, optional): plot the result in QuarkStudio after the data is loaded(1D or 2D).

    Returns:
        dict: data & meta
    """
    from ._db import get_dataset_by_tid
    from ._view import plot

    info, data = get_dataset_by_tid(tid)

    signal = info['meta']['other']['signal'].split('|')[0]

    if kwds.get('plot', False) and signal:
        task = Task({'meta': info['meta']})
        task.meta = info['meta']
        task.data = {signal: data[signal]}
        task.index = len(data[signal]) + 1
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
        assert sys.platform != 'win32', 'sudo can not be used on Windows'

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

    lib = kwds.get('lib', '')
    if isinstance(lib, str) and lib:
        try:
            logger.warning(f'using lib: {lib}')
            kwds['lib'] = reload(import_module(lib)).lib
        except Exception as e:
            logger.error(f'lib: {e}')
    ctx = initialize(cfg if cfg else get_config_by_tid(tid))
    return ctx, ccompile(0, {}, circuit, signal='iq', prep=True, **kwds)


def preview(cmds: dict, keys: tuple[str] = ('',), calibrate: bool = False,
            start: float = 0, end: float = 100e-6, srate: float = 0,
            unit: float = 1e-6, offset: float = 0, space: float = 0, ax=None):
    import matplotlib.pyplot as plt
    from matplotlib.axes import Axes
    from waveforms import Waveform

    from quark.runtime import calculate

    ax: Axes = plt.subplot() if not ax else ax
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
                value[-1]['LEN'] = end
                value[-1]['filter'] = []
                if not calibrate:
                    for ch, val in value[-1]['calibration'].items():
                        try:
                            val['delay'] = 0
                        except Exception as e:
                            logger.error(f'{target, ch, val, e}')

                xt = np.arange(start, end, 1/srate)/unit
                (_, _, cmd), _ = calculate('main', target, value)
                wf[_target] = cmd[1]+index*offset
                index += 1

                ax.plot(xt, wf[_target])
                ax.text(xt[-1], np.mean(wf[_target]), _target, va='center')
                ax.set_xlim(xt[0]-space, xt[-1]+space)
    # plt.axis('off')
    # plt.legend(tuple(wf))
    return wf


def profile(functions: list[Callable] = []):
    # pycallgraph
    try:
        from line_profiler import LineProfiler
    except ImportError as e:
        return print(e)
    lp = LineProfiler()
    [lp.add_function(f) for f in functions]

    def wrapper(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            print(f'{func.__name__} started ...')
            lpf = lp(func=func)
            result = lpf(*args, **kwargs)
            lp.print_stats()
            print(f'{func.__name__} finished !!!')
            return result
        return wrapped
    return wrapper
