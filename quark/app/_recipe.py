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


import numpy as np


class Recipe(object):
    """**Recipe仅用于生成任务，没有编译/执行/数据处理等任何逻辑！**
    """

    def __init__(self, name: str, shots: int = 1024, signal: str = 'iq_avg',
                 align_right: bool = False, waveform_length: float = 98e-6):
        """初始化任务描述

        Args:
            name (str, optional): 实验名称, 如 S21. Defaults to ''.
            shots (int, optional): 触发次数, 1024的整数倍. Defaults to 1024.
            signal (str, optional): 采集信号. Defaults to 'iq_avg'.
            align_right (bool, optional): 波形是否右对齐. Defaults to False.
            waveform_length (float, optional): 波形长度. Defaults to 98e-6.
        """
        self.name = name
        self.shots = shots
        self.signal = signal
        self.align_right = align_right
        self.waveform_length = waveform_length

        self.fillzero = True  # 每一步编译开始前初始化所有通道
        self.initcmd = []  # [('AWG.CH1.Waveform', 'zero()', 'au')]
        self.postcmd = []  # [('AWG.CH1.Waveform', 'zero()', 'au')]
        self.__circuit: list[list] = []  # qlisp线路

        self.filename: str = 'baqis'  # 数据存储文件名, 位于桌面/home/dat文件夹下
        self.priority: int = 0  # 任务排队用, 越小优先级越高

        self.rules: list[str] = []  # 变量依赖关系列表
        self.loops: dict[str, list] = {}  # 变量列表

        self.__ckey = ''
        self.__dict = {}

    @property
    def circuit(self):
        return self.__circuit

    @circuit.setter
    def circuit(self, cirq):
        if isinstance(cirq, list):
            self.__circuit = cirq
        elif callable(cirq):
            self.__circuit = {'module': cirq.__module__, 'name': cirq.__name__}
        else:
            raise TypeError(f'invalid circuit: list[list] or function needed!')

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

        Raises:
            ValueError: _description_
            ValueError: _description_

        Examples: `self.rules`
            >>> self.assign('gate.R.Q0.params.frequency', value='freq.Q0')
            >>> self.assign('gate.R.Q1.params.amp', value=0.1)
            ['⟨gate.R.Q0.params.frequency⟩=⟨freq.Q0⟩', '⟨gate.R.Q1.params.amp⟩=0.1']
        """
        if isinstance(value, str):
            if '.' in value and value.split('.')[0] in self.loops:
                dep = f'⟨{path}⟩=⟨{value}⟩'
            else:
                dep = f'⟨{path}⟩="{value}"'
        else:
            dep = f'⟨{path}⟩={value}'

        if dep not in self.rules:
            self.rules.append(dep)

    def define(self, group: str, target: str, value: list | np.ndarray):
        """增加变量target到组group中

        Args:
            group (str): 变量组, 如对多个比特同时变频率扫描. 每个group对应一层循环, 多个group对应多层嵌套循环.
            target (str): 变量对应的标识符号, 任意即可.
            value (list | np.array): 变量对应的取值范围.

        Examples: `self.loops`
            >>> self.define('freq', 'Q0', array([2e6, 1e6,  0. ,  1e6,  2e6]))
            >>> self.define('freq', 'Q1', array([-3e6, -1.5e6,  0. ,  1.5e6,  3e6]))
            >>> self.define('amps', 'Q0', array([-0.2, -0.1,  0. ,  0.1,  0.2]))
            >>> self.define('amps', 'Q1', array([-0.24, -0.12,  0. ,  0.12,  0.24]))
            {'freq':[('Q0',array([2e6, 1e6,  0. ,  1e6,  2e6]), 'au')), ('Q1',array([-3e6, -1.5e6,  0. ,  1.5e6,  3e6]), 'au'))],
             'amps':[('Q0',array([-0.2, -0.1,  0. ,  0.1,  0.2]), 'au')), ('Q1',array([-0.24, -0.12,  0. ,  0.12,  0.24]), 'au'))]
            }
        """
        self.loops.setdefault(group, [])
        var = (target, value, 'au')

        if var not in self.loops[group]:
            self.loops[group].append(var)

    def export(self):
        """导出任务

        Returns:
            _type_: 任务描述，详见**submit**
        """
        return {'meta': {'name': f'{self.filename}:/{self.name}',
                         'priority': self.priority,
                         'other': {'shots': self.shots,
                                   'signal': self.signal,
                                   'align_right': self.align_right,
                                   'fillzero': self.fillzero,
                                   'waveform_length': self.waveform_length,
                                   'shape': [len(v[0][1]) for v in self.loops.values()]
                                   } | {k: v for k, v in self.__dict.items() if not isinstance(v, (list, np.ndarray))}
                         },
                'body': {'step': {'main': ['WRITE', tuple(self.loops)],
                                  'trig': ['WRITE', 'trig'],
                                  'read': ['READ', 'read'],
                                  },
                         'init': self.initcmd,
                         'post': self.postcmd,
                         'cirq': self.circuit,
                         'rule': self.rules,
                         'loop': {} | self.loops
                         },
                }
