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


import random
import string
import time
from datetime import datetime
from queue import Empty, Queue
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from .graph import TaskManager

bs = BackgroundScheduler()


def newid():
    time.sleep(0.01)
    return datetime.now().strftime('%y%m%d%H%M%S%f')+random.choice(string.digits)


nodetask = [('S21', 'Spectrum'), ('Spectrum', 'PowerRabi'), ('Spectrum', 'TimeRabi'),
            ('PowerRabi', 'Ramsey'), ('TimeRabi', 'Ramsey'), ('Ramsey', 'Spectrum')]


class Scheduler(object):
    def __init__(self) -> None:
        self.graph = TaskManager(nodetask)
        self.registry = {}
        self.queue = Queue()
        self.current: dict = {}

        Thread(target=self.run, name='Scheduler', daemon=True).start()

        bs.add_job(self.check, 'interval', seconds=20)
        bs.start()

    def check(self, method: str = 'Ramsey', group: dict = {'0': ['Q0', 'Q1'], '1': ['Q5', 'Q8']}):
        logger.info('start to check')
        broken = {}
        for idx, target in group.items():
            params = self.graph.check(method, target)
            broken.update(params)
        self.queue.put(broken)
        logger.info('checked')

    def run(self):
        self.check()
        while True:
            try:
                self.current: dict = self.queue.get()
                logger.info('start to calibrate')

                retry = 0
                while True:
                    failed = {}
                    for target, method in self.current.items():
                        params = self.graph.calibrate(method, target)
                        failed.update(params)
                    if not failed:
                        break
                    else:
                        pmethod = self.graph.parents(method)
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
