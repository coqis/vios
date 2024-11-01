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


"""扩展各Scanner以用于submit
"""

from abc import ABC, abstractmethod
from pathlib import Path

import dill
import numpy as np
from kernel.terminal.scan import App
from kernel.terminal.scan import Scan as _Scan
from loguru import logger
from qos_tools.experiment.scanner2 import Scanner as _Scanner
from tqdm import tqdm
from waveforms.dicttree import flattenDictIter
from waveforms.scan_iter import StepStatus


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

    def run(self, dry_run=False, quiet=False):
        try:
            self.toserver.run()
        except:
            import kernel
            from kernel.sched.sched import generate_task_id, get_system_info
            self.runtime.prog.task_arguments = (), {}
            self.runtime.prog.meta_info['arguments'] = {}
            self.runtime.id = generate_task_id()
            self.runtime.user = None
            self.runtime.system_info = {}  # get_system_info()
            kernel.submit(self, dry_run=dry_run)
            if not dry_run and not quiet:
                self.bar()

    def result(self, reshape=True):
        d = super(App, self).result(reshape)
        try:
            if self.toserver:
                for k, v in self.toserver.result().items():
                    try:
                        dk = np.asarray(v)
                        d[k] = dk.reshape([*self.shape, *dk[0].shape])
                    except Exception as e:
                        logger.error(f'Failed to fill result: {e}')
                        d[k] = v
                d['mqubits'] = self.toserver.title
        except Exception as e:
            logger.error(f'Failed to get result: {e}')
        return d

    def cancel(self):
        try:
            self.toserver.cancel()
        except:
            super(App, self).cancel()

    def bar(self, interval: float = 2.0):
        try:
            self.toserver.bar(interval)
        except:
            super(App, self).bar()

    def save(self):
        from kernel.sched.sched import session
        from storage.models import Record
        with session() as db:
            record = db.get(Record, self.record_id)
            record.data = self.result(self.reshape_record)

    def dumps(self, filepath: Path, localhost: bool = True):
        """将线路写入文件

        Args:
            filepath (Path): 线路待写入的文件路径

        Raises:
            TypeError: 线路由StepStatus得到

        Returns:
            list: 线路中的比特列表
        """
        qubits = []
        circuits = []
        with open(filepath, 'w', encoding='utf-8') as f:
            for step in tqdm(self.circuits(), desc='CircuitExpansion'):
                if isinstance(step, StepStatus):
                    cc = step.kwds['circuit']
                    if localhost:
                        f.writelines(str(dill.dumps(cc))+'\n')
                    else:
                        circuits.append(cc)

                    if step.iteration == 0:
                        # 获取线路中读取比特列表
                        for ops in cc:
                            if isinstance(ops[0], tuple) and ops[0][0] == 'Measure':
                                qubits.append((ops[0][1], ops[1]))
                else:
                    raise TypeError('Wrong type of step!')
            self.shape = [i+1 for i in step.index]
        return qubits, circuits


class Scan(_Scan, TaskMixin):
    """扩展Scanner3, 可直接替换原Scanner3
    """
    def __init__(self, name, *args, mixin=None, **kwds):
        super().__init__(name, *args, mixin=mixin, **kwds)
        self.patches = {}

    def variables(self) -> dict[str, list[tuple]]:
        loops = {}
        for k, v in self.loops.items():
            loops[k] = [(k, v, 'au')]
        return loops

    def circuits(self):
        from waveforms.scan.base import _try_to_call as try_to_call

        self.assemble()
        for step in self.scan():
            for k, v in self.mapping.items():
                self.set(k, step.kwds[v])
                if not isinstance(step.kwds[v], dict):
                    self.patches.setdefault((k, v), []).append(step.kwds[v])
            circ = try_to_call(self.circuit, (), step.kwds)
            step.kwds['circuit'] = circ
            yield step
        # self.assemble()
        # for step in self.scan():
        #     for k, v in self.mapping.items():
        #         self.set(k, step.kwds[v])
        #     yield step

    def resolve(self):
        """
        Examples: 解析获取变量定义
            >>> loops
            ({'x': [('x',  array([-0.5, -0.4, -0.3, -0.2, -0.1,  0. ,  0.1,  0.2,  0.3,  0.4,  0.5]), 'au'),
                    ('__tmp_0__', array([-0.5, -0.4, -0.3, -0.2, -0.1,  0. ,  0.1,  0.2,  0.3,  0.4,  0.5]), 'au'),
                    ('__tmp_1__', array([-0.5, -0.4, -0.3, -0.2, -0.1,  0. ,  0.1,  0.2,  0.3,  0.4,  0.5]), au'),
                    ('__tmp_2__', array([-0.5, -0.4, -0.3, -0.2, -0.1,  0. ,  0.1,  0.2,  0.3,  0.4,  0.5]), 'au'),
                    ('__tmp_3__',  array([-0.5, -0.4, -0.3, -0.2, -0.1,  0. ,  0.1,  0.2,  0.3,  0.4,  0.5]), 'au')],
            'frequency': [('frequency', array([-2000000.,  2000000.]), 'au')]},
            >>> deps
            ['<Q7.bias>=<x.__tmp_0__',
            '<Q25.bias>=<x.__tmp_1__',
            '<Q37.bias>=<x.__tmp_2__',
            '<Q17.bias>=<x.__tmp_3__'])
        """
        loops = self.variables()
        deps = []
        for axis, value in loops.items():
            _val = []
            for k, v in self.patches.items():
                self.patches[k] = np.unique(v)
                target, tmpvar = k
                if len(self.patches[k]) == len(value[0][1]):
                    _val.append((tmpvar, self.patches[k], 'au'))
                    deps.append(f'<{target}>=<{axis}.{tmpvar}>')
                elif len(self.patches[k]) == 1:
                    dep = f'<{target}>={self.patches[k][0]}'
                    if dep not in deps:
                        deps.append(dep)
            value.extend(_val)
        return loops, deps

    def dependencies(self) -> list[str]:
        deps = []
        for k, v in self.mapping.items():
            if isinstance(self[v], str):
                deps.append(f'<{k}>="{self[v]}"')
            elif isinstance(self[v], dict):
                for _k, _v in flattenDictIter(self[v]):
                    if isinstance(_v, str):
                        deps.append(f'<{k}.{_k}>="{_v}"')
                    else:
                        deps.append(f'<{k}.{_k}>={_v}')
            else:
                deps.append(f'<{k}>={self[v]}')
        return deps


class Scanner(_Scanner, TaskMixin):
    """扩展Scanner2, 可直接替换原Scanner2
    """
    def __init__(self, name: str, qubits: list[int], scanner_name: str = '', **kw):
        super().__init__(name, qubits, scanner_name, **kw)

    def variables(self) -> dict[str, list[tuple]]:
        loops = {}
        for k, v in self.sweep_setting.items():
            if isinstance(k, tuple):
                loops['temp'] = list(zip(k, v, ['au']*len(k)))
            else:
                if 'rb' in self.name.lower() and k == 'gate':
                    continue
                loops[k] = [(k, v, 'au')]
        return loops

    def circuits(self):
        for step in self.scan():
            # self.update({v_dict['addr']: step.kwds[k]
            #              for k, v_dict in self.sweep_config.items()})
            yield step

    def resolve(self):
        loops = self.variables()
        deps = []
        return loops, deps

    def dependencies(self) -> list[str]:
        return super().dependencies()
