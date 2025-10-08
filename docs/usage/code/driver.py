import numpy as np

from quark.driver import BaseDriver, Quantity


class Driver(BaseDriver):
    """驱动模板

    类名固定为Driver，且继承自BaseDriver

    必须实现open/close/read/write方法
    """

    CHs = list(range(36))  # 通道列表

    quants = [  # 定义设备的属性，根据设备实际情况修改
        # MW
        Quantity('Frequency', value=0, ch=1, unit='Hz'),  # float
        Quantity('Power', value=0, ch=1, unit='dBm'),  # loat
        Quantity('Output', value='OFF', ch=1),  # str

        # AWG
        Quantity('Amplitude', value=0, ch=1, unit='Vpp'),  # float
        Quantity('Offset', value=0, ch=1, unit='V'),  # float
        Quantity('Waveform', value=np.array([]), ch=1),  # np.array
        Quantity('Marker1', value=[], ch=1),  # Marker1，np.array
        Quantity('Marker2', value=[], ch=1),  # Marker2，np.array

        # ADC
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

        # Trigger
        Quantity('TRIG'),
        Quantity('TriggerMode'),  # burst or continuous
        Quantity('Wait', value=0, ch=1),  # wait

        # NA
        Quantity('S', value=np.array([]), ch=1),
        Quantity('FrequencyStart', value=0, ch=1),
        Quantity('FrequencyStop', value=10e9, ch=1),
        Quantity('NumberOfPoints', value=1001, ch=1),
        Quantity('Bandwidth', value=101, ch=1),
        Quantity('Power', value=-10, ch=1),
        Quantity('Frequency', value=np.linspace(1, 10, 1001) * 1e9, ch=1)
    ]

    def __init__(self, addr: str = '', **kw):
        super().__init__(addr=addr, **kw)
        self.model = 'VirtualDevice'  # 设备型号
        self.srate = 1e9  # 设备采样率，单位Hz

    def open(self, **kw):
        """打开设备时的初始化操作，根据设备实际情况修改
        例如，打开串口、TCP/IP连接等.
        建议：将设备连接句柄赋值给self.handle，方便后续操作
        """
        self.handle = 'DeviceHandler'

    def close(self, **kw):
        """关闭设备的操作，根据设备实际情况修改
        例如，关闭串口、TCP/IP连接等
        """
        self.handle.close()

    def write(self, name: str, value, **kw):
        """向设备写入数据
        根据name参数判断写入哪种数据，value为对应的数据格式
        例如，name为'Frequency'时，value为float类型的频率值
        """
        if name == 'Frequency':
            self.set_frequency(value)
        elif name == 'Waveform':
            self.set_waveform(value, **kw)
        return value

    def read(self, name: str, **kw):
        """从设备读取数据
        根据name参数判断读取哪种数据，返回对应的数据格式
        例如，name为'Frequency'时，返回float类型的频率值
        """
        if name == 'TraceIQ':
            shot = self.getValue('Shot', **kw)
            point = self.getValue('PointNumber', **kw)
            # test = 1/0
            return np.random.randn(shot, point), np.random.randn(shot, point)
        elif name == 'Frequency':
            return 1.23e9

    # *#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*# user defined #*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#
    def set_waveform(self, value, **kw):
        """向仪器写入波形数据
        """

    def set_frequency(self, frequency: float):
        pass


if __name__ == '__main__':
    # 测试代码
    driver = Driver(addr='192.168.1.42')  # 初始化设备
    driver.open()  # 打开设备
    print('Device opened:', driver.handle)

    driver.setValue('Frequency', 1e9)  # setValue方法会做属性及通道检查，再调用write方法
    print(driver.getValue('Frequency'))  # getValue方法会做属性及通道检查，再调用read方法

    driver.setValue('Waveform', np.random.randn(1024))
    trace_iq = driver.getValue('TraceIQ')
    print(trace_iq)

    driver.close()  # 关闭设备
    print('Device closed.')
