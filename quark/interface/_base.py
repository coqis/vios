# MIT License

# Copyright (c) 2025 YL Feng <fengyulong@pku.org.cn>

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


import sys
import types
from pathlib import Path

import numpy as np
from loguru import logger
from waveforms import Waveform, WaveVStack, square, wave_eval
from zee import query_dict_from_string


class Pulse(object):

    WINDOW = square(500e-3) >> 150e-3

    def __init__(self):
        pass

    @classmethod
    def typeof(cls, pulse: Waveform | np.ndarray):
        return 'object' if isinstance(pulse, Waveform) else 'array'

    @classmethod
    def fromstr(cls, pulse: str):
        return wave_eval(pulse)

    @classmethod
    def correct(cls, points: np.ndarray, cali: dict = {}) -> np.ndarray:
        """失真校准，从 `qlispc.kernel_utils` 复制而来。仅测试用，不会在实验中调用。

        Args:
            points (np.ndarray): 输入信号
            cali (dict, optional): 校准所需参数. Defaults to {}.

        Returns:
            np.ndarray: 校准后信号
        """
        from wath.signal import (correct_reflection, exp_decay_filter,
                                 predistort)

        distortion_params = cali.get('distortion', {})
        if not distortion_params:
            return points

        if not isinstance(distortion_params, dict):
            distortion_params = {}

        filters = []
        ker = None
        if 'decay' in distortion_params and isinstance(distortion_params['decay'],
                                                       (list, tuple, np.ndarray)):
            for amp, tau in distortion_params.get('decay', []):
                a, b = exp_decay_filter(amp, tau, cali['srate'])
                filters.append((b, a))

        length = len(points)
        if length > 0:
            last = points[-1]
            try:
                points = predistort(points, filters, ker, initial=last)
            except:
                points = np.hstack([np.full((length, ), last), points])
                points = predistort(points, filters, ker)[length:]
            points[-1] = last

        return points

    @classmethod
    def sample(cls, pulse: Waveform | np.ndarray, cali: dict = {}):
        cali = cali.get('calibration', cali)
        if isinstance(pulse, Waveform) and cali:
            pulse >>= cali.get('delay', 0)
            pulse.sample_rate = cali['srate']
            pulse.start = 0
            pulse.stop = cali['end']
        return pulse.sample() if isinstance(pulse, Waveform) else pulse

    @classmethod
    def equal(cls, a, b):
        try:
            if isinstance(a, WaveVStack) or isinstance(b, WaveVStack):
                return False

            if isinstance(a, Waveform) and isinstance(b, Waveform):
                return (a * cls.WINDOW) == (b * cls.WINDOW)

            res = a == b
            if isinstance(res, np.ndarray):
                return np.all(res)
            return res
        except Exception as e:
            logger.warning(f'Failed to compare waveform: {e}')
            return False


SCHEMA = {
    'type': 'object',
    'properties': {}
}

for k in ['drive', 'probe', 'acquire']:
    SCHEMA['properties'][k] = {'type': 'object',
                               'properties': {'address': {'type': 'string'},
                                              'delay': {'type': 'number'},
                                              'start': {'type': 'number'},
                                              'end': {'type': 'number'},
                                              'offset': {'type': 'number'}
                                              },
                               'required': ['address']
                               }


class Registry(object):
    def __init__(self, source: dict):
        self.source = source

    def keys(self):
        return list(self.source)

    def query(self, path: str):
        try:
            return query_dict_from_string(path, self.source)
        except Exception as e:
            return f'Failed to query {path}: {e}'

    @classmethod
    def node(cls):
        return {'Measure': {'duration': 4e-06,
                            'amp': 0.019,
                            'frequency': 6964370000.0,
                            'weight': 'const(1)',
                            'phi': -2.636421695283167,
                            'threshold': 8502633802.265065,
                            'ring_up_amp': 0.024,
                            'ring_up_waist': 0.006,
                            'ring_up_time': 6e-07
                            },
                'R': {'width': 2.1e-08,
                      'amp': 0.5140937118030053,
                      'frequency': 4473337704.6286335,
                      'delta': 947840.2529478334,
                      'plateau': 2.1e-08
                      },
                'probe': {'address': 'ZW_AD2.CH1.Waveform',
                          'delay': 5e-0,  # optional
                          'start': 0,  # optional
                          'end': 98e-6  # optional
                          },
                'drive': {'address': 'ZW_AWG_13.CH2.Waveform',
                          'delay': 2.52e-07,  # optional
                          'end': 98e-6  # optional
                          },
                'acquire': {'address': 'ZW_AD2.CH13.IQ',
                            'TRIGD': 5.222e-06  # optional
                            },
                'flux': {'address': 'board_all.CH10.Waveform',
                         'delay': 0,
                         'distortion': {
                             'decay': [],
                             'expfit': [],
                             'multfit': []
                         }
                         },
                }

    @classmethod
    def validate(cls, instance: dict):
        from jsonschema import validate

        try:
            validate(instance, schema=SCHEMA)
            return True
        except Exception as e:
            print(e)
            return False
