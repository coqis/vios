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


import sys
from copy import deepcopy
from importlib import import_module, reload
from itertools import permutations

import numpy as np
from loguru import logger
from qlispc.arch.baqis import QuarkLocalConfig

try:
    # lib: systemq
    try:
        from lib import stdlib
    except ImportError as e:
        from systemq.lib import stdlib
except Exception as e:
    logger.critical('systemq may not be installed', e)
    raise e


try:
    # qlispc
    try:
        from lib import DictDriver, Signal, get_arch, qcompile, sample_waveform
    except ImportError as e:
        try:
            from systemq.lib import (DictDriver, Signal, get_arch, qcompile,
                                     sample_waveform)
        except ImportError as e:
            from qlispc import Signal, get_arch
            from qlispc.kernel_utils import qcompile, sample_waveform
            from qlispc.namespace import DictDriver
except Exception as e:
    logger.critical('qlispc error', e)
    raise e


# waveforms.math: waveforms or waveform-math
from waveforms import Waveform, WaveVStack, square, wave_eval


def _form_signal(sig):
    """signal类型
    """
    sig_tab = {
        'trace': Signal.trace,
        'iq': Signal.iq,
        'state': Signal.state,
        'count': Signal.count,
        'diag': Signal.diag,
        'population': Signal.population,
        'trace_avg': Signal.trace_avg,
        'iq_avg': Signal.iq_avg,
        'remote_trace_avg': Signal.remote_trace_avg,
        'remote_iq_avg': Signal.remote_iq_avg,
        'remote_state': Signal.remote_state,
        'remote_population': Signal.remote_population,
        'remote_count': Signal.remote_count,
    }
    if isinstance(sig, str):
        if sig == 'raw':
            sig = 'iq'
        try:
            if '|' not in sig:
                return sig_tab[sig]
            _sig = None
            for s in sig.split('|'):
                _s = getattr(Signal, s)
                _sig = _s if not _sig else _sig | _s
            return _sig
        except KeyError:
            pass
    elif isinstance(sig, Signal):
        return sig
    raise ValueError(f'unknow type of signal "{sig}".'
                     f" optional signal types: {list(sig_tab.keys())}")


def get_gate_lib(lib: str):
    if lib:
        return reload(import_module(lib)).lib
    else:
        return stdlib


class Context(QuarkLocalConfig):

    def __init__(self, data) -> None:
        super().__init__(data)
        self.reset(data)
        self.initial = {}
        self.bypass = {}
        self._keys = []

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
    base = get_arch(arch).snapshot_factory
    Context.__bases__ = (base,)
    ctx = Context(data)
    ctx.arch = arch
    print(f'using {arch}: ', sys.modules[base.__module__])
    if hasattr(ctx, 'test'):
        print(ctx.test())
    return ctx


class Pulse(object):

    WINDOW = square(500e-3) >> 150e-3

    def __init__(self):
        pass

    @classmethod
    def fromstr(cls, pulse: str):
        return wave_eval(pulse)

    @classmethod
    def sample(cls, pulse: Waveform | np.ndarray):
        return pulse.sample() if isinstance(pulse, Waveform) else pulse

    @classmethod
    def compare(cls, a, b):
        try:
            if isinstance(a, WaveVStack) or isinstance(b, WaveVStack):
                return False

            if isinstance(a, Waveform) and isinstance(b, Waveform):
                return (a * cls.WINDOW) == (b * cls.WINDOW)

            return a == b
        except Exception as e:
            logger.warning(f'Failed to compare waveform: {e}')
            return False


class Workflow(object):
    def __init__(self):
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

        try:
            signal = _form_signal(kwds.get('signal'))
        except Exception as e:
            if not isinstance(circuit, list):
                raise TypeError(f'wrong type circuit: {circuit}')

            # [(('SET','Frequency'), 'MW.CH1'), (('GET','S'), 'NA.CH1')]
            cmds = []
            for op in circuit:
                if isinstance(op[0], tuple) and op[0][0] == 'GET':
                    cmds.append(('READ', f'{op[-1]}.{op[0][-1]}', '', 'au'))
            return {'read': cmds}, {'arch': 'undefined'}

        ctx: Context = kwds.pop('ctx')
        ctx._getGateConfig.cache_clear()
        ctx.snapshot().cache = kwds.pop('cache', {})

        compiled = {'main': [('WRITE', *cmd)
                             for cmd in kwds.get('precompile', [])]}

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
                                          waveform_length=kwds.get('waveform_length', 98e-6))

        for cmd in cmds:
            ctype = type(cmd).__name__  # WRITE, READ
            step = 'main' if ctype == 'WRITE' else ctype
            op = (ctype, cmd.address, cmd.value, 'au')
            compiled.setdefault(step, []).append(op)
        return compiled, dmap

    @classmethod
    def calculate(cls, value, **kwds):

        if isinstance(value, str):
            try:
                func = Pulse.fromstr(value)
            except SyntaxError as e:
                func = value
        else:
            func = value

        delay = 0
        offset = kwds.get('setting', {}).get('OFFSET', 0)

        # sm, _value = loadv(func) # _value[:] = _value*10

        if isinstance(func, Waveform):
            support_waveform_object = kwds.pop('sampled', False)

            try:
                # ch = kwds['target'].split('.')[-1]
                cali = {} if kwds['sid'] < 0 else kwds['calibration']  # [ch]
                delay = cali.get('delay', 0)
                pulse = sample_waveform(func,
                                        cali,
                                        sample_rate=kwds['srate'],
                                        start=kwds.get('start', 0), stop=kwds.get('LEN', 98e-6),
                                        support_waveform_object=support_waveform_object)
            except Exception as e:
                # KeyError: 'calibration'
                logger.error(f"Failed to sample: {e}(@{kwds['target']})")
                raise e
                if func.start is None:
                    func.start = 0
                if func.stop is None:
                    func.stop = 60e-6
                if func.sample_rate is None:
                    func.sample_rate = kwds['srate']

                if support_waveform_object:
                    cmd[1] = func
                else:
                    cmd[1] = func.sample()
        else:
            pulse = func

        return pulse, delay, offset

    @classmethod
    def analyze(cls, data: dict, datamap: dict):
        return get_arch(datamap['arch']).assembly_data(data, datamap)
