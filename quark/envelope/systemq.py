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


class CompilerContext(QuarkLocalConfig):
    """context used by compiler
    """

    def __init__(self, data) -> None:
        super().__init__(data)
        self.reset(data)
        self.initial = {}
        self.bypass = {}
        self._keys = []

    def reset(self, snapshot):
        """reset for every task

        Args:
            snapshot (_type_): frozen snapshot from server for the task
        """
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
