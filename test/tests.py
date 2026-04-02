import json

import numpy as np
import pytest

from quark.app import s

with open('test/tests.json', 'r') as f:
    cfg = json.load(f)


@pytest.fixture
def ss():
    """login后才能使用"""
    s.login(verbose=False)

    # if not s.user_exists():
    #     raise pytest.fail("登录失败")
    yield s
    # print('logout')


def test_login(ss):
    """测试登录"""
    assert s.user_exists()


def test_getid():
    """测试获取ID"""
    assert isinstance(s.getid(), int)


def test_snapshot():
    """测试快照"""
    assert isinstance(s.snapshot(), dict)


def test_crud():
    """测试CRUD"""
    assert isinstance(t := s.query('abc'), str) and t.startswith('Failed')
    s.update('abc', {})
    assert isinstance(s.query('abc'), dict)
    s.delete('abc')


def test_translate():
    """测试翻译"""
    import time
    time.sleep(1)
    ctx, (cmds, dmap) = s.translate([(('Measure', '0'), 'Q0')])
    assert isinstance(cmds, dict)
    assert isinstance(dmap, dict)

    wf = s.preview(cmds, keys=['Q0'], end=10e-6, offset=1)
    # s.display(wf)
    assert isinstance(wf, dict)


def test_submit():
    """测试提交"""

    qubits = ['Q0']

    rcp = s.recipe('s21', signal='iq_avg')
    rcp.lib = r'glib.gates.u3rcp'  # 指定体系结构
    rcp.arch = 'rcp'  # 指定体系结构
    rcp.circuit = [
        # *[('X', q) for q in qubits] * 10,
        *[(('Measures', i), q) for i, q in enumerate(qubits)],
    ]  # 指定扫描线路函数

    rcp['qubits'] = tuple(qubits)  # 必须为tuple
    rcp['freq'] = np.linspace(-3, 3, 3) * 1e6  # 扫描范围

    for q in qubits:
        rcp[f'{q}.Measure.frequency'] = rcp['freq'] + \
            s.query(f'{q}.Measure.frequency')  # 在中心频率正负10M范围内扫描

    s21n = s.submit(rcp.export() | {'base': cfg},
                    block=True, preview=[], plot=False)
    s21n.bar(interval=0.1)

    rp = s21n.report(show=False)
    assert isinstance(rp, dict)
    assert rp['cirq'].startswith('Failed to run task')

    assert s.diff(s21n.ctx.export(), cfg) == {}

    assert s21n.circuit() == [(('Measures', 0), 'Q0')]
    assert s21n.step(0) == "KeyError: 'ini'"
    assert s21n.status()['status'] == 'Failed'
