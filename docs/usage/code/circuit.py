"""线路生成模块，也仅用于存放线路函数！
"""

import numpy as np


def circuit(qubits: tuple[str], freq: float, amps: float, b, c=3, ctx=None):
    """线路模板.

    Args:
        qubits (tuple[str]): 待测比特.
        freq (float): 频率.
        amps (float): 幅值.
        b (_type_): 其他参数.
        c (int, optional): 其他可选参数. Defaults to 3.
        ctx (_type_, optional): 编译所用上下文，用于cfg表的查询，任务提交后由server传入. Defaults to None.

    Returns:
        _type_: 根据传入参数生成的qlisp线路
    """
    print(qubits, freq, amps, b, c)
    print(ctx.query('gate.Measure.Q0.params.frequency'))
    return [(('Measure', i), q) for i, q in enumerate(qubits)]


def S21(qubits: list[str], ctx=None) -> list:
    cc = [(('Measure', i, ), q) for i, q in enumerate(qubits)]
    return cc


def Spectrum(qubits: tuple[str], act_qubits: list[str] = None, ctx=None) -> list:
    act_qubits = qubits if act_qubits is None else act_qubits

    cc = [*[(('R', 0), q) for q in act_qubits],
          ('Barrier', tuple(qubits)),
          *[(('Measure', j), q) for j, q in enumerate(qubits)],
          ]
    return cc


def TimeRabi(qubits: tuple[str], act_qubits: tuple[str] = None, ctx=None):
    act_qubits = qubits if act_qubits is None else act_qubits

    cc = [*[(('R', 0), q) for q in act_qubits] * 2,
          ('Barrier', tuple(qubits)),
          *[(('Measure', j), q) for j, q in enumerate(qubits)],
          ]
    return cc


def Scatter(qubits: list[str], state: str = '0', ctx=None) -> list:
    state2gate = {'0': ['I'],
                  '1': [('R', 0), ('R', 0)]}

    cc = [*[(gate, q) for q in qubits for gate in state2gate[state]],
          ('Barrier', tuple(qubits)),
          *[(('Measure', j), q) for j, q in enumerate(qubits)]]
    return cc


def T1(qubits: list[str], delay: float, act_qubits: list[str] = None, ctx=None) -> list:
    act_qubits = qubits

    cc = [*[(('R', 0), q) for q in act_qubits] * 2,
          *[(('Delay', delay), q) for q in act_qubits],
          ('Barrier', tuple(qubits)),
          *[(('Measure', j), q) for j, q in enumerate(qubits)],
          ]
    return cc


def Ramsey(qubits: list[str], delay: float, rotate: float,
           act_qubits=None, ctx=None) -> list:
    act_qubits = qubits
    cc = [*[(('R', 0), q) for q in act_qubits],
          *[(('Delay', delay), q) for q in act_qubits],
          *[(('R', 2 * np.pi * rotate * delay), q) for q in act_qubits],
          ('Barrier', tuple(qubits)),
          *[(('Measure', j), q) for j, q in enumerate(qubits)],
          ]
    return cc


def SpinEcho(qubits: list[str], delay: float, rotate: float,
             act_qubits: list[str] = None, ctx=None) -> list:
    act_qubits = qubits
    cc = [*[(('R', 0), q) for q in act_qubits],
          *[(('Delay', delay / 2), q) for q in act_qubits],
          *[(('R', np.pi * rotate * delay), q) for q in act_qubits],
          *[(('R', np.pi * rotate * delay), q) for q in act_qubits],
          *[(('Delay', delay / 2), q) for q in act_qubits],
          *[(('R', 0), q) for q in act_qubits],
          ('Barrier', tuple(qubits)),
          *[(('Measure', j), q) for j, q in enumerate(qubits)],
          ]
    return cc
