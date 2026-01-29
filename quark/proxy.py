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


import json
import os
import random
import string
import sys
from pathlib import Path
from queue import Empty, Queue

import numpy as np
from loguru import logger


def init(path: str | Path = Path.cwd() / 'quark.json'):
    global QUARK, HOME

    try:
        QUARK = {"server": {"home": Path.home() / "Desktop/home"}}
        for qjs in [Path(path), Path.home() / 'quark.json']:
            if qjs.exists():
                with open(qjs, 'r') as f:
                    print(f'Load settings from {qjs}')
                    QUARK = json.loads(f.read())
                    break
        HOME = Path(QUARK['server']['home']).resolve()
        HOME.mkdir(parents=True, exist_ok=True)
        if str(HOME) not in sys.path:
            sys.path.append(str(HOME))

        return QUARK, HOME
    except Exception as e:
        os.remove(qjs)
        logger.critical('Restart and try again!!!')
        raise KeyboardInterrupt


QUARK, HOME = init()


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


class QuarkProxy(object):

    def __init__(self, file: str = '') -> None:
        from .app import s

        self.tqueue = Queue(-1)
        self.ready = False
        setlog()

        try:
            s.login()
            self.server = s.qs()
        except Exception as e:
            logger.error('Failed to connect QuarkServer')

        if file:
            # if not file.endswith('.json'):
            #     raise ValueError('file should be a json file')
            # if not Path(file).exists():
            #     raise FileNotFoundError(f'file {file} not found')
            # with open(file, 'r') as f:
            #     dag = json.loads(f.read())

            (Path(HOME) / 'run').mkdir(parents=True, exist_ok=True)

            try:
                from .dag import Scheduler
                Scheduler(self.proxy().dag())
            except Exception as e:
                logger.error('Failed to start Scheduler')

    @classmethod
    def proxy(cls):
        from importlib import reload

        import run.proxy as rp
        return reload(rp)

    def get_circuit(self, timeout: float = 1.0):
        if not self.ready:
            return 'previous task unfinished'

        try:
            if not self.tqueue.qsize():
                raise Empty
            self.task = self.tqueue.get(timeout=timeout)
        except Empty as e:
            return 'no pending tasks'
        self.ready = False
        return self.task['body']['cirq'][0]

    def put_circuit(self, circuit):
        self.task['body']['cirq'] = [circuit]
        self.submit(self.task, suspend=False)
        self.ready = True

    def submit(self, task: dict, suspend: bool = False):
        from .app import submit

        if suspend:
            self.tqueue.put(task['body']['cirq'][0])
            return task['meta']['tid']

        logger.warning(f'\n\n\n{"#" * 80} task starts to run ...\n')

        # try:
        #     before = []  # insert circuit
        #     after = []  # append circuit
        # except Exception as e:
        #     before = []
        #     after = []
        #     logger.error(f'Failed to extend circuit: {e}!')
        mcq = task['meta']['other']['measure']  # cbits and qubits from Measure
        task['body']['post'] = [(t, v, 'au')
                                for t, v in self.proxy().clear(mcq)]
        circuit = [self.proxy().circuit(c, mcq) for c in task['body']['cirq']]
        task['body']['cirq'] = circuit

        qlisp = ',\n'.join([str(op) for op in circuit[0]])
        qasm = task['meta']['coqis']['qasm']
        logger.info(f"\n{'>' * 36}qasm:\n{qasm}\n{'>' * 36}qlisp:\n[{qlisp}]")

        t = submit(task)  # local machine
        eid = task['meta']['coqis']['eid']
        user = task['meta']['coqis']['user']
        logger.warning(f'task {t.tid}[{eid}, {user}] will be executed!')

        return t.tid

    def cancel(self, tid: int):
        return self.server.cancel(tid)

    def status(self, tid: int = 0):
        pass

    def result(self, tid: int, raw: bool = False):
        from .app import get_data_by_tid
        try:
            result = get_data_by_tid(tid, 'count')
            return result if raw else self.process(result)
        except Exception as e:
            return f'No data found for {tid}!'

    @classmethod
    def process(cls, result: dict):

        def dropout(data: dict, num: int = 0):
            while num > 0:

                tmp = np.cumsum(list(data.values()))
                val = np.random.randint(tmp[-1] + 1)
                idx = np.searchsorted(tmp, val)
                key = list(data)[idx]  # random.choice

                data[key] -= 1
                if data[key] == 0:
                    data.pop(key, 0)

                num -= 1

        meta = result['meta']
        coqis = meta.get('coqis', {})
        shots = coqis.get('shots', 1024)

        status = 'Failed'
        if meta['status'] in ['Finished', 'Archived']:
            try:
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

            dropout(dres, sum(dres.values()) - shots)

            try:
                if coqis['correct']:
                    cdres = cls.proxy().process(dres, meta['other']['measure'])
                else:
                    cdres = {}
            except Exception as e:
                cdres = dres
                logger.error(f'Failed to correct readout, {e}!')

        ret = {'count': {''.join((str(i) for i in k)): v for k, v in dres.items()},
               'corrected': {''.join((str(i) for i in k)): v for k, v in cdres.items()},
               'chip': coqis.get('chip', ''),
               'shots': shots,
               'circuit': coqis.get('circuit', ''),
               'transpiled': coqis.get('qasm', ''),
               'qlisp': coqis.get('qlisp', ''),
               'tid': meta['tid'],
               'error': meta.get('error', ''),
               'status': status,
               'created': meta['created'],
               'finished': meta['finished'],
               'system': meta['system']
               }
        return ret

    def snr(self, data):
        return data
