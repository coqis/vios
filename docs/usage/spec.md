## 环境一致性

### 基础环境

1. git
2. python >= 3.12

### 测量环境

1. `quark init`下载dev/glib等并安装所有依赖（systemq的toml文件）。**可反复执行**
2. `quark update`(uv还需要`uv sync -U`来更新lock文件)更新相关库。**可反复执行**

## Remote设备（含windows或linux）

- **remote目录结构**
  > 驱动相关文件统一放`~/Desktop/remote`目录下
  > 启动服务配置文件命名统一为`quarkremote.service`。后续通过`s.remote`管理。
  ```CoffeeScript
  remote # 目录结构和命名保持一致
  ├── dev
  │   ├── common # 可选，如果有dll/so等动态链接库，放在这里
  │   └── VirtualDevice.py # 继承BaseDriver并实现open/close/write/read 
  └── remote.json # 配置文件，见下方说明
  ```
- **启动remote服务**
  ```Shell
  # 安装：pip install -U quarkstudio
  # 初始化或更新：quark init/update --mode=remote
  # 在remote目录下执行（如果需要root权限，需要在命令前加sudo）
  quark remote remote.json
  ```
- **remote.json内容**
  ```JSON
  {
      "AWG1": { # 第一块卡
          "name": "dev.VirtualDevice",
          "addr": "192.168.1.41" # 卡地址 
          "slot": 1,
          "borad_type":"XY",
          "srate":4e6,
          "port": 40001 # 端口不能相同，否则会冲突
      },
      "AWG2": { # 第二块卡
          "name": "dev.VirtualDevice",
          "addr": "192.168.1.42" 
          "slot": 2,
          "borad_type":"Z",
          "srate":2e6,
          "port": 40002 # 端口不能相同，否则会冲突
      },
      ...
  }
  ```

## 关于实验

能够引起不同的地方，除了设备差异，还有：

- lib: Recipe.lib = "path/to/u3.py"
- 线路：rcp.circuit = cc.S21
- 可执行文件`exp.py`
  1. 线路定义：def circuit():...
  2. 入口定义：def run():...
  3. 执行：`python exp.py`(`if __name__ == "__main__": run()`)

