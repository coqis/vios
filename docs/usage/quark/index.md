# **Beginner's Guide**

## 1. **安装配置**
- [安装](../#installation)前：若无把握，**务必**删除干净电脑上**所有多余的Python或Conda**！！！
- [安装](../#installation)后：确保**环境变量**被正确设置，否则提示命令找不到！！！


## 2. **实验过程**

### **导入模块**
```python

import matplotlib.pyplot as plt
import numpy as np

from quark.app import Recipe, s, submit  # (1)!
```

???+ note "导入模块"
    1. :material-language-python: quark.app
        - Recipe: 记录任务信息，生成任务描述
        - s: 与server进行通信交互的工具，如
            - 更新参数：`s.update('gate.Measure.Q0.params.frequency', 5.321e9)`
            - 查询参数：`s.query('gate.Measure.Q0.params.frequency')`
            - 写设备：`s.write('ZW_AD3.CH1.Offset', 0.2)`
            - 读设备：`s.read('ZW_AD3.CH1.Offset')`
        - submit: 向server提交Recipe生成的任务



### **准备工作**

???+ warning "启动服务"
    - 将实验所用配置信息表（如[checkpoint.json](../code/checkpoint.json)，后以**cfg**代称）复制到： ~/Desktop/home/cfg(如目录不存在可自行创建)
    - 任意位置打开终端并执行`quark server`以启动[**QuarkServer**](server)(后以**server**代称)
    - 注册登录

```python
s.login('baqis') # 登录 (1)

# s.signup('baqis','checkpoint') 注册 (2)

s.start() # 打开设备 (3)
```

???+ tip "注册登录"
    1. :material-language-python: login
        - 如果login提示错误，则执行signup操作
        - 每次重启server都需要重新login，用户名与注册时保持一致

    2. :material-language-python: signup
        - 用户名任意(此处为baqis)，用于login
        - signup完毕后重新login

    2. :material-language-python: start
        - 根据设备连接类型不同打开或连接设备
            ```python
            for alias, info in dev.items():
                if info['type'] == 'driver':
                    from dev import info['name'] as device
                    d = device.Driver(info['addr'])
                    d.open()
                elif info['type'] == 'remote':
                    d = connect(‘alias’, host, port)
            ```
        - 设备打开之前，任务不可执行！
        - 若设备打开异常，参考**设备调试**进行排查！


### **Example: s21**

#### 编写线路
```python
def S21(qubits: list[str], freq:float, ctx=None) -> list: # (1)
    cc = [(('Measure', i, ), q) for i, q in enumerate(qubits)]
    return cc
```

1. :material-language-python: S21
    - ctx: 编译所用上下文，固定为最后一个参数，当前环境下等价于**s**，可用于查询**cfg**中的参数
    - cc: 返回每步的**qlisp**线路


```python
rcp = Recipe('s21', signal='iq_avg') # 任务定义
rcp.circuit = S21 # 线路指定 (1)

qubits = tuple(['Q0', 'Q4', 'Q9'])
rcp['qubits'] = qubits
rcp['freq'] = np.linspace(-5, 5, 101) * 1e6 # (2)

for q in qubits: # 参数设置 (3)
    rcp[f'gate.Measure.{q}.params.frequency'] = rcp['freq'] + \
        s.query(f'gate.Measure.{q}.params.frequency') # 变量关联
    rcp[f'gate.Measure.{q}.default_type'] = 'default' # 临时设置
```

???+ tip "编写线路"
    1. :material-language-python: Recipe
        - rcp.circuit: 定义任务并指定所用线路函数

    2. :material-language-python: rcp参数定义
        - rcp['qubits']：传与**S21**中**qubits**
        - rcp['freq']：当值为**list**或**np.array**时为扫描变量，迭代过程中，每次传一个值给**S21**中的**freq**

    3. :material-language-python: qubits参数设置
        - 将变量与**cfg**中的值关联
        - 临时更改**cfg**中的某些值，仅对当前任务有效

#### 提交任务
```python
s21 = submit(rcp.export(), block=False, preview=['M1'], plot=False) # (1)
s21.bar(interval=1)  # (2)
```

???+ note "提交任务"
    1. :material-language-python: submit
        - block: 是否阻塞当前任务
        - preview：指定要查看的波形（需要打开**quark canvas**）
        - plot：是否查看实时的测量数据（需要打开**quark viewer**）

    2. :material-language-python: bar
        - interval: 获取数据的周期，默认为2s

#### 获取结果
```python
rs = s21.result()
signal = rs['meta']['other']['signal'].split('|')[0]

r = np.asarray(rs['data'][signal])
ax = plt.subplots(1, 3, figsize=(12, 2))[1].flatten()
for i, q in enumerate(qubits):
    fq = rs['meta']['axis']['freq']['def']
    rq = np.abs(r)[:, i]
    ax[i].plot(fq, rq)

    ax[i].set_title(f'{q}')
```
![alt text](image/s21.png)


#### 常用函数

???+ abstract annotate "常用函数"
    - s21.report()：获取任务错误信息
    - s21.cancel()：取消任务执行流程
    - s21.circuit(0)：查看第0步线路
        ```python 
        [(('Measure', 0), 'Q0'), (('Measure', 1), 'Q4'), (('Measure', 2), 'Q8')]
        ```
    - s21.step(0)：查看第0步命令 (1)

        ```python 
        from quark.app import preview

        cmds = s21.step(0)
        wfv = preview(cmds['main'], start=0, end=10e-6, srate=5e9, keys=['M1'])
        ```
        ![alt text](image/preview.png)


1.  :man_raising_hand: 查看命令
    - cmds由编译生成，包含全部指令
    - cmds由三部分构成，依次顺序执行，分别为
        - cmds['main']: 写波形（驱动、偏置、读取等所有波形，可由`preview`函数看波形）、设置AD(如Shots、解调系数等)。
        - cmds['trig']: 待cmds['main']中命令全部就绪，触发设备开始发**trigger**。***trigger数量务必与AD中的Shots设置一致！！！***
        - cmds['READ']: 从设备将数据读回。如果没有数据返回或TIMEOUT，***第一时间检查触发设置***！！！
    - 若对下发到设备的指令存疑，可逐一排查cmds或单独执行cmds中命令以确定问题所在！


#### **日志信息**
???+ example "日志信息"
    - 📥[baqis, 0] 📤[2503072329410017622, 0] 🕓[100%(  1/  2)  0.000/ 0.436]<0.003, 0.003, 0.000> 💻(866.34, 3385.867)
    - 📥[用户名, 剩余任务数] 📤[任务id, 任务优先级] 🕓[进度(步数/总步数) 剩余时间/已用时间]<波形采样, **设备执行**, 数据处理> 💻(server占用内存, **系统剩余内存**)
    ???+ danger "日志信息"
        - 任务执行时间，一般情况下主要决定于**设备执行**时间！
        - **系统剩余内存**如果过低，可能会导致电脑死机！


#### **设备调试**
??? bug "设备调试"
    - 如需编写驱动（可参考dev中其他设备的实现）：
        - 设备驱动必须继承自BaseDriver(`from quark.driver.common import BaseDriver`)
        - 所有驱动必须实现`open`/`close`/`write`/`read`方法

    - 测试并确保设备驱动***完全无误***：
        ```python
        # 根据设备类型导入设备驱动，如网分
        from dev import NetworkAnalyzer

        # 根据设备地址实例化设备
        dev = NetworkAnalyzer.Driver('192.168.1.42')
        # 打开设备
        dev.open()

        # 设备写操作，通过setValue（实际调用`write`方法），可操作属性见驱动文件定义的quants列表
        dev.setValue('Power', -10)
        # 设备读操作，通过getValue（实际调用`read`方法），可操作属性见驱动文件定义的quants列表
        dev.getVaule('Power')
        ```
    - > 如在实验过程中发现设备不正常工作，回到此处按此方法进行查验！！！


#### **常见问题**
??? qustion "常见问题"
    ***遇到问题先看错误信息！遇到问题先看错误信息！遇到问题先看错误信息！***
    1. 设备没有正常开启？
    - 检查`etc.driver.path`是否正确，一般为`~/Desktop/home/dev`！
    - 设备`type`为`remote`时，检查设备名字、`host`和`port`是否和设备的ip和端口匹配！

    2. 线路编译错误？
    - 检查线路编写是否有误！
    - 检查`lib.gates.__init__`中导入的门模块是否正确，或cfg表中填写的参数是否匹配！

    3. 实验没有数据或采集设备显示超时？
    - 检查触发设备是否输出或`shots`设置和采集设备设置是否一致！

    4. 波形下发错误？
    - 检查设备上的numpy（**大**版本同为1.x.x或2.x.x）和waveforms版本和测量电脑是否一致！