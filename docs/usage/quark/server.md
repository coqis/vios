# **Introduction to QuarkServer**
### **How to start**
???+ example "start"
    ```bash
    # pip install quarkstudio[full] (if not installed)
    quark server
    ```


### :material-server: ***QuarkServer***
<!-- !!! info "cfg表及kernel配置" -->

- Create a folder named `home/cfg` on the desktop and place the cfg file(e.g., checkpoint_demo.json) in it. 

    ??? note "checkpoint demo"
        ```python
        {
            {
            "etc": {
                "driver": {
                    "path": "dev",
                    "concurrent": true,
                    "timeout": 30.0,
                    "filter": [
                        "send Waveform or np.array"
                    ],
                    "mapping": {
                        "setting_LO": "LO.Frequency",
                        "setting_POW": "LO.Power",
                        "setting_OFFSET": "ZBIAS.Offset",
                        "waveform_RF_I": "I.Waveform",
                        "waveform_RF_Q": "Q.Waveform",
                        "waveform_TRIG": "TRIG.Marker1",
                        "waveform_DDS": "DDS.Waveform",
                        "waveform_SW": "SW.Marker1",
                        "waveform_Z": "Z.Waveform",
                        "setting_PNT": "ADC.PointNumber",
                        "setting_SHOT": "ADC.Shot",
                        "setting_TRIGD": "ADC.TriggerDelay"
                    },
                    "root": "C:\\Users\\NUC\\Desktop\\quarkstudio\\systemqos"
                },
                "server": {
                    "workers": 1,
                    "shared": 0,
                    "delay": 10.0,
                    "cached": 5,
                    "review": [
                        0,
                        1,
                        10
                    ],
                    "schedule": {
                        "job": {
                            "hour": "2"
                        }
                    },
                    "filesize": 4000.0
                },
                "canvas": {
                    "range": [
                        0,
                        0.0001
                    ],
                    "filter": []
                },
                "cloud": {
                    "host": "172.16.1.251",
                    "online": false,
                    "station": "Dongling"
                    }
                }
            },
            "Q0101": {
                "probe": "M1",
                "couplers": [],
                "setting": {
                    "LO": 5000000000.0,
                    "POW": null,
                    "OFFSET": null
                },
                "waveform": {
                    "SR": 5000000000.0,
                    "LEN": 0.0001,
                    "DDS_LO": 5000000000.0,
                    "SW": "zero()",
                    "TRIG": "zero()",
                    "RF": "zero()",
                    "Z": "zero()",
                    "DDS": "zero()"
                },
                "channel": {
                    "I": null,
                    "Q": null,
                    "LO": null,
                    "DDS": "DA.CH1",
                    "SW": null,
                    "TRIG": null,
                    "Z": null
                },
                "calibration": {
                    "I": {
                        "delay": 0,
                        "distortion": null
                    },
                    "Q": {
                        "delay": 0,
                        "distortion": null
                    },
                    "Z": {
                        "delay": 0,
                        "distortion": null
                    },
                    "DDS": {
                        "delay": 0,
                        "distortion": null
                    },
                    "TRIG": {
                        "delay": 0,
                        "distortion": null
                    }
                },
                "index": [
                    -9,
                    -9
                ],
                "color": "green",
                "params": {
                    "T1": 22.877572853156877,
                    "T2star": 19.89653436653619,
                    "T2echo": 10.596272798347714,
                    "Ec": 293.64997371460817
                }
            },
            "Q0102": {
                "probe": "M1",
                "couplers": [],
                "setting": {
                    "LO": 5000000000.0,
                    "POW": null,
                    "OFFSET": null
                },
                "waveform": {
                    "SR": 5000000000.0,
                    "LEN": 0.0001,
                    "DDS_LO": 5000000000.0,
                    "SW": "zero()",
                    "TRIG": "zero()",
                    "RF": "zero()",
                    "Z": "zero()",
                    "DDS": "zero()"
                },
                "channel": {
                    "I": null,
                    "Q": null,
                    "LO": null,
                    "DDS": "DA.CH2",
                    "SW": null,
                    "TRIG": null,
                    "Z": null
                },
                "calibration": {
                    "I": {
                        "delay": 0,
                        "distortion": null
                    },
                    "Q": {
                        "delay": 0,
                        "distortion": null
                    },
                    "Z": {
                        "delay": 0,
                        "distortion": null
                    },
                    "DDS": {
                        "delay": 0,
                        "distortion": null
                    },
                    "TRIG": {
                        "delay": 0,
                        "distortion": null
                    }
                },
                "index": [
                    -9,
                    -9
                ],
                "color": "green",
                "params": {
                    "T1": 22.877572853156877,
                    "T2star": 19.89653436653619,
                    "T2echo": 10.596272798347714,
                    "Ec": 293.64997371460817
                }
            },
            "M1": {
                "qubits": [
                    "Q0101",
                    "Q0102"
                ],
                "adcsr": 2500000000.0,
                "setting": {
                    "LO": 0,
                    "POW": null,
                    "SHOT": 2048,
                    "TRIGD": 6.76e-07,
                    "PNT": 2048
                },
                "waveform": {
                    "SR": 5000000000.0,
                    "LEN": 0.0001,
                    "DDS_LO": 5000000000.0,
                    "SW": "zero()",
                    "TRIG": "zero()",
                    "RF": "zero()",
                    "Z": "zero()",
                    "DDS": "zero()"
                },
                "channel": {
                    "I": null,
                    "Q": null,
                    "LO": null,
                    "DDS": "DA.CH3",
                    "SW": null,
                    "TRIG": null,
                    "Z": null,
                    "ADC": "AD.CH1"
                },
                "calibration": {
                    "I": {
                        "delay": 0,
                        "distortion": null
                    },
                    "Q": {
                        "delay": 0,
                        "distortion": null
                    },
                    "Z": {
                        "delay": 0,
                        "distortion": null
                    },
                    "DDS": {
                        "delay": 4e-07,
                        "distortion": null
                    },
                    "TRIG": {
                        "delay": 0,
                        "distortion": null
                    }
                },
                "index": [
                    -9,
                    -9
                ],
                "color": "green"
            },
            "gate": {
                "index": [
                    -9,
                    -9
                ],
                "color": "green",
                "Measure": {
                    "Q0101": {
                        "default_type": "default",
                        "params": {
                            "duration": 4e-06,
                            "amp": 0.08,
                            "frequency": 6831710000.0,
                            "phase": [
                                [
                                    -1,
                                    1
                                ],
                                [
                                    -1,
                                    1
                                ]
                            ],
                            "weight": "const(1)",
                            "phi": 3.0329629454360374,
                            "threshold": -509981053.76118374,
                            "ring_up_amp": 0.08,
                            "ring_up_waist": 0.08,
                            "ring_up_time": 5e-07
                        },
                        "e2f": {
                            "duration": 4e-06,
                            "amp": 0.083,
                            "frequency": 6831710000.0,
                            "phase": [
                                [
                                    -1,
                                    1
                                ],
                                [
                                    -1,
                                    1
                                ]
                            ],
                            "weight": "const(1)",
                            "phi": -0.9911058876517705,
                            "threshold": 776721471.0094932,
                            "ring_up_amp": 0.083,
                            "ring_up_waist": 0.083,
                            "ring_up_time": 5e-07
                        }
                    },
                    "Q0102": {
                        "default_type": "e2f",
                        "params": {
                            "duration": 4e-06,
                            "amp": 0.08,
                            "frequency": 6882300000.0,
                            "phase": [
                                [
                                    -1,
                                    1
                                ],
                                [
                                    -1,
                                    1
                                ]
                            ],
                            "weight": "const(1)",
                            "phi": 2.3922746535598924,
                            "threshold": -2901740990.844984,
                            "ring_up_amp": 0.08,
                            "ring_up_waist": 0.08,
                            "ring_up_time": 5e-07
                        },
                        "e2f": {
                            "duration": 4e-06,
                            "amp": 0.06,
                            "frequency": 6882300000.0,
                            "phase": [
                                [
                                    -1,
                                    1
                                ],
                                [
                                    -1,
                                    1
                                ]
                            ],
                            "weight": "const(1)",
                            "phi": 1.981768672445414,
                            "threshold": -886772018.1241105,
                            "ring_up_amp": 0.06,
                            "ring_up_waist": 0.06,
                            "ring_up_time": 5e-07
                        }
                    }
                },
                "CR": {
                    "Q0101_Q0102": {
                        "default_type": "echo",
                        "params": {
                            "duration": 2e-07,
                            "frequency": 4652305857.788959,
                            "edge_type": "cos",
                            "edge": 3e-08,
                            "amp1": 1,
                            "amp2": 0,
                            "drag": 0,
                            "skew": 0,
                            "global_phase": 0,
                            "relative_phase": 0,
                            "phi1": 0,
                            "phi2": 0,
                            "buffer": 1e-08
                        },
                        "echo": {
                            "duration": 2e-07,
                            "frequency": 4652396850.007304,
                            "edge_type": "cos",
                            "edge": 3e-08,
                            "amp1": 1,
                            "amp2": 0,
                            "drag": 0,
                            "skew": 0,
                            "global_phase": 2.2809076064433413,
                            "relative_phase": 0,
                            "phi1": 0,
                            "phi2": 0,
                            "buffer": 1e-08,
                            "echo": true,
                            "theta2": 1.5707963267948966
                        },
                        "direct": {
                            "duration": 2e-07,
                            "frequency": 4652305857.788959,
                            "edge_type": "cos",
                            "edge": 3e-08,
                            "amp1": 1,
                            "amp2": 0,
                            "drag": 0,
                            "skew": 0,
                            "global_phase": 0,
                            "relative_phase": 0,
                            "phi1": 0,
                            "phi2": 0,
                            "buffer": 1e-08,
                            "echo": false,
                            "theta2": 0
                        }
                    }
                },
                "dev": {
                    "index": [
                        -9,
                        -9
                    ],
                    "color": "green",
                    "DA": {
                        "addr": "192.168.103.2",
                        "name": "VirtualDevice",
                        "type": "driver",
                        "srate": 1000000000.0,
                        "port": 40007
                    },
                    "AD": {
                        "addr": "192.168.103.3",
                        "name": "VirtualDevice",
                        "type": "driver",
                        "srate": 1000000000.0,
                        "port": 40007
                    }
                }
            }
        }
        ```

- Run `quark server` in a terminal and you'll see the following information if everything is OK![alt text](image/server.png){.center}

- Once the `QuarkServer` is ready, run `quark studio` in another termnal. Click `Signup` and fill the username(`baqis` is recommended) and system name(the cfg file name `checkpoint_demo`) in the corresponding blanks and click `sign up`.![alt text](image/signup.png){.center}
    :material-information: equaivalent operations in Python code
    ```python
    from quark.app import signup
    signup('baqis', 'checkpoint_demo') # (username, cfg file name)
    ```

- Fill the username and password in the Login window。![alt text](image/login.png){.center}
- Fill in the following content into the configuration file for kernel and place it in `systemq/etc/bootstrap.json`
```python
{
    "executor": {
        "type": "quark",
        "host": "127.0.0.1", # host computer's IP address
        "port": 2088
    },
    "data": { # settings of data storage 
        "path": "",
        "url": ""
    },
    "repo": { # systemq location
        "systemq": "C:\\systemq\\"
    }
}
```
    :warning: ***kernel login to the server with `baqis` as the default username(see `kernel.sched.executor.QuarkClient.connect`)***

### :material-frequently-asked-questions: ***FAQ***
<!-- !!! question "cfg表常见问题" -->
#### :material-cloud-question: cfg structure？

:material-message-reply: server accept `json`(see ***checkpoint demo*** above) as input and there is no restriction on the file content. Traditionally, the cfg file includes user-defined fields(qubits, couplers, gates and so on) and system-defined fields(**etc**, **dev**)

#### :material-cloud-question: what is dev？

:material-message-reply: **dev** stores device information
```python
{
    "dev": {
        'awg':{ # alias of the device
            "addr": "192.168.3.48", # IP address of the device
            "name": "VirtualDevice", # filename of the driver
            "srate": 1000000000.0, # sampling rate(defined by the srate attribute in the driver class)
            "type": "driver", # connection type, driver or remote
            "host": "useless", # IP address of the host computer(required only if the type is remote)
            "port": "useless" # service port(required only if the type is remote)
        }
}
```

#### :material-cloud-question: what is etc？

:material-message-reply: **etc** mainly includes some global settings, such as the MAPPING
```python
{
    "etc": {
        "driver": {
            "path": "dev", # driver path relative to systemq
            "concurrent": True, # open device concurrently if True
            "timeout": 30.0, # device execution timeout
            "filter": ["send Waveform or np.array to device in the list"],
            "mapping": { # mapping between logical channel and hardware channel
                "setting_LO": "LO.Frequency", # see driver for more details about device attributes
                "setting_POW": "LO.Power",
                "setting_OFFSET": "ZBIAS.Offset",
                "waveform_RF_I": "I.Waveform",
                "waveform_RF_Q": "Q.Waveform",
                "waveform_TRIG": "TRIG.Marker1",
                "waveform_DDS": "DDS.Waveform",
                "waveform_SW": "SW.Marker1",
                "waveform_Z": "Z.Waveform",
                "setting_PNT": "ADC.PointNumber",
                "setting_SHOT": "ADC.Shot",
                "setting_TRIGD": "ADC.TriggerDelay"
            },
            "root": "~/Desktop/systemq" # systemq location
        },
        "server": {
            "workers": 1, # number of compilation processes
            "shared": 0,
            "delay": 10.0, # maximum delay(in the unit of second) for feed
            "cached": 5, # number of cached task
            "review": [0, 1, 10], # index of cached step
            "schedule": {
                "job": {
                    "hour": "2"
                }
            },
            "filesize": 4000.0 # maximum size of an hdf5 file
        },
        "canvas": {
            "range": [0, 0.0001], # time range in QuarkCanvas
            "filter": [] # targets to be displayed in QuarkCanvas
        }
    }
}
```