
### Remote设备（内含windows或linux）配置

- **remote目录结构**
  ```CoffeeScript
  remote # 与设备相关的驱动文件统一放`~/Desktop/remote`目录下
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
          "name": "dev.VirtualDevice", # 必填
          "addr": "192.168.1.41" # 必填，卡地址 
          "slot": 1, # 可选
          "borad_type":"XY", # 可选
          "srate":4e6, # 可选，传与driver属性`srate`
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

### 测量电脑连接remote设备

- **连接remote设备**
  ```Python
  # 在notebook中快速测试连接
  from quark import connect

  # host为设备内x86系统的IP地址，不是卡地址，port为remote.json中配置的端口
  awg1 = connect('AWG1',host='192.168.1.12',port=40001) 
  # 如果成功，则返回设备信息
  awg1.info() 
  ```
  ```Python
  # 在server中配置dev信息
  {
      "AWG1": { # 第一块卡
          "type": "remote", # 必填
          "host": "192.168.1.12", # 与设备内x86系统的IP地址一致
          "port": 40001 # 与remote.json中配置的端口一致
      },
      "AWG2": { # 第二块卡
          "type": "remote",
          "host": "192.168.1.12", # 与设备内x86系统的IP地址一致
          "port": 40002 # 与remote.json中配置的端口一致
      },
      ...
  }
  ```
- **管理remote服务**
  ```Python
  # 在notebook中连接remote服务
  from quark import s

  # host为设备内x86系统的IP地址，不是卡地址
  rs = s.remote(host='192.168.1.12') 
  # 如果成功，则返回remote.json中配置的设备信息
  rs.info() 
  ```


