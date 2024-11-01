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
            &ccompile   ↑    &calculate -->  &read|write -->     &process -->   &postprocess --->
            ↓           ↑
            &assemble -->
    ```
"""


import dill

from quark.proxy import dumpv, loadv

from .assembler import MAPPING, assemble, ccompile, decode, initialize
from .calculator import calculate
from .device import read, write
from .processor import process
from .router import postprocess, schedule

loads = dill.loads
dumps = dill.dumps


class Future(object):
    def __init__(self, index: int = -1) -> None:
        self.index = index

    def result(self, timeout: float = 3.0):
        return self.quark.result(self.index, timeout=timeout)
