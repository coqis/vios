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


from typing import Any

from quark.driver.common import BaseDriver


def fibonacci(n: int = 35) -> int:
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def read(device: BaseDriver, quantity: str, channel: str = 'CH1', **kwds) -> Any:
    """read from the device

    Args:
        device (_type_): device handler
        quantity (str): hardware attribute, e.g., Waveform/Power/Offset
        channel (int, optional): channel string. Defaults to 'CH1'.

    Returns:
        Any: result from the device
    """
    # assert isinstance(channel, str) and channel.startswith('CH'), \
    #     f'channel should be a string starting with "CH", got {channel}'
    chstr = channel[2:]
    ch = int(chstr) if chstr.isdigit() else chstr
    return device.getValue(quantity, ch=ch, **kwds)


def write(device: BaseDriver, quantity: str, value: Any, channel: str = 'CH1', **kwds):
    """write to the device

    Args:
        device (_type_): device handler
        quantity (str): hardware attribute, e.g., Waveform/Power/Offset
        value (Any): value to be written
        channel (int, optional): channel string. Defaults to 'CH1'.
    """
    # assert isinstance(channel, str) and channel.startswith('CH'), \
    #     f'channel should be a string starting with "CH", got {channel}'
    chstr = channel[2:]
    ch = int(chstr) if chstr.isdigit() else chstr
    return device.setValue(quantity, value, ch=ch, **kwds)
