# MIT License

# Copyright (c) 2025 YL Feng

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
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

import numpy as np
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from quark.proxy import startup

from .executor import execute
from .graph import ChipManger, TaskManager

bs = BackgroundScheduler()
bs.add_executor(ThreadPoolExecutor(max_workers=1,
                                   pool_kwargs={'thread_name_prefix': 'QDAG Checking'}))


dag = {'task': {'graph': [('S21', 'Spectrum'), ('Spectrum', 'PowerRabi'), ('PowerRabi', 'Ramsey')],
                'check': {'period': 60, 'method': 'Ramsey'}
                },

       'chip': {'group': {'0': ['Q0', 'Q1'], '1': ['Q5', 'Q8']}}
       }
home = Path(startup['quarkserver']['home']) / 'cfg/dag.json'
home.parent.mkdir(parents=True, exist_ok=True)


class Scheduler(object):
    def __init__(self, dag: dict = dag) -> None:
        self.cmgr = ChipManger(dag['chip'])
        self.tmgr = TaskManager(dag['task'])

        try:
            self.cmgr.load(home)
        except Exception as e:
            print('creating dag ...........', e)
            for g, ts in self.cmgr['group'].items():
                for t in ts:
                    for n2 in self.tmgr.nodes:
                        self.cmgr.update(f'{t}.{n2}', deepcopy(self.cmgr.VT))

        self.start()

    def start(self):
        self.queue = Queue()
        self.current: dict = {}

        Thread(target=self.run, name='QDAG Calibration', daemon=True).start()

        bs.add_job(lambda: self.check(self.tmgr.checkin['method'], self.cmgr['group']),
                   'interval', seconds=self.tmgr.checkin['period'])
        bs.start()

        self.check(self.tmgr.checkin['method'], self.cmgr['group'])

    def check(self, method: str = 'Ramsey', group: dict = {'0': ['Q0', 'Q1'], '1': ['Q5', 'Q8']}):
        logger.info('start to check')
        ts = {tuple(v): method for v in self.expired(method, group).values()}
        failed = self.execute(ts, 'check')
        self.queue.put(failed)
        logger.info('checked')

    def expired(self, method: str = 'Ramsey', group: dict = {}, fmt: str = '%Y-%m-%d %H:%M:%S'):
        tx: dict[str, list] = {}
        tc = time.strftime(fmt)
        for g, v in group.items():
            for t in v:
                try:
                    lt, tid, status, value = self.cmgr.query(
                        f'{t}.{method}.history')[-1]
                except IndexError as e:
                    tx.setdefault(g, []).append(t)
                    continue

                lifetime = self.cmgr.query(f'{t}.{method}.lifetime')
                dt = datetime.strptime(tc, fmt) - datetime.strptime(lt, fmt)
                print(t, lt, status, tc, dt)
                if (dt.total_seconds() >= lifetime) or (status != 'green'):
                    tx.setdefault(g, []).append(t)
                else:
                    pass
        return tx

    def execute(self, tasks: dict, level: str = ''):
        failed = {}
        for target, method in tasks.items():
            history = self.cmgr.history([f'{t}.{method}' for t in target])
            summary: dict[str, tuple] = execute(method, target, level, history)
            tid = summary.pop('tid', -1)
            ts = []
            for t, (st, v) in summary.items():
                hh: list = self.cmgr.query(f'{t}.{method}.history')
                if len(hh) > 10:
                    hh.pop(0)
                hh.append((time.strftime('%Y-%m-%d %H:%M:%S'), tid, st, v))
                if st == 'red':
                    ts.append(t)
            failed[tuple(ts)] = method

        self.cmgr.checkpoint(home.as_posix())
        return failed

    def run(self):
        while True:
            try:
                self.current: dict = self.queue.get()
                logger.info('start to calibrate')

                retry = 0
                while True:
                    failed = self.execute(self.current, 'calibrate')
                    if not failed:
                        break
                    else:
                        method = list(failed.values())[0]
                        pmethod = self.tmgr.parents(method)
                        if not pmethod:
                            break
                        logger.warning(
                            f'failed to calibrate {method}, trying {pmethod[0]}')
                        for target in self.current:
                            self.current[target] = pmethod[0]
                logger.info('calibration finished')
            except Empty:
                pass
            except Exception as e:
                print(e)
