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


import os
from typing import Any

from loguru import logger

from quark.interface import Context, Pulse, Workflow
from quark.proxy import dumpv

cfg = Context({})


def initialize(snapshot, **kwds):
    """compiler context for current task

    Note:
        every task has its own context

    Args:
        snapshot (_type_): frozen snapshot for current task

    Returns:
        cfg (Context): Context to be used in compilation

    """
    if isinstance(snapshot, int):
        return os.getpid()
    cfg.reset(snapshot)
    cfg.initial = kwds.get('initial', {'restore': []})
    cfg.bypass = kwds.get('bypass', {})
    cfg._keys = kwds.get('keys', [])
    return cfg


def ccompile(sid: int, instruction: dict[str, list[tuple[str, str, Any, str]]], circuit: list, **kwds) -> tuple:
    """compile circuits to commands(saved in **instruction**)

    Args:
        sid (int): step index(starts from 0)
        instruction (dict): where commands are saved
        circuit (list): qlisp circuit(@HK)

    Returns:
        tuple: instruction, extra arguments

    Example: compile a circuit to instruction
        ``` {.py3 linenums="1"}
        from quark import connect
        s = connect('QuarkServer')
        cfg = initialize(s.snapshot())
        circuit = [(('Measure',0),'Q0503')]
        instruction, datamap =ccompile(0,circuit,signal='iq')

        print(instruction) # before assemble
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

        print(datamap)
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

    compiled, datamap = Workflow.qcompile(circuit, **(kwds | {'ctx': cfg}))

    # merge loop body with compiled result
    for step, _cmds in compiled.items():
        if step in instruction:
            instruction[step].extend(_cmds)
        else:
            instruction[step] = _cmds

    assemble(sid, instruction,
             prep=kwds.get('prep', False),
             hold=kwds.get('hold', False))

    if sid == 0:
        kwds['restore'] = cfg.initial
        kwds['clear'] = True
    logger.info(f'Step {sid} compiled >>>>>>>>>>>>>')

    return instruction, {'dataMap': datamap} | kwds


def assemble(sid: int, instruction: dict[str, list[tuple[str, str, Any, str]]], **kw):
    """assemble compiled instruction(see cccompile) to corresponding devices

    Args:
        sid (int): step index
        instruction (dict[str, list[str, str, Any, str]]): see cccompile

    Raises:
        TypeError: srate should be float, defaults to -1.0
    """

    try:
        query = kw.get('ctx', cfg).query
    except AttributeError as e:
        query = cfg.query

    for step, operations in instruction.items():
        if not isinstance(operations, list):
            break
        scmd = {}
        for ctype, target, value, unit in operations:
            if step.lower() == 'update':
                cfg.update(target, value)
                continue

            kwds = {'sid': sid, 'target': target,
                    'track': query('etc.server.review'),
                    'shared': query('etc.server.shared'),
                    'filter': query('etc.driver.filter')}
            if 'CH' in target or ctype == 'WAIT':
                _target = target
            else:
                try:
                    # logical channel to hardware channel
                    context = query(target.split('.', 1)[0])
                    mapping = query('etc.driver.mapping')
                    _target = decode(target, context, mapping)
                    kwds.update({"context": context})
                except (ValueError, KeyError) as e:
                    continue

                # save initial value to restore
                if sid == 0 and not kw.get('hold', False):
                    init = query(target.removesuffix(
                        '.I').removesuffix('.Q'))
                    cfg.initial['restore'].append((ctype, target, init, unit))

            # get sample rate from device
            if ctype != 'WAIT':
                dev = _target.split('.', 1)[0]
                kwds['srate'] = query(f'dev.{dev}.srate')
                if not isinstance(kwds['srate'], (float, int)):  # None, str
                    logger.critical(f'Failed to get srate: {dev}({target})!')
            cmd = [ctype, value, unit, kwds]

            # shared channels
            try:
                if _target in scmd and 'waveform' in target.lower():
                    if isinstance(scmd[_target][1], str):
                        scmd[_target][1] = Pulse.fromstr(scmd[_target][1])
                    if isinstance(cmd[1], str):
                        cmd[1] = Pulse.fromstr(cmd[1])
                    scmd[_target][1] += cmd[1]
                else:
                    scmd[_target] = cmd
            except Exception as e:
                logger.warning(f'Channel[{_target}] mutiplexing error: {e}')
                scmd[_target] = cmd
        instruction[step] = scmd

    # preprocess if True
    if kw.get('prep', True):
        return preprocess(sid, instruction)


# mapping logical channel to hardware channel
MAPPING = {
    "setting_LO": "LO.Frequency",
    "setting_POW": "LO.Power",
    "setting_OFFSET": "ZBIAS.Offset",
    "waveform_RF_I": "I.Waveform",
    "waveform_RF_Q": "Q.Waveform",
    "waveform_TRIG": "TRIG.Marker1",
    "waveform_DDS": "DDS.Waveform",
    "waveform_SW": "SW.Marker1",
    "waveform_Z": "Z.Waveform",
    "setting_PNT": "ADC.PointNumber",
    "setting_SHOT": "ADC.Shot",
    "setting_TRIGD": "ADC.TriggerDelay"
}


# command filters
SUFFIX = ('Waveform', 'Shot', 'Coefficient', 'TriggerDelay')


def decode(target: str, context: dict, mapping: dict = MAPPING) -> str:
    """decode target to hardware channel

    Args:
        target (str): target to be decoded like **Q0.setting.LO**
        context (dict): target location like **Q0**
        mapping (dict, optional): mapping relations. Defaults to MAPPING.

    Raises:
        KeyError: mapping not found
        ValueError: channel not found

    Returns:
        str: hardware channel like **AD.CH1.TraceIQ**
    """
    try:
        mkey = target.split('.', 1)[-1].replace('.', '_')
        chkey, quantity = mapping[mkey].split('.', 1)
    except KeyError as e:
        raise KeyError(f'{e} not found in mapping!')

    try:
        channel = context.get('channel', {})[chkey]
    except KeyError as e:
        raise KeyError(f'{chkey} not found!')

    if channel is None:
        raise ValueError('ChannelNotFound')
    elif not isinstance(channel, str):
        raise TypeError(
            f'Wrong type of channel of {target}, string needed got {channel}')
    elif 'Marker' not in channel:
        channel = '.'.join((channel, quantity))

    return channel


def preprocess(sid: int, instruction: dict[str, dict[str, list[str, Any, str, dict]]]):
    """filters and paramters 

    Args:
        sid (int): step index
        instruction (dict):instruction set like **{step: {target: [ctype, value, unit, kwds]}}**

    Example: instruction structure
        - step (str): step name, e.g., main/step1/step2
        - target (list): hardware channel, e.g., AWG.CH1.Waveform、AD.CH2.TraceIQ
            - ctype (str): command type, must be one of READ/WRITE/WAIT
            - value (Any): command value, None for READ, seconds for WAIT, arbitary for WRITE, see corresponding driver
            - unit (str): command unit, useless for now
            - kwds (dict):
                - sid (int): step index
                - track (list): list of sid to be tracked
                - target (str): original target like Q0101.waveform.Z
                - filter (list): sample waveform in the filter list to show in `QuarkCanvas`
                - srate (float): sampling rate
                - context (dict): target location like Q0101
    """
    if sid == 0:
        cfg.bypass.clear()
    bypass = cfg.bypass

    shared = []
    for step, operations in instruction.items():
        if not isinstance(operations, dict):
            break
        scmd = {}
        for target, cmd in operations.items():
            try:
                kwds = cmd[-1]
                # 重复指令缓存比较, 如果与上一步相同, 则跳过执行
                if target in bypass and target.endswith(SUFFIX) and Pulse.compare(bypass[target][0], cmd[1]):
                    continue
                bypass[target] = (cmd[1], kwds['target'])

                # context设置, 用于calculator.calculate
                context = kwds.pop('context', {})  # 即cfg表中的Qubit、Coupler等
                if context:
                    kwds['LEN'] = context['waveform']['LEN']
                    kwds['calibration'] = context['calibration']

                # if isinstance(cmd[1], Waveform):
                #     cmd[1].sample_rate = kwds['srate']
                #     cmd[1].start = 0
                #     cmd[1].stop = 1e-3  # kwds['LEN']
                #     cmd[1] = cmd[1].sample()

                if kwds['shared']:
                    sm, value = dumpv(cmd[1])
                    if sm:
                        shared.append(sm)
                        cmd[1] = value
            except Exception as e:
                logger.error(f'Failed to preprocess {target}, {e}!')
            scmd[target] = cmd
        instruction[step] = scmd

    return shared


# %%
if __name__ == "__main__":
    import doctest
    doctest.testmod()
