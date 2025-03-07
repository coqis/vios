### **配置表**
- 配置表是一个[json文件](checkpoint.json)，习惯上称之为`cfg`表，后续如无特指，均以`cfg`代称
- cfg中包含比特所有门参数信息、硬件连接信息及其他程序运行所需配置信息

- cfg中的**Q**字段，存储Qubit相关的设置，如硬件连接、失真参数等

    ???- Example "***Qubit***" 
        ```python
        {
            "probe": "M1",
            "couplers": ["C0"],
            "waveform": {
                "SR": 6000000000.0,
                "LEN": 8e-05,
                "DDS_LO": 6000000000.0,
                "RF": "zero()",
                "DDS": "zero()"
            },
            "channel": {
                "DDS": "ZW_AWG_13.CH2"
            },
            "calibration": {
                "DDS": {
                    "delay": 3.05e-08
                }
            },
            "params": {
                "T1": 7.544957236854869e-05,
                "T2_star": 1.9762589666408893e-05,
                "T2_echo": 3.951455640774801e-05,
                "chi": 0.525,
                "Ec": null,
                "T2star": 21.77932423416822
            },
            "setting": {}
        }
        ```

- cfg中的**C**字段，存储Coupler相关的设置，如硬件连接、失真参数等

    ???- Example "***Coupler***"
        ```python
        {
            "qubits": ["Q1", "Q2"],
            "setting": {
                "OFFSET": -0.0488
            },
            "waveform": {
                "SR": 2000000000.0,
                "LEN": 8e-05,
                "Z": "zero()"
            },
            "channel": {
                "Z": "AWG_16_116_51.CH8",
                "ZBIAS": "AWG_16_116_51.CH8"
            },
            "calibration": {
                "Z": {
                    "delay": 8.5e-08,
                    "distortion": {
                        "decay": [
                            [
                                0.005705237154544386,
                                2.859411109981787e-05
                            ],
                            [
                                0.01952275840125321,
                                1.701118665477762e-06
                            ],
                            [
                                0.04884840923438657,
                                1.9703647790561616e-07
                            ]
                        ]
                    }
                }
            },
            "bias": {
                "amps": [
                    0.005705237154544386,
                    0.01952275840125321,
                    0.04884840923438657
                ],
                "taus": [
                    2.859411109981787e-05,
                    1.701118665477762e-06,
                    1.9703647790561616e-07
                ],
                "sym": -0.0488,
                "Q2_min": 0.42,
                "Q1_min": 0.592
            }
        }
        ```


- cfg中的**M**字段，存储Measure相关的设置，如硬件连接、通道参数等

    ???- Example "***Measure***"
        ```python
        {
            "qubits": ["Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12"],
            "adcsr": 2500000000.0,
            "setting": {
                "TRIGD": 5.222e-06,
                "LO": 0
            },
            "waveform": {
                "SR": 8000000000.0,
                "LEN": 0.0002,
                "DDS_LO": 8000000000.0,
                "RF": "zero()",
                "TRIG": "zero()",
                "DDS": "zero()"
            },
            "channel": {
                "DDS": "ZW_AD3.CH1",
                "ADC": "ZW_AD3.CH13",
                "TRIG": null,
                "LO": null
            },
            "calibration": {
                "DDS": {
                    "delay": 5e-06
                }
            }
        }
        ```

- cfg中的**gate**字段，存储所有门相关的参数

    ???- Example "***Gate***"
        ```python
        "Measure": {
                "Q0": {
                    "params": {
                        "duration": 4e-06,
                        "amp": 0.012,
                        "frequency": 6965447457.23823,
                        "weight": "const(1)",
                        "phi": -2.1814890350845695,
                        "threshold": 4621349023.817672,
                        "ring_up_amp": 0.024,
                        "ring_up_waist": 0.006,
                        "ring_up_time": 6e-07,
                        "default_type": "default"
                    },
                    "e2f": {
                        "duration": 4e-06,
                        "amp": 0.019,
                        "frequency": 6964950000.0,
                        "weight": "const(1)",
                        "phi": 2.7678138242169874,
                        "threshold": 5453564391.573079,
                        "ring_up_amp": 0.038,
                        "ring_up_waist": 0.0095,
                        "ring_up_time": 6e-07
                    },
                    "default_type": "default",
                    "jpa": {
                        "duration": 4.096e-06,
                        "amp": 0.0066,
                        "frequency": 6965450000.0,
                        "weight": "const(1)",
                        "phi": 2.627060110045811,
                        "threshold": 13563399529.92167,
                        "ring_up_amp": 0.0132,
                        "ring_up_waist": 0.0033,
                        "ring_up_time": 2.56e-07,
                        "jpa_q": "Q65536"
                    },
                    "e2f_jpa": {
                        "duration": 4.096e-06,
                        "amp": 0.007399999999999998,
                        "frequency": 6965050000.0,
                        "weight": "const(1)",
                        "phi": 2.7197048084828355,
                        "threshold": 9821219703.416685,
                        "ring_up_amp": 0.014799999999999995,
                        "ring_up_waist": 0.003699999999999999,
                        "ring_up_time": 2.56e-07,
                        "jpa_q": "Q65536"
                    }
                }
            }
        ```



