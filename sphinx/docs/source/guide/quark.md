# QuarkServer

## 一、启动
（1） clone并进入systemq目录，执行：pip install -e . 安装完所有依赖

（2） 打开etc/bootstrap.json文件（如下），并配置相应的路径，然后运行quark server(quark studio打开UI)

```python
{
    "executor": { # kernerl使用
        "type": "quark",
        "host": "127.0.0.1",
        "port": 2088
    },
    "data": { # kernerl使用
        "path": "",
        "url": ""
    },
    "repo": { # kernerl使用
        "systemq": "C:\\PythonQOS\\Repository\\systemq\\"
    }
    "quarkserver": {
        "name": "QuarkServer", # server名字
        "host": "0.0.0.0", # server地址
        "home": "../home", # server存储的根目录
        "checkpoint": "checkpoint.dat" # 位于home/cfg下，指定config文件，没有则加载同名的json文件。
    },
    "quarkstudio": { # 可删除可为空可不设
        "home": "../home", # 根目录，文件管理及notebook目录
        "userapi": "vios/collection/uapi.py", # 用户自定义画图mplot、实时波形vplot
        "theme":"dark" # 默认light，更改后重启生效
    }
}
```

（3） remote device

适用于设备由其他电脑控制的情景

将以下内容放于json文件中如remote.json，然后运行quark remote remote.json
```python
{
    "path":"driver", # 设备驱动所在模块路径
    "host":"192.168.1.42", # 控制设备的电脑ip地址
    "ADC": { # 设备别名，用于连接
        "name": "VirtualDevice", # 设备驱动
        "addr": "192.168.1.44" #  # 设备地址
    }
}
```


## 二、入门
### （1）连接server
```python
# 连接到server，如果不在本机，需要指定IP（需在同一样网段下）
from quark import connect
server = connect('QuarkServer', '127.0.0.1')
```


### （2） 实验
#### （a） 填任务
```python
import numpy as np
# 线路定义，@HK
qubits = ['1']
cc = [
    *[(('Delay', 2e-6), f'Q{i}') for i in qubits],
    ('Barrier', tuple(f'Q{i}' for i in qubits)),
    *[(('rfUnitary', np.pi, 0), f'Q{i}') for i in qubits],
    *[(('Delay', 2e-6), f'Q{i}') for i in qubits],
    ('Barrier', tuple(f'Q{i}' for i in qubits)),
    *[(('Measure', j), f'Q{i}') for j, i in enumerate(qubits)],
]

filename = 'sample'  # 存储文件为 sample.hdf5
# STEP：大写，保留关键字，描述任务执行过程
# CIRQ：大写，保留关键字，描述任务线路，可为空
# INIT：大写，保留关键字，任务初始化设置，可为空
# RULE：大写，保留关键字，变量关系列表，可为空
# LOOP：大写，保留关键字，循环执行所用变量，与STEP中的值对应，STEP中所用变量为LOOP的子集
task = {'metainfo': {'name': f'{filename}:/s21', # 冒号后为数据集名
                     'other': {'shots': 1234, 'signal': 'iq','autosave':False,'autorun':False}},  # 额外参数，如编译参数，与数据一起存于文件
        'taskinfo': {'STEP': {'main': ['WRITE', ('freq', 'offset', 'power')],  # main为保留关键字，不得替换
                              'step2': ['WRITE', 'trig'], # 触发
                              'step3': ['WAIT', 0.8101], # 等待一段时间，单位为秒
                              'READ': ['READ', 'read'], # step4（此处名为READ），后续数据处理需要，只能大写
                              'step5': ['WAIT', 0.202]},
                     'CIRQ': cc,
                     'INIT': [('Trigger.CHAB.TRIG', 0, 'any')],
                     'RULE': ['<gate>.Measure.Q1.params.frequency = <Q0>.setting.LO+<Q2>.setting.LO +1250'],
                     'LOOP': {'freq': [('Q0.setting.LO', np.linspace(0, 10, 2), 'Hz'),
                                       ('gate.Measure.Q1.index',  np.linspace(0, 1, 2), 'Hz')],
                              'offset': [('M0.setting.TRIGD', np.linspace(0, 10, 1), 'Hz'),
                                         ('Q2.setting.LO', np.linspace(0, 10, 1), 'Hz')],
                              'power': [('Q3.setting.LO', np.linspace(0, 10, 15), 'Hz'),
                                        ('Q4.setting.POW', np.linspace(0, 10, 15), 'Hz')],
                              'trig': [('Trigger.CHAB.TRIG', 0, 'any')],
                              'read': ['NA10.CH1.TraceIQ', 'M0.setting.POW']
                              }
                     },
        }
```

以上等价于
```python
for f in freq:
    for o in offset:
        for p in power:
            设置 f, o, p并执行RULE, 编译并生成指令序列准备执行 # main
            触发设备 # step2
            等待0.1s # step3
            采集数据 # READ
            等0.2s # # step5
```
每个step的值的第一个元素为操作类型，目前有三种：**WRITE、WAIT、READ**。**WRITE**和**READ**对应仪器的**setValue**和**getValue**（注：这两个接口日后会废弃，目前为保持兼容性而存在）。**WAIT**表示等待，数值表示时间（单位为秒）
***！！！注意！！！main的值第二项（WRITE之后的值）必须为tuple，如果仅有一项，须写成(freq,)形式，逗号不可少！！！***

#### （b） 提交任务并获取数据
```python
server.submit(task)
server.fetch(server.getid(), meta=True)
```

## 三、API
以下命令将通过`server`实现，而在`kernel`中，通过`kernel.cfg.conn`来调用

1、 连接服务
```python
from quark import connect
server = connect('QuarkStudio')
```

2、 数据操作基础
如果存在字段如a.b.c，可直接调用query查询对应的值
```python
server.query('a.b.c')
```

3、 如果不存在字段如a.b.c（但a.b存在），可直接调用update为其赋值。
> update 不可用于根节点
```python
server.update('a.b.c',value) # value为任意对象，等价于a.b.c = value
```

4、 对根节点a，可调用remove删除节点a及a中所有的数据，相对的创建操作为create
```python
server.remove('a')
server.create('a',value) # 等价于a = value
```

5、 存储用户数据，调用checkpoint保存并生成用户数据
```python
server.checkpoint()
```

6、 提交任务，生成任务字典task之后 ，调用submit，只针对网分测量
```python
server.submit(task)
```

7、 查询任务id，如果不传参数，返回当前任务id
```python
server.getid('group')
```

8、 根据任务id获取结果，当meta为True时返任务的描述性信息如坐标等
```python
data, axis = server.fetch(id, meta=True)
```

9、 根据id查询文件路径，如果数据在内存中，可查任务状态、执行时间等信息
```python
server.track(id)
```

10、 根据id加载存储在HDF5文件中的数据
```python
# 结合track可以根据id获取hdf5文件中的数据及对应的config
path, dataset = server.track(id)['file'].split(':/')
data, cfg = server.load(path, dataset)
```

## 四、FAQ!
1、Config表基本结构？

A: Server接受json作为输入，对其中内容无限制。当前所用config由用户自定义数据
和系统定义数据（包括etc、usr、dev）构成。

2、dev是什么？

A：dev下主要存放设备信息，包括设备别名、驱动名称、连接地址、采样率、端口号（用于remote）。如：
```python
{
    "dev": {
        "NA0": { # 设备别名
            "addr": "192.168.1.41", # 设备地址
            "name": "VirtualDevice", # 设备驱动名称
            "type": "driver", # 连接类型，driver或remote
            "srate": 1000000000.0, # 采样率，从设备读取
            "port":40001 # 当连接类型为remote时需要
        }
    }
}
```

3、etc是什么？

A：etc主要用于方便用户更改一些全局设置，如果设备属性映射。如：
```python
{
    "etc": {
        "sysdir": "../systemq" # systemq所在根目录
        "driver": "vios/driver", # 设备驱动路径，相对于所在根目录（sysdir）
        "concurrent": True, # True为同时打开设备，否则顺序打开
        "mapping": { # 用户定义的数据结构与设备间的映射关系
            "setting_LO": "LO.Frequency", # 大小写应与驱动中属性一致，否则报错
            "setting_POW": "LO.Power",
            "setting_OFFSET": "ZBIAS.Offset",
            "waveform_RF_I": "I.Waveform",
            "waveform_RF_Q": "Q.Waveform",
            "waveform_TRIG": "TRIG.Marker1",
            "waveform_SW": "SW.Marker1",
            "waveform_Z": "Z.Waveform",
            "setting_PNT": "ADC.PointNumber",
            "setting_SHOT": "ADC.Shot",
            "setting_TRIGD": "ADC.TriggerDelay"
        },
        "taskid": 1000004635, # 任务id，整数，连接编号，可修改
    }
}
```

4、usr是什么？

A：usr存储一些重要但不常用的设置。如
```python
{
    "usr": {
        "autorun": True, # 自动执行任务
        "autosave": True, # 自动保存
        "filesize": 0.552, # 记录当前hdf5文件大小（单位为MB）
        "sizelimit": 1024 # 单个hdf5文件大小限制（单位为MB），超出则另起新文件
    }
}
```