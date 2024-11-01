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


import numpy as np
from loguru import logger

from quark.proxy import loadv

from .systemq import Waveform, sample_waveform, wave_eval


def calculate(step: str, target: str, cmd: list, preview: dict = {}) -> tuple:
    """preprocess each command such as predistortion and sampling

    Args:
        step (str): step name, e.g., main/step1/...
        target (str): hardware channel like **AWG.CH1.Offset**
        cmd (list): command, in the type of tuple **(ctype, value, unit, kwds)**, where ctype
            must be one of **WRITE/READ/WAIT**, see `assembler.preprocess` for more details. 
        preview (dict): `QuarkCanvas` settings from `etc.preview`

    Returns:
        tuple: (preprocessed result, sampled waveform to be shown in the `QuarkCanvas`)

    Example:
        ``` {.py3 linenums="1"}
        calculate('main', 'AWG.CH1.Waveform',('WRITE',square(100e-6),'au',{'calibration':{}}))
        ```
    """
    ctype, value, unit, kwds = cmd

    line = {}

    if ctype != 'WRITE':
        return (step, target, cmd), line

    if isinstance(value, str):
        try:
            func = wave_eval(value)
        except SyntaxError as e:
            func = value
    else:
        func = value

    delay = 0

    # sm, _value = loadv(func) # _value[:] = _value*10

    if isinstance(func, Waveform):
        if target.startswith(tuple(kwds.get('filter', ['zzzzz']))):
            support_waveform_object = True
        else:
            support_waveform_object = False

        try:
            ch = kwds['target'].split('.')[-1]
            delay = kwds['calibration'][ch].get('delay', 0)
            cmd[1] = sample_waveform(func, kwds['calibration'][ch],
                                     sample_rate=kwds['srate'],
                                     start=kwds.get('start', 0), stop=kwds.get('LEN', 98e-6),
                                     support_waveform_object=support_waveform_object)
        except Exception as e:
            # KeyError: 'calibration'
            logger.error(f'Failed to sample waveform: {e}')
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
        cmd[1] = func

    cmd[-1] = {'sid': kwds['sid'], 'target': kwds['target'], 'srate': kwds['srate'],
               'track': kwds['track'], 'shared': kwds['shared']}

    try:
        line = plot(target, cmd, preview, delay)
    except Exception as e:
        logger.error(
            f"{'>'*30}'  failed to calculate waveform', {e}, {type(e).__name__}")

    return (step, target, cmd), line


def plot(target: str, cmd: dict, preview: dict = {}, delay: float = 0.0) -> dict:
    """sample waveforms needed to be shown in the `QuarkCanvas`

    Args:
        target (str): hardware channel
        cmd (dict): see calculator
        preview (dict, optional): from **etc.preview**. Defaults to {}.
        delay (float, optional): time delay for the channel. Defaults to 0.0.

    Returns:
        dict: _description_
    """
    if not preview.get('filter', []):
        return {}

    if cmd[-1]['target'].split('.')[0] not in preview['filter'] or cmd[-1]['sid'] < 0:
        return {}

    if target.endswith('Waveform'):

        srate = cmd[-1]['srate']
        t1, t2 = preview['range']
        xr = slice(int(t1*srate), int(t2*srate))

        val = cmd[1]
        if isinstance(val, Waveform):
            val = val.sample()

        xt = (np.arange(len(val))/srate)[xr] - delay
        yt = val[xr]

        try:
            nz = np.argwhere(np.abs(np.diff(yt)) > 1e-6).squeeze()
            nz = np.hstack((0, nz-1, nz, nz+1, len(yt)-1))
            # nz.sort(kind='mergesort')
            nz = np.unique(nz[nz >= 0])
            xx, yy = xt[nz], yt[nz]
        except Exception as e:
            xx, yy = xt, yt

        line = {'xdata': xx, 'ydata': yy, 'suptitle': cmd[-1]["sid"]}
        color = preview.get('color', None)
        if color and isinstance(color, (list, tuple)):
            line['color'] = tuple(color)

        return {cmd[-1]['target']: line}
    return {}


if __name__ == "__main__":
    import doctest
    doctest.testmod()
