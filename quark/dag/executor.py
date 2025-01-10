# MIT License

# Copyright (c) 2025 YL Feng

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


import time


def execute(method: str = 'ramsey', target: list[str] | tuple[str] = ['Q0', 'Q1']):
    time.sleep(1)
    print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}]',
          f'{method}({target}) finished')
    res = {'gate.R.Q1.params.frequency': 4.4e9,
           'gate.R.Q3.params.frequency': 4.8e9}

    return compare(res, method)


def compare(result: dict, method: str) -> dict[tuple, str]:
    return {('Q1', 'Q3', 'Q5'): method}


def update(result: dict):
    print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] updated!', result)
