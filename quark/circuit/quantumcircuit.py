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
This module contains the QuantumCircuit class, which offers an intuitive interface for designing, visualizing, 
and converting quantum circuits in various formats such as OpenQASM 2.0 and qlisp.
"""

import copy
from typing import Iterable
from IPython.display import display, HTML
import numpy as np
from .quantumcircuit_helpers import (
    one_qubit_gates_available,
    two_qubit_gates_available,
    one_qubit_parameter_gates_available,
    two_qubit_parameter_gates_available,
    three_qubit_gates_available,
    functional_gates_available,
    convert_gate_info_to_dag_info,
    parse_openqasm2_to_gates,
    parse_qlisp_to_gates,
    add_gates_to_lines,
    )
from .utils import u3_decompose, zyz_decompose, kak_decompose
from .matrix import h_mat

def generate_ghz_state(nqubits: int) -> 'QuantumCircuit':
    r"""
    Produce a GHZ state on n qubits.

    Args:
        nqubits (int): The number of qubits. Must be >= 2.

    Returns:
        QuantumCircuit: A quantum circuit representing the GHZ state.
    """
    cir =  QuantumCircuit(nqubits)
    cir.h(0)
    for i in range(1,nqubits):
        cir.cx(0,i)
    return cir

class QuantumCircuit:
    r"""
    A class used to build and manipulate a quantum circuit.

    This class allows you to create quantum circuits with a specified number of quantum and classical bits. 
    The circuit can be customized using various quantum gates, and additional features (such as simulation support, 
    circuit summary, and more) will be added in future versions.
    
    Attributes:
        nqubits (int or None): Number of quantum bits in the circuit.
        ncbits (int or None): Number of classical bits in the circuit.
    """
    def __init__(self, *args):
        r"""
        Initialize a QuantumCircuit object.

        The constructor supports three different initialization modes:
        1. `QuantumCircuit()`: Creates a circuit with `nqubits` and `ncbits` both set to `None`.
        2. `QuantumCircuit(nqubits)`: Creates a circuit with the specified number of quantum bits (`nqubits`), 
        and classical bits (`ncbits`) set to the same value as `nqubits`.
        3. `QuantumCircuit(nqubits, ncbits)`: Creates a circuit with the specified number of quantum bits (`nqubits`) 
        and classical bits (`ncbits`).

        Args:
            *args: Variable length argument list used to specify the number of qubits and classical bits.

        Raises:
            ValueError: If more than two arguments are provided, or if the arguments are not in one of the specified valid forms.
        """
        if len(args) == 0:
            self.nqubits = None
            self.ncbits = self.nqubits
        elif len(args) == 1:
            self.nqubits = args[0]
            self.ncbits = self.nqubits
        elif len(args) == 2:
            self.nqubits = args[0]
            self.ncbits = args[1]
        else:
            raise ValueError("Support only QuantumCircuit(), QuantumCircuit(nqubits) or QuantumCircuit(nqubits,ncbits).")
        
        self.qubits = []
        self.gates = []
        self.params_value = {}

    def deepcopy(self):
        new_qc = QuantumCircuit(self.nqubits,self.ncbits)
        new_qc.qubits = copy.deepcopy(self.qubits)
        new_qc.params_value = copy.deepcopy(self.params_value)
        new_qc.gates = copy.deepcopy(self.gates)
        return new_qc

    def adjust_index(self,thres:int):
        gates = []
        for gate_info in self.gates:
            gate = gate_info[0]
            if gate in one_qubit_gates_available.keys():
                qubit = gate_info[-1] + thres
                gates.append((gate,qubit))
            elif gate in two_qubit_gates_available.keys():
                qubit1 = gate_info[1] + thres
                qubit2 = gate_info[2] + thres
                gates.append((gate,qubit1,qubit2))
            elif gate in one_qubit_parameter_gates_available.keys():
                qubit = gate_info[-1] + thres
                gates.append((gate,*gate_info[1:-1],qubit))
            elif gate in ['reset']:
                qubit = gate_info[-1] + thres
                gates.append((gate,qubit))
            elif gate in ['barrier']:
                qubits = [idx + thres for idx in gate_info[1]]
                gates.append((gate,tuple(qubits)))
            elif gate in ['measure']:
                qubits = [idx + thres for idx in gate_info[1]]
                gates.append((gate,qubits,gate_info[-1]))
        self.gates = gates   
        self.nqubits = self.nqubits + thres
        self.qubits = [idx + thres for idx in self.qubits] 

    def _add_qubits(self,*args):
        # 去重 排序
        temp_set = set(self.qubits).union(args)
        self.qubits = sorted(temp_set)
        return self

    def from_openqasm2(self,openqasm2_str: str) -> None:
        r"""
        Initializes the QuantumCircuit object based on the given OpenQASM 2.0 string.

        Args:
            openqasm2_str (str): A string representing a quantum circuit in OpenQASM 2.0 format.
        """
        assert('OPENQASM 2.0' in openqasm2_str)
        new_gates,qubit_used,cbit_used = parse_openqasm2_to_gates(openqasm2_str)
        self.nqubits = max(qubit_used, default=0) + 1 
        self.ncbits = max(cbit_used, default=0) + 1
        self.qubits = list(qubit_used) #[i for i in range(self.nqubits)]
        self.gates = new_gates
        return self
    
    def from_qlisp(self, qlisp: list|str) -> None:
        r"""
        Initializes the QuantumCircuit object based on the given qlisp list.

        Args:
            qlisp (list): A list representing a quantum circuit in qlisp format.
        """
        if isinstance(qlisp, str):
            import ast
            qlisp = ast.literal_eval(qlisp)
        new_gates, qubit_used,cbit_used = parse_qlisp_to_gates(qlisp)
        self.nqubits = max(qubit_used, default=0) + 1 
        self.ncbits = max(cbit_used, default=0) + 1
        self.qubits = list(qubit_used) #[i for i in range(self.nqubits)]
        self.gates = new_gates
        return self

    def id(self, qubit: int) -> None:
        r"""
        Add a Identity gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('id', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")

    def x(self, qubit: int) -> None:
        r"""
        Add a X gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('x', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")

    def y(self, qubit: int) -> None:
        r"""
        Add a Y gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('y', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")

    def z(self, qubit: int) -> None:
        r"""
        Add a Z gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('z', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")

    def s(self, qubit: int) -> None:
        r"""
        Add a S gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('s', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")

    def sdg(self, qubit: int) -> None:
        r"""
        Add a S dagger gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('sdg', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")

    def sx(self, qubit: int) -> None:
        r"""
        Add a Sqrt(X) gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('sx', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")
        
    def sxdg(self, qubit: int) -> None:
        r"""
        Add a Sqrt(X) dagger gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('sxdg', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")

    def t(self, qubit: int) -> None:
        r"""
        Add a T gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('t', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")

    def tdg(self, qubit: int) -> None:
        r"""Add a T dagger gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('tdg', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")
               
    def h(self, qubit: int) -> None:
        r"""
        Add a H gate.

        Args:
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('h', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")

    def swap(self, qubit1: int, qubit2: int) -> None:
        r"""
        Add a SWAP gate.

        Args:
            qubit1 (int): The first qubit to apply the gate to.
            qubit2 (int): The second qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if max(qubit1,qubit2) < self.nqubits:
            if qubit1 != qubit2:
                self.gates.append(('swap', qubit1,qubit2))
                self._add_qubits(qubit1,qubit2)
            else:
                raise ValueError(f"Qubit index conflict: qubit1 and qubit2 are both {qubit1}")
        else:
            raise ValueError("Qubit index out of range")
        
    def iswap(self, qubit1: int, qubit2: int) -> None:
        r"""
        Add a ISWAP gate.

        Args:
            qubit1 (int): The first qubit to apply the gate to.
            qubit2 (int): The second qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if max(qubit1, qubit2) < self.nqubits:
            if qubit1 != qubit2:
                self.gates.append(('iswap', qubit1,qubit2))
                self._add_qubits(qubit1,qubit2)
            else:
                raise ValueError(f"Qubit index conflict: qubit1 and qubit2 are both {qubit1}")
        else:
            raise ValueError("Qubit index out of range")
        
    def cx(self, control_qubit: int, target_qubit: int):
        r"""
        Add a CX gate.

        Args:
            control_qubit (int): The qubit used as control.
            target_qubit (int): The qubit targeted by the gate.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if max(control_qubit,target_qubit) < self.nqubits:
            if control_qubit != target_qubit:
                self.gates.append(('cx', control_qubit,target_qubit))
                self._add_qubits(control_qubit,target_qubit)
            else:
                raise ValueError(f"Qubit index conflict: control_qubit and target_qubit are both {control_qubit}")
        else:
            raise ValueError("Qubit index out of range")
        
    def cnot(self, control_qubit: int, target_qubit: int) -> None:
        r"""
        Add a CNOT gate.

        Args:
            control_qubit (int): The qubit used as control.
            target_qubit (int): The qubit targeted by the gate.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if max(control_qubit,target_qubit) < self.nqubits:
            if control_qubit != target_qubit:
                self.cx(control_qubit, target_qubit)
                self._add_qubits(control_qubit,target_qubit)
            else:
                raise ValueError(f"Qubit index conflict: control_qubit and target_qubit are both {control_qubit}")
        else:
            raise ValueError("Qubit index out of range")
                
    def cy(self, control_qubit: int, target_qubit: int) -> None:
        r"""
        Add a CY gate.

        Args:
            control_qubit (int): The qubit used as control.
            target_qubit (int): The qubit targeted by the gate.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if max(control_qubit,target_qubit) < self.nqubits:
            if control_qubit != target_qubit:
                self.gates.append(('cy', control_qubit,target_qubit))
                self._add_qubits(control_qubit,target_qubit)
            else:
                raise ValueError(f"Qubit index conflict: control_qubit and target_qubit are both {control_qubit}")
        else:
            raise ValueError("Qubit index out of range")
        
    def cz(self, control_qubit: int, target_qubit: int) -> None:
        r"""
        Add a CZ gate.

        Args:
            control_qubit (int): The qubit used as control.
            target_qubit (int): The qubit targeted by the gate.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if max(control_qubit,target_qubit) < self.nqubits:
            if control_qubit != target_qubit:
                self.gates.append(('cz', control_qubit, target_qubit))
                self._add_qubits(control_qubit,target_qubit)
            else:
                raise ValueError(f"Qubit index conflict: control_qubit and target_qubit are both {control_qubit}")
        else:
            raise ValueError("Qubit index out of range")

    def ccz(self,control_qubit1:int,control_qubit2:int,target_qubit:int):
        """Add CCZ gate.

        Args:
            control_qubit1 (int): The qubit used as the first control.
            control_qubit2 (int): The qubit used as the second control.
            target_qubit (int): The qubit targeted by the gate.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        qubits0 = [control_qubit1,control_qubit2,target_qubit]
        if max(qubits0) < self.nqubits:
            if len(set(qubits0)) == 3:
                self.gates.append(('ccz',control_qubit1,control_qubit2,target_qubit))
                self._add_qubits(*qubits0)
            else:
                raise ValueError(f"Qubit index conflict: control_qubit1 {control_qubit1} control_qubit2 {control_qubit2} target_qubit {target_qubit}")
        else:
            raise ValueError("Qubit index out of range")
        
    def ccx(self,control_qubit1:int,control_qubit2:int,target_qubit:int):
        """Add CCX gate.

        Args:
            control_qubit1 (int): The qubit used as the first control.
            control_qubit2 (int): The qubit used as the second control.
            target_qubit (int): The qubit targeted by the gate.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        qubits0 = [control_qubit1,control_qubit2,target_qubit]
        if max(qubits0) < self.nqubits:
            if len(set(qubits0)) == 3:
                self.gates.append(('ccx',control_qubit1,control_qubit2,target_qubit))
                self._add_qubits(*qubits0)
            else:
                raise ValueError(f"Qubit index conflict: control_qubit1 {control_qubit1} control_qubit2 {control_qubit2} target_qubit {target_qubit}")
        else:
            raise ValueError("Qubit index out of range")
        
    def cswap(self,control_qubit1:int,control_qubit2:int,target_qubit:int):
        """Add CSWAP gate.

        Args:
            control_qubit1 (int): The qubit used as the first control.
            control_qubit2 (int): The qubit used as the second control.
            target_qubit (int): The qubit targeted by the gate.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        qubits0 = [control_qubit1,control_qubit2,target_qubit]
        if max(qubits0) < self.nqubits:
            if len(set(qubits0)) == 3:
                self.gates.append(('cswap',control_qubit1,control_qubit2,target_qubit))
                self._add_qubits(*qubits0)
            else:
                raise ValueError(f"Qubit index conflict: control_qubit1 {control_qubit1} control_qubit2 {control_qubit2} target_qubit {target_qubit}")
        else:
            raise ValueError("Qubit index out of range")
        
    def p(self, theta: float, qubit: int) -> None:
        r"""
        Add a Phase gate.

        Args:
            theta (float): The rotation angle of the gate.
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('p', theta, qubit))
            self._add_qubits(qubit)
            if isinstance(theta,str):
                self.params_value[theta] = theta
        else:
            raise ValueError("Qubit index out of range")
        
    def r(self, theta: float, phi:float, qubit: int) -> None:
        r"""
        Add a R gate.

        $$
        R(\theta,\phi) = e^{-i\frac{\theta}{2}(\cos{\phi x}+\sin{\phi y})} = \begin{bmatrix}
         \cos(\frac{\theta}{2})             & -i e^{-i\phi}\sin(\frac{\theta}{2}) \\
         -i e^{i\phi}\sin(\frac{\theta}{2}) & \cos(\frac{\theta}{2})      
        \end{bmatrix}
        $$

        Args:
            theta (float): The rotation angle of the gate.
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('r', theta, phi, qubit))
            self._add_qubits(qubit)
            if isinstance(theta,str):
                self.params_value[theta] = theta
            if isinstance(phi,str):
                self.params_value[phi] = phi
        else:
            raise ValueError("Qubit index out of range")
        
    def u(self, theta: float, phi: float, lamda: float, qubit: int) -> None:
        r"""
        Add a U3 gate.

        The U3 gate is a single-qubit gate with the following matrix representation:

        $$
        U3(\theta, \phi, \lambda) = \begin{bmatrix}
            \cos(\theta/2) & -e^{i\lambda} \sin(\theta/2) \\
            e^{i\phi} \sin(\theta/2) & e^{i(\phi + \lambda)} \cos(\theta/2)
            \end{bmatrix}
        $$

        Args:
            theta (float): The rotation angle of the gate.
            phi (float): The rotation angle of the gate.
            lamda (float): The rotation angle of the gate.
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('u', theta, phi, lamda, qubit))
            self._add_qubits(qubit)
            if isinstance(theta,str):
                self.params_value[theta] = theta
            if isinstance(phi,str):
                self.params_value[phi] = phi
            if isinstance(lamda,str):
                self.params_value[lamda] = lamda
        else:
            raise ValueError("Qubit index out of range")

    def u3(self, theta: float, phi: float, lamda: float, qubit: int) -> None:
        r"""
        Add a U3 gate.

        The U3 gate is a single-qubit gate with the following matrix representation:

        $$
        U3(\theta, \phi, \lambda) = \begin{bmatrix}
            \cos(\theta/2) & -e^{i\lambda} \sin(\theta/2) \\
            e^{i\phi} \sin(\theta/2) & e^{i(\phi + \lambda)} \cos(\theta/2)
            \end{bmatrix}
        $$

        Args:
            theta (float): The rotation angle of the gate.
            phi (float): The rotation angle of the gate.
            lamda (float): The rotation angle of the gate.
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.u(theta, phi, lamda, qubit)
            self._add_qubits(qubit)
            if isinstance(theta,str):
                self.params_value[theta] = theta
            if isinstance(phi,str):
                self.params_value[phi] = phi
            if isinstance(lamda,str):
                self.params_value[lamda] = lamda
        else:
            raise ValueError("Qubit index out of range")   

    def rx(self, theta: float, qubit: int) -> None:
        r"""
        Add a RX gate.

        Args:
            theta (float): The rotation angle of the gate.
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('rx', theta, qubit))
            self._add_qubits(qubit)
            if isinstance(theta,str):
                self.params_value[theta] = theta
        else:
            raise ValueError("Qubit index out of range")
        
    def ry(self, theta: float, qubit: int) -> None:
        r"""
        Add a RY gate.

        Args:
            theta (float: The rotation angle of the gate.
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('ry', theta, qubit))
            self._add_qubits(qubit)
            if isinstance(theta,str):
                self.params_value[theta] = theta
        else:
            raise ValueError("Qubit index out of range")
        
    def rz(self, theta: float, qubit: int) -> None:
        r"""
        Add a RZ gate.

        Args:
            theta (float): The rotation angle of the gate.
            qubit (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('rz', theta, qubit))
            self._add_qubits(qubit)
            if isinstance(theta,str):
                self.params_value[theta] = theta
        else:
            raise ValueError("Qubit index out of range")
        
    def rxx(self, theta: float, qubit1: int, qubit2:int) -> None:
        r"""
        Add a RXX gate.

        $$
        Rxx(\theta) = e^{-i\frac{\theta}{2}X\otimes X} = 
        \begin{bmatrix}
         \cos(\frac{\theta}{2})  & 0 & 0 & -i\sin(\frac{\theta}{2}) \\
         0 & \cos(\frac{\theta}{2}) & -i\sin(\frac{\theta}{2}) & 0 \\
         0 & -i\sin(\frac{\theta}{2}) & \cos(\frac{\theta}{2}) & 0 \\
         -i\sin(\frac{\theta}{2}) & 0 & 0 & \cos(\frac{\theta}{2})
        \end{bmatrix}.
        $$

        Args:
            theta (float): The rotation angle of the gate.
            qubit1 (int): The qubit to apply the gate to.
            qubit2 (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if max(qubit1, qubit2) < self.nqubits:
            if qubit1 != qubit2:
                self.gates.append(('rxx', theta, qubit1, qubit2))
                self._add_qubits(qubit1,qubit2)
                if isinstance(theta,str):
                    self.params_value[theta] = theta
            else:
                raise ValueError(f"Qubit index conflict: qubit1 and qubit2 are both {qubit1}")
        else:
            raise ValueError("Qubit index out of range")
        
    def ryy(self, theta: float, qubit1: int, qubit2:int) -> None:
        r"""
        Add a RYY gate.

        $$
        Ryy(\theta) = e^{-i\frac{\theta}{2}Y\otimes Y} = 
        \begin{bmatrix}
         \cos(\frac{\theta}{2})  & 0 & 0 & i\sin(\frac{\theta}{2}) \\
         0 & \cos(\frac{\theta}{2}) & -i\sin(\frac{\theta}{2}) & 0 \\
         0 & -i\sin(\frac{\theta}{2}) & \cos(\frac{\theta}{2}) & 0 \\
         i\sin(\frac{\theta}{2}) & 0 & 0 & \cos(\frac{\theta}{2})
        \end{bmatrix}.
        $$

        Args:
            theta (float): The rotation angle of the gate.
            qubit1 (int): The qubit to apply the gate to.
            qubit2 (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if max(qubit1, qubit2) < self.nqubits:
            if qubit1 != qubit2:
                self.gates.append(('ryy', theta, qubit1, qubit2))
                self._add_qubits(qubit1, qubit2)
                if isinstance(theta, str):
                    self.params_value[theta] = theta
            else:
                raise ValueError(f"Qubit index conflict: qubit1 and qubit2 are both {qubit1}")
        else:
            raise ValueError("Qubit index out of range")
        
    def rzz(self, theta: float, qubit1: int, qubit2:int) -> None:
        r"""
        Add a RZZ gate.

        $$
        Rzz(\theta) = e^{-i\frac{\theta}{2}Z\otimes Z} = 
        \begin{bmatrix}
         e^{-i\frac{\theta}{2}}  & 0 & 0 & 0 \\
         0 & e^{i\frac{\theta}{2}} & 0 & 0 \\
         0 & 0 & e^{i\frac{\theta}{2}} & 0 \\
         0 & 0 & 0 & e^{-i\frac{\theta}{2}}
        \end{bmatrix}.
        $$

        Args:
            theta (float): The rotation angle of the gate.
            qubit1 (int): The qubit to apply the gate to.
            qubit2 (int): The qubit to apply the gate to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if max(qubit1, qubit2) < self.nqubits:
            if qubit1 != qubit2:
                self.gates.append(('rzz', theta, qubit1, qubit2))
                self._add_qubits(qubit1,qubit2)
                if isinstance(theta,str):
                    self.params_value[theta] = theta
            else:
                raise ValueError(f"Qubit index conflict: qubit1 and qubit2 are both {qubit1}")
        else:
            raise ValueError("Qubit index out of range")
        
    def shallow_apply_value(self,params_dic):
        for k,v in self.params_value.items():
            self.params_value[k] = k
        for k,v in params_dic.items():
            self.params_value[k] = v

    def deep_apply_value(self,params_dic):
        for k,v in self.params_value.items():
            self.params_value[k] = k

        gates = []
        for gate_info in self.gates:
            gate = gate_info[0]
            if gate in one_qubit_parameter_gates_available.keys():
                param = gate_info[1]
                qubit = gate_info[-1]
                if param in params_dic.keys():
                    param = params_dic[param]
                    del self.params_value[gate_info[1]]
                    gate_info = (gate,param,qubit)
            gates.append(gate_info)
        self.gates = gates

    def u3_for_unitary(self, unitary: np.ndarray, qubit: int):
        r"""
        Decomposes a 2x2 unitary matrix into a U3 gate and applies it to a specified qubit.

        Args:
            unitary (np.ndarray): A 2x2 unitary matrix.
            qubit (int): The qubit to apply the gate to.
        """
        assert(unitary.shape == (2,2))
        assert(qubit < self.nqubits)
        theta,phi,lamda,phase = u3_decompose(unitary)
        self.gates.append(('u', theta, phi, lamda, qubit))
        self._add_qubits(qubit)

    def zyz_for_unitary(self, unitary: np.ndarray, qubit:int) -> None:
        r"""
        Decomposes a 2x2 unitary matrix into Rz-Ry-Rz gate sequence and applies it to a specified qubit.

        Args:
            unitary (np.ndarray): A 2x2 unitary matrix.
            qubit (int): The qubit to apply the gate sequence to.
        """
        assert(unitary.shape == (2,2))
        assert(qubit < self.nqubits)
        theta, phi, lamda, alpha = zyz_decompose(unitary)
        self.gates.append(('rz', lamda, qubit))
        self.gates.append(('ry', theta, qubit))
        self.gates.append(('rz', phi, qubit))
        self._add_qubits(qubit)

    def kak_for_unitary(self, unitary: np.ndarray, qubit1: int, qubit2: int) -> None:
        r"""
        Decomposes a 4 x 4 unitary matrix into a sequence of CZ and U3 gates using KAK decomposition and applies them to the specified qubits.

        Args:
            unitary (np.ndarray): A 4 x 4 unitary matrix.
            qubit1 (int): The first qubit to apply the gates to.
            qubit2 (int): The second qubit to apply the gates to.
        """
        assert(unitary.shape == (4,4))
        assert(qubit1 != qubit2)
        rots1, rots2 = kak_decompose(unitary)
        self.u3_for_unitary(rots1[0], qubit1)
        self.u3_for_unitary(h_mat @ rots2[0], qubit2)
        self.gates.append(('cz', qubit1, qubit2))
        self.u3_for_unitary(rots1[1], qubit1)
        self.u3_for_unitary(h_mat @ rots2[1] @ h_mat, qubit2)
        self.gates.append(('cz', qubit1, qubit2))
        self.u3_for_unitary(rots1[2], qubit1)
        self.u3_for_unitary(h_mat @ rots2[2] @ h_mat, qubit2)
        self.gates.append(('cz', qubit1, qubit2))        
        self.u3_for_unitary(rots1[3], qubit1)
        self.u3_for_unitary(rots2[3] @ h_mat, qubit2)
        self._add_qubits(qubit1,qubit2)

    def reset(self, qubit: int) -> None:
        r"""
        Add reset to qubit.

        Args:
            qubit (int): The qubit to apply the instruction to.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if qubit < self.nqubits:
            self.gates.append(('reset', qubit))
            self._add_qubits(qubit)
        else:
            raise ValueError("Qubit index out of range")
        
    def delay(self,duration:int|float, *qubits:tuple[int],unit='s') ->None:
        r"""
        Adds delay to qubits, the unit is s.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        # convert 'ns' 'ms' 'us' to 's
        if unit == 'ns':
            duration = duration * 1e-9
        elif unit == 'us':
            duration = duration * 1e-6
        elif unit =='ms':
            duration = duration * 1e-3

        if not qubits: # it will add barrier for all qubits
            self.gates.append(('delay', duration, tuple(self.qubits)))
        else:
            if max(qubits) < self.nqubits:
                self.gates.append(('delay', duration, qubits))
                self._add_qubits(*qubits)
            else:
                raise ValueError("Qubit index out of range")
        
    def barrier(self,*qubits: tuple[int]) -> None:
        r"""
        Adds barrier to qubits.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if not qubits: # it will add barrier for all qubits
            self.gates.append(('barrier', tuple(self.qubits)))
        else:
            if max(qubits) < self.nqubits:
                if len(set(qubits)) == len(qubits):
                    self.gates.append(('barrier', qubits))
                else:
                    raise(ValueError(f'Qubit index conflict. {qubits}'))
            else:
                raise ValueError("Qubit index out of range")
            
    def remove_barrier(self) -> 'QuantumCircuit':
        r"""
        Remove all barrier gates from the quantum circuit.

        Returns:
            QuantumCircuit: The updated quantum circuit with all barrier gates removed.
        """
        new = []
        for gate_info in self.gates:
            gate  = gate_info[0]
            if gate != 'barrier':
                new.append(gate_info)
        self.gates = new
        return self
    
    def measure(self,qubitlst: int | Iterable[int], cbitlst: int | Iterable[int]) -> None:
        r"""Adds measurement to qubits.

        Args:
            qubitlst (int | list): Qubit(s) to measure.
            cbitlst (int | list): Classical bit(s) to place the measure results in.
        """
        if isinstance(qubitlst,Iterable):
            qubitlst = list(qubitlst)
            cbitlst = list(cbitlst)
            if (len(set(qubitlst)) == len(qubitlst) and 
                len(set(cbitlst)) == len(cbitlst) and 
                len(qubitlst) == len(cbitlst)):
                self.gates.append(('measure', qubitlst,cbitlst))
                self._add_qubits(*qubitlst)
            else:
                raise(ValueError(f'Qubit or Cbits index conflict. {qubitlst} {cbitlst}'))
        elif isinstance(qubitlst,int):
            if qubitlst < self.nqubits:
                self.gates.append(('measure', [qubitlst], [cbitlst]))
                self._add_qubits(qubitlst)
            else:
                raise ValueError("Qubit index out of range")
        else:
            raise(ValueError(''))

    def measure_all(self) -> None:
        r"""
        Adds measurement to all qubits.
        """
        qubitlst = [i for i in self.qubits]
        cbitlst = [i for i in range(len(qubitlst))]
        self.gates.append(('measure', qubitlst,cbitlst))

    @property
    def to_latex(self) -> str:
        print('If you need this feature, please contact the developer.')    

    @property
    def to_openqasm2(self) -> str:
        r"""
        Export the quantum circuit to an OpenQASM 2 program in a string.

        Returns:
            str: An OpenQASM 2 string representing the circuit.
        """
        qasm_str = "OPENQASM 2.0;\n"
        qasm_str += "include \"qelib1.inc\";\n"
        gates0 = [gate[0] for gate in self.gates]
        if 'delay' in gates0:
            qasm_str += "opaque delay(param0) q0;\n"
        if 'r' in gates0:
            qasm_str += "gate r(param0,param1) q0 { u3(param0,param1 - pi/2,pi/2 - param1) q0; }\n"
        qasm_str += f"qreg q[{self.nqubits}];\n"
        qasm_str += f"creg c[{self.ncbits}];\n"
        for gate in self.gates:
            if gate[0] in one_qubit_gates_available.keys(): # single qubit gate 
                qasm_str += f"{gate[0]} q[{gate[1]}];\n"
            elif gate[0] in two_qubit_gates_available.keys(): # two qubit gate 
                qasm_str += f"{gate[0]} q[{gate[1]}],q[{gate[2]}];\n"
            elif gate[0] in three_qubit_gates_available.keys():
                qasm_str += f"{gate[0]} q[{gate[1]}],q[{gate[2]}],q[{gate[3]}];\n"
            elif gate[0] in two_qubit_parameter_gates_available.keys():
                if isinstance(gate[1],float):
                    theta = gate[1]
                elif isinstance(gate[1],str):
                    param = self.params_value[gate[1]]
                    if isinstance(param,float):
                        theta = param
                    else:
                        raise(ValueError(f'please apply value for parameter {param}')) 
                qasm_str += f"{gate[0]}({theta}) q[{gate[2]}],q[{gate[3]}];\n"                        
            elif gate[0] in one_qubit_parameter_gates_available.keys():
                if gate[0] == 'u':
                    if isinstance(gate[1],float):
                        theta = gate[1]
                    elif isinstance(gate[1],str):
                        param = self.params_value[gate[1]]
                        if isinstance(param,float):
                            theta = param
                        else:
                            raise(ValueError(f'please apply value for parameter {param}')) 
                        
                    if isinstance(gate[2],float):
                        phi = gate[2]
                    elif isinstance(gate[2],str):
                        param = self.params_value[gate[2]]
                        if isinstance(param,float):
                            phi = param
                        else:
                            raise(ValueError(f'please apply value for parameter {param}')) 
                        
                    if isinstance(gate[3],float):
                        lamda = gate[3]
                    elif isinstance(gate[3],str):
                        param = self.params_value[gate[3]]
                        if isinstance(param,float):
                            lamda = param
                        else:
                            raise(ValueError(f'please apply value for parameter {param}')) 
                        
                    qasm_str += f"{gate[0]}({theta},{phi},{lamda}) q[{gate[-1]}];\n"
                elif gate[0] == 'r':
                    if isinstance(gate[1],float):
                        theta = gate[1]
                    elif isinstance(gate[1],str):
                        param = self.params_value[gate[1]]
                        if isinstance(param,float):
                            theta = param
                        else:
                            raise(ValueError(f'please apply value for parameter {param}')) 
                        
                    if isinstance(gate[2],float):
                        phi = gate[2]
                    elif isinstance(gate[2],str):
                        param = self.params_value[gate[2]]
                        if isinstance(param,float):
                            phi = param
                        else:
                            raise(ValueError(f'please apply value for parameter {param}')) 
                        
                    qasm_str += f"{gate[0]}({theta},{phi}) q[{gate[-1]}];\n"

                else:
                    if isinstance(gate[1],float):
                        qasm_str += f"{gate[0]}({gate[1]}) q[{gate[2]}];\n"
                    elif isinstance(gate[1],str):
                        param = self.params_value[gate[1]]
                        if isinstance(param,float):
                            qasm_str += f"{gate[0]}({param}) q[{gate[2]}];\n"
                        else:
                            raise(ValueError(f'please apply value for parameter {param}')) 
            elif gate[0] in ['reset']:
                qasm_str += f"{gate[0]} q[{gate[1]}];\n"
            elif gate[0] in ['delay']:
                for qubit in gate[2]:
                    qasm_str += f"{gate[0]}({gate[1]}) q[{qubit}];\n"
            elif gate[0] in ['barrier']:
                qasm_str += f"{gate[0]} q[{gate[1][0]}]"
                for idx in gate[1][1:]:
                    qasm_str += f",q[{idx}]"
                qasm_str += ';\n'
            elif gate[0] in ['measure']:
                for idx in range(len(gate[1])):
                    qasm_str += f"{gate[0]} q[{gate[1][idx]}] -> c[{gate[2][idx]}];\n"
            else:
                raise(ValueError(f"Sorry, Quark could not find the corresponding OpenQASM 2.0 syntax for now. Please contact the developer for assistance.{gate[0]}"))
        return qasm_str.rstrip('\n')
    
    @property
    def to_qlisp(self) -> list:
        r"""Export the quantum circuit to qlisp list.

        Returns:
            list: qlisp list
        """
        qlisp = []
        for gate_info in self.gates:
            gate = gate_info[0]
            if gate in ['x', 'y', 'z', 's', 't', 'h']:
                qlisp.append((gate.upper(), 'Q'+str(gate_info[1])))
            elif gate in ['id']:
                qlisp.append(('I', 'Q'+str(gate_info[1])))
            elif gate in ['sdg','tdg']:
                qlisp.append(('-' + gate[0].upper(), 'Q'+str(gate_info[1])))
            elif gate in ['sx']:
                qlisp.append(('X/2', 'Q'+str(gate_info[1])))
            elif gate in ['sxdg']:
                qlisp.append(('-X/2', 'Q'+str(gate_info[1])))
            elif gate in ['u']:
                if isinstance(gate_info[1],float):
                    theta = gate_info[1]
                elif isinstance(gate_info[1],str):
                    param = self.params_value[gate_info[1]]
                    if isinstance(param,float):
                        theta = param
                    else:
                        raise(ValueError(f'please apply value for parameter {param}')) 
                    
                if isinstance(gate_info[2],float):
                    phi = gate_info[2]
                elif isinstance(gate_info[2],str):
                    param = self.params_value[gate_info[2]]
                    if isinstance(param,float):
                        phi = param
                    else:
                        raise(ValueError(f'please apply value for parameter {param}')) 
                    
                if isinstance(gate_info[3],float):
                    lamda = gate_info[3]
                elif isinstance(gate_info[3],str):
                    param = self.params_value[gate_info[3]]
                    if isinstance(param,float):
                        lamda = param
                    else:
                        raise(ValueError(f'please apply value for parameter {param}'))                    
                qlisp.append((('U', theta, phi, lamda),'Q'+str(gate_info[4])))
            elif gate in ['r']:
                if isinstance(gate_info[1],float):
                    theta = gate_info[1]
                elif isinstance(gate_info[1],str):
                    param = self.params_value[gate_info[1]]
                    if isinstance(param,float):
                        theta = param
                    else:
                        raise(ValueError(f'please apply value for parameter {param}')) 
                    
                if isinstance(gate_info[2],float):
                    phi = gate_info[2]
                elif isinstance(gate_info[2],str):
                    param = self.params_value[gate_info[2]]
                    if isinstance(param,float):
                        phi = param
                    else:
                        raise(ValueError(f'please apply value for parameter {param}')) 
                if abs(theta-np.pi/2) < 1e-9:
                    qlisp.append((('R', phi),'Q'+str(gate_info[3])))
                else:
                    qlisp.append((('U', theta, phi-np.pi/2, np.pi/2-phi),'Q'+str(gate_info[3])))
                    #qlisp.append((('rfUnitary', theta, phi),'Q'+str(gate_info[3])))
            elif gate in ['cx','cy', 'cz', 'swap']:
                if gate == 'cx':
                    qlisp.append(('Cnot', tuple('Q'+str(i) for i in gate_info[1:])))
                else:
                    qlisp.append((gate.upper(), tuple('Q'+str(i) for i in gate_info[1:])))
            elif gate in ['iswap']:
                qlisp.append(('iSWAP', tuple('Q'+str(i) for i in gate_info[1:])))
            elif gate in three_qubit_gates_available.keys():
                qlisp.append((gate.upper(), tuple('Q'+str(i) for i in gate_info[1:])))
            elif gate in ['rx', 'ry', 'rz', 'p']:
                if isinstance(gate_info[1],float):
                    qlisp.append(((gate.capitalize(), gate_info[1]), 'Q'+str(gate_info[2])))
                elif isinstance(gate_info[1],str):
                    param = self.params_value[gate_info[1]]
                    if isinstance(param,float):
                        qlisp.append(((gate.capitalize(),param), 'Q'+str(gate_info[2])))
                    else:
                        raise(ValueError(f'please apply value for parameter {param}')) 
            elif gate in ['delay']:#qlisp unit in s
                for qubit in gate_info[-1]:
                    qlisp.append(((gate.capitalize(),gate_info[1]),'Q'+str(qubit)))
            elif gate in ['reset']:
                qlisp.append((gate.capitalize(), 'Q'+str(gate_info[1])))
            elif gate in ['barrier']:
                qlisp.append((gate.capitalize(), tuple('Q'+str(i) for i in gate_info[1])))
            elif gate in ['measure']:
                for idx,cbit in enumerate(gate_info[2]):
                    qlisp.append(((gate.capitalize(), cbit), 'Q'+str(gate_info[1][idx])))
            else:
                raise(ValueError(f'Sorry, quarkcircuit could not find the corresponding qlisp syntax for now. Please contact the developer for assistance. {gate}'))
        return qlisp

    @property
    def depth(self) -> int:
        r"""Count QuantumCircuit depth.

        Returns:
            int: QuantumCircuit depth.
        """
        import networkx as nx

        new = []
        for gate_info in self.gates:
            gate  = gate_info[0]
            if gate != 'barrier':
                new.append(gate_info) 

        node_list,edge_list = convert_gate_info_to_dag_info(self.nqubits,self.qubits,new,show_qubits=False)
        dag = nx.DiGraph()
        dag.add_nodes_from(node_list)
        dag.add_edges_from(edge_list)
        dag_nodes_layered = list(nx.topological_generations(dag))
        return len(dag_nodes_layered)
    
    @property
    def ncz(self) -> int:
        r"""Count all two-qubit gates in this QuantumCircuit.

        Returns:
            int: The number of two-qubit gates.
        """
        ncz = 0
        for gate_info in self.gates:
            gate  = gate_info[0]
            if gate in two_qubit_gates_available.keys():
                ncz += 1
            elif gate in two_qubit_parameter_gates_available.keys():
                ncz += 1
            else:
                continue
        return ncz
    
    def draw(self, width: int = 4) -> None:
        r"""
        Draw the quantum circuit.

        Args:
            width (int, optional): The width between gates. Defaults to 4.
        """
        lines1,lines_use = add_gates_to_lines(self.nqubits,self.ncbits,self.gates,self.params_value, width = width)
        fline = str()
        for line in lines1:
            fline += '\n'
            fline += line
            
        formatted_string = fline.replace("\n", "<br>").replace(" ", "&nbsp;")
        html_content = f'<div style="overflow-x: auto; white-space: nowrap; font-family: consolas;">{formatted_string}</div>'
        display(HTML(html_content))

    def draw_simply(self, width: int = 4) -> None:
        r"""
        Draw a simplified quantum circuit diagram.
        
        This method visualizes the quantum circuit by displaying only the qubits that have gates applied to them,
        omitting any qubits without active gates. The result is a cleaner, more concise circuit diagram.

        Args:
            width (int, optional): The width between gates. Defaults to 4.
        """
        lines1,lines_use = add_gates_to_lines(self.nqubits,self.ncbits,self.gates,self.params_value, width=width)
        fline = str()
        for idx in range(2 * self.nqubits):
            if idx in lines_use:
                fline += '\n'
                fline += lines1[idx]
        for idx in range(2 * self.nqubits, len(lines1)):
            fline += '\n'
            fline += lines1[idx]
            
        formatted_string = fline.replace("\n", "<br>").replace(" ", "&nbsp;")
        html_content = f'<div style="overflow-x: auto; white-space: nowrap; font-family: consolas;">{formatted_string}</div>'
        display(HTML(html_content))

    def to_qiskitQC(self):
        from qiskit import QuantumCircuit as qiskitQC
        qc = qiskitQC(self.nqubits,self.ncbits)
        one_qubit_gates_in_qiskit = {
            'id':qc.id, 
            'x':qc.x, 
            'y':qc.y, 
            'z':qc.z,
            's':qc.s, 
            'sdg':qc.sdg,
            't':qc.t, 
            'tdg':qc.tdg,
            'h':qc.h, 
            'sx':qc.sx,
            'sxdg':qc.sxdg,
            }
        two_qubit_gates_in_qiskit = {
            'cx':qc.cx, 
            'cnot':qc.cx, 
            'cy':qc.cy, 
            'cz':qc.cz, 
            'swap':qc.swap, 
            'iswap':qc.iswap,
            }
        three_qubit_gates_in_qiskit = {
            'ccz':qc.ccz,
            'ccx':qc.ccx,
            'cswap':qc.cswap,
        }
        one_qubit_parameter_gates_in_qiskit = {
            'rx':qc.rx, 
            'ry':qc.ry, 
            'rz':qc.rz, 
            'p':qc.p, 
            'u':qc.u,
            'r':qc.r,
            }
        two_qubit_parameter_gates_in_qiskit = {
            'rxx':qc.rxx, 
            'ryy':qc.ryy, 
            'rzz':qc.rzz, 
            }
        functional_gates_in_qiskit = {
            'barrier':qc.barrier, 
            'measure':qc.measure, 
            'reset':qc.reset,
            'delay':qc.delay,
            }
        for gate_info in self.gates:
            gate = gate_info[0]
            if gate in one_qubit_gates_in_qiskit.keys():
                one_qubit_gates_in_qiskit[gate](*gate_info[1:])
            elif gate in two_qubit_gates_in_qiskit.keys():
                two_qubit_gates_in_qiskit[gate](*gate_info[1:])
            elif gate in three_qubit_gates_in_qiskit.keys():
                three_qubit_gates_in_qiskit[gate](*gate_info[1:])
            elif gate in one_qubit_parameter_gates_in_qiskit.keys():
                one_qubit_parameter_gates_in_qiskit[gate](*gate_info[1:])
            elif gate in two_qubit_parameter_gates_in_qiskit.keys():
                two_qubit_parameter_gates_in_qiskit[gate](*gate_info[1:])
            elif gate in functional_gates_in_qiskit.keys():
                if gate =='delay':
                    functional_gates_in_qiskit[gate](*gate_info[1:],unit='ns')
                else:
                    functional_gates_in_qiskit[gate](*gate_info[1:])
            else:
                raise(ValueError(f'the gate name is wrong! {gate}'))
        return qc

    def plot_with_qiskit(self,file_name=None):
        from qiskit.visualization import circuit_drawer
        qc = self.to_qiskitQC()
        return circuit_drawer(qc,output="mpl",filename=file_name,idle_wires=False, style = {'backgroundcolor':'#EEEEEE','linecolor':'grey'})