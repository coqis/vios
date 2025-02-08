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


import re
import sys
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any

from .quantity import newcfg

PATTERN = r'^192\.168\.({seg})\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{{1,2}})'


class BaseDriver(ABC):
    """Base class for all drivers and methods open/close/read/write are required.

    See template **VirtualDevice**
    """
    # 设备网段,(设备种类缩写，指定ip段)
    segment = ('na', '103|104')

    # 设备通道数量
    CHs = [1]

    # 设备读写属性列表
    quants = []

    def __init__(self, addr: str = '192.168.1.42', **kw):
        """initialization of the driver

        Args:
            addr (str, optional): ip address of the device. Defaults to '192.168.1.42'.
        """
        self.addr = addr
        self.validate()

        self.host = kw.get('host', '127.0.0.1')
        self.port = kw.get('port', 0)  # for remote device
        self.timeout = kw.get('timeout', 3.0)
        self.model = kw.get('model', 'None')
        self.srate = kw.get('srate', -1)

        self.config = newcfg(self.quants, self.CHs)
        self.quantities = {q.name: q for q in self.quants}

    def validate(self):
        return
        dev, seg = self.segment
        self.pattern = re.compile(PATTERN.format(seg=seg))
        if not self.pattern.match(self.addr):
            raise ValueError(f'Wrong IP address format: {self.addr}!')

    def __repr__(self):
        return self.info()

    def __del__(self):
        try:
            self.close()
        except Exception as e:
            print(f'Failed to close {self}: {e}')

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.close()

    def info(self):
        base = f'''🔖Driver(addr={self.addr}, model={self.model}, srate={self.srate}, host={self.host}, port={self.port})'''
        try:
            return f'{base}<{sys.modules[self.__module__].__spec__.origin}>'
        except Exception as e:
            return base

    def dict_from_quantity(self):
        conn = {}
        channel = {}
        chx = {}
        for q in deepcopy(self.quants):
            ch = q.default['ch']
            if ch == 'global':
                chx[q.name] = q.default['value']
            else:
                channel[q.name] = q.default['value']
        for ch in self.CHs:
            conn[f'CH{ch}'] = channel
        conn['CHglobal'] = chx
        return conn

    @abstractmethod
    def open(self, **kw):
        """how device is opened
        """
        pass

    @abstractmethod
    def close(self, **kw):
        """how device is closed
        """
        pass

    @abstractmethod
    def write(self, name: str, value, **kw):
        """write a command(specified by name and value) to the device
        """
        pass

    @abstractmethod
    def read(self, name: str, **kw):
        """read a value(specified by name) from the device
        """
        pass

    def cancel(self):
        pass

    def check(self, name: str, channel: int):
        assert name in self.quantities, f'{self}: quantity({name}) not Found!'
        assert channel in self.CHs or channel == 'global', f"{self}: channel({channel}) not found!"

    def update(self, name: str, value: Any, channel: int = 1):
        self.config[name][channel]['value'] = value

    def setValue(self, name: str, value: Any, **kw):
        channel = kw.get('ch', 1)
        self.check(name, channel)
        opc = self.write(name, value, **kw)
        self.update(name, opc, channel)
        if kw.get('sid', 0) in kw.get('track', [0]):
            return opc
        # return opc

    def getValue(self, name: str, **kw):
        if name == 'quantity':
            return self.dict_from_quantity()
        elif hasattr(self, name):
            return getattr(self, name)

        channel = kw.get('ch', 1)
        self.check(name, channel)
        value = self.read(name, **kw)
        if value is None:
            value = self.config[name][channel]['value']
        else:
            self.update(name, value, channel)
        return value
