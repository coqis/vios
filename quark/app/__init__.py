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
from pathlib import Path
from threading import current_thread
from typing import Callable

import numpy as np
from loguru import logger
from srpc import connect, loads
from zee import flatten_dict

from quark.proxy import Task

from . import _dp as dp
from ._db import get_tid_by_rid
from ._recipe import Recipe


class Super(object):
    def __init__(self):
        pass

    def tree(self, filename: str = '', d: dict = {}, name="root"):
        from rich.console import Console
        from rich.tree import Tree

        """print nested dict as a tree structure

        Args:
            d (dict): dict
            name (str, optional): root name. Defaults to "root".

        Returns:
            _type_: _description_
        """
        if filename and filename.endswith(('hdf5', 'zarr')):
            from ._db import get_tree_of_file
            d = get_tree_of_file(filename)
            if not d:
                return
            name = 'hdf5'

        root = Tree(f"[bold]{name}[/bold]")

        def add_nodes(parent, node):
            for k, v in node.items():
                if isinstance(v, dict):
                    # 递归添加子节点
                    child = parent.add(f"{k}")
                    add_nodes(child, v)
                else:
                    # 叶子普通值
                    parent.add(f"{k}: {v}")

        add_nodes(root, d)

        console = Console()
        console.print(root)

    def fig(self):
        from ._viewer import fig
        return fig

    def ssh(self, username: str, password: str, host: str = '192.168.1.42'):
        from quark.terminal import open_ssh
        return open_ssh(username, password, host)

    def terminal(self, command: str | None = None, cwd: str | None = None):
        from quark.terminal import open_terminal
        open_terminal(command, cwd)

    def init(self, path: str | Path = Path.cwd() / 'quark.json'):
        from quark.proxy import init
        init(path)

    def __repr__(self):
        try:
            return f'connection to {self.addr}'
        except Exception as e:
            return ''

    def qs(self):
        try:
            return self._s
        except Exception as e:
            raise AttributeError('Please login first!')

    @property
    def addr(self):
        try:
            return self.qs().raddr
        except Exception as e:
            return ('127.0.0.1', str(e))

    def user_exists(self):
        return self.qs().user_exists

    def login(self, user: str = 'baqis', host: str = '127.0.0.1', port: int = 2088):

        self._s = login(user, host, port)

        for mth in ['start', 'query', 'write', 'read', 'checkpoint', 'track', 'getid', 'cancel', 'report', 'review']:
            setattr(self, mth, getattr(self._s, mth))

        for name in ['signup', 'submit']:
            setattr(self, name, globals()[name])

    def ping(self):
        return ping(self.qs())

    def snapshot(self, tid: int = 0):
        if tid and self.addr[0] == '127.0.0.1':
            if tid < 1e10:
                return get_config_by_rid(tid)
            return get_config_by_tid(tid)
        else:
            return self.qs().snapshot(tid=tid)

    def result(self, tid: int, **kwds):
        if self.addr[0] == '127.0.0.1':
            if tid < 1e10:
                return get_data_by_rid(tid, **kwds)
            return get_data_by_tid(tid, **kwds)
        else:
            data = self.qs().load(tid)
            try:
                from ._db import reshape

                shape = data['meta']['other']['shape']
                data['data'] = {k: reshape(np.asarray(v), shape)
                                for k, v in data['data'].items()}
            except Exception as e:
                logger.error(f'Failed to reshape data: {e}')
            return data

    def lookup(self, start: str = '', end: str = '', name: str = ''):
        if self.addr[0] == '127.0.0.1':
            return lookup(start, end, name)
        else:
            return lookup(records=self.qs().load(0))

    def update(self, path: str, value, failed: list = []):
        qs = self.qs()
        rs: str = qs.update(path, value)
        if rs.startswith('Failed'):
            if path.count('.') == 0:
                qs.create(path, value)
            else:
                path, _f = path.rsplit('.', 1)
                failed.append((_f, value))
                self.update(path, {}, failed)

        while failed:
            _f, v = failed.pop()
            path = f'{path}.{_f}'
            qs.update(path, v)

    def delete(self, path: str):
        qs = self.qs()
        if path.count('.') > 0:
            qs.delete(path)
        else:
            qs.remove(path)

    def profile(self):
        return self.qs().progress(profile=True)


_sp = {}  # defaultdict(lambda: connect('QuarkServer', host, port))

s = Super()


def ping(qs):
    return qs.ping('hello') == 'hello'


def login(user: str = 'baqis', host: str = '127.0.0.1', port: int = 2088, verbose: bool = True):
    """login to the server as **user**

    Args:
        user (str, optional): name of the user(same as signup). Defaults to 'baqis'.
        verbose (bool, optional): print login info if True. Defaults to True.

    Returns:
        _type_: a connection to the server
    """
    uid = f'{current_thread().name}: {user}@{host}:{port}'
    try:
        qs = _sp[uid]
    except KeyError as e:
        qs = _sp[uid] = connect('QuarkServer', host, port)

    m: str = qs.login(user)
    qs.user_exists = isinstance(m, str) and not m.startswith('LookupError')
    if verbose:
        logger.info(m)
    return qs


def signup(user: str, system: str, **kwds):
    """register a new **user** on the **system**

    Args:
        user (str): name of the user
        system (str): name of the system(i.e. the name of the cfg file)
    """
    qs = s.qs()
    logger.info(qs.adduser(user, system, **kwds))
    qs.login(user)  # relogin


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

    if 'backend' in kwds:  # from master
        qs = kwds['backend']
    else:
        qs = s.qs()

        # trigger: list[str] = qs.query('station.triggercmds')
        station = s.query('station')
        task['body']['loop']['trig'] = [(t, 0, 'au')
                                        for t in station.get('triggercmds', [])]
        task['meta']['other'].update(station)

        # waveforms to be previewed
        qs.update('etc.canvas.filter', kwds.get('preview', []))

    t = Task(task,
             timeout=1e9 if block else None,
             plot=kwds.get('plot', False))
    t.server = qs
    t.run()
    return t


def rollback(rid: int = 0, tid: int = 0):
    """rollback the parameters with given task id and checkpoint name

    Args:
        tid (int): task id
    """
    qs = s.qs()

    try:
        if rid:
            config = get_config_by_rid(rid)
        elif tid:
            config = get_config_by_tid(tid)
        else:
            raise ValueError('one of rid and tid is required!')
        qs.clear()
        for k, v in config.items():
            qs.create(k, v)
    except Exception as e:
        logger.error(f'Failed to rollback: {e}')


def diff(new: int | dict, old: int | dict, fmt: str = 'dict'):

    if fmt == 'dict':
        fda = flatten_dict(get_config_by_rid(
            new) if isinstance(new, int) else new)
        fdb = flatten_dict(get_config_by_rid(
            old) if isinstance(old, int) else old)
        changes = {}
        for k in set(fda) | set(fdb):
            if k.startswith('usr') or k.endswith('pid'):
                continue

            if k in fda and k in fdb:
                try:
                    if isinstance(fda[k], np.ndarray) and isinstance(fdb[k], np.ndarray):
                        if not np.all(fda[k] == fdb[k]):
                            changes[k] = f'{fdb[k]}> ⇴ {fda[k]}'
                    elif fda[k] != fdb[k]:
                        changes[k] = f'{fdb[k]}> ⇴ {fda[k]}'
                except Exception as e:
                    print(e)
                    changes[k] = f'{fdb[k]} ⇴ {fda[k]}'
            elif k in fda and k not in fdb:
                changes[k] = f' ⥅ {fda[k]}'
            elif k not in fda and k in fdb:
                changes[k] = f'{fdb[k]} ⥇ '

        return changes
    elif fmt == 'git':
        from ._db import get_commit_by_tid
        assert isinstance(new, int), 'argument must be an integer'
        assert isinstance(old, int), 'argument must be an integer'

        cma, filea = get_commit_by_tid(get_tid_by_rid(new))
        cmb, fileb = get_commit_by_tid(get_tid_by_rid(old))
        msg = ''
        for df in cma.diff(cmb, create_patch=True):
            # msg = str([0])
            if filea.name == df.a_path and fileb.name == df.b_path:
                msg = df.diff.decode('utf-8')

        return msg


def lookup(start: str = '', end: str = '', name: str = '', fmt: str = '%Y-%m-%d-%H-%M-%S', records: list = []):
    import itables
    import pandas as pd

    from ._db import get_record_list_by_name
    from ._viewer import PagedTable

    itables.init_notebook_mode()
    itables.options.style = "width:100%"  # 让表格宽度为100%

    if not records:
        days = time.localtime(time.time() - 14 * 24 * 60 * 60)
        start = time.strftime(fmt, days) if not start else start
        end = time.strftime(fmt) if not end else end
        rs = get_record_list_by_name(name, start, end)[::-1]
    else:
        rs = records

    try:
        df = pd.DataFrame(rs)[[0, 1, 2, 6, 9, 10]]
        df.columns = ['rid', 'tid', 'name', 'status', 'created', 'finished']
    except Exception as e:
        # logger.error(f'Failed to get records: {e}')
        return pd.DataFrame()

    # paged_table = PagedTable(df, page_size=10)
    # paged_table.show()
    return df

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


def run_task_by_rid(rid: int):
    t = submit(get_task_by_rid(rid) | {'base': get_config_by_rid(rid)})
    t.bar()
    return t


def get_task_by_rid(rid: int):
    from ._db import get_dataset_by_tid

    return get_dataset_by_tid(get_tid_by_rid(rid), True)


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
    from ._viewer import plot

    retry = 3
    while retry > 0:
        # Windows: OSError: [Errno 0] Unable to synchronously open file (unable to lock file, errno = 0, error message = 'No error', Win32 GetLastError() = 33)
        # MacOSX: BlockingIOError: [Errno 35] Unable to synchronously open file (unable to lock file, errno = 35, error message = 'Resource Temporarily unavailable')
        try:
            info, data = get_dataset_by_tid(tid)
            break
        except Exception as e:
            logger.error(str(e))
            time.sleep(1)
            retry -= 1
            continue

    if kwds.get('plot', False):
        signal = info['meta']['other']['signal'].split('|')[0]
        task = Task({'meta': info['meta']})
        task.meta = info['meta']
        task.data = {signal: data[signal]}
        task.index = len(data[signal]) + 1
        return plot(task, backend=kwds.get('backend', 'studio'))

    return {'data': data, 'meta': info['meta']}


def update_remote_wheel(wheel: str, index: str | Path, host: str = '127.0.0.1', sudo: bool = False):
    """update the package on remote device

    Args:
        wheel (str): package to be installed.
        index (str): location of required packages (downloaded from PyPI).
        host (str, optional): IP address of remote device. Defaults to '127.0.0.1'.
        sudo (bool, optional): used on Mac or Linux. Defaults to False.
    """
    if not host:
        return None, 'host address is required!'

    links = {}
    for filename in Path(index).glob('*.whl'):
        with open(filename, 'rb') as f:
            print(f'{filename} added to links!')
            links[filename.parts[-1]] = f.read()
    rs = connect('QuarkRemote', host=host,
                 port=2087) if isinstance(host, str) else host
    sysinfo = rs.install(wheel, links, sudo)
    print(sysinfo)
    print(rs.restart())
    return rs, sysinfo


def translate(circuit: list = [(('Measure', 0), 'Q1001')], cfg: dict = {}, tid: int = 0, **kwds) -> tuple:
    """translate circuit to executable commands(i.e., waveforms or settings)

    Args:
        circuit (list, optional): qlisp circuit. Defaults to [(('Measure', 0), 'Q1001')].
        cfg (dict, optional): parameters of qubits in the circuit. Defaults to {}.
        tid (int, optional): task id used to load cfg. Defaults to 0.

    Returns:
        tuple: context that contains cfg, translated result
    """
    from quark.runtime import initialize, schedule

    ctx = initialize(cfg if cfg else get_config_by_tid(tid), main=True, **kwds)
    return ctx, schedule(0, {}, circuit, signal='iq', **kwds)


def preview(cmds: dict, keys: tuple[str] = ('',), calibrate: bool = True,
            start: float = 0, end: float = 0, srate: float = 0,
            unit: float = 1e-6, offset: float = 0, space: float = 0, ax=None):
    from copy import deepcopy

    import matplotlib.pyplot as plt
    from matplotlib.axes import Axes
    from waveforms import Waveform

    from quark.runtime import calculate

    ax: Axes = plt.subplot() if not ax else ax
    wf, index = {}, 0
    for target, value in deepcopy(cmds).items():
        if isinstance(value[1], (Waveform, np.ndarray)):
            _target = value[-1]['target']
            if _target.split('.')[0] in keys:
                value[-1]['filter'] = []

                calibration = value[-1].get('calibration', {})

                if srate:
                    calibration['srate'] = srate
                else:
                    srate = calibration['srate']

                if start:
                    calibration['start'] = start
                else:
                    start = calibration.get('start', 0)

                if end:
                    calibration['end'] = end
                else:
                    end = calibration.get('end', 100e-6)

                if not calibrate:
                    try:
                        calibration['delay'] = 0
                    except Exception as e:
                        logger.error(f'{target, e}')

                xt = np.arange(start, end, 1 / srate) / unit
                (_, _, cmd), _ = calculate('main', target, value)
                wf[_target] = cmd[1] + index * offset
                index += 1

                ax.plot(xt, wf[_target])
                ax.text(xt[-1], wf[_target][-1], _target, va='center')
                ax.set_xlim(xt[0] - space, xt[-1] + space)
    # plt.axis('off')
    # plt.legend(tuple(wf))
    return wf
