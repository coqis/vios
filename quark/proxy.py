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
Abstract: **about proxy**
    `Task` and some other usefull functions
"""


import asyncio
import json
import os
import string
import sys
import time
from collections import defaultdict
from functools import cached_property
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path
from threading import current_thread

import numpy as np
from loguru import logger


try:
    qjs = Path.home() / 'quark.json'
    if qjs.exists():
        with open(qjs, 'r') as f:
            startup = json.loads(f.read())
            SYSTEMQ = str(Path(startup['root']).resolve())
            if SYSTEMQ not in sys.path:
                sys.path.append(SYSTEMQ)
except Exception as e:
    # logger.error(str(e))
    os.remove(qjs)
    logger.critical('Restart QuarkServer Again!!!')
    raise KeyboardInterrupt
    startup = {}


def setlog(prefix: str = ''):
    logger.remove()
    root = Path.home() / f"Desktop/home/log/proxy/{prefix}"
    path = root / "{time:%Y-%m-%d}.log"
    level = "INFO"
    config = {'handlers': [{'sink': sys.stdout,
                            'level': level},
                           {'sink': path,
                            'rotation': '00:00',
                            'retention': '10 days',
                            'encoding': 'utf-8',
                            'level': level,
                            'backtrace': False, }]}
    # logger.add(path, rotation="20 MB")
    logger.configure(**config)


TABLE = string.digits + string.ascii_uppercase


def basen(number: int, base: int, table: str = TABLE):
    mods = []
    while True:
        div, mod = divmod(number, base)
        mods.append(mod)
        if div == 0:
            mods.reverse()
            return ''.join([table[i] for i in mods])
        number = div


def baser(number: str, base: int, table: str = TABLE):
    return sum([table.index(c) * base**i for i, c in enumerate(reversed(number))])


def dumpv(value):
    # print('ccccccccccccccccccccccc', value)
    # if type(value).__name__ in ['Waveform', 'WaveVStack']:
    #     sl = ShareableList([dump(value)])
    #     result = ('ShareableList', sl.shm.name)
    if isinstance(value, np.ndarray):
        sm = SharedMemory(create=True, size=value.nbytes)
        buf = np.ndarray(value.shape, dtype=value.dtype, buffer=sm.buf)
        buf[:] = value[:]
        result = sm, ('SharedMemory', sm.name, buf.shape, buf.dtype.str)
        # sm.close()
    else:
        result = '', value
    return result


def loadv(value):
    if isinstance(value, tuple) and value[0] == 'SharedMemory':
        name, shape, dtype = value[1:]
        shm = SharedMemory(name=name)
        buf = np.ndarray(shape=shape, dtype=dtype, buffer=shm.buf)
        return shm, buf
    else:
        return '', value


try:
    from IPython import get_ipython

    shell = get_ipython().__class__.__name__
    if shell == 'ZMQInteractiveShell':
        from tqdm.notebook import tqdm  # jupyter notebook or qtconsole
    else:
        # ipython in terminal(TerminalInteractiveShell)
        # None(Win)
        # Nonetype(Mac)
        from tqdm import tqdm
except Exception as e:
    # not installed or Probably IDLE
    from tqdm import tqdm


class Progress(tqdm):
    bar_format = '{desc} {percentage:3.0f}%|{bar}|{n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]'

    def __init__(self, desc='test', total=100, postfix='running', disable: bool = False):
        super().__init__([], desc, total, ncols=None, colour='blue',
                         bar_format=self.bar_format, position=0, postfix=postfix, disable=disable)

    @property
    def max(self):
        return self.total

    @max.setter
    def max(self, value: int):
        self.reset(value)

    def goto(self, index: int):
        self.n = index
        self.refresh()

    def finish(self, success: bool = True):
        self.colour = 'green' if success else 'red'
        # self.set_description_str(str(success))


def math_demo(x, y):
    r"""Look at these formulas:

    The U3 gate is a single-qubit gate with the following matrix representation:

    $$
    U3(\theta, \phi, \lambda) = \begin{bmatrix}
        \cos(\theta/2) & -e^{i\lambda} \sin(\theta/2) \\
        e^{i\phi} \sin(\theta/2) & e^{i(\phi + \lambda)} \cos(\theta/2)
    \end{bmatrix}
    $$

    inline: $P(A_i|B)=\frac{P(B|A_i)P(A_i)}{\sum_j P(B|A_j)P(A_j)}$


    That is, remove $e^{i\alpha}$ from $U = e^{i\alpha} R_z(\phi) R_y(\theta) R_z(\lambda)$ and return
    $R_z(\phi) R_y(\theta) R_z(\lambda)$.

    $$
        U = e^{i \cdot p} U3(\theta, \phi, \lambda)
    $$

    $P(A_i|B)=\frac{P(B|A_i)P(A_i)}{\sum_j P(B|A_j)P(A_j)}$
    """


class Task(object):
    """Interact with `QuarkServer` from the view of a `Task`, including tracking progress, getting result, plotting and debugging
    """

    handles = {}
    counter = defaultdict(lambda: 0)
    server = None

    def __init__(self, task: dict, timeout: float | None = None, plot: bool = False) -> None:
        """instantiate a task

        Args:
            task (dict): see **quark.app.submit**
            timeout (float | None, optional): timeout for the task. Defaults to None.
            plot (bool, optional): plot result in `quark studio` if True. Defaults to False.
        """
        self.task = task
        self.timeout = timeout
        self.plot = plot

        self.data: dict[str, np.ndarray] = {}  # retrieved data from server
        self.meta = {}  # meta info like axis
        self.index = 0  # index of data already retrieved
        self.last = 0  # last index of retrieved data

    @cached_property
    def name(self):
        return self.task['meta'].get('name', 'Unknown')

    @cached_property
    def ctx(self):
        return self.step(-9, 'ctx')

    @cached_property
    def rid(self):
        from quark.app._db import get_record_by_tid
        return get_record_by_tid(self.tid)[0]

    def __repr__(self):
        return f'{self.name}(rid={self.rid}, tid={self.tid})'

    def cancel(self):
        """cancel the task
        """
        self.server.cancel(self.tid)
        # self.clear()

    def circuit(self, sid: int = 0):
        return self.step(sid, 'cirq')[0][-1]

    def step(self, index: int, stage: str = 'raw') -> dict:
        """step details

        Args:
            index (int): step index
            stage (str, optional): stage name. Defaults to 'raw'.

        Examples: stage values
            - ini: original instruction
            - raw: preprocessed instruction
            - ctx: compiler context
            - debug: raw data returned from devices
            - trace: time consumption for each channel

        Returns:
            dict: _description_
        """
        review = ['cirq', 'ini', 'raw', 'ctx', 'byp']
        track = ['debug', 'trace']
        if stage in review:
            r = self.server.review(self.tid, index)
        elif stage in track:
            r = self.server.track(self.tid, index)

        try:
            assert stage in review + track, f'stage should be {review + track}'
            return r[stage]
        except (AssertionError, KeyError) as e:
            return f'{type(e).__name__}: {e}'
        except Exception as e:
            return r

    def result(self):
        try:
            shape = self.meta['other']['shape']
            data = {k: np.asarray(v).reshape(*shape, *v[0].shape)
                    for k, v in self.data.items()}
        except Exception as e:
            logger.error(f'Failed to reshape data: {e}')
            data = self.data
        return {'data': data} | {'meta': self.meta}

    def run(self):
        """submit the task to the `QuarkServer`
        """
        self.stime = time.time()  # start time
        self.tid = self.server.submit(self.task, keep=True)

    def status(self, key: str = 'runtime'):
        if key == 'runtime':
            return self.server.track(self.tid)
        elif key == 'compile':
            return self.server.apply('status', user='task')
        else:
            return 'supported arguments are: {rumtime, compile}'

    def report(self, show=True):
        r: dict = self.server.report(self.tid)
        if show:
            for k, v in r.items():
                if k == 'size':
                    continue
                if k == 'exec':
                    fv = ['error traceback']
                    for sk, sv in v.items():
                        _sv = sv.replace("\n", "\n    ")
                        fv.append(f'--->{sk}: {_sv}')
                    msg = '\r\n'.join(fv)
                elif k == 'cirq':
                    msg = v.replace("\n", "\n    ")
                print(f'{k}: {msg}')
        return r

    def process(self, data: list[dict]):
        for dat in data:
            for k, v in dat.items():
                if k in self.data:
                    self.data[k].append(v)
                else:
                    self.data[k] = [v]

    def fetch(self):
        """result of the task
        """
        meta = True if not self.meta else False
        res = self.server.fetch(self.tid, start=self.index, meta=meta)

        if isinstance(res, str):
            return self.data
        elif isinstance(res, tuple):
            if isinstance(res[0], str):
                return self.data
            data, self.meta = res
        else:
            data = res
        self.last = self.index
        self.index += len(data)
        # data.clear()
        self.process(data)

        if self.plot:
            from quark.app._view import plot
            plot(self, not meta)

        return self.data

    def update(self):
        try:
            self.fetch()
        except Exception as e:
            logger.error(f'Failed to fetch result: {e}')

        status = self.status()['status']

        if status in ['Failed', 'Canceled']:
            self.stop(self.tid, False)
            return True
        elif status in ['Running']:
            self.progress.goto(self.index)
            return False
        elif status in ['Finished', 'Archived']:
            self.progress.goto(self.progress.max)
            if hasattr(self, 'app'):
                self.app.save()
            self.stop(self.tid)
            self.fetch()
            return True

    def clear(self):
        self.counter.clear()
        for tid, handle in self.handles.items():
            self.stop(tid)

    def stop(self, tid: int, success: bool = True):
        try:
            self.progress.finish(success)
            self.handles[tid].cancel()
        except Exception as e:
            pass

    def bar(self, interval: float = 2.0, disable: bool = False):
        """task progress. 

        Tip: tips
            - Reduce the interval if result is empty.
            - If timeout is not None or not 0, task will be blocked, otherwise, the task will be executed asynchronously.

        Args:
            interval (float, optional): time period to retrieve data from `QuarkServer`. Defaults to 2.0.

        Raises:
            TimeoutError: if TimeoutError is raised, the task progress bar will be stopped.
        """
        while True:
            try:
                status = self.status()['status']
                if status in ['Pending']:
                    time.sleep(interval)
                    continue
                elif status == 'Canceled':
                    return 'Task canceled!'
                else:
                    self.progress = Progress(desc=self.name,
                                             total=self.report(False)['size'],
                                             postfix=current_thread().name,
                                             disable=disable)
                    break
            except Exception as e:
                logger.error(
                    f'Failed to get status: {e},{self.report(False)}')
                if not hasattr(self.progress, 'disp'):
                    break

        if isinstance(self.timeout, float):
            while True:
                if self.timeout > 0 and (time.time() - self.stime > self.timeout):
                    msg = f'Timeout: {self.timeout}'
                    logger.warning(msg)
                    raise TimeoutError(msg)
                time.sleep(interval)
                if self.update():
                    break
        else:
            self.progress.clear()
            self.refresh(interval)
        self.progress.close()

    def refresh(self, interval: float = 2.0):
        self.progress.display()
        if self.update():
            self.progress.display()
            return
        self.handles[self.tid] = asyncio.get_running_loop(
        ).call_later(interval, self.refresh, *(interval,))


class QuarkProxy(object):

    def __init__(self) -> None:
        from quark.app import login

        self.server = login()
        setlog()

        try:
            from home.demo.run import dag

            from quark.dag import Scheduler
            self.scheduler = Scheduler(dag)
        except Exception as e:
            logger.error(f'Failed to start Scheduler: {e}')

    def submit(self, task: dict, block: bool = False):
        from quark.app import submit

        # by server
        # logger.info(f'task will be executed on local machine: {chip}!')
        logger.warning(f'\n\n\n{"#" * 80} task start to run ...\n')

        try:
            before = []
            after = []
        except Exception as e:
            before = []
            after = []
            logger.error(f'Failed to extend circuit: {e}!')
        circuit = [before + c + after for c in task['body']['cirq']]
        task['body']['cirq'] = circuit

        qlisp = ',\n'.join([str(op) for op in circuit[0]])
        qasm = task['meta']['coqis']['qasm']
        logger.info(f"\n{'>' * 36}qasm:\n{qasm}\n{'>' * 36}qlisp:\n[{qlisp}]")

        t: Task = submit(task, block=block)  # local machine
        if block:
            t.bar(0.2, disable=False)  # if block is True
        eid = task['meta']['coqis']['eid']
        user = task['meta']['coqis']['user']
        logger.warning(f'task {t.tid}[{eid}, {user}] will be executed!')

        return t.tid

    def cancel(self, tid: int):
        return self.server.cancel(tid)

    def status(self, tid: int = 0):
        pass

    def result(self, tid: int, raw: bool = False):
        from quark.app import get_data_by_tid
        try:
            result = get_data_by_tid(tid, 'count')
            return result if raw else self.process(result)
        except Exception as e:
            return f'No data found for {tid}!'

    @classmethod
    def process(cls, result: dict, dropout: bool = False):
        def _delete_dict(ret: dict, num: int = 0):
            while num > 0:
                tmp = np.cumsum(list(ret.values()))
                ran_num = np.random.randint(tmp[-1] + 1)
                ran_pos = np.searchsorted(tmp, ran_num)
                ret[list(ret.keys())[ran_pos]] -= 1
                if ret[list(ret.keys())[ran_pos]] == 0:
                    ret.pop(list(ret.keys())[ran_pos], 0)
                num -= 1

        meta = result['meta']
        coqis = meta.get('coqis', {})
        status = 'Failed'
        if meta['status'] in ['Finished', 'Archived']:
            try:
                # data: list[dict] = result['data']['count']
                signal = meta['other'].get('signal', 'count')
                data: list[np.ndarray] = result['data'][signal]
                status = 'Finished'
            except Exception as e:
                logger.error(f'Failed to postprocess result: {e}')

        dres, cdres = {}, {}
        if status == 'Finished':
            for dat in data:
                # for k, v in dat.items():  # dat[()][0]
                #     dres[k] = dres.get(k, 0)+v
                for kv in dat:
                    if kv[-1] < 0:
                        continue
                    base = tuple(kv[:-1] - 1)  # from 1&2 to 0&1
                    dres[base] = dres.get(base, 0) + int(kv[-1])

            try:
                if dropout:
                    shots = meta['other']['shots'] * \
                        len(meta['axis']['repeat']['repeat'])
                    _delete_dict(dres, shots - (shots // 1000) * 1000)
            except Exception as e:
                logger.error(f'Failed to dropout: {e}')

            try:
                if coqis['correct']:
                    from home.ylfeng.cloud import correct_readout
                    cdres = correct_readout(dres, meta['other']['measure'])
                else:
                    cdres = {}
            except Exception as e:
                cdres = dres
                logger.error(f'Failed to correct readout, {e}!')

        ret = {'count': {''.join((str(i) for i in k)): v for k, v in dres.items()},
               'corrected': {''.join((str(i) for i in k)): v for k, v in cdres.items()},
               'chip': coqis.get('chip', ''),
               'circuit': coqis.get('circuit', ''),
               'transpiled': coqis.get('qasm', ''),
               'qlisp': coqis.get('qlisp', ''),
               'tid': meta['tid'],
               'error': meta.get('error', ''),
               'status': status,
               'created': meta['created'],
               'finished': meta['finished'],
               'system': meta['system'],
               'token': coqis.get('token', '')
               }
        return ret

    def snr(self, data):
        return data
