---
hide:
  - navigation
  # - toc
---

<!-- ![SystemQ](image/aniatom.gif){ .center } -->

# Quafu Quantum Computing Cloud(Superconducting)


## 1. Introduction
Welcome to the Quafu quantum cloud computing cluster([https://quafu.baqis.ac.cn/](https://quafu.baqis.ac.cn/)). Quafu is a stable, open-access quantum computing platform that aims to help users develop novel quantum algorithms and applications, thus promoting the practical development of quantum computing technologies. The platform is developed and maintained by teams from the Beijing Academy of Quantum Information Sciences (BAQIS), the Institute of Physics of the Chinese Academy of Sciences (IOPCAS) and Tsinghua University.


## 2. Available Resources

<iframe
    width=100% 
    src="https://quafu-sqc.baqis.ac.cn"  
    frameborder=0  
    allowfullscreen>
</iframe>

In addition to using Quafu website, advanced users can fully experience the quantum computing platform more freely with `QuarkStudio`(see [Installation](#3-installation)).


## 3. Installation
`QuarkStudio` supports all major operating systems, including Windows, MacOS and Linux. To install, a Python(>=3.10) is required and then install latest `QuarkStudio` by pip (in a terminal):

```bash
pip install quarkstudio # python>=3.10
```

Once `QuarkStudio` is installed, you are ready to submit your quantum circuits **directly** to the backends listed above.


## 4. Quick Guide
To begin with, you need to initialize a task manager

```python
from quark import Task
tmgr = Task('token')
```
!!! warning "quarkstudio"
    A token is required here, which can be applied by click [**SQCLab**](https://quafu-sqc.baqis.ac.cn/) above or sending an email to quafu_ts@baqis.ac.cn. The token is a verification key that guarantees your rights to fully use the platform, so **don't share it with others**. Each token has a expiration time of **30 days**. When it expires, you need to apply a new token from [**SQCLab**](https://quafu-sqc.baqis.ac.cn/). 


    Each user can submit 1000 tasks per day since the backend quantum computing systems have a limited processing capacity, which is designed to ensure fair access and optimal performance for all users. The daily limit for users may be adjusted according to the overall load. Your submitted tasks that exceed the daily limit will be queued and processed on the following days. 

    If you have heavy computation resource requirement, please contact us at quafu_ts@baqis.ac.cn for additional collaboration opportunities.


The `tmgr` object has three main methods, namely `tmgr.status()`、`tmgr.run(task)` and `tmgr.result(tid)`, which help the users to interact with the backends listed above. Let us make a brief view about the usage of these methods.


Before submit you task, you may want to check the running status of all the backends, so as to decide which one suits for your current task,

```python
print(tmgr.status())
```

The output may looks like

```python
{'Dongling': 0, # no task in queue
 'Miaofeng': 0,
 'Baihua': 0,
 'Baiwang': 0,
 'Yunmeng': 'Offline', # not available
 'Haituo': 1224, # 1224 tasks in queue
 }
```
 
The number following the backend's name shows the tasks in queue. If it shows 'Offline', it tells us that this backend is not available righ now. If it shows 'Maintenance', it tells us that this backend is under maintenance now.

Now, With the information from `tmgr.status()`, you can choose a backend without too many tasks in queue, or estimate a waiting time if you want to run one a specific backend.

Assume that you've already written a quantum circuit using OpenQASM2.0

```python
circuit = """
    OPENQASM 2.0;
    include "qelib1.inc";  
    qreg q[5];
    creg meas[5];
    h q[2];
    cx q[2],q[3];
    cx q[3],q[4];
    cx q[4],q[5];
    measure q[2] -> meas[0];
    measure q[3] -> meas[1];
    measure q[4] -> meas[2];
    measure q[5] -> meas[3];
    """
```

> We highly recommend users to use qlisp to write the circuits, see [qlisp](https://quarkstudio.readthedocs.io/en/latest/usage/qlisp) for more information.

Then, you can put this circuit in a Python dict to define a task as shown below. The backend can be set by the key `chip`. Besides, you can name this task `MyJob` or whatever you want. You can also choose whether to transpile your circuit or not by the `compile` key. If you want to get the bayesian-corrected evaluations of all bases, you can set the `correct` key to `True`(Bayesian correction is not performed by default, so this option has no effect for now).

```python
task = {
  'chip': 'Dongling',  # chip name
  'name': 'MyJob',  # task name
  'circuit':circuit, # circuit written in OpenQASM2.0
  'compile': True, # transpile to native gate sets if True
  'correct': False # Bayesian correction for the readout
}
```

Now you can run the task with the following script

```python
tid = tmgr.run(task, repeat=1) # shots = repeat*1024
print(tid) # tid means task id
# output: 2024041917095371986
```

> Note: tasks are submitted and executed asynchronously by default, meaning that you don't need to wait until the task is done. As long as the task id is kept properly, you can retrieve the data whenever you want. 

Once the task is submitted, a unique task id will be returned imediately, with which the data can be retrieved strightforward,
```python
res = tmgr.result(2024041917095371986)
```

The returned `res` is a Python dict which looks like

```python
{
'count': {'0000': 399,
          '0001': 19,
          '0010': 18,
          '0011': 29,
          '0100': 4,
          '0101': 1,
          '0110': 3,
          '0111': 34,
          '1000': 38,
          '1001': 4,
          '1010': 4,
          '1011': 16,
          '1100': 38,
          '1101': 11,
          '1110': 45,
          '1111': 361},
'corrected': {},
'transpiled':'''OPENQASM 2.0;
                include "qelib1.inc";
                qreg q[130];
                creg c[4];
                h q[2];
                cx q[2],q[3];
                cx q[3],q[4];
                cx q[4],q[5];
                barrier q[2],q[3],q[4],q[5];
                measure q[2] -> c[0];
                measure q[3] -> c[1];
                measure q[4] -> c[2];
                measure q[5] -> c[3];'''
'status': 'Finished',

'tid': 2024041917095371986,
'error': '', 
'finished': '2024-04-19-17-09-48',
'qlisp': '''[('H', 'Q2'),
            ('Cnot', ('Q2', 'Q3')),
            ('Cnot', ('Q3', 'Q4')),
            ('Cnot', ('Q4', 'Q5')),
            ('Barrier', ('Q2', 'Q3', 'Q4', 'Q5')),
            (('Measure', 0), 'Q2'),
            (('Measure', 1), 'Q3'),
            (('Measure', 2), 'Q4'),
            (('Measure', 3), 'Q5')]''',
}

```

It contains four main parts: the measured sampling counts of all bases; the byesian-corrected evaluations of all bases; the transpiled circuit that physically runs on the specific chip; the status of the task. In addition, we also provide a qlisp circuit description for users to debug when the returned result is not as expected.

You may want to process or visualize the result. Here is a demo script to visualize the results,

```python
import matplotlib.pyplot as plt
data = res['count']
bases = sorted(data)
count = [data[base] for base in bases]

plt.bar(bases, count)
plt.xticks(rotation=45)
```

![count](usage/2024041917095371986.jpg)

By default, the Bayesian corrected result is not returned. Since the inevitable readout & initialization errors of the physical qubits, the resulted data may not reflect your circuit evolution. To show how the errors can be corrected, the readout correction matrix $M$ was measured in advance and then multiplied by the raw `data`, giving us the corrected result as shown in the figure below,

![corrected](usage/2024041917095371986_corrected.jpg)

<!-- >For more information about the topic, see [Bayesian Correction](https://www.yuque.com/wuming-6g8w2/ghzgfk/um1z1x474lgihb2w?singleDoc# ) -->



## 5. Technical Support

If you encounter any problems, please feel free to contact us and we will provide immediate feedback.
Contact email: quafu_ts@baqis.ac.cn

