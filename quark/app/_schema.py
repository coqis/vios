# MIT License

# Copyright (c) 2024 YL Feng

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


class Template(object):
    def __init__(self):
        pass

    @classmethod
    def node(self):
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
                            }
                }

    @classmethod
    def validate(cls, instance: dict):
        from jsonschema import validate

        try:
            validate(instance, schema=cls.schema)
            return True
        except Exception as e:
            print(e)
            return False
