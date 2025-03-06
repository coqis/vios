### **安装**

#### 前置条件？
- 安装好[**git**](https://git-scm.com/)（如何安装自行查找）。
- 安装[**python**](https://python.org)，建议3.12（如何安装自行查找）。
    > 安装前，**务必**删除干净电脑上**多余的Python或Conda**！！！
    > 对于Windows，安装后确保**环境变量**被正确设置，否则提示命令找不到！！！


#### 什么是systemq？
- systemq本身：包含设备驱动**dev**和门定义**lib**
- 编译器：包含**waveforms**、**waveforms-math**、**qlisp**、**qlispc**，核心功能为将线路转为波形等指令序列
- quarkstudio：主要由**server**和**studio**及其他系列组合构成（输入quark后回车可看到其他子命令选项），其中**server**用于管理**cfg表**和**设备**并执行编译生成的指令，**studio**用于可视化数据。


#### 如何安装systemq？

    ``` bash
    # 下载systemq，默认在当前路径下
    git clone https://gitee.com/baqis/systemq.git

    # 安装，依赖项会自动安装
    cd systemq
    pip install -e.
    ```

#### 如何检查安装是否成功？
- 执行```pip show systemq```，若返回相关信息则安装成功！

#### 版本一致吗？
- 检查设备上的numpy（**大**版本同为1.x.x或2.x.x）和waveforms版本和测量电脑是否一致！


### **使用**
#### demo在哪儿？
- [notebook](demo.ipynb)
- [circuit](circuit.py)
- 鼠标右键点击顶部右侧箭头另存可下载对应demo文件

#### 什么是cfg表？
- cfg表本质是一个json文件或Python中的字典包含
    - dev: 存放设备相关的信息
    - etc：存放配置信息
    - 比特/读取等各类硬件连接、配置和门参数等实验相关信息

#### cfg表怎么填写？
- 参考[checkpoint.json](checkpoint.json)
- 填写完毕将其复制到： **~/Desktop/home/cfg**(如目录不存在可自行创建)
- 完成后可以在终端中启动[服务](../quark/server.md)，即```quark server```
- [注册](../quark/server.md)cfg表

#### server启动后，start干了什么？
- 根据设备连接类型不同打开或连接设备（可参考**quark server**启动时开始的信息）
- type=[driver](../quark/server.md/#what-is-dev)
    - 根据**name**导入Driver
    - 传入**addr**实例化Driver
    - 执行**open()**
    - 即将dev中设备按如下方式打开
        ```bash
        for alias, info in dev.items():
            from systemq.dev import info['name'] as device
            d = device.Driver(info['addr'])
            d.open()
        ```
- type=[remote](../quark/remote.md)
    - ```connect(‘alias’, host, port) # 三个参数需和设备上配置完全一致```
    - 没有open()

#### 设备打开不正常？
- 检查cfg表中`etc.driver.path`字段是否正确，默认应为`systemq/dev`
- 如果是remote设备，检查设备**别名**、**host**和**port**是否一致！

#### 线路编译错误？
- 检查线路编写是否有误！
- 检查`systemq.lib.gates.__init__`中导入的门模块是否正确，或cfg表中填写的参数是否与对应的门匹配！
