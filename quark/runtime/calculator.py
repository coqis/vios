# MIT License

# Copyright (c) 2021 YL Feng <fengyulong@pku.org.cn>

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
from loguru import logger

from quark.interface import Pulse, Workflow


def calculate(step: str, target: str, cmd: dict, canvas: dict = {}) -> tuple:
    """preprocess each command such as predistortion and sampling

    Args:
        step (str): step name, e.g., main/step1/...
        target (str): hardware channel like **AWG.CH1.Offset**
        cmd (dict): command like **{'ctype': ctype, 'value': value, 'unit': unit, 'cargs': cargs}**,\
            where ctype must be one of **WRITE/READ/WAIT**. 
        canvas (dict): `QuarkCanvas` settings from `etc.canvas`

    Returns:
        tuple: (preprocessed result, sampled waveform to be shown in the `QuarkCanvas`)

    Example:
        ``` {.py3 linenums="1"}
        calculate('main', 'AWG.CH1.Waveform',{'ctype': 'WRITE', 'value': square(100e-6), 'unit': 'au', 'cargs': {'calibration': {}}})
        ```
    """
    ctype = cmd['ctype']
    value = cmd['value']
    unit = cmd['unit']
    kwds = cmd['cargs']

    line = {}

    if ctype != 'WRITE':
        cmd['cargs'] = {'sid': kwds['sid'], 'target': kwds['target']}
        return (step, target, cmd), line

    isobject = target.startswith(tuple(kwds.get('filter', ['Waveform'])))

    cmd['value'], delay, offset, srate = Workflow.calculate(
        value, **(kwds | {'isobject': isobject}))

    # _value[:] = _value * 1000

    cmd['cargs'] = {'sid': kwds['sid'], 'target': kwds['target']}

    try:
        opts = cmd['cargs'] | canvas | {'type': target.split('.')[-1]}
        line = sample(cmd['value'], delay, offset, srate, **opts)
    except Exception as e:
        logger.error(
            f"{'>' * 30}'  failed to sample waveform', {e}, {type(e).__name__}")

    return (step, target, cmd), line


def sample(pulse, delay: float = 0.0, offset: float = 0.0, srate: float = 1e9, **kwds) -> dict:
    """sample waveforms needed to be shown in the `QuarkCanvas`

    Args:
        pulse (Pulse): waveform to be sampled
        delay (float, optional): time delay for the channel. Defaults to 0.0.
        offset (float, optional): offset added to the channel. Defaults to 0.0.
        srate (float, optional): sample rate of the channel. Defaults to 1e9.

    Returns:
        dict: _description_
    """
    # if not canvas.get('filter', []):
    #     return {}
    if kwds['sid'] not in kwds.get('step', np.arange(1000000)):
        return {}

    if not kwds.get('reset', False) and kwds['sid'] < 0:
        return {}

    if kwds['target'].split('.')[0] not in kwds.get('filter', []):
        return {}

    ptype = kwds.get('type', 'Waveform')
    if ptype.endswith(('Waveform', 'Offset')):
        t1, t2 = kwds.get('range', [0, 100e-6])
        xr = slice(int(t1 * srate), int(t2 * srate))

        if ptype == 'Waveform':
            val = Pulse.sample(pulse)  # + offset
        else:
            val = np.zeros(xr.stop - xr.start) + pulse

        xt = (np.arange(len(val)) / srate)[xr] - delay
        yt = val[xr]

        line = {'xdata': xt, 'ydata': yt, 'suptitle': str(kwds["sid"])}
        color = kwds.get('color', None)
        if color and isinstance(color, (list, tuple)):
            line['color'] = tuple(color)

        return {kwds['target']: line}
    return {}


if __name__ == "__main__":
    import doctest
    doctest.testmod()
