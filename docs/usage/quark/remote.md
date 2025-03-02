# **Introduction to QuarkRemote**
### **How to start**
???+ example "start"
    ```bash
    # pip install quarkstudio[remote] (if not installed)
    quark remote remote.json
    ```

### :material-remote: ***QuarkRemote***

<!-- !!! note "适用于自身带有操作系统的设备" -->

**QuarkRemote** runs on the device's built-in operating system(often windows or linux) and mainly implements functions such as device control and remote software updates. Below is a simple user manual:

Clone the [`remote`](https://gitee.com/baqis/remote.git) wherever you want,
``` bash title="remote folder"
remote
├── dev
│   ├── VirtualDevice.py # (1)!
│   └── __init__.py
├── remote.json # (2)!
├── requirements.txt # (3)!
└── setup.py # (4)!
```

1. :material-language-python: VirtualDevice
    [driver template](https://quarkstudio.readthedocs.io/en/latest/modules/quark/driver/VirtualDevice/)
2. :material-code-json: remote
    ```python title="remote.json"
    {
        "path":"dev", # driver path
        "host":"192.168.1.42", # IP address of the host computer
        "ADC": { # alias of the device
            "name": "VirtualDevice", # filename of the driver
            "addr": "192.168.1.44" #  # IP address of the device
            "port": 1169 # service port
        }
    }
    ```
3. :material-text-box:requirements
    ```python title="requirements.txt"
    waveforms-math
    quarkstudio[remote]
    ```
4. :material-language-python: setup
    ```python title="setup.py"
    from setuptools import setup

    with open('requirements.txt', encoding='utf-8') as f:
        requirements = f.read()

    setup(
        name="remote",
        version='1.0.0',
        author="baqis",
        license="MIT",
        description="Remote Driver",
        install_requires=requirements,
        python_requires='>=3.10.0'
    )
    ```

Run `pip install -e.` in the `remote` folder (run `pip show remote` to check) and `quark remote remote.json` to start the remote service. 

To connect the device `ADC` on another computer within the same local area network (LAN), please refer to the following example
???+ Example "connect to a remote device"
    ```python
    # pip install quarkstudio (if not installed)
    from quark import connect

    adc = connect('ADC',host='192.168.1.42',port=1169)
    # driver methods can be called with adc as if it was a local driver instance
    adc.getValue('IQ')
    ```
