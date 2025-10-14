# MIT License

# Copyright (c) 2021 YL Feng

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


"""
Abstract: about envelope
    Each step of a task will be executed in a **pipeline** through the following stages

    ``` {.py3 linenums="1" title=" stages of the pipeline"}
    --->@assembler      @calculator       @device          @processor       @router
            ↓           ↑    ↓            ↑  ↓             ↑     ↓          ↑   ↓ 
            &schedule   ↑    &calculate -->  &read|write -->     &process -->   &postprocess --->
            ↓           ↑
            &assemble -->
    ```
"""


import dill

from quark.proxy import dumpv, loadv

from .assembler import MAPPING, assemble, decode, initialize, schedule
from .calculator import calculate
from .device import read, write
from .processor import process
from .router import postprocess, transfer

loads = dill.loads
dumps = dill.dumps


class Future(object):
    def __init__(self, index: int = -1) -> None:
        self.index = index

    def result(self, timeout: float = 3.0):
        return self.quark.result(self.index, timeout=timeout)


mdev = '''
```python
┌────────────────────────────────────────────────┬────────────────────────────────────────────────┐
│               dev in QuarkServer               │               dev in QuarkRemote               │
├────────────────────────────────────────────────┼───driver folder on device──────────────────────┤
│{'awg':{                                        │ driver                                         │
│        "addr": "192.168.3.48",                 │ ├── dev                         <─────┐        │
│        "name": "VirtualDevice", <─────────────>│ │   ├── VirtualDevice.py        <─────┼──┐     │
│        "srate": 1000000000.0,                  │ │   └── __init__.py                   │  │     │
│        "type": "driver"                        │ ├── remote.json                       │  │     │
│        }                                       │ ├── requirements.txt                  │  │     │
│}                                               │ └── setup.py                          │  │     │
│                                                │                                       │  │     │
├────────────────────────────────────────────────┼───contents of remote.json─────────────┼──┼─────┤
│{'awg':{ <───────────────────────────┐          │{"path": "dev",                  <─────┘  │     │
│        "host": "192.168.1.42",  <───┼─────────>│ "host": "192.168.1.42",                  │     │
│        "port": 40052,           <─┐ └─────────>│ "awg":{                                  │     │
│        "srate": 1000000000.0,     │            │        "addr": "192.168.3.48",           │     │
│        "type": "remote"           │            │        "name": "VirtualDevice", <────────┘     │
│        }                          └───────────>│        "port": 40052                           │
│}                                               │        }                                       │
│                                                │ "adc":{"addr": "", "name": "", "port": 40053}  │
│                                                │ }                                              │
└────────────────────────────────────────────────┴────────────────────────────────────────────────┘
```
- > ***For more details see [Quark](https://quarkstudio.readthedocs.io/en/latest/usage/quark/)!!!***
- > ***If you don't know the current version of Python, read the above!!!***
- > ***If you don't know how to set up the instrument, read the above!!!***
'''


mdev = '''┌─────────────────────────────────┬─────────────────────────────────┐
│           local device          │          remote device          │
├─────────────────────────────────┼─────────────────────────────────┤
│{                                │{                                │
│  'awg':{                        │  'awg':{                        │
│    "addr": "192.168.3.48",      │    "host": "192.168.1.42",      │
│    "name": "dev.VirtualDevice", │    "port": 40052,               │
│    "type": "driver"             │    "type": "remote"             │
│  }                              │  }                              │
│}                                │}                                │
└─────────────────────────────────┴─────────────────────────────────┘'''


def is_main_process():
    import multiprocessing as mp

    return mp.current_process().name == 'MainProcess'


try:
    import os

    if is_main_process() and 'DRIVER' in os.environ:
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax

        console = Console()

        def print_code_with_title(code: str, title: str, language: str = "python"):
            syntax = Syntax(code, language, theme="dracula",
                            line_numbers=False, background_color=None)
            console.print(Panel(syntax, title=title,  # style="bold",
                          border_style="cyan", expand=False, padding=(0, 1)))

        print_code_with_title(mdev, "Device in QuarkServer")
except Exception as e:
    pass
