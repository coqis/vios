# MIT License

# Copyright (c) 2024 YL Feng <fengyulong@pku.org.cn>

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
from pathlib import Path

import numpy as np
from loguru import logger
from qlispc.arch.baqis import QuarkLocalConfig

from ._base import Pulse, Registry, Waveform

LIBCACHE = []

try:
    from systemq import get_arch, qcompile, qsample
except Exception as e:
    logger.critical('try `quark init` to fix this', e)
    raise e


def get_gate_lib(lib: str | dict):
    if not lib:
        raise ValueError('gate lib must be specified!')

    mp = lib
    if isinstance(lib, dict):
        gp = Path(sys.modules['glib'].__file__).parent
        lp = gp / 'gates' / lib['file']
        lh = hash(lib['code'])
        if lh not in LIBCACHE or not lp.exists():
            logger.warning(f'Updating gate lib: {lp}')
            LIBCACHE.append(lh)
            with open(lp, 'w', encoding='utf-8') as f:
                f.write(lib['code'])
            if len(LIBCACHE) > 1000:
                LIBCACHE.pop(0)
        mp = 'glib.gates.'
        mp = mp + lib['file'].replace('\\', '/').replace('/', '.')
        mp = mp.removesuffix('.py')

    return reload(import_module(mp)).lib


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
        self.bypass = {}
        self.opaques = {}

    def reset(self, snapshot):
        self._getGateConfig.cache_clear()
        if isinstance(snapshot, dict):  # local call
            self._QuarkLocalConfig__driver = Registry(deepcopy(snapshot))
            self._keys = list(snapshot.keys())
        else:
            self._QuarkLocalConfig__driver = snapshot
            self._keys = list(snapshot().nodes)

    def snapshot(self):
        return self._QuarkLocalConfig__driver

    def export(self):
        try:
            return self.snapshot().todict()
        except Exception as e:
            return self.snapshot().source

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

    def getGate(self, name, *qubits):
        # ------------------------- added -------------------------
        if name in ['Barrier', 'Delay', 'setBias', 'Pulse']:
            return {}
        return super().getGate(name, *qubits)


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
        """
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
        compiled['trig'] = [('WRITE', t, 0, 'au')
                            for t in kwds.get('triggercmds', [])]

        glib = get_gate_lib(kwds['lib'])
        ctx.opaques = glib.opaques  # Q.R/Q.Measure is not a command

        ctx.code, (cmds, dmap) = qcompile(circuit,
                                          lib=glib,
                                          cfg=kwds.get('ctx', ctx),
                                          signal=signal,
                                          shots=kwds['shots'],
                                          context={},
                                          arch=kwds['arch'],
                                          align_right=kwds['align_right'],
                                          waveform_length=kwds['waveform_length']
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
        if isinstance(value, str):
            try:
                func = Pulse.fromstr(value)
            except SyntaxError as e:
                func = value
        else:
            func = value

        cali = kwds['calibration']
        srate = cali['srate']  # must have key 'srate'
        delay = 0
        offset = 0

        if isinstance(func, Waveform):
            try:
                # ch = kwds['target'].split('.')[-1]
                delay = cali.get('delay', 0)
                offset = cali.get('offset', 0)
                pulse = qsample(func,
                                cali,
                                sample_rate=srate,
                                start=cali.get('start', 0),
                                stop=cali.get('end', 98e-6),
                                support_waveform_object=kwds.pop('isobject', False))
            except Exception as e:
                # KeyError: 'calibration'
                logger.error(f"Failed to sample: {e}(@{kwds['target']})")
                raise e
        elif isinstance(func, np.ndarray):
            # 失真校准
            # logger.debug(f"Calculate waveform distortion for {kwds['target']}")
            if not func.flags.writeable:
                func = func.copy()
            func[:] = Pulse.correct(func, cali=cali)
            pulse = func
        else:
            pulse = func

        return pulse, delay, offset, srate

    @classmethod
    def analyze(cls, data: dict, datamap: dict):
        return get_arch(datamap['arch']).assembly_data(data, datamap)
