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
import numpy as np
from collections import deque

from .executor import execute


class TaskNode(object):
    def __init__(self, name: str = '', parent: str = 'Q0') -> None:
        self.name = name
        self.parent = parent

        self.history = deque(maxlen=1000)
        self.tolerance = 0.01  # 偏差，如果参数偏差大于此值，更新参数
        self.last_updated = time.time()

        self._result = {}  # 任务执行结果，由测控系统返回

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, data):
        self._result = data  # 接收测量返回结果

    def run(self):
        task: dict = getattr(experiment, self.name)([self.parent])  # 任务描述
        target = task.pop('target', '')  # 待维护参数
        analyze = getattr(analyzer, task.pop('callback', ''))  # 分析方法

        result = execute(task)
        self.result = analyze(result)
        print(self.result)
        self.history.append(self.result)

        return self.check()

    def check(self):
        return True
        success = True
        if np.mean(self.history) - self.result > self.tolerance:
            success = False
        return success
