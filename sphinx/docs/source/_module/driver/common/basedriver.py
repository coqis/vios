from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Union

from .quantity import newcfg


class BaseDriver(ABC):
    """设备驱动基类，所有设备驱动均需继承此基类
    """
    # 设备通道数量
    CHs = [1]

    # 设备读写属性列表
    quants = []

    def __init__(self, addr: Union[str, tuple] = '192.168.1.42', timeout: float = 3.0, **kw):
        """实例化设备

        Args:
            addr (Union[str, tuple], optional): 设备地址, host 或 (host, port). Defaults to '192.168.1.42'.
            timeout (float, optional): 超时时间. Defaults to 3.0.
        """
        self.addr = addr
        self.timeout = timeout

        self.model = kw.get('model', None)
        self.srate = -1.0

        self.config = newcfg(self.quants, self.CHs)
        self.quantities = {q.name: q for q in self.quants}

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
        return f'Driver(addr={self.addr}, model={self.model})'

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
        """设备打开时的操作，必须由子类实现
        """
        pass
    
    @abstractmethod
    def close(self, **kw):
        """设备关闭时的操作，必须由子类实现
        """
        pass

    @abstractmethod
    def write(self, name: str, value, **kw):
        """设备写操作，必须由子类实现
        """
        pass

    @abstractmethod
    def read(self, name: str, **kw):
        """设备读操作，必须由子类实现
        """
        pass

    def check(self, name: str, channel: int):
        assert name in self.quantities, f'{self}: quantity({name}) not Found!'
        assert channel in self.CHs or channel == 'global', f"{self}: channel({channel}) not found!"

    def update(self, name: str, value: Any, channel: int = 1):
        self.config[name][channel]['value'] = value

    def setValue(self, name: str, value: Any, **kw):
        """Deprecation Warning: will be removed in the future!
        """
        channel = kw.get('ch', 1)
        self.check(name, channel)
        opc = self.write(name, value, **kw)
        self.update(name, opc, channel)
        # return opc

    def getValue(self, name: str, **kw):
        """Deprecation Warning: will be removed in the future!
        """
        if name == 'quantity':
            return self.dict_from_quantity()
        elif name == 'srate':
            return self.srate

        channel = kw.get('ch', 1)
        self.check(name, channel)
        value = self.read(name, **kw)
        if value is None:
            value = self.config[name][channel]['value']
        else:
            self.update(name, value, channel)
        return value
