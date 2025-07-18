---
hide:
  - navigation
  - toc
---

- 配置表是一个[json文件](checkpoint.json)，习惯上称之为`cfg`表
- cfg中主要包含比特参数信息(**qubit**)、硬件连接信息(**dev**)及其他程序运行所需配置信息


???+ Tip annotate "***qubit***" 
    ```python linenums="1"
    {
        "probe": { # (1)
            "address": "NS_6_Read.CH11.Waveform",
            "delay": 0
        },
        "acquire": { # (2)
            "address": "NS_6_Read.CH11.IQ",
            "TRIGD": 0
        },
        "drive": { # (3)
            "address": "NS_6_XY1.CH5.Waveform",
            "delay": 0
        },
        "flux": { # (4)
            "address": "ChipQ4_1.CH1",
            "delay": 0,
            "distortion": {
                "decay": [],
                "expfit": [],
                "multfit": []
            }
        },
        "R": {  # (5)
                "shape": "cosPulse",
                "frequency": 4000000000.0,
                "amp": 0.2,
                "width": 2e-08,
                "plateau": 0,
                "eps": 1,
                "buffer": 0,
                "alpha": 1,
                "beta": 0,
                "delta": 0,
                "block_freq": None,
                "tab": 0.5
        },
        "R12": {  # (6)
            "shape": "cosPulse",
            "frequency": 3800000000.0,
            "amp": 0.2,
            "width": 2e-08,
            "plateau": 0,
            "eps": 1,
            "buffer": 0,
            "alpha": 1,
            "beta": 0,
            "delta": 0,
            "block_freq": None,
            "tab": 0.5
        },
        "Measure": {  # (7)
            "frequency": 6960875000.0,
            "duration": 1.8e-06,
            "amp": 0.08,
            "ring_up_amp": 0.04,
            "ring_up_time": 5e-08,
            "rsing_edge_time": 5e-09,
            "buffer": 0,
            "space": 0,
            "weight": "square(1800e-9)>>900e-9",
            "bias": None,
            "signal": "state",
            "threshold": 0,
            "phi": 0,
            "PgPe": [
                0,
                1
            ]
        },
        "caliinfo": {
            "sweetbias": 0,
            "idlebias": 0,
            "isobias": 0,
            "readbias": 0,
            "spectrum2D": []
        },
        "topoinfo": {
            "couplers": [
                "QC120"
            ],
            "NQ": [
                "Q65"
            ],
            "HNNQ": [
                "Q70"
            ],
            "VNNQ": [
                "Q59"
            ]
        },
        "params": {
            "T1": 0,
            "T2_star": 0,
            "T2_echo": 0,
            "1Qfidelity": 1,
            "Readfidelity_g": 1,
            "Readfidelity_e": 1
        }
    }
    ```


1.  :material-transit-connection-variant: 读取通道
    - address：格式为`设备.通道.属性`，`属性`列表参见驱动文件的`quants`。波形由**Measure**门生成。
    - address以外的其他参数（比如delay）传与`quark.interface.Workflow.calculate`，即其中的`cali`
    ```python
    pulse = sample_waveform(func,
                            cali, # address以外的其他参数
                            sample_rate=kwds['srate'],
                            start=cali.get('start', 0),
                            stop=cali.get('end', 98e-6),
                            support_waveform_object=support_waveform_object)
    ......
    ```
2.  :material-transit-connection-variant: 采集通道
    - address：同**读取通道**。解调系数由编译生成的**Coefficient**生成。
    - TRIGD: 触发延时
    - 采集回来的数据传与`quark.interface.Workflow.process`处理，实际调用函数为`lib.arch.rcp.data.assembly_data`
    ```python
    def assembly_data(raw_data: RawData, dataMap: DataMap) -> Result:
        if not dataMap:
            return raw_data

        result = {}

        def decode(value):
            if (isinstance(value, tuple) and len(value) == 2
                    and isinstance(value[0], np.ndarray)
                    and isinstance(value[1], np.ndarray)
                    and value[0].shape == value[1].shape):
                return value[0] + 1j * value[1]
            else:
                return value

        ......
    ```
3. :material-transit-connection-variant: 驱动通道
    - address：同**读取通道**，波形由**R**门生成
4. :material-transit-connection-variant: 偏置通道
    - address：同**读取通道**，波形由**setBias**门生成
5. :material-transit-connection-variant: **R**门
    - 编译生成的波形写入**drive**通道
    - 见lib.gates.u3中**R**门
    ```python
    def R(ctx: Context, qubits, phi=0, level1=0, level2=1):
        qubit, = qubits

        freq, phase = get_frequency_phase(ctx, qubit, phi, level1, level2)
        amp = ctx.params.get('amp', 0.5)
        shape = ctx.params.get('shape', 'cosPulse')
        width = ctx.params.get('width', 5e-9)
        plateau = ctx.params.get('plateau', 0.0)
        buffer = ctx.params.get('buffer', 0)
        tab = ctx.params.get('tab', 0.5)
        phi = ctx.params.get('phi', 0)
        ......
    ```
6. :material-transit-connection-variant: **R12**门
    - 编译生成的波形写入**drive**通道
    - 见lib.gates.u3中**R12**门
    ```python
    @lib.opaque('R12')
    def _R12(ctx: Context, qubits, phi=0):
        yield from R(ctx, qubits, phi, 1, 2)
    ```
7. :material-transit-connection-variant: **Measure**门
    - 编译生成的波形写入**probe**通道
    - 见lib.gates.u3中**Measure**门
    ```python
    @lib.opaque('Measure')
    def measure(ctx: Context, qubits, cbit=None):
        from qlispc.libs.stdlib import extract_variable_and_index_if_match
        from waveforms import cos, exp, pi, step

        qubit, = qubits

        if cbit is None:
            if len(ctx.measures) == 0:
                cbit = 0
            else:
                cbit = max(ctx.measures.keys()) + 1

        if isinstance(cbit, int):
            cbit = ('result', cbit)
        elif isinstance(cbit, str):
            cbit = extract_variable_and_index_if_match(cbit)

        # lo = ctx.cfg._getReadoutADLO(qubit)
        amp = ctx.params['amp']
        duration = ctx.params['duration']
        frequency = ctx.params['frequency']
        bias = ctx.params.get('bias', None)
        signal = ctx.params.get('signal', 'state')
        ring_up_amp = ctx.params.get('ring_up_amp', amp)
        ring_up_time = ctx.params.get('ring_up_time', 50e-9)
        rsing_edge_time = ctx.params.get('rsing_edge_time', 5e-9)
        buffer = ctx.params.get('buffer', 0)
        space = ctx.params.get('space', 0)
        ......
    ```



???+ Tip annotate "***dev***" 
    ```python linenums="1"
    { # 设备列表(1)
        "MW1": { 
            "addr": "192.168.126.25",
            "name": "PSG",
            "type": "driver", # (2)
            "srate": -1.0,
            "pid": 1989,
            "Keepmode": None,
            "model": None,
            "inuse": true
        },
        "NA": {
            "addr": "192.168.103.125",
            "name": "NetworkAnalyzer",
            "type": "driver",
            "srate": -1.0,
            "pid": 62605,
            "Keepmode": None, # 其他设置，可选
            "model": "3674C", # 设备型号，可选
            "inuse": true
        },
        "ChipQ4_1": {
            "type": "remote", # (3)
            "srate": 2000000000.0,
            "pid": 62605,
            "inuse": true,
            "host": "127.0.0.1",
            "port": 40043
        }
    }
    ```

1.  :material-developer-board: 设备列表
    - 记录设备信息
    - 根据设备连接类型不同打开或连接设备，即
    ```python
    for alias, info in dev.items():
        if info['type'] == 'driver':
            from dev import info['name'] as device
            d = device.Driver(info['addr'])
            d.open()
        elif info['type'] == 'remote':
            d = connect(‘alias’, host, port)
    ```
2. :material-developer-board: **driver**类型
    - name: 必需，设备驱动文件名，位于**dev**下
    - addr：必需，连接设备所需的ip地址
    - srate：读取自驱动的**srate**属性
    - inuse：必需，是否使用
    - 其他必要的信息
3. :material-developer-board: **remote**类型
    - host：必需，设备内操作系统的ip地址
    - port：必需，**remote.json**配置中分配给设备的端口号（习惯上取在40000到50000之间的整数）
    - srate：读取自驱动的**srate**属性
    - inuse：必需，是否使用
    - 其他必要的信息
