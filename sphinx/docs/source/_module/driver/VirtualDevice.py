import numpy as np
from .common import BaseDriver, Quantity


class Driver(BaseDriver):
    """设备驱动，类名统一为Driver，文件名为设备名称，如VirtualDevice

    Args:
        BaseDriver (class): 所有的驱动均继承自基类，要求实现
        open/close/read/write四个接口
    """
    # 设备可用通道数量
    CHs = [1, 2, 3, 4, 5, 6, 7, 8]

    # 设备常见读写属性，可自行增加，对应在read/write中实现不同的方法即可
    # 属性名中的单词均以大写开头，缩写全为大写，用于说明有哪些可读写设置
    # 应给每个属性加上注释，方便了解设置的作用
    quants = [
        # 微波源(MW)
        Quantity('Frequency', value=0, ch=1, unit='Hz'), # 频率，float
        Quantity('Power', value=0, ch=1, unit='dBm'),  # 功率，float
        Quantity('Output', value='OFF', ch=1),  # 输出开关，str

        # 任意波形发生器(AWG)
        Quantity('Amplitude', value=0, ch=1, unit='Vpp'), # 振幅，float
        Quantity('Offset', value=0, ch=1, unit='V'), # 偏置，float
        Quantity('Waveform', value=np.array([]), ch=1), # 波形，np.array
        Quantity('Marker1', value=[], ch=1), # Marker1，np.array
        Quantity('Marker2', value=[], ch=1), # Marker2，np.array

        # 数据采集(ADC)
        Quantity('PointNumber', value=1024, ch=1, unit='point'),  # 采样点数，int
        Quantity('TriggerDelay', value=0, ch=1, unit='s'),  # 采样延迟，float
        Quantity('Shot', value=512, ch=1),  # 采样次数，int
        Quantity('TraceIQ', value=np.array([]), ch=1),  # 时域采样，np.array
        Quantity('IQ', value=np.array([]), ch=1),  # 解调后数据，np.array
        Quantity('Coefficient', value=np.array([]), ch=1),  # 解调所需系数，np.array
        Quantity('StartCapture', value=1, ch=1,),  # 开始采集，value随机，通知采集卡准备就绪
        Quantity('CaptureMode', value='raw', ch=1),  # 采集模式，str，raw->TraceIQ, alg-> IQ
    ]

    def __init__(self, addr: str = '', timeout: float = 3.0, **kw):
        super().__init__(addr=addr, timeout=timeout, **kw)
        """根据设备地址、超时时间实例化设备驱动
        """
        self.model = 'VirtualDevice' # 默认为设备名字
        self.srate = 1e9 # 设备采样率

    def open(self, **kw):
        """打开并初始化仪器设置，获取仪器操作句柄，必须实现，可以为空(pass)但不能没有
        """
        self.handle = 'DeviceHandler'
        # test = 1/0

    def close(self, **kw):
        """关闭仪器，必须实现，可以为空(pass)但不能没有
        """
        self.handle.close()

    def write(self, name: str, value, **kw):
        """设置仪器，额外的参数(如通道指定)可通过kw传入。必须实现，如

        if name == '属性名':
            执行操作
        elif name == '属性名':
            执行操作
        """
        if name == 'PointNumber':
            pass
            # 如，self.set_offset(value, ch=1)
        elif name == 'Shot':
            pass
            # 如，self.set_shot(value, ch=2)
        return value

    def read(self, name: str, **kw):
        """读取仪器，额外的参数(如通道指定)可通过kw传入。必须实现，如

        if name == '属性名':
            return 执行操作
        elif name == '属性名':
            return 执行操作
        """
        if name == 'TraceIQ':
            return self.get_trace()
        elif name == 'IQ':
            return self.get_iq()

    #*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*# user defined #*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#
    def get_iq(self):
        shot = 1024#self.getValue('Shot')
        fnum = 2048#self.getValue('Coefficient')[0].shape[0]
        return np.ones((shot, fnum)), np.ones((shot, fnum))

    def get_trace(self):
        shot = self.getValue('Shot')
        point = self.getValue('PointNumber')
        # test = 1/0
        return np.ones((shot, point))
