# Copyright (c) 2024 XX Xiao

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files(the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and / or sell
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

r"""
The quark.circuit module provides tools for constructing, visualizing, and transpiling quantum circuits.
"""

from .circuit_wapper import QuantumCircuitWrapper
from .circuit import (
    QuantumCircuit,
    generate_ghz_state,
    generate_random_circuit,
    one_qubit_gates_avaliable,
    two_qubit_gates_avaliable,
    one_qubit_parameter_gates_avaliable,
    functional_gates_avaliable,
    )
from .utils import (zyz_decompose,
                    u3_decompose,
                    kak_decompose,
                    generate_random_unitary_matrix,
                    glob_phase,
                    remove_glob_phase,
                    is_equiv_unitary,
                    )
from .matrix import *
from .transpiler import Transpiler
from .dag import dag2qc,qc2dag,draw_dag
from .backend import Backend
from .layout_helpers import Layout
from .test_transpiler import call_quarkcircuit_transpiler