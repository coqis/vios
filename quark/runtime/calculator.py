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

from quark.interface import Pulse, Workflow


def calculate(step: str, target: str, cmd: list, canvas: dict = {}) -> tuple:
    """preprocess each command such as predistortion and sampling

    Args:
        step (str): step name, e.g., main/step1/...
        target (str): hardware channel like **AWG.CH1.Offset**
        cmd (list): command, in the type of tuple **(ctype, value, unit, kwds)**, where ctype
            must be one of **WRITE/READ/WAIT**, see `assembler.preprocess` for more details. 
        canvas (dict): `QuarkCanvas` settings from `etc.canvas`

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

    sampled = target.startswith(tuple(kwds.get('filter', ['zzzzz'])))

    cmd[1], delay, offset = Workflow.calculate(
        value, **(kwds | {'sampled': sampled}))

    cmd[-1] = {'sid': kwds['sid'], 'target': kwds['target'], 'srate': kwds['srate'],
               'track': kwds['track'], 'shared': kwds['shared']}

    try:
        line = sample(target, cmd, canvas, delay, offset)
    except Exception as e:
        logger.error(
            f"{'>' * 30}'  failed to calculate waveform', {e}, {type(e).__name__}")

    return (step, target, cmd), line


def sample(target: str, cmd: dict, canvas: dict = {}, delay: float = 0.0, offset: float = 0.0) -> dict:
    """sample waveforms needed to be shown in the `QuarkCanvas`

    Args:
        target (str): hardware channel
        cmd (dict): see calculator
        canvas (dict, optional): from **etc.canvas**. Defaults to {}.
        delay (float, optional): time delay for the channel. Defaults to 0.0.
        offset (float, optional): offset added to the channel. Defaults to 0.0.

    Returns:
        dict: _description_
    """
    # if not canvas.get('filter', []):
    #     return {}
    if cmd[-1]['sid'] not in canvas.get('step', np.arange(1000000)):
        return {}

    if not canvas.get('reset', False) and cmd[-1]['sid'] < 0:
        return {}

    if cmd[-1]['target'].split('.')[0] not in canvas['filter']:
        return {}

    if target.endswith('Waveform'):

        srate = cmd[-1]['srate']
        t1, t2 = canvas['range']
        xr = slice(int(t1 * srate), int(t2 * srate))

        val = Pulse.sample(cmd[1]) + offset

        xt = (np.arange(len(val)) / srate)[xr] - delay
        yt = val[xr]

        line = {'xdata': xt, 'ydata': yt, 'suptitle': str(cmd[-1]["sid"])}
        color = canvas.get('color', None)
        if color and isinstance(color, (list, tuple)):
            line['color'] = tuple(color)

        return {cmd[-1]['target']: line}
    return {}


if __name__ == "__main__":
    import doctest
    doctest.testmod()
