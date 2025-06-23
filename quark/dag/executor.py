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
from importlib import import_module, reload

import numpy as np
from loguru import logger


def execute(method: str = 'ramsey', target: list[str] | tuple[str] = ['Q0', 'Q1'], level: str = 'check', history: dict = {}):
    try:
        # tid = mapping[method][level]['exp'](target)  # args
        logger.info(f'{method}{target} started')
        module = reload(import_module(f'run.{method}'))
        result, tid = module.calibrate(target)  # args
        fitted = module.analyze(result, level)
        summary = module.diagnose(fitted, level, history)

        logger.info(f'{tid} {method}{target} finished')

        return summary | {'tid': tid}
    except Exception as e:
        logger.error(f'{method}{target} failed: {e}')
        # summary = {'Q0': ('red', 5e9),
        #            'Q1': ('green', 5.353e9),
        #            'Q5': ('green', 5.123e9),
        #            'Q8': ('red', 5.1e9)}  # 所有比特
        summary = {q: ('red', 0) for q in target}  # 所有比特
        return summary


def analyze(method: str = 'Ramsey', result: dict = {}, level: str = ''):
    # fitted = mapping[method][level]['fit'](result)
    fitted = {'Q0.param.frequency': 5e9}
    return fitted


def diagnose(method: str = 'Ramsey', result: dict = {}, level: str = '', history: list = []):
    # status = mapping[method][level]['diag'](result)

    def f(): return float((4.4 + np.random.randn(1)) * 1e9)

    summary = {'Q0': ('red', f()), 'Q1': ('green', f()),
               'Q5': ('green', f()), 'Q8': ('red', f())}  # 所有比特
    #    'adaptive_args': {'Q0': [], 'Q1': []}  # 下次扫描参数
    #   'group': ('Q0', 'Q1', 'Q5', 'Q8') # 动态分组备用
    #    }

    return summary


def update(summary: dict):
    # for t, (status, value) in summary.items():
    #     if status == 'green':
    #         exp.s.update()
    print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] updated!', summary)
