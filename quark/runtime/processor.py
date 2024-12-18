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
from zee import flatten_dict

from quark.interface import Workflow


def demodulate(raw_data, **kwds):
    pass


def process(raw_data, **kwds):
    """processing data

    Args:
        raw_data (dict): result from devices

    Returns:
        result (dict): processed data in the form of {'key1':np.array,'key2':np.array, ...}

    Example: raw_data
        ``` {.py3 linenums="1"}
        {'main': {'DAx86_153': {'CH1.Waveform': None}, 
                                'DAx86_50': {'CH1.Waveform': None}, 
                                'ADx86_159': {'CH10.CaptureMode': None,
                                              'CH11.CaptureMode': None, 
                                              'CH10.StartCapture': None, 
                                              'CH11.StartCapture': None}}, 
         'tigger': {'Trigger': {'CH1.TRIG': None}}, 
         'READ': {'ADx86_159': {'CH10.IQ': (array([[16.62256833],
                                                   ...,
                                                   [14.58617952]]), 
                                            array([[4.0120324 ],
                                                   ...,
                                                   [4.97671573]])), 
                                'CH11.IQ': (array([[14.6038444],
                                                   ...,
                                                   [15.33774413]]),
                                            array([[10.76387584],
                                                   ...,
                                                   [11.23863306]]))}}
        }
        ```
    """
    # print('ddddddddddoooooooooooooooooooooo', kwds)
    # print("=============================================", raw_data)

    dataMap = kwds.get('dataMap', {'arch': 'baqis'})
    result = {}

    try:

        if 'arch' in dataMap and dataMap['arch'] == 'general':
            return raw_data['READ']['AD']
        elif 'arch' in dataMap and dataMap['arch'] == 'undefined':
            data = flatten_dict(raw_data)
            for k, v in data.items():
                if kwds['signal'] in k:
                    result[kwds['signal']] = v
            # if 'READ' in raw_data:
            #     print(raw_data)
            #     nadata = result['data'] = raw_data['READ']['NA']
            #     if 'CH1.Trace' in nadata:
            #         result['data'] = raw_data['READ']['NA'].pop('CH1.Trace')
            #     elif 'CH1.S' in nadata:
            #         result['data'] = raw_data['READ']['NA'].pop('CH1.S')
            # result['extra'] = raw_data
        else:
            result = Workflow.analyze(raw_data, dataMap)

            for k, v in result.items():
                if isinstance(v, dict):  # k: count or remote_count
                    # v: {(0, 0): 100, (0, 1): 1, (1, 0): 2, (1, 1): 100}
                    base = np.array(tuple(v))
                    count = np.array(tuple(v.values()))
                    # result[k] = np.hstack((base, count[:, None]))
                    nb, nq, shots = *base.shape, kwds.get('shots', 1024)
                    # _k = k.removeprefix('remote_')
                    result[k] = np.zeros((min(2**nq, shots), nq+1), int) - 1
                    result[k][:nb] = np.hstack((base, count[:, None]))
                else:
                    result[k] = np.asarray(v)
    except Exception as e:
        logger.error(f"{'>'*10} 'Failed to process the result', {e}, {'<'*10}")
        print('raw data', raw_data)
        print('data map', dataMap)
        raise e
        result['error'] = [
            f'Failed to process the result, raise Exception: {e.__class__.__name__}("{str(e)}")',
            raw_data,
            dataMap
        ]

    return result
