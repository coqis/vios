# MIT License

# Copyright (c) 2024 YL Feng

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


import inspect
import sys

import numpy as np


class Recipe(object):
    """**Recipe仅用于生成任务，没有编译/执行/数据处理等任何逻辑！**
    """

    # --ignore=E731
    before_the_task: list[tuple] = []  # 任务开始前初始化
    before_compiling: list[tuple] = []  # 每步开始前初始化
    after_the_task: list[tuple] = []  # 任务结束后复位

    arch: str = 'baqis'
    align_right: bool = False
    waveform_length: float = 98e-6

    def __init__(self, name: str, shots: int = 1024, signal: str = 'iq_avg',
                 lib: str = '', filename: str = 'baiqs', priority: int = 0):
        """初始化任务描述

        Args:
            name (str, optional): 实验名称, 如 S21. Defaults to ''.
            shots (int, optional): 触发次数, 1024的整数倍. Defaults to 1024.
            signal (str, optional): 采集信号. Defaults to 'iq_avg'.
        """
        self.name = name
        self.shots = shots
        self.signal = signal
        self.lib = lib

        self.filename = filename  # 数据存储文件名, 位于桌面/home/dat文件夹下
        self.priority = priority  # 任务排队用, 越小优先级越高

        # [('AWG.CH1.Waveform', 'zero()', 'au')]
        self.initcmd = [(t, v, 'au') for t, v in Recipe.before_the_task]
        self.postcmd = [(t, v, 'au') for t, v in Recipe.after_the_task]
        self.prestep = [(t, v, 'au') for t, v in Recipe.before_compiling]

        self.verbose = False

        self.__circuit: list[list] = []  # qlisp线路
        self.__setting: list[tuple] = []  # 临时设置

        self.__rules: list[str] = []  # 变量依赖关系列表
        self.__loops: dict[str, list] = {}  # 变量列表

        self.__ckey = ''
        self.__dict = {}

    @property
    def circuit(self):
        return self.__circuit

    @circuit.setter
    def circuit(self, cirq):
        if isinstance(cirq, list) and cirq:
            if isinstance(cirq[0], list):
                self.__circuit = cirq
            else:
                self.__circuit = [cirq]
        elif isinstance(cirq, dict):
            self.__circuit = {'name': cirq['name'],
                              'code': cirq['code'],
                              'module': '__user__'}
        elif callable(cirq):
            self.__circuit = {'name': cirq.__name__,
                              'code': inspect.getsource(cirq),
                              'module': cirq.__module__}
            try:
                self.__circuit['file'] = sys.modules[cirq.__module__].__file__
            except Exception as e:
                self.__circuit['file'] = ''
        else:
            raise TypeError(f'invalid circuit: list[list] or function needed!')

    @property
    def setting(self):
        return self.__setting

    @setting.setter
    def setting(self, cmds: list[tuple]):
        for cmd, val in cmds:
            self[cmd] = val

    def __getitem__(self, key: str):
        try:
            self.__ckey = key
            return self.__dict[key]
        except KeyError as e:
            self.__ckey = ''
            return f'{key} not found!'

    def __setitem__(self, key: str, value):
        if hasattr(self, key):
            raise KeyError(f'{key} is already a class attribute!')

        if isinstance(value, (list, np.ndarray)):
            if '.' in key:
                # cfg表中参数，如'gate.Measure.Q0.params.frequency'
                # value = np.asarray(value)
                if self.__ckey:
                    self.define(self.__ckey, f'${key}', value)
                    self.__ckey = ''
                else:
                    target, group = key.rsplit('.', 1)
                    target = target.replace('.', '_')
                    self.define(group, target, value)
                    self.assign(key, f'{group}.{target}')
            else:
                self.define(key, 'def', value)
        else:
            self.assign(key, value)

        self.__dict[key] = value

    def assign(self, path: str, value):
        """变量依赖关系列表
        ### NOTE: '⟨' is not '<', '⟩' is not '>'
        - On Windows, press Windows + . (period) to open the emoji and symbol picker.
        - On Mac, press Control + Command + Space to open the Character Viewer.

        Args:
            path (str): 变量在cfg表中的完整路径, 如gate.R.Q1.params.amp
            value (Any, optional): 变量的值. Defaults to None.

        Examples: `self.__rules`
            >>> self.assign('gate.R.Q0.params.frequency', value='freq.Q0')
            >>> self.assign('gate.R.Q1.params.amp', value=0.1)
            ['⟨gate.R.Q0.params.frequency⟩=⟨freq.Q0⟩', '⟨gate.R.Q1.params.amp⟩=0.1']
        """
        if isinstance(value, str):
            if '.' in value and value.split('.')[0] in self.__loops:
                dep = f'⟨{path}⟩=⟨{value}⟩'
            else:
                dep = f'⟨{path}⟩="{value}"'
        else:
            dep = f'⟨{path}⟩={value}'

        if dep not in self.__rules:
            self.__rules.append(dep)

    def define(self, group: str, target: str, value: list | np.ndarray):
        """增加变量target到组group中

        Args:
            group (str): 变量组, 如对多个比特同时变频率扫描. 每个group对应一层循环, 多个group对应多层嵌套循环.
            target (str): 变量对应的标识符号, 任意即可.
            value (list | np.array): 变量对应的取值范围.

        Examples: `self.__loops`
            >>> self.define('freq', 'Q0', array([2e6, 1e6,  0. ,  1e6,  2e6]))
            >>> self.define('freq', 'Q1', array([-3e6, -1.5e6,  0. ,  1.5e6,  3e6]))
            >>> self.define('amps', 'Q0', array([-0.2, -0.1,  0. ,  0.1,  0.2]))
            >>> self.define('amps', 'Q1', array([-0.24, -0.12,  0. ,  0.12,  0.24]))
            {'freq':[('Q0',array([2e6, 1e6,  0. ,  1e6,  2e6]), 'au')), ('Q1',array([-3e6, -1.5e6,  0. ,  1.5e6,  3e6]), 'au'))],
             'amps':[('Q0',array([-0.2, -0.1,  0. ,  0.1,  0.2]), 'au')), ('Q1',array([-0.24, -0.12,  0. ,  0.12,  0.24]), 'au'))]
            }
        """
        self.__loops.setdefault(group, [])
        var = (target, value, 'au')

        if var not in self.__loops[group]:
            self.__loops[group].append(var)

    def export(self):
        """导出任务

        Returns:
            _type_: 任务描述，详见**submit**
        """
        return {'meta': {'name': f'{self.filename}:/{self.name}',
                         'priority': self.priority,
                         'other': {'shots': self.shots,
                                   'signal': self.signal,
                                   'lib': self.lib,
                                   'arch': self.arch,
                                   'align_right': self.align_right,
                                   'verbose': self.verbose,
                                   'precompile': self.prestep,
                                   'waveform_length': self.waveform_length,
                                   'shape': [len(v[0][1]) for v in self.__loops.values()],
                                   } | {k: v for k, v in self.__dict.items() if not isinstance(v, (list, np.ndarray))}
                         },
                'body': {'step': {'main': ['WRITE', tuple(self.__loops)],
                                  'trig': ['WRITE', 'trig'],
                                  'read': ['READ', 'read'],
                                  },
                         'init': self.initcmd,
                         'post': self.postcmd,
                         'cirq': self.circuit,
                         'rule': self.__rules,
                         'loop': {} | self.__loops
                         },
                }
