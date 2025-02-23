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


import struct

import numpy as np
import pyvisa as visa

from .basedriver import BaseDriver


class VisaDriver(BaseDriver):

    error_command = 'SYST:ERR?'

    def __init__(self, addr, **kw):
        super().__init__(addr, **kw)
        self.visa_backend = kw.get('visa_backend', '')

    def open(self, **kw):
        self.addr_hash = hash(self.addr)
        try:
            self.handle.open()
        except:
            rm = visa.ResourceManager(self.visa_backend)
            self.handle = rm.open_resource(self.addr, read_termination='\n')
        self.handle.timeout = self.timeout * 1000
        try:
            IDN = self.handle.query("*IDN?").split(',')
            # company = IDN[0].strip()
            model = IDN[1].strip()
            # version = IDN[3].strip()
            self.model = model
        except Exception as e:
            # raise IOError(f'{self} query IDN error {e}!')
            print(f'Failed to get device info for {self}')

    def close(self, **kw):
        self.handle.close()

    def write(self, name: str, value, **kw):
        quant = self.quantities[name]
        if quant.set_cmd != '':
            cmd = quant._formatSetCmd(value, **kw)
            self.handle.write(cmd)
        else:
            pass
        return value

    def read(self, name: str, **kw):
        quant = self.quantities[name]
        if quant.get_cmd != '':
            cmd = quant._formatGetCmd(**kw)
            value = self.handle.query(cmd)
            return quant._process(value)
        else:
            return None

    def set_timeout(self, t):
        self.timeout = t
        if self.handle is not None:
            self.handle.timeout = t * 1000

    def errors(self):
        e = []
        if self.error_command == '':
            return e
        while True:
            s = self.handle.query(self.error_command)
            _ = s[:-1].split(',"')
            code = int(_[0])
            msg = _[1]
            if code == 0:
                break
            e.append((code, msg))
        return e

    def query_ascii_values(self, message, converter='f', separator=',',
                           container=list, delay=None,):
        if self.handle is None:
            return None
        try:
            res = self.handle.query_ascii_values(
                message, converter, separator, container, delay)
            return res
        except Exception as e:
            print(e)

    def query_binary_values(self, message, datatype='f', is_big_endian=False,
                            container=list, delay=None,
                            header_fmt='ieee',):
        if self.handle is None:
            return None
        try:
            res = self.handle.query_binary_values(message, datatype,
                                                  is_big_endian, container, delay, header_fmt)
            return res
        except Exception as e:
            print(e)

    def write_ascii_values(self, message, values, converter='f', separator=',',
                           termination=None, encoding=None,):
        if self.handle is None:
            return None
        log_msg = message + ('<%d values>' % len(values))
        try:
            self.handle.write_ascii_values(message, values, converter,
                                           separator, termination, encoding)
        except Exception as e:
            print(e)

    def write_binary_values(self, message, values, datatype='f',
                            is_big_endian=False, termination=None,
                            encoding=None,):
        if self.handle is None:
            return None
        block, header = IEEE_488_2_BinBlock(values, datatype, is_big_endian)
        log_msg = message + header + '<DATABLOCK>'
        try:
            self.handle.write_binary_values(message, values, datatype,
                                            is_big_endian, termination, encoding)
        except Exception as e:
            print(e)


def IEEE_488_2_BinBlock(datalist, dtype="int16", is_big_endian=True):
    """将一组数据打包成 IEEE 488.2 标准二进制块

    datalist : 要打包的数字列表
    dtype    : 数据类型
    endian   : 字节序

    返回二进制块, 以及其 'header'
    """
    types = {"b": (int, 'b'), "B": (int, 'B'),
             "h": (int, 'h'), "H": (int, 'H'),
             "i": (int, 'i'), "I": (int, 'I'),
             "q": (int, 'q'), "Q": (int, 'Q'),
             "f": (float, 'f'), "d": (float, 'd'),
             "int8": (int, 'b'), "uint8": (int, 'B'),
             "int16": (int, 'h'), "uint16": (int, 'H'),
             "int32": (int, 'i'), "uint32": (int, 'I'),
             "int64": (int, 'q'), "uint64": (int, 'Q'),
             "float": (float, 'f'), "double": (float, 'd'),
             "float32": (float, 'f'), "float64": (float, 'd')}

    datalist = np.asarray(datalist)
    datalist.astype(types[dtype][0])
    if is_big_endian:
        endianc = '>'
    else:
        endianc = '<'
    datablock = struct.pack('%s%d%s' % (
        endianc, len(datalist), types[dtype][1]), *datalist)
    size = '%d' % len(datablock)
    header = '#%d%s' % (len(size), size)

    return header.encode() + datablock, header
