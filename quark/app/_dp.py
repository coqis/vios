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


from functools import cached_property

import numpy as np
import sympy as sp
from lmfit import Model, Parameters


class SymbolicFunction(object):
    """Create a function based on the formula.

    ***Example***
    >>> T1 = SymbolicFunction('T1', 'A*exp(-t/T1)+B', ['t'])
    >>> params = {'A': 2, 'B': 3, 'T1': 5}
    >>> T1(t = np.array([1, 2, 3]), **params)
    """

    def __init__(self, name: str, expr: str, independent_vars: list[str]):
        self.name = name
        self.__expr = sp.parse_expr(expr, evaluate=True)
        self.__vars = independent_vars

        self.lambdify()
        self.__model = Model(self.__func, independent_vars=self.__vars)

    def __repr__(self):
        return f'{self.name}{tuple(self.args)}'

    def show(self):
        print(self)
        try:
            from IPython.display import display
            display(self.expr)
        except Exception as e:
            print(e)

    @property
    def expr(self):
        return self.__expr

    @property
    def func(self):
        return self.__func

    @cached_property
    def args(self) -> list[sp.Symbol]:
        args = []
        for s in self.expr.atoms(sp.Symbol):
            if s.name in self.__vars:
                args.insert(0, s)
            else:
                args.append(s)
        # return sorted(args, key=lambda arg: arg.name, reverse=True)
        return sorted(args, key=lambda arg: str(self.expr).index(arg.name))

    def fit(self, data: np.ndarray, **kwds):
        assert len(data.shape) == 1, 'the input data must be a 1D array!'

        params = {}
        for arg in self.args:
            if arg.name in self.__model.independent_vars:
                continue
            assert arg.name in kwds, f'parameter {arg.name} is missing!'
            params[arg.name] = kwds.pop(arg.name)

        kwds['params'] = self.__model.make_params(**params)

        # from matplotlib.axes import Axes
        ax = kwds.pop('ax', None)
        # title = kwds.pop('title', '')

        result = self.__model.fit(data, **kwds)

        if ax:
            _var = self.__model.independent_vars[0]
            ax.plot(kwds[_var], data, 'bo')
            ax.plot(kwds[_var], result.best_fit, 'r.-')
            ax.legend(['raw', 'fit'])
            # ax.set_title(title)

        return result

    def __call__(self, *args, **kwds):
        if not self.func:
            self.lambdify()
        return self.func(*args, **kwds)

    def lambdify(self):
        self.__func = sp.lambdify(self.args, self.expr)


S21 = SymbolicFunction('S21',
                       'A * abs(1 - (Ql / abs(Qc) * exp(1j*phi)) / (1 + 2j * Ql * (f - fr)/fr)) + B',
                       ['f'])

T1 = SymbolicFunction('T1',
                      'A * exp(-t / T1) + B',
                      ['t'])

Rabi = SymbolicFunction('Rabi',
                        'A * exp(-t / Tr) * cos(2 * pi * Omega * t + phi) + B',
                        ['t'])

Ramsey = SymbolicFunction('Ramsey',
                          'A * exp(-t / 2 / T1 - (t / Tphi)**2) * cos(2 * pi * Delta * t + phi) + B',
                          ['t'])


RamseyWithBeat = SymbolicFunction('RamseyWithBeat',
                                  """A * exp(-t / 2 / T1 - (t / Tphi)**2) * cos(2 * pi * Delta * t + phi) * cos(2 * pi * Delta2 * t + phi2) + B""",
                                  ['t'])

RB = SymbolicFunction('RB',
                      'A * p**t + B',
                      ['t'])

Sin = SymbolicFunction('Sin',
                       'A * sin(2 * pi * f * t + phi) + B',
                       ['t'])

Gauss = SymbolicFunction('Gauss',
                         'A * exp(-((t - mu) / sigma)**2 / 2)',
                         ['t'])

Lorentzian = SymbolicFunction('Lorentzian',
                              '(A*Gamma/2) / ((Gamma/2)**2 + (omega - omega0)**2)',
                              ['omega'])

if __name__ == '__main__':
    s21d = np.array([0])
    f = np.array([1])
    params = dict(fr=6.965e9,
                  Ql=dict(value=1e4, min=1e3, max=1e5),
                  Qc=1e3,
                  phi=0.1,
                  A=1,
                  B=0)
    params['f'] = f
    result = S21.fit(np.abs(s21d), **params)
