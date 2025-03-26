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

r"""This module contains the Transpiler class, which is designed to convert quantum circuits 
into formats that are more suitable for execution on hardware backends"""

from quark.circuit.quantumcircuit import QuantumCircuit
from quark.circuit.backend import Backend
from quark.circuit.decompose import ThreeQubitGateDecompose
from quark.circuit.layout import Layout
from quark.circuit.routing import SabreRouting
from quark.circuit.translate import TranslateToBasisGates
from quark.circuit.optimize import GateCompressor

class Transpiler:
    r"""The transpilation process involves converting the operations
    in the circuit to those supported by the device and swapping
    qubits (via swap gates) within the circuit to overcome limited
    qubit connectivity.
    """
    def __init__(self, chip_backend: Backend):
        
        r"""Obtain basic information from input quantum circuit.

        Args:
            qc (QuantumCircuit | str | list): The quantum circuit to be transpiled. Can be a QuantumCircuit object or OpenQASM 2.0 str or qlisp list.

            chip_backend (Backend): An instance of the Backend class that contains the information about the quantum chip to be used for layout selection. Defaults to None

        Raises:
            TypeError: The quantum circuit format is incorrect.
        """
        self.chip_backend = chip_backend

    def run(self, qc:QuantumCircuit | str | list,target_qubits:list=[],optimize_level=1):

        if isinstance(qc,QuantumCircuit):
            pass
        elif isinstance(qc, str):
            qc = QuantumCircuit().from_openqasm2(qc)
        elif isinstance(qc, list):
            qc = QuantumCircuit().from_qlisp(qc)
        else:
            raise TypeError("Expected a Quark QuantumCircuit or OpenQASM 2.0 or qlisp, but got a {}.".format(type(qc)))
        
        subgraph = Layout(len(qc.qubits),self.chip_backend).select_layout(target_qubits=target_qubits,
                                                                        use_chip_priority=True,
                                                                        select_criteria={ 'key': 'fidelity_var','topology': 'linear1' })
        if optimize_level == 0:
            passes = [ThreeQubitGateDecompose(),
                      SabreRouting(subgraph,initial_mapping='trivial',do_random_choice=False,iterations=1),
                      TranslateToBasisGates(convert_single_qubit_gate_to_u=True,two_qubit_gate_basis='cz'),
                      ]
        elif optimize_level == 1:
            passes = [ThreeQubitGateDecompose(),
                      SabreRouting(subgraph,initial_mapping='trivial',do_random_choice=False,iterations=5),
                      TranslateToBasisGates(convert_single_qubit_gate_to_u=True,two_qubit_gate_basis='cz'),
                      GateCompressor()]
        else:
            raise(ValueError(f'Currently, only optimize_level values of 0 or 1 are supported.'))
        for pass_obj in passes:
            qc = pass_obj.run(qc)
        return qc