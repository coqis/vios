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


import time

import numpy as np

from waveforms import Waveform, wave_eval
from waveforms.math.signal import getFTMatrix, shift

from .common import BaseDriver, Quantity


def get_coef(coef_info, sampleRate):
    start, stop = coef_info['start'], coef_info['stop']
    numberOfPoints = int(
        (stop - start) * sampleRate)
    if numberOfPoints % 1024 != 0:
        numberOfPoints = numberOfPoints + 1024 - numberOfPoints % 1024
    t = np.arange(numberOfPoints) / sampleRate + start

    fList = []
    wList = []
    phases = []

    for kw in coef_info['wList']:
        Delta, t0, weight, w, phase = kw['Delta'], kw['t0'], kw['weight'], kw['w'], kw['phase']
        fList.append(Delta)

        if w is not None:
            w = np.zeros(numberOfPoints, dtype=complex)
            w[:len(w)] = w
            w = shift(w, t0 - start)
            phases.append(np.mod(phase + 2 * np.pi * Delta * start, 2*np.pi))
        else:
            weight = weight
            if isinstance(weight, np.ndarray):
                pass
            else:
                if isinstance(weight, str):
                    fun = wave_eval(weight) >> t0
                elif isinstance(weight, Waveform):
                    fun = weight >> t0
                else:
                    raise TypeError(f'Unsupported type {weight}')
                weight = fun(t)
            phase += 2 * np.pi * Delta * start
            w = getFTMatrix([Delta],
                            numberOfPoints,
                            phaseList=[phase],
                            weight=weight,
                            sampleRate=sampleRate)[:, 0]
            phases.append(np.mod(phase, 2*np.pi))
        wList.append(w)
    return np.asarray(wList), fList, numberOfPoints, phases


# class Quantity(object):
#     def __init__(self, name: str, value=None, ch: int = None, unit: str = ''):
#         self.name = name
#         self.default = dict(value=value, ch=ch, unit=unit)


class Driver(BaseDriver):
    """driver template

    Warning:
        All drivers must inherit from the base class(with fixed class name ***Driver***) and methods open/close/read/write must be implemented!
    """
    segment = ('na', '101|102|103')
    # number of available channels
    CHs = list(range(36))

    quants = [
        # Microwave source(MW)
        Quantity('Frequency', value=0, ch=1, unit='Hz'),  # float
        Quantity('Power', value=0, ch=1, unit='dBm'),  # loat
        Quantity('Output', value='OFF', ch=1),  # str

        # 任意波形发生器(AWG)
        Quantity('Amplitude', value=0, ch=1, unit='Vpp'),  # float
        Quantity('Offset', value=0, ch=1, unit='V'),  # float
        Quantity('Waveform', value=np.array([]), ch=1),  # np.array or Waveform
        Quantity('Marker1', value=[], ch=1),  # Marker1，np.array
        Quantity('Marker2', value=[], ch=1),  # Marker2，np.array

        # Data Acquisition(ADC)
        Quantity('PointNumber', value=1024, ch=1, unit='point'),  # int
        Quantity('TriggerDelay', value=0, ch=1, unit='s'),  # float
        Quantity('Shot', value=512, ch=1),  # int
        Quantity('TraceIQ', value=np.array([]), ch=1),  # np.array
        Quantity('Trace', value=np.array([]), ch=1),  # np.array
        Quantity('IQ', value=np.array([]), ch=1),  # np.array
        Quantity('Coefficient', value=np.array([]), ch=1),  # np.array
        Quantity('StartCapture', value=1, ch=1,),  # int

        Quantity('CaptureMode', value='raw', ch=1),  # raw->TraceIQ, alg-> IQ

        # test
        Quantity('Classify', value=0, ch=1),
        Quantity('Counts', value=[], ch=1),

        # Trigger(TRIG)
        Quantity('TRIG'),
        Quantity('TriggerMode'),  # burst or continuous
        Quantity('Wait', value=0, ch=1),  # wait
    ]

    def __init__(self, addr: str = '', timeout: float = 3.0, **kw):
        super().__init__(addr=addr, timeout=timeout, **kw)
        self.model = 'VirtualDevice'  # device model
        self.timeout = 1.0
        self.srate = 1e9  # sampling rate

    def open(self, **kw):
        """open device
        """
        self.handle = 'DeviceHandler'
        # test = 1/0

    def close(self, **kw):
        """close device
        """
        self.handle.close()

    def write(self, name: str, value, **kw):
        """write to device
        """
        if name == 'Wait':
            time.sleep(value)
        elif name == 'Waveform':
            if isinstance(value, list):
                t0 = time.time()
                wf = Waveform.fromlist(value)
                t1 = time.time()
                wf.sample()
            if isinstance(value, Waveform):
                t0 = time.time()
                value.sample()
            # 如，self.set_offset(value, ch=1)
        elif name == 'Shot':
            pass
        elif name == 'Coefficient':
            data, f_list, numberOfPoints, phase = get_coef(value, self.srate)
            # coef_data = np.moveaxis([data.real,data.imag],0,-2)
            self.setValue('PointNumber', numberOfPoints, **kw)
            # self.update('Coefficient', data, channel=ch)
            return data
            # 如，self.set_shot(value, ch=2)
        return value

    def read(self, name: str, **kw):
        """read from device
        """
        if name == 'TraceIQ':
            shot = self.getValue('Shot', **kw)
            point = self.getValue('PointNumber', **kw)
            # test = 1/0
            return np.ones((shot, point)), np.ones((shot, point))
        elif name == 'IQ':
            shot = self.getValue('Shot', **kw)
            fnum = self.getValue('Coefficient', **kw).shape[0]
            # time.sleep(0.1)
            si = np.random.randint(20)+np.random.randn(shot, fnum)
            sq = np.random.randint(20)+np.random.randn(shot, fnum)
            return si, sq

    # *#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*# user defined #*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#
    def get_iq(self):
        pass

    def get_trace(self):
        pass
