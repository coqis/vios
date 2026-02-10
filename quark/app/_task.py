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


import asyncio
import textwrap
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import cached_property
from threading import current_thread

import numpy as np
from loguru import logger
from tqdm import tqdm

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

    def __init__(self, desc='test', total=100, postfix='running', disable: bool = False, leave: bool = True):
        super().__init__([], desc, total, postfix=postfix, disable=disable, leave=leave,
                         ncols=None, colour='blue', bar_format=self.bar_format, position=0)

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
        from ._db import get_record_by_tid
        return get_record_by_tid(self.tid)[0]

    def __repr__(self):
        return f'{self.name}(tid={self.tid})'  # rid={self.rid},

    def cancel(self):
        """cancel the task
        """
        self.server.cancel(self.tid)
        # self.clear()

    def circuit(self, sid: int = 0, draw: bool = False):
        circ = self.step(sid, 'cirq')[0][-1]
        if draw:
            from quark.circuit import QuantumCircuit
            QuantumCircuit().from_qlisp(circ).draw_simply()
        return circ

    def step(self, index: int, stage: str = 'ini') -> dict:
        """step details

        Args:
            index (int): step index
            stage (str, optional): stage name. Defaults to 'raw'.

        Examples: stage values
            - cirq: original qlisp circuit
            - ini: original instruction
            - raw: preprocessed instruction
            - ctx: compiler context
            - byp: filtered commands
            - trace: time consumption for each channel

        Returns:
            dict: _description_
        """
        review = ['cirq', 'ini', 'raw', 'ctx', 'byp']
        track = ['trace']
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
            from ._db import reshape
            shape = self.meta['other']['shape']
            data = {k: reshape(np.asarray(v), shape)
                    for k, v in self.data.items()}
        except Exception as e:
            logger.error(f'Failed to reshape data: {e}')
            data = self.data
        return {'data': data} | {'meta': self.meta}

    def run(self):
        """submit the task to the `QuarkServer`
        """
        self.stime = time.time()  # start time
        self.tid = self.server.submit(self.task)  # , keep=True)

    def raw(self, sid: int):
        return self.server.track(self.tid, sid, raw=True)

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
                        fv.append(f'--> {sk}: {_sv}')
                    msg = '\r\n'.join(fv)
                elif k == 'cirq':
                    msg = v.replace("\n", "\n    ")
                print(textwrap.fill(f'{k}: {msg}',
                                    width=120,
                                    replace_whitespace=False))
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
            from ._viewer import plot
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

    def bar(self, interval: float = 2.0, disable: bool = False, leave: bool = True):
        """task progress. 

        Tip: tips
            - Reduce the interval if result is empty.
            - If timeout is not None or not 0, task will be blocked, otherwise, the task will be executed asynchronously.

        Args:
            interval (float, optional): time period to retrieve data from `QuarkServer`. Defaults to 2.0.
            disable (bool, optional): disable the progress bar. Defaults to False.
            leave (bool, optional): whether to leave the progress bar after completion. Defaults to True

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
                    self.progress = Progress(desc=str(self),
                                             total=self.report(False)['size'],
                                             postfix=current_thread().name,
                                             disable=disable,
                                             leave=leave)
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


class TaskMixin(ABC):
    """扩展兼容App
    """

    def __new__(cls, *args, **kwds):
        for base in cls.__mro__:
            if base.__name__ == 'TaskMixin':
                for k in dir(base):
                    if not k.startswith('__') and k not in base.__abstractmethods__:
                        setattr(cls, k, getattr(base, k))
        return super().__new__(cls)

    @abstractmethod
    def variables(self) -> dict[str, list[tuple]]:
        """生成变量

        Examples: 形如
            >>> {'x':[('x1', [1,2,3], 'au'), ('x2', [1,2,3], 'au')],
                'y':[('y1', [1,2,3], 'au'), ('y2', [1,2,3], 'au')],
                'z':[('z1', [1,2,3], 'au'), ('z2', [1,2,3], 'au')]
                }
        """
        return {}

    @abstractmethod
    def dependencies(self) -> list[str]:
        """生成参数依赖

        Examples: 形如
            >>> [f'<gate.rfUnitary.{q}.params.frequency>=12345' for q in qubits]
        """
        return []

    @abstractmethod
    def circuits(self):
        """生成线路描述

        Examples: 形如
            >>> [c1, c2, c3, ...]
        """
        yield

    def run(self):
        pass

    # def result(self, reshape=True):
    #     d = super(App, self).result(reshape)
    #     try:
    #         if self.toserver:
    #             for k, v in self.toserver.result().items():
    #                 try:
    #                     dk = np.asarray(v)
    #                     d[k] = dk.reshape([*self.shape, *dk[0].shape])
    #                 except Exception as e:
    #                     logger.error(f'Failed to fill result: {e}')
    #                     d[k] = v
    #             d['mqubits'] = self.toserver.title
    #     except Exception as e:
    #         logger.error(f'Failed to get result: {e}')
    #     return d

    # def cancel(self):
    #     try:
    #         self.toserver.cancel()
    #     except:
    #         super(App, self).cancel()

    # def bar(self, interval: float = 2.0):
    #     try:
    #         self.toserver.bar(interval)
    #     except:
    #         super(App, self).bar()

    # def dumps(self, filepath: Path, localhost: bool = True):
    #     """将线路写入文件

    #     Args:
    #         filepath (Path): 线路待写入的文件路径

    #     Raises:
    #         TypeError: 线路由StepStatus得到

    #     Returns:
    #         list: 线路中的比特列表
    #     """
    #     qubits = []
    #     circuits = []
    #     with open(filepath, 'w', encoding='utf-8') as f:
    #         for step in tqdm(self.circuits(), desc='CircuitExpansion'):
    #             if isinstance(step, StepStatus):
    #                 cc = step.kwds['circuit']
    #                 if localhost:
    #                     f.writelines(str(dill.dumps(cc)) + '\n')
    #                 else:
    #                     circuits.append(cc)

    #                 if step.iteration == 0:
    #                     # 获取线路中读取比特列表
    #                     for ops in cc:
    #                         if isinstance(ops[0], tuple) and ops[0][0] == 'Measure':
    #                             qubits.append((ops[0][1], ops[1]))
    #             else:
    #                 raise TypeError('Wrong type of step!')
    #         self.shape = [i + 1 for i in step.index]
    #     return qubits, circuits
