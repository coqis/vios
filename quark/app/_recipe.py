from pathlib import Path

import dill
import numpy as np
from tqdm import tqdm


class Recipe(object):
    """**Recipe仅用于生成任务，没有编译或执行逻辑！**
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

        self.fillzero = True
        self.reset = []
        self._circuit: list[list] = []  # qlisp线路

        self.filename: str = 'baqis'  # 数据存储文件名, 位于桌面/home/dat文件夹下
        self.priority: int = 0  # 任务排队用, 越小优先级越高
        self.rules: list[str] = []  # 变量依赖关系列表
        self.loops: dict[str, list] = {}  # 变量列表

        self.__ckey = ''
        self.__dict = {}

    @property
    def circuit(self):
        return self._circuit

    @circuit.setter
    def circuit(self, cirq):
        if isinstance(cirq, list):
            self._circuit = cirq
        elif callable(cirq):
            self._circuit = {'module': cirq.__module__, 'name': cirq.__name__}

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

    def define(self, group: str, target: str, value: np.ndarray):
        """增加变量target到组group中

        Args:
            group (str): 变量组, 如对多个比特同时变频率扫描. 每个group对应一层循环, 多个group对应多层嵌套循环.
            target (str): 变量对应的标识符号, 任意即可.
            value (np.array): 变量对应的取值范围.

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

    def dumps(self, filepath: Path, localhost: bool = True):
        """将线路写入文件

        Args:
            filepath (Path): 线路待写入的文件路径

        Returns:
            list: 线路中的比特列表
        """
        qubits = []
        circuits = []
        with open(filepath, 'w', encoding='utf-8') as f:
            for i, cc in enumerate(tqdm(self.circuits(), desc='CircuitExpansion')):
                if localhost:
                    f.writelines(str(dill.dumps(cc))+'\n')
                else:
                    circuits.append(cc)

                if i == 0:
                    # 获取线路中读取比特列表
                    for ops in cc:
                        if isinstance(ops[0], tuple) and ops[0][0] == 'Measure':
                            qubits.append((ops[0][1], ops[1]))
        return qubits, circuits

    def export(self):
        return {'meta': {'name': f'{self.filename}:/{self.name}',
                         'priority': self.priority,
                         'other': {'shots': self.shots,
                                   'signal': self.signal,
                                   'align_right': self.align_right,
                                   'fillzero': self.fillzero,  # 编译开始前初始化所有通道
                                   'waveform_length': self.waveform_length,
                                   'shape': [len(v[0][1]) for v in self.loops.values()]
                                   } | {k: v for k, v in self.__dict.items() if not isinstance(v, (list, np.ndarray))}
                         },
                'body': {'step': {'main': ['WRITE', tuple(self.loops)],
                                  'trig': ['WRITE', 'trig'],
                                  'read': ['READ', 'read'],
                                  },
                         'init': self.reset,  # 实验开始前执行
                         'post': self.reset,  # 实验结束后执行
                         'cirq': self.circuit,
                         'rule': self.rules,
                         'loop': {} | self.loops
                         },
                }
