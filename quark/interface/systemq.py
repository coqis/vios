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


from copy import deepcopy

import numpy as np

from loguru import logger

try:
    # lib: systemq
    try:
        from lib import stdlib
    except ImportError as e:
        from systemq.lib import stdlib
except Exception as e:
    logger.critical('systemq may not be installed', e)
    raise e


# latest waveforms/qlisp/qlispc
from qlispc import Signal, get_arch, register_arch
from qlispc.arch.baqis import baqisArchitecture
from qlispc.arch.baqis.config import QuarkLocalConfig
from qlispc.kernel_utils import get_all_channels, qcompile, sample_waveform


# waveform==1.7.7
# from qlisp import Signal,get_arch,register_arch
# from lib.arch.baqis import baqisArchitecture
# from lib.arch.baqis_config import QuarkLocalConfig
# from qlisp.kernel_utils import get_all_channels,qcompile,sample_waveform


# waveforms.math: waveforms or waveform-math
from waveforms import Waveform, WaveVStack, square, wave_eval
from waveforms.namespace import DictDriver

register_arch(baqisArchitecture)


class Context(QuarkLocalConfig):

    def __init__(self, data) -> None:
        super().__init__(data)
        self.reset(data)
        self.initial = {}
        self.bypass = {}
        self._keys = []

    def reset(self, snapshot):
        self._getGateConfig.cache_clear()
        if isinstance(snapshot, dict):
            self._QuarkLocalConfig__driver = DictDriver(deepcopy(snapshot))
        else:
            self._QuarkLocalConfig__driver = snapshot

    def snapshot(self):
        return self._QuarkLocalConfig__driver

    def export(self):
        return self.snapshot().todict()


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
            return sig_tab[sig]
        except KeyError:
            pass
    elif isinstance(sig, Signal):
        return sig
    raise ValueError(f'unknow type of signal "{sig}".'
                     f" optional signal types: {list(sig_tab.keys())}")


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
                return (a*cls.WINDOW) == (b*cls.WINDOW)

            return a == b
        except Exception as e:
            logger.warning(f'Failed to compare waveform: {e}')
            return False


class Workflow(object):
    def __init__(self):
        pass

    @classmethod
    def qcompile(cls, circuit: list, **kwds):

        ctx: Context = kwds.pop('ctx')
        ctx._getGateConfig.cache_clear()
        ctx.snapshot().cache = kwds.pop('cache', {})

        # align_right = kwds.pop('align_right', True)
        # waveform_length = kwds.pop('waveform_length', 98e-6)
        if kwds.get('fillzero', False):  # whether to initialize all channels to zero()
            compiled = {'main': [('WRITE', target, 'zero()', '')
                                 for target in get_all_channels(ctx)]}
        else:
            compiled = {}

        _, (cmds, dmap) = qcompile(circuit,
                                   lib=kwds.get('lib', stdlib),
                                   cfg=kwds.get('cfg', ctx),
                                   signal=_form_signal(kwds.get('signal')),
                                   shots=kwds.get('shots', 1024),
                                   context=kwds.get('context', {}),
                                   arch=kwds.get('arch', 'baqis'),
                                   align_right=kwds.get('align_right', True),
                                   waveform_length=kwds.get('waveform_length', 98e-6))

        for cmd in cmds:
            ctype = type(cmd).__name__  # WRITE,TRIG,READ
            if ctype == 'WRITE':
                step = 'main'
            else:
                step = ctype
            op = (ctype, cmd.address, cmd.value, 'au')
            if step in compiled:
                compiled[step].append(op)
            else:
                compiled[step] = [op]
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

        # sm, _value = loadv(func) # _value[:] = _value*10

        if isinstance(func, Waveform):
            support_waveform_object = kwds.pop('sampled', False)

            try:
                ch = kwds['target'].split('.')[-1]
                delay = kwds['calibration'][ch].get('delay', 0)
                pulse = sample_waveform(func, kwds['calibration'][ch],
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

        return pulse, delay

    @classmethod
    def analyze(cls, data: dict, datamap: dict):
        return get_arch(datamap['arch']).assembly_data(data, datamap)
