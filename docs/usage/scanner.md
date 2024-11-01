# Scanner 介绍

***LP by 2023.1.15***

Scanner是一个扫描器的封装，通过简单的参数表配置，来生成一个扫描任务。

扫描原则：最小化参数修改原则。也就是，在一次扫描修改只修改需要修改的参数，不动其他参数表的项目。

本文档的内容适用于scanner2的新版Scanner，旧版的请参考老文档。

## 常见调用代码

加载相关库和和文件
```python
import kernel
from qos_tools.experiment.scanner2 import Scanner
```

假设已经知道配置字典`para_dict`，使用其来创建一个扫描任务，此时只是创建了任务，未提交执行
```python
test = kernel.create_task(Scanner, args=(), kwds=para_dict['init'])
test.init(**para_dict)
```

向`kernel`提交待执行任务，该代码运行后任务开始编译和执行，同时任务执行中的相关信息可以通过task的属性来进行查看
```python
task = kernel.submit(test)
```

创建任务进度条
```python
task.bar()
```

查看任务状态
```python
task.status
```

阻塞函数，等待任务执行完毕，`t`为该任务最长等待时间，单位为秒
```python
task.join(t)
```

获取任务结果，`flag`是`Bool`型数据，表示是否按照扫描格式来调整数据维度，`False`则数据返回默认格式
```python
result = task.result(flag)
```

取消任务，可以在提交执行后运行
```python
task.cancel()
```

## 配置字典书写规范

### 前置知识：参数表逻辑

`config`是实验参数管理系统，本质是一个json文件，作为一个树形索引结构，一般其关键字具有`aaa.bbb.ccc`等多级结构。

其中第一级关键字，一般有以下几类：

1. `etc` 固定关键字，一般是该`server`全局设置，供`quark`调用，具体参考`quark`部分文档；
2. `usr` 固定关键字，一些其他设置，与文件存储有关；一般会保留近几十条实验记录索引，供`quark`调用，可以参考`quark`文档；
2. `dev` 固定关键字，仪器配置文件，记录仪器连接地址和属性，供`quark`调用，可以参考`quark`文档；
1. `station` 固定关键字，与登录`quark`、文件保存核定、`trigger`命令，属于当前实验的设置，供`kernel`调用；
2. `Q*` 比特相关的通道设置，包括采样率、仪器连接通道、波形采样率、总长度等，以及部分硬件线路校准信息，如delay等信息。名字并不是固定的，一般根据大家习惯，会以`Q`开头。
1. `M*` 读取probe的相关设置，基本结构类似于比特通道，名字也不是固定的，看大家习惯以`M`开头
1. `C*` 可调耦合线的相关设置，基本结构类似于比特通道，名字也不是固定的，看大家习惯以`C`开头
2. `gate` 固定关键字，所有门的参数，也是本文档中需要核心关注的结构。索引`gate.gate_name.qubit_name.type.parameter_name`将会对应到某名为`gate_name`的门，作用在`qubit_name`上时，按照`type`的作用规则下`parameter_name`参数对应的参数。

config的规则这里只是简单有个了解，在`Scanner`的配置字典中最关心的就是与门参数相关的结构，其次关心的就是门编译的操作规则，门编译规则相关的内容适合在编译器文档中来介绍。

### 前置知识：Qlisp语言规范

请参考waveforms文档，以下内容部分摘自该文档。

硬件层面最基本的单比特操作是微波脉冲实现的`rfUnitary`门和相位`P`门,由它们可以组合出单比特通用门`U`。

`rfUnitary`门具有两个参数，数学表示如下：
```python
def rfUnitary(theta, phi):
    """
    Gives the unitary operator for an ideal microwave gate.
    phi gives the rotation axis on the plane of the bloch sphere (RF drive phase)
    theta is the rotation angle of the gate (pulse area)

    rfUnitary(theta, phi) := expm(-1j * theta / 2 * \
        (sigmaX() * cos(phi) + sigmaY() * sin(phi)))

    rfUnitary(theta, phi + pi/2) == U(theta, phi, -phi)
    """
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -1j * s * np.exp(-1j * phi)],
                     [-1j * s * np.exp(1j * phi), c]])
```

而其他常见的门定义如下：

| statement | gate | matrix  |
|:---------:|:----:|:------:|
|`('I', 'Q0')`|  $I$   | $\begin{pmatrix}1 & 0\\0 & 1\end{pmatrix}$ | |
|`('X', 'Q0')`|  $\sigma_x$   | $\begin{pmatrix}0 & 1\\1 & 0\end{pmatrix}$ | |
|`('Y', 'Q0')`|  $\sigma_y$   | $\begin{pmatrix}0 & -i\\i & 0\end{pmatrix}$ | |
|`('Z', 'Q0')`|  $\sigma_z$   | $\begin{pmatrix}1 & 0\\0 & -1\end{pmatrix}$ | |
|`('H', 'Q0')`|  $H$   | $\frac{1}{\sqrt{2}}\begin{pmatrix}1 & 1\\1 & -1\end{pmatrix}$ | |
|`('S', 'Q0')`|  $S$   | $\begin{pmatrix}1 & 0\\0 & i\end{pmatrix}$ | |
|`('-S', 'Q0')`|  $S^{\dagger}$   | $\begin{pmatrix}1 & 0\\0 & -i\end{pmatrix}$ | |
|`('T', 'Q0')`|  $T$   | $\begin{pmatrix}1 & 0\\0 & e^{i\pi/4}\end{pmatrix}$ | |
|`('-T', 'Q0')`|  $T^{\dagger}$   | $\begin{pmatrix}1 & 0\\0 & e^{-i\pi/4}\end{pmatrix}$ | |
|`(('Rx', theta), 'Q0')`|  $R_x(\theta)$   | $\exp\left(-i\frac{\theta}{2}\sigma_x\right)$ | |
|`(('Ry', theta), 'Q0'`|  $R_y(\theta)$   | $\exp\left(-i\frac{\theta}{2}\sigma_y\right)$ | |
|`(('Rz', phi), 'Q0')`|  $R_z(\theta)$   | $\exp\left(-i\frac{\phi}{2}\sigma_z\right)$ | |
|`('X/2', 'Q0')`|  $R_x(\pi/2)$   | $\exp\left(-i\frac{\pi}{4}\sigma_x\right)$ | |
|`('-X/2', 'Q0')`|  $R_x(-\pi/2)$   | $\exp\left(i\frac{\pi}{4}\sigma_x\right)$ | |
|`('Y/2', 'Q0')`|  $R_y(\pi/2)$   | $\exp\left(-i\frac{\pi}{4}\sigma_y\right)$ | |
|`('-Y/2', 'Q0')`|  $R_y(-\pi/2)$   | $\exp\left(i\frac{\pi}{4}\sigma_y\right)$ | |
|`('iSWAP', ('Q0', 'Q1'))`|  $i\mathrm{SWAP}$   | $\begin{pmatrix}1&0&0&0\\0&0&i&0\\0&i&0&0\\0&0&0&1\end{pmatrix}$ | |
|`('Cnot', ('Q0', 'Q1'))`|  C-Not   | $\begin{pmatrix}1&0&0&0\\0&1&0&0\\0&0&0&1\\0&0&1&0\end{pmatrix}$ | |

除此之外，还有——

`Delay` 含一个 float 类型的参数 `t`,表示将目标比特后续操作延迟指定时间,比如测量 $T1$ 的线路为，
```python
[('X', 'Q1'), (('Delay', t), 'Q1'), (('Measure', 0), 'Q1')]
```
`t` 的单位为秒。

`Barrier` 可作用于任意个量子比特,将所作用的各比特时间对齐,比如同时测量三个比特的 $T_1$ 可用以下线路
```python
[
    ('X', 'Q0'),
    ('X', 'Q1'),
    ('X', 'Q2'),
    ('Barrier', ('Q0', 'Q1', 'Q2')),
    (('Delay', t), 'Q0'),
    ('Barrier', ('Q0', 'Q1', 'Q2')),
    (('Measure', 0), 'Q0'),
    (('Measure', 0), 'Q1'),
    (('Measure', 0), 'Q2')
]
```

`Measure` 含一个 int 类型的参数 `cbit`,表示将目标比特的测量结果放置在输出 bit-word 的第 `cbit` 位上。

除了这些常见门，其他自定义门规则的内容和方法，适合在编译器文档来介绍。

> 思考题1：线路`[('X', 0)]`和线路`[(('rfUnitary', pi, 0), 0)]`有什么区别？

> 思考题2：线路`[('X', 0), ('X', 0), ('X', 0)]`和线路`[(('rfUnitary', pi, 0), 0), (('rfUnitary', pi, 0), 0), (('rfUnitary', pi, 0), 0)]`有什么区别？

### 配置字典结构

一个完整版的参数配置字典应该具有以下结构，这里只给出了第一级参数的名称和值的类型。

```python
para_dict = {
	'init': dict, # 初始化任务的相关设置
    'setting': dict, # 当前扫描任务的参数配置区，也是也是临时变量存储区
    'sweep_config': dict, # 扫描中的参数地址映射
    'sweep_setting': dict, # 扫描参数的循环迭代逻辑
    'sweep_addition': dict, # 带约束的扫描参数定义
    'constrains': list[tuple], # scanner内嵌的约束管理逻辑，会在进阶内容中介绍
    'sweep_trackers': list, # 扫描中的跟踪器，属于高阶内容
    'sweep_filter': Callable or None, # 扫描参数的掩模函数，属于高阶内容
}
```

在以上内容中， `sweep_trackers`不会在此文档中展开，其他部分内容将会给出介绍。

#### `init`字段

本字段其实是`App`初始化的基础内容，常见的内容包括：
```python
    'init': {
        'name': str, # 该scanner的名字，同时也是数据库检索和hdf5文件中实验名称
        'qubits': list, # 并非必须，当前实验中作用的比特，会参与该实验对应的哈希值计算，可以理解作用在Q1上的Rabi实验和作用在Q2上的Rabi实验室两个实验
        'signal': str or SIGNAL, # 该实验返回的数据是什么形式的
        'shots': int, # 在一轮测试中重复的测试，一般都是一个固定值，与触发硬件的设置相关，默认1024
        'arch': str, # 本实验中的编译规则，默认'baqis'
        'calibration_level': int, # 原有向图维护中的一流参数，可以不管，默认为0
    }
```

#### 扫描参数`sweep_setting`，`sweep_addition`和`sweep_filter`

这三个参数组合起来将构成主要的参数扫描逻辑。`sweep_setting`主要关注独立参数的变化情况，而`sweep_addition`更关心在扫描中依赖于别的参数而变的参数，`sweep_filter`一般情况下默认为`None`，需要调用时是一个掩模函数，方便构造更加复杂的参数迭代过程，例如要求在$x^2+y^2<1$的情况下扫描$x$和$y$，解析的形式来写有点麻烦，反而不如令$x$和$y$独立变化，添加对应掩模函数来的方便。

在独立变量`sweep_setting`中，以下例子，
```python
    'sweep_setting': {
        ('a', 'b'): ((1, 2), (13, 14)),
        ('c', 'd'): ((115, 116), (1117, 1118)),
    },
    'sweep_addition': {
        'e': lambda a, c, **kw: a+c+kw['d']
    },
    'sweep_filter': None
```
将会产生4步迭代过程，每一步的迭代过程中的值如下:

* step 1: a = 1, b = 13, c = 115, d = 1117, e = a + c + d = 1 + 115 + 1117 = 1233
* step 2: a = 1, b = 13, c = 116, d = 1118, e = a + c + d = 1 + 116 + 1118 = 1235
* step 2: a = 2, b = 14, c = 115, d = 1117, e = a + c + d = 2 + 115 + 1117 = 1234
* step 2: a = 2, b = 14, c = 116, d = 1118, e = a + c + d = 2 + 116 + 1118 = 1236

而如果给一个掩模函数形如
```python
    'sweep_filter': lambda **kw: kw['a']+kw['e']<=1236
```
则只会产生3步迭代，也就是上面4步中的前3步。

> 思考题：请理解上述迭代中的计算规则。

#### 从变量到真正参数的映射

在上面的迭代参数生成器中，参数的名称都是随意的，但是在实验中，我们需要把对应的参数名映射到`config`的对应的参数地址中。一般有两种方法：直接修改整个表中的参数，或者使用`with`语法规范做局部最小化修改。

##### 全局映射`sweep_config`

如果定义
```python
    'sweep_config': {
        'a': {
            'addr': 'gate.rfUnitary.Q1.params.amp',
        },
        'b': {
            'addr': 'gate.rfUnitary.Q2.params.amp',
        },
```
则会在每次循环迭代中，将当前对应的变量的值设置到对应的地址上去。没有绑定地址的变量不会设置相应的值（也不知道设置到哪里去）。注意，此时在线路中所有该参数相关的门都会被修改。

##### 局部修改`with`

如果只是想修改线路中的个别门的参数，那么需要注意的就是，此时的线路在每一次扫描迭代中都不同，那么线路，也是扫描参数的一个函数，则
```python
    'sweep_addition': {
        'circuit': lambda a, b: [
            # 只显示需要修改的参数，这里的theta和phi任意参数，取决于待写线路，其余的部分不予显示。参数amp仅仅是举了个例子。
            (('rfUnitary', theta, phi, ('with', ('param:amp', a))), 'Q1'),
            (('rfUnitary', theta, phi, ('with', ('param:amp', b))), 'Q2'),
        ]
        },
}
```

#### 大杂烩`setting`字段

以上几个字段都具有明确的内容，`setting`则是其他功能的支持区域，并不是必须出现的。该部分的内容该写什么，将会在进阶功能中介绍。

值得说明的是，变量关键词`circuit`是保留字，如果在扫描变量中没有描述`circuit'`，则需要在`setting`中添加一个固定线路。
```python
    'setting': {
        'circuit': list[tuple]
    }
```

## 获取返回结果

对于通过
```python
result = task.result()
```
获得的实验结果`result`是一个字典，具有以下结构
```python
result = {
    'index': dict, # 各个扫描参数在每一步迭代中的值
    'circuit': numpy.ndarray, # 各步中的线路
    'meta': dict，# 本次实验的基础信息，包括迭代的层次结构信息，开始实验时参数表的快照
    #形如
    signal: np.ndarray, # 返回结果，取决于信号格式的选择，可以支持同时多种参数
    key:value, # 涉及到参数追踪的部分，参考高阶内容
}
```

对不同实验结果的需求，将会影响创建实验时对返回参数类型`signal`的选择，常见`signal`类型：

|字符串表示|`Signal`类型|操作含义|
|:-:|:-:|:-:|
|`'trace'`|`Signal.trace`|获得采集到的trace，每一个shot的数据都返回|
|`'iq'`|`Signal.iq`|返回测量到的复数点们|
|`'iq_avg'`|`Signal.iq_avg`|返回测量到的复数点，对采集shot进行平均|
|`'state'`|`Signal.state`|对比特的量子态进行判别后返回对应状态|
|`'population'`|`Signal.population`|在单比特量状态判别的基础上，返回对单比特各个态概率分布|
|`'count'`|`Signal.count`|对多比特状态串的统计|
|`'diag'`|`Signal.diag`|在状态串的基础上，给出全空间的概率分布，慎用|

以上信号参数可以组合，可以定义复合信号，例如`Signal.iq_avg|Signal.state`，则返回结果中同时返回两种结果，即`iq_avg`和`state`。这里的运算规则是或运算。

一般情况下，返回的数据`result[signal]`具有通用形状`[sweep_iteration_steps, shots, cbits]`，根据具体的信号选择可能会去掉`shots`维度。如果扫描参数具有规则的形状，并且选择
```python
result = task.result(True) # 默认False
```
则会对`sweep_iteration_steps`维度重新修改形状，让它符合扫描参数的维度。

## 实验例子

这一部分将给出一些简单实验的配置字典描述，并不是最优美的形式，很多很笨拙，只是展示功能。更多的例子可以参考`qos_tools.experiment.libs`。

### 同时扫多个比特的S21
```python

import numpy as np

qubits = ['Q1', 'Q2']
signal = 'iq_avg'
sweep_list1 = np.linspace(-20e6, 20e6, 21)+7e9
sweep_list2 = np.linspace(-20e6, 20e6, 21)+7.1e9

para_dict = {
        'init': {
            'name': 'S21',
            'qubits': qubits,
            'signal': signal,
        },
        'setting': {
            'circuit': [(('Measure', j), q) for j, q in enumerate(qubits)],
        },
        'sweep_config': {
            q: {
                'addr': f'gate.Measure.{q}.params.frequency',
            } for q in qubits
        },
        'sweep_setting': {
            tuple(qubits): tuple([sweep_list1, sweep_list2])
        },
    }
```
值得注意的是，这里面只改变了读取门的频率，按照最小修改原则，也就是如果在混频方案下还想要同步地修改微波源local的频率，那还需要额外的操作。

### 多个比特的PowerRabi
```python
qubits = ['Q1', 'Q2']
signal = 'population'
n = 21
sweep_points = 21
mode = 'log'

scale = {q: kernel.get(f'gate.rfUnitary.{q}.params.amp')[-1][-1] for q in qubits}

from qos_tool.experiment.tools import generate_spanlist

para_dict = {
        'init': {
            'name': 'N Power Rabi',
            'qubits': qubits,
            'signal': signal,
        },
        'sweep_setting': {
            tuple(qubits): tuple([
                generate_spanlist(center=scale[q], st=scale[q]*(1-1/n), ed=min(1, scale[q]*(1+1/n)), sweep_points=sweep_points, mode=mode) for q in qubits
            ]),
        },
        'sweep_addition': {
            'circuit': lambda n=n, **kw: [
                *[(('rfUnitary', np.pi, 0, ('with',
                                            ('param:amp', [[0, 0.5], [0, kw[q]]]))), q) for q in qubits]*n,
                ('Barrier', tuple(qubits)),
                *[(('Measure', j), q) for j, q in enumerate(qubits)],
            ],
        },
    }
```

### 同时扫delta参数和buffer，二维扫描
```python

from itertools import chain
from typing import Optional

def XXDelta_buffer(qubits: list[str], buffer_list: np.ndarray,
                   n: int = 1, bound: float = 60e6, mode: str = 'linear', sweep_points: int = 21, ini_gate=('rfUnitary', np.pi, np.pi/2),
                   signal: str = 'iq_avg', act_qubits: Optional[list[str]] = None,
                   with_other_params: list[tuple] = [], **kw) -> dict:
    """
    [f'{q}'] measure DRAG delta using a sequence as 'Y'-'X'-'-X'-'X'-'-X'-...-'X'-'-X'.

    Args:
        qubits (list[str]): the qubit name.
        buffer_list (np.ndarray): array of buffer.
        n (int, optional): numbers of pulses 'X' and '-X'. Defaults to 1.
        bound (float, optional): delta upper bound, actually bound/n is applied. Defaults to 60e6.
        mode (str, optional): in ['linear' (for linear time sampling), 'log' (for log time sampling)]. Defaults to 'linear'.
        sweep_points (int, optional): sweep points. Defaults to 21.
        ini_gate (tuple, optional): first gate. Defaults to ('rfUnitary', np.pi, np.pi/2).
        signal (str, optional): signal. Defaults to 'iq_avg'.
        act_qubits (Optional[list[str]], optional): act qubits. Defaults to None.
        with_other_params (list[tuple], optional): other params. Defaults to [].
    """

    act_qubits = qubits if act_qubits is None else act_qubits
    sweep_list = generate_spanlist(
        center=0, delta=bound/n, sweep_points=sweep_points, mode=mode)

    return {
        'init': {
            'name': 'X-X Delta Buffer',
            'qubits': qubits,
            'signal': signal,
        },
        'sweep_config': {
            q: {
                'addr': f'gate.rfUnitary.{q}.params.delta',
            } for q in qubits
        },
        'sweep_setting': {
            tuple(act_qubits): tuple([
                sweep_list+kernel.get(f'gate.rfUnitary.{q}.params.delta') for q in act_qubits
            ]),
            'buffer': buffer_list,
        },
        'sweep_addition': {
            'circuit': lambda buffer, n=n, **kw: [
                *[(ini_gate, q) for q in act_qubits],
                *chain.from_iterable(zip([*[(('rfUnitary', np.pi, 0,
                                              ('with', ('param:buffer', buffer), ('param:delta', kw[q]), *with_other_params)), q) for q in act_qubits]*n],
                                         [*[(('rfUnitary', np.pi, np.pi,
                                              ('with', ('param:buffer', buffer), ('param:delta', kw[q]), *with_other_params)), q) for q in act_qubits]*n])),
                ('Barrier', tuple(qubits)),
                *[(('Measure', j), q) for j, q in enumerate(qubits)],
            ],
        },
    }

para_dict = XXDelta_buffer(['Q0', 'Q1'], buffer_list)
```

> 以上三个例子从脚本语言到逐渐封装成固定功能，每种写法都有自己的用途和适用者，没有优劣之分，请注意体会。

## 进阶：参数之间依赖如何解决

在一些实验中，有时候会出现参数依赖的关系，例如在混频方案下，想固定载波频率来扫描频率，此时就会产生一个参数依赖，自变量只有一个，但是随之变化的变量有多个，此时就要怎么来描述依赖关系。

### 尽量在扫描参数阶段描述，学会利用扫描变量的语法支持能力

在前面扫描参数的定义中，已经支持了一些参数依赖功能，大多数情况下，推荐使用扫描参数解释器中的参数依赖解决，例如
```python
para_dict = {
    # 忽略其他内容，只保留关键内容，扫描范围为sweep_list
    'sweep_config': {
        'freq': {
            'addr': 'gate.Measure.Q0.params.frequency',
        },
        'lo': {
            'addr': 'Q0.setting.LO',
        },
    },
    'sweep_setting': {
        'freq': sweep_list
    }
    'sweep_addition': {
        'lo': lambda freq: freq-100e6
    }
}
```
又或者
```python
para_dict = {
    'sweep_config': {
        'freq': {
            'addr': 'gate.Measure.Q0.params.frequency',
        },
        'lo': {
            'addr': 'Q0.setting.LO',
        },
    },
    'sweep_setting': {
        ('freq', 'lo'): (sweep_list, sweep_list-100e6),
    }
}
```

### 使用scanner内置的约束管理器

如果利用扫描参数生成的能力还是感觉到描述困难，不如考虑一下`Scanner`内置的约束更新。

目前的约束更新是在原约束管理器的基础上发展而来的，考虑到原约束管理器的脉冲响应式更新方式，这里在更新顺序上做了一些调整，即采用了按照拓扑序更新的方式来维护参数，避免了一些错误的可能。同时对原有描述方式做了一些改善和补充。

> 在逻辑关系上参数依赖自发的构成一张有向图，在生成时必须要先判断环，并且按照图上的拓扑序更新。这句话写给有缘人，能看懂的自然能看懂，看不懂的就当没看见。

一条约束是一个三元组`(keys, func, goal)`，`keys`是可迭代对象，表示一个或多个自变量，`func`是可调用对象，用于计算唯一因变量`goal`。

实际上，不同约束之间的因变量不能相同。如果有多条约束指向同一个因变量，那么此时这多条约束之间还存在一个未被告知的信息，可以认为是多条约束之间的优先级关系，那么实际上这样的描述是不完备的。为了补充信息且避免错误，此时就必须引入辅助变量来补充这部分信息，从某种角度上来说这可能会引起约束描述的复杂性。

在`Scanner`内部，`'constrans'`字段中传入的是多条约束组成的列表，故而类型为`list[tuple]`。一个简单的例子如下，
```python
para_dict = {
	# 其余部分略，只写与约束有关的内容
	'setting': {
		'delta': 0,
		'qubit_frequency': {
			'Q0': 7.1e9,
			'Q1': 7.2e9,
		},
		'LO_frequency': {
			'M0': 7e9,
		}
	},
	'constrains': [
		(('setting.qubit_frequency.Q0', 'setting.delta'), lambda a, b: a+b, 'gate.Measure.Q0.params.frequency'), # 第一条约束
		(('setting.qubit_frequency.Q1', 'setting.delta'), lambda a, b: a+b, 'gate.Measure.Q1.params.frequency'), # 第二条约束
		(('setting.LO_frequency.M0', 'setting.delta'), lambda a, b: a+b, 'M0.setting.LO'), # 第三条约束，假设M0是Q0和Q1的对应probe
	],
}
```
此时在如果独立地改变`setting.delta`中的值，相应的参数中的值也会发生改变，这就实现了按照约束响应式更新的内容。

这里的`key`和`goal`支持`config`中的访问，辅助变量建议使用`setting`中开辟的存储空间。在`setting`内部，支持多层嵌套字典按照类的对象式访问。

## 进阶：如何追踪不在扫描描述中的参数变化

如果我们在实验中创建了一个辅助变量，在迭代中会随着迭代过程变化，但是很遗憾，扫描变量记录`index`里面无法记录下来，是否有办法能自发追踪参数的变化？答案是可以的，请看以下例子：
```python
def CR_tomo_amp1(qubits: list[tuple[str]],
                 st: Optional[float] = None, ed: Optional[float] = None, sweep_points: int = 13, mode: str = 'linear',
                 tomo_time_length: float = 10, tomo_time_step: float = 0.1,
                 gate1: list = ['I', 'X'], gate2: list = ['-Y/2', 'X/2', 'I'],
                 signal: str = 'population', default_type: str = 'default', **kw) -> dict:
    """
    [Feed 'duration'] H tomography for CR as amp1 changing.

    Args:
        qubits (list[tuple[str]]): qubit names.
        st (Optional[float], optional): scale start. Defaults to None.
        ed (Optional[float], optional): scale end. Defaults to None.
        sweep_points (int, optional): sweep points. Defaults to 13.
        mode (str, optional): sampling mode. Defaults to 'linear'.
        tomo_time_length (float, optional): times of duration. Defaults to 10.
        tomo_time_step (float, optional): step of duration. Defaults to 0.1.
        gate1 (list, optional): gate on control. Defaults to ['I', 'X'].
        gate2 (list, optional): gate on target. Defaults to ['-Y/2', 'X/2', 'I'].
        signal (str, optional): signal. Defaults to 'population'.
    """

    config_type = 'params' if default_type == 'default' else default_type

    amp1 = {
        q: kernel.get(f'gate.CR.{q[0]}_{q[1]}.{default_type}.amp1') for q in qubits
    }
    strength = {
        q: kernel.get(f'gate.CR.{q[0]}_{q[1]}.{default_type}.duration')*amp1[q] for q in qubits
    }
    readout_qubits = _cr_readout_list(qubits=qubits, **kw)

    return {
        'init': {
            'name': 'CR Tomo Amp1',
            'qubits': qubits,
            'signal': signal,
        },
        'setting': {
            'feed': lambda _, step, amp1=amp1, strength=strength, qubits=qubits: step.feed(
                {
                    'duration': [
                        strength[q]/amp1[q]/step.kwds['amp1_times']*step.kwds['duration_times'] for q in qubits
                    ]
                },
                store=True), # 核心就在这里，添加一个Callable对象，通过step.feed(追踪值)来返回需要跟踪的对象。此时会在result中增加一个名为'duration'的关键字，记录了每次迭代中duration的值
        },
        'sweep_setting': {
            'amp1_times': generate_spanlist(st=st, ed=ed, sweep_points=sweep_points, mode=mode),
            'duration_times': np.arange(tomo_time_step, tomo_time_length + tomo_time_step, tomo_time_step),
            'gate1': gate1,
            'gate2': gate2,
        },
        'sweep_addition': {
            'circuit':
            lambda amp1_times, duration_times, gate1, gate2, amp1=amp1, strength=strength, qubits=qubits: [
                *[(gate1, q[0]) for q in qubits],
                *[(('CR', ('with',
                           ('type', default_type), # 切换同一个门的多种实现方式
                           ('param:duration',
                            strength[q]/amp1[q]/amp1_times*duration_times),
                           ('param:amp1', amp1[q]*amp1_times))), q) for q in qubits],
                *[(gate2, q[1]) for q in qubits],
                ('Barrier', tuple(chain.from_iterable(qubits))),
                *[(('Measure', j), q) for j, q in enumerate(readout_qubits)],
            ],
        },
    }
```
同时，这个例子中也展示了如何切换同一个门的多种实现方式，在门的自定义和编译中会进一步介绍。

## 进阶：如何构造测量中带反馈的参数体系

扫描不仅仅是预定好参数（无反馈）的扫描，也可以是有反馈式的扫描。在上一代`Scanner`中，只支持了无反馈的体系，而目前这一代将反馈的能力包含了进来。换言之，可以根据前若干步的扫描结果，来决定接下来若干步的扫描参数，然后如此往复，实现参数优化的过程。

### 利用扫描参数描述进行支持

可以参考以下的例子，利用固定长度的两比特RB线路的population，来优化两比特门参数。注意框架逻辑，具体的执行内容并不重要，因为会根据具体实验来进行替换。

```python
lost_value = {} # 用来存优化目标函数的，因为一些未知bug，目前还不能顺利feed进去，只能是在脚本中定义了一个追踪值

# 执行优化的线路（们），不要在意具体形式
def opt_circuit(qubits, seed_list=np.random.randint(0xfffffff,size=[1]), cycle=2, base=base):
    from itertools import chain
    from qos_tools.experiment.libs.fidelity import _cr_2RB
    ret = []
    for seed in seed_list:
        tmp = []
        tmp.extend([('X', q[0]) for q in qubits])
        tmp.extend([('X', q[1]) for q in qubits])
        for q in qubits:
            tmp.extend(_cr_2RB(qubits=q, cycle=cycle, seed=seed, base=base, interleaves=(576, [('CR', (0, 1))])))
        tmp.append(('Barrier', tuple(chain.from_iterable(qubits))))
        tmp.extend([(('Measure', i), q) for i, q in enumerate(chain(*qubits))])
        ret.append(tmp)
    return ret

# 优化损失函数，根据执行优化线路的结果来确定
def opt_lost(qubits, result):
    diag = count_recount(result, qubits=qubits)
#     diag = qpt_diag_recount(np.asarray(result), qubits=qubits)
    ret = []
    for i, q in enumerate(qubits):
        ret.append(-np.mean(diag[i, :, 3])+np.std(diag[i, :, 3])*0.25)
    return ret

# 优化用的参数配置字典
def opt_CR_rb(qubits, var_list, low_list, high_list, circuit_func, lost_func, signal, max_iters = 10, mul_list = ['amp2']):
    
    # 定义反馈控制优化函数，需要执行lost函数计算，将相应的值设置回去，基本是固定操作。
    def _feed_back_func(task, step, lost_func=lost_func, qubits=qubits, var_list=var_list):
        lost_list = lost_func(qubits, [item.result()[signal] for item in task._cache])
#         step.feed({f'{q[0]}_{q[1]}_lost': lost_list[i] for i, q in enumerate(qubits)}, store=True) 注释掉的原因已经解释过了
        for i, q in enumerate(qubits):
            if f'{q[0]}_{q[1]}_lost' not in lost_value.keys():
                lost_value[f'{q[0]}_{q[1]}_lost'] = []
            lost_value[f'{q[0]}_{q[1]}_lost'].append(lost_list[i])
            step.feedback(tuple(f'{q[0]}_{q[1]}_{var}' for var in var_list), lost_list[i])
        task._cache = []
    
    from waveforms.scan_iter import OptimizerConfig
    from qos_tools.feedback.ngOpt import NgOpt, VarData
    # NgOpt是包装的nevergrad库的优化函数，还可以封装其他优化库的函数，只要具有标准接口，就可以顺利介入Scanner，另一个已经封装优化库是sklearn里面的贝叶斯优化。默认支持scipy的optimize。
    return {
        'init': {
            'name': f'CR opt {var_list}',
            'qubits': qubits,
            'signal': signal,
        },
        'setting': {
            'level_marker': True, # 使用反馈式扫描必须添加的关键字和值
            'feedback': {
                0: _feed_back_func, #
            }, # 这里需要写一个参数优化层级和对应的优化处理的过程，比如下面对应的优化参数都位于第一层迭代，对应的优先级别就是0。如果是优化套优化，就可以需要两个优化处理函数，位于不同的层级上。
        },
        'sweep_config': {
            f'{q[0]}_{q[1]}_{var}': {'addr': f'gate.CR.{q[0]}_{q[1]}.params.{var}'} for var in var_list for q in qubits
        },
        'sweep_setting': {
            tuple(
                tuple(f'{q[0]}_{q[1]}_{var}' for var in var_list) 
            for q in qubits): tuple(
                OptimizerConfig(NgOpt,
                               [VarData('add' if var not in mul_list else 'mul', 
                                        kernel.get(f'gate.CR.{q[0]}_{q[1]}.params.{var}'),
                                        low_list[i], 
                                        high_list[i],) for i, var in enumerate(var_list)], 
                                kwds={
                                    'config': {'budget': max_iters},
                                }, max_iters=max_iters) for q in qubits
            ), # 同时优化多个参数，创建一层优化。
            'circuit': opt_circuit(qubits),
        },
    }
```
上面例子给出了一个单层优化多参数的逻辑例子。实际上还可以支持优化套优化，如果有需求的可以直接找笔者。

### 学会在外层套用优化器控制

如果上面的例子实在是看不懂，那么优化反馈的逻辑其实是这样的：
初始化一个优化器
当循环迭代次数还没达标的时候：
1. 向一个优化器询问目前建议的参数是什么
1. 按照询问到的参数创建一个无反馈的扫描（子线路），获得一些结果，计算一些损失函数
2. 将执行的参数和损失函数喂回优化器，
1. 重复以上步骤直到达到理想迭代次数

对，也就是自行编程写一个简单的优化器控制，并不困难，代码量也不大。一个简单脚本就可以实现。

## 进阶：如果使用了其他语法写的线路怎么处理？

实际上在最早的`Scanner`里面支持了语言类型转换，不过功能很旧，支持的语法转换也不多。在Qlisp里面也具有相应的模块，目前这里正在功能整合。急需的话可以翻旧文档，这里就不再啰嗦了。