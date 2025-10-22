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


"""interface with systemq
"""


import json
import sys
from copy import deepcopy
from importlib import import_module, reload
from itertools import permutations
from pathlib import Path

import numpy as np
from loguru import logger
from qlispc.arch.baqis import QuarkLocalConfig
from waveforms import Waveform, WaveVStack, square, wave_eval

try:
    from glib import stdlib
except Exception as e:
    logger.critical('systemq may not be installed', e)
    raise e


try:
    try:
        from glib import DictDriver, get_arch, qcompile, sample_waveform
    except ImportError as e:
        from qlispc import get_arch
        from qlispc.kernel_utils import qcompile, sample_waveform
        from qlispc.namespace import DictDriver
except Exception as e:
    logger.critical('qlispc error', e)
    raise e


def get_gate_lib(lib: str):
    if lib:
        return reload(import_module(lib)).lib
    else:
        return stdlib


def split_circuit(circuit: list):
    """split circuit to commands and circuit

    Args:
        circuit (list): qlisp circuit

    Returns:
        tuple: commands, circuit
    """
    cmds = {'main': [], 'trig': [], 'read': []}
    try:
        circ = []
        for op, target in circuit:
            if isinstance(op, tuple):
                if op[0] == 'GET':
                    cmds['read'].append(
                        ('READ', f'{target}.{op[1]}', '', 'au'))
                elif op[0] == 'SET':
                    cmds['main'].append(
                        ('WRITE', f'{target}.{op[1]}', op[2], 'au'))
                else:
                    circ.append((op, target))
            else:
                circ.append((op, target))
    except Exception as e:
        circ = circuit
    return cmds, circ


class Context(QuarkLocalConfig):

    def __init__(self, data) -> None:
        super().__init__(data)
        self.reset(data)
        self.initial = {}
        self.bypass = {}
        self._keys = []
        self.opaques = stdlib.opaques

        self.__skip = ['Barrier', 'Delay', 'setBias', 'Pulse']

    def reset(self, snapshot):
        self._getGateConfig.cache_clear()
        if isinstance(snapshot, dict):
            self._QuarkLocalConfig__driver = DictDriver(deepcopy(snapshot))
        else:
            self._QuarkLocalConfig__driver = snapshot

    def snapshot(self):
        return self._QuarkLocalConfig__driver

    def export(self):
        try:
            return self.snapshot().todict()
        except Exception as e:
            return self.snapshot().dct

    def query(self, q, default=None):
        qr = super().query(q)
        return self.correct(qr, default)

    def correct(self, old, default=None):
        """set default value for key
        """
        if default is None:
            return old
        if isinstance(old, tuple) or (isinstance(old, str) and old.startswith('Failed')):
            return default
        return old

    def iscmd(self, target: str):
        """check if target is a command
        """
        parts = target.split('.')
        return not any(s in parts for s in self.opaques)

    def autofill(self, keys: list[str | tuple] = ['drive', 'flux']):
        """autofill commands with given keys"""

        if all(isinstance(cmd, tuple) for cmd in keys):
            # from before_the_task, after_the_task, before_compiling
            return keys

        cmds = []

        if not keys:
            return cmds

        for node, value in self.export().items():
            for key in set.intersection(*(set(value), keys)):
                cmds.append((f'{node}.{key}', 'zero()', 'au'))

        return cmds

    def getGate3(self, name, *qubits):
        # ------------------------- added -------------------------
        if name in self.__skip:
            raise Exception(f"gate {name} of {qubits} not calibrated.")

        if len(qubits) > 1:
            order_senstive = self.query(f"gate.{name}.__order_senstive__")
        else:
            order_senstive = False
        # ------------------------- added -------------------------

        if order_senstive is None:
            order_senstive = True
        if len(qubits) == 1 or order_senstive:
            ret = self.query(f"gate.{name}.{'_'.join(qubits)}")
            if isinstance(ret, dict):
                ret['qubits'] = tuple(qubits)
                return ret
            else:
                raise Exception(f"gate {name} of {qubits} not calibrated.")
        else:
            for qlist in permutations(qubits):
                try:
                    ret = self.query(f"gate.{name}.{'_'.join(qlist)}")
                    if isinstance(ret, dict):
                        ret['qubits'] = tuple(qlist)
                        return ret
                except:
                    break
            raise Exception(f"gate {name} of {qubits} not calibrated.")


def create_context(arch: str, data):

    if isinstance(data, dict):
        station = data.get('station', {})
    else:
        station = data.query('station')
        if not isinstance(station, dict):
            station = {}
    arch = station.get('arch', arch)

    base = get_arch(arch).snapshot_factory
    Context.__bases__ = (base,)
    ctx = Context(data)
    ctx.arch = arch
    print(f'using {arch} from ', sys.modules[base.__module__].__file__)
    # if hasattr(ctx, 'test'):
    #     print(ctx.test())
    return ctx


class Pulse(object):

    WINDOW = square(500e-3) >> 150e-3

    def __init__(self):
        pass

    @classmethod
    def typeof(cls, pulse: Waveform | np.ndarray):
        return 'object' if isinstance(pulse, Waveform) else 'array'

    @classmethod
    def fromstr(cls, pulse: str):
        return wave_eval(pulse)

    @classmethod
    def sample(cls, pulse: Waveform | np.ndarray, cali: dict = {}):
        if isinstance(pulse, Waveform) and cali:
            pulse >>= cali.get('delay', 0)
            pulse.sample_rate = cali['srate']
            pulse.start = 0
            pulse.stop = cali['end']
        return pulse.sample() if isinstance(pulse, Waveform) else pulse

    @classmethod
    def equal(cls, a, b):
        try:
            if isinstance(a, WaveVStack) or isinstance(b, WaveVStack):
                return False

            if isinstance(a, Waveform) and isinstance(b, Waveform):
                return (a * cls.WINDOW) == (b * cls.WINDOW)

            res = a == b
            if isinstance(res, np.ndarray):
                return np.all(res)
            return res
        except Exception as e:
            logger.warning(f'Failed to compare waveform: {e}')
            return False


class Workflow(object):
    def __init__(self):
        pass

    @classmethod
    def check(cls):
        try:
            with open(Path.home() / 'quark.json', 'r') as f:
                for path in json.loads(f.read()).get('path', []):
                    if path not in sys.path:
                        # logger.warning(f'add {path} to sys.path!')
                        sys.path.append(path)
        except Exception as e:
            pass

    @classmethod
    def qcompile(cls, circuit: list, **kwds):
        """compile circuits to commands

        Args:
            circuit (list): qlisp circuit

        Returns:
            tuple: compiled commands, extra arguments

        Example: compile a circuit to commands
            ``` {.py3 linenums="1"}

            >>> print(compiled)
            {'main': [('WRITE', 'Q0503.waveform.DDS', <waveforms.waveform.Waveform at 0x291381b6c80>, ''),
                    ('WRITE', 'M5.waveform.DDS', <waveforms.waveform.Waveform at 0x291381b7f40>, ''),
                    ('WRITE', 'ADx86_159.CH5.Shot', 1024, ''),
                    ('WRITE', 'ADx86_159.CH5.Coefficient', {'start': 2.4000000000000003e-08,
                                                            'stop': 4.0299999999999995e-06,
                                                            'wList': [{'Delta': 6932860000.0,
                                                                        'phase': 0,
                                                                        'weight': 'const(1)',
                                                                        'window': (0, 1024),
                                                                        'w': None,
                                                                        't0': 3e-08,
                                                                        'phi': -0.7873217091999384,
                                                                        'threshold': 2334194991.172387}]}, ''),
                    ('WRITE', 'ADx86_159.CH5.TriggerDelay', 7e-07, ''),
                    ('WRITE', 'ADx86_159.CH5.CaptureMode', 'alg', ''),
                    ('WRITE', 'ADx86_159.CH5.StartCapture', 54328, '')],
            'READ': [('READ', 'ADx86_159.CH5.IQ', 'READ', '')]
            }

            >>> print(datamap)
            {'dataMap': {'cbits': {0: ('READ.ADx86_159.CH5',
                                    0,
                                    6932860000.0,
                                    {'duration': 4e-06,
                                        'amp': 0.083,
                                        'frequency': 6932860000.0,
                                        'phase': [[-1, 1], [-1, 1]],
                                        'weight': 'const(1)',
                                        'phi': -0.7873217091999384,
                                        'threshold': 2334194991.172387,
                                        'ring_up_amp': 0.083,
                                        'ring_up_waist': 0.083,
                                        'ring_up_time': 5e-07,
                                        'w': None},
                                    3e-08,
                                    2.4000000000000003e-08,
                                    4.0299999999999995e-06)
                                    },
                        'signal': 2,
                        'arch': 'baqis'
                        }
            }
            ```
        """
        cls.check()

        compiled, circuit = split_circuit(circuit)
        rmap = {'signal': kwds['signal'], 'arch': 'undefined'}
        if not circuit:
            return compiled, rmap

        signal = 'iq' if rmap['signal'] in ['S', 'Trace'] else rmap['signal']

        ctx: Context = kwds.pop('ctx')
        ctx._getGateConfig.cache_clear()
        ctx.snapshot().cache = kwds.pop('cache', {})

        kwds.update(ctx.query('station', {}))
        precompile = kwds.get('auto_clear', kwds.pop(
            'precompile', []))  # for changing targets
        if isinstance(precompile, list):
            compiled['main'].extend([('WRITE', *cmd)
                                    for cmd in ctx.autofill(precompile)])

        ctx.code, (cmds, dmap) = qcompile(circuit,
                                          lib=get_gate_lib(
                                              kwds.get('lib', '')),
                                          cfg=kwds.get('ctx', ctx),
                                          signal=signal,
                                          shots=kwds.get('shots', 1024),
                                          context=kwds.get('context', {}),
                                          arch=kwds.get('arch', 'baqis'),
                                          align_right=kwds.get(
                                              'align_right', False),
                                          waveform_length=kwds.get(
                                              'waveform_length', 98e-6)
                                          )

        for cmd in cmds:
            ctype = type(cmd).__name__  # WRITE, READ
            step = 'main' if ctype == 'WRITE' else ctype
            op = (ctype, cmd.address, cmd.value, 'au')
            compiled.setdefault(step, []).append(op)
        if rmap['signal'] in ['S', 'Trace']:
            # for NA
            dmap = rmap
        return compiled, dmap

    @classmethod
    def calculate(cls, value, **kwds):
        cls.check()

        if isinstance(value, str):
            try:
                func = Pulse.fromstr(value)
            except SyntaxError as e:
                func = value
        else:
            func = value

        cali = kwds['calibration']  # {} if kwds['sid'] < 0 else
        srate = cali['srate']  # must have key 'srate'
        delay = 0
        offset = 0  # kwds.get('setting', {}).get('OFFSET', 0)

        if isinstance(func, Waveform):
            try:
                # ch = kwds['target'].split('.')[-1]
                delay = cali.get('delay', 0)
                offset = cali.get('offset', 0)
                pulse = sample_waveform(func,
                                        cali,
                                        sample_rate=srate,
                                        start=cali.get('start', 0),
                                        stop=cali.get('end', 98e-6),
                                        support_waveform_object=kwds.pop('isobject', False))
            except Exception as e:
                # KeyError: 'calibration'
                logger.error(f"Failed to sample: {e}(@{kwds['target']})")
                raise e
        else:
            pulse = func

        return pulse, delay, offset, srate

    @classmethod
    def analyze(cls, data: dict, datamap: dict):
        cls.check()
        return get_arch(datamap['arch']).assembly_data(data, datamap)
