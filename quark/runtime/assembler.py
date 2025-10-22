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
from copy import deepcopy
from typing import Any

from loguru import logger

from quark.interface import Pulse, Workflow, create_context

ctx = None  # create_context('baqis', {})


def initialize(snapshot, **kwds):
    """compiler context for current task

    Note:
        every task has its own context

    Args:
        snapshot (_type_): frozen snapshot for current task

    Returns:
        ctx (Context): Context to be used in compilation

    """
    global ctx

    if isinstance(snapshot, int):
        return os.getpid()

    ctx = create_context(kwds.get('arch', 'baqis'), snapshot)
    # ctx.reset(snapshot)
    # ctx.initial = kwds.get('initial', {'restore': []})
    ctx.bypass = kwds.get('bypass', {})
    ctx._keys = kwds.get('keys', [])
    if kwds.get('main', False):
        return ctx


def schedule(sid: int, instruction: dict[str, list[tuple[str, str, Any, str]]], circuit: list, **kwds) -> tuple:
    """compile circuits to commands(saved in **instruction**)

    Args:
        sid (int): step index(starts from 0)
        instruction (dict): where commands are saved
        circuit (list): qlisp circuit(@HK)

    Returns:
        tuple: instruction, extra arguments
    """
    logger.info(f'>>>>>>>> Step[{sid}] starts compiling ...')

    compiled, datamap = Workflow.qcompile(circuit, **(kwds | {'ctx': ctx}))

    # merge loop body with compiled result
    for step, _cmds in compiled.items():
        if step in instruction:
            _cmds.extend(instruction[step])
            instruction[step] = _cmds  # .extend(_cmds)
        else:
            instruction[step] = _cmds

    assemble(sid, instruction)

    if sid == 0:
        # kwds['restore'] = ctx.initial
        kwds['clear'] = True
    logger.info(f'>>>>>>>> Step[{sid}] is compiled!')

    return instruction, {'dataMap': datamap} | kwds


def assemble(sid: int, instruction: dict[str, list[tuple[str, str, Any, str]]], **kw):
    """assemble compiled instruction(see schedule) to corresponding devices

    Args:
        sid (int): step index
        instruction (dict[str, list[str, str, Any, str]]): see cccompile

    Raises:
        TypeError: srate should be float, defaults to -1.0
    """

    try:
        # for s.write and s.read
        query = kw.get('ctx', ctx).query
        ctx.bypass = {}  # clear bypass cache
    except AttributeError as e:
        query = ctx.query

    if sid < 0 and (atuo_clear := ctx.query('station', {}).get('auto_clear', {})):
        try:
            step = set.intersection(
                *(set(instruction), ['init', 'post'])).pop()
            instruction[step].extend([('WRITE', *cmd)
                                     for cmd in ctx.autofill(atuo_clear.get(step, []))])
        except KeyError:
            pass

    for step, operations in instruction.items():
        if not isinstance(operations, list):
            break
        scmd = {}
        for ctype, target, value, unit in operations:
            if step.lower() == 'update':
                ctx.update(target, value)
                continue

            if ctype not in ('READ', 'WRITE', 'WAIT'):
                logger.warning(f'Unknown command type: {ctype}!')
                continue

            kwds = {'sid': sid, 'target': target,
                    'shared': ctx.correct(query('etc.server.shared'), 0),
                    'filter': ctx.correct(query('etc.driver.filter'), [])}

            context = {}
            if 'CH' in target or ctype == 'WAIT':
                _target = target
            else:
                if not ctx.iscmd(target):
                    # logger.warning(f'Unknown target: {target}!')
                    continue
                try:
                    # logical channel to hardware channel
                    if target.endswith(('drive', 'probe', 'flux', 'acquire')):
                        try:
                            value = ctx.snapshot().cache.pop(target, value)
                        except Exception as e:
                            pass
                        context = deepcopy(query(target))
                        _target = context.pop('address', f'address: {target}')
                        # kwds['context'] = context
                    else:
                        # old
                        context = query(target.split('.', 1)[0])
                        mapping = query('etc.driver.mapping')
                        _target = decode(target, context, mapping)
                        # kwds.update({"context": context})
                except Exception as e:  # (ValueError, KeyError, AttributeError)
                    # logger.error(f'Failed to map {target}: {e}!')
                    continue

            if not (isinstance(_target, str) and _target and _target.count('.') == 2):
                logger.error(f'wrong target: {target}({_target})')
                continue

            # get sample rate from device
            dev, channel, quantity = _target.split('.')
            srate = query(f'dev.{dev}.srate')

            # context设置, 用于calculator.calculate
            try:
                kwds['calibration'] = {
                    'srate': srate,
                    'end': context['waveform']['LEN'],
                    'offset': context.get('setting', {}).get('OFFSET', 0)
                } | context['calibration'][target.split('.')[-1]]
                # kwds['setting'] = context['setting']
            except Exception as e:
                end = None
                if quantity == 'Waveform':
                    end = ctx.query('station', {}).get(
                        'waveform_length', 98e-6)
                kwds['calibration'] = context | {'end': end, 'srate': srate}
            cmd = [ctype, value, unit, kwds]

            # Merge commands with the same channel
            try:
                if _target in scmd and quantity == 'Waveform':
                    if isinstance(scmd[_target][1], str):
                        scmd[_target][1] = Pulse.fromstr(scmd[_target][1])
                    if isinstance(cmd[1], str):
                        cmd[1] = Pulse.fromstr(cmd[1])
                    scmd[_target][1] += cmd[1]
                    scmd[_target][-1].update(cmd[-1])
                else:
                    scmd[_target] = cmd
            except Exception as e:
                logger.warning(f'Channel[{_target}] mutiplexing error: {e}')
                scmd[_target] = cmd
        instruction[step] = scmd


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
SUFFIX = ('Waveform', )  # 'Shot', 'Coefficient', 'TriggerDelay')


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


# %%
if __name__ == "__main__":
    import doctest
    doctest.testmod()
