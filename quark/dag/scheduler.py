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
from queue import Empty, Queue
from threading import Thread

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from .graph import ChipManger, TaskManager
from .executor import execute

bs = BackgroundScheduler()
bs.add_executor(ThreadPoolExecutor(max_workers=1,
                                   pool_kwargs={'thread_name_prefix': 'QDAG Checking'}))


dag = {'task': {'edges': [('S21', 'Spectrum'), ('Spectrum', 'PowerRabi'), ('Spectrum', 'TimeRabi'),
                          ('PowerRabi', 'Ramsey'), ('TimeRabi', 'Ramsey')],
                'check': {'period': 60, 'method': 'Ramsey'}
                },

       'chip': {'group': {'0': ['Q0', 'Q1'], '1': ['Q5', 'Q8']},
                'Q0': {'frequency': {'status': 'OK',
                                     'lifetime': 200,
                                     'tolerance': 0.01,
                                     'history': {},
                                     'last_updated': time.time()}},
                'Q1': {'frequency': {'status': 'OK',
                                     'lifetime': 200,
                                     'tolerance': 0.01,
                                     'history': {},
                                     'last_updated': time.time()}},
                'C1': {'fidelity': {'status': 'OK',
                                    'lifetime': 200,
                                    'tolerance': 0.01,
                                    'history': {},
                                    'last_updated': time.time()}}
                }
       }


class Scheduler(object):
    def __init__(self, dag: dict = dag) -> None:
        self.cmgr = ChipManger(dag['chip'])
        self.tmgr = TaskManager(dag['task'])

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
        broken = {}
        for idx, target in group.items():
            params = execute(method, target)
            broken.update(params)
        self.queue.put(broken)
        logger.info('checked')

    def run(self):
        while True:
            try:
                self.current: dict = self.queue.get()
                logger.info('start to calibrate')

                retry = 0
                while True:
                    failed = {}
                    for target, method in self.current.items():
                        params = execute(method, target)
                        failed.update(params)
                    if not failed:
                        break
                    else:
                        pmethod = self.tmgr.parents(method)
                        if not pmethod:
                            break
                        logger.info(
                            f'failed to calibrate {method}, trying {pmethod[0]}')
                        for target in self.current:
                            self.current[target] = pmethod[0]
                logger.info('calibration finished')
            except Empty:
                pass
            except Exception as e:
                print(e)
