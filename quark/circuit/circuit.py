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

import re, copy

from IPython.display import display, HTML
import numpy as np

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

def generate_random_circuit(nqubits: int, ncycle: int, seed: int = 2024, function_gates: bool = True) -> 'QuantumCircuit':
    r"""
    Generate random quantum circuits, mainly for testing.

    Args:
        nqubits (int): The number of qubits.
        ncycle (int): The number of quantum circuit layers.
        seed (int, optional): Random seed. Defaults to 2024.
        function_gates (bool, optional): Whether it contains functional gates. Defaults to True.

    Returns:
        QuantumCircuit: A random quantum circuit.
    """
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(nqubits)
    # print('ncycle: {}, nqubit: {}'.format(ncycle, nqubits))
    two_qubit_gates_avaliable_qiskit = copy.deepcopy(two_qubit_gates_avaliable)
    two_qubit_gates_avaliable_qiskit.pop('iswap')
    for _ in range(ncycle):
        for qubit in range(nqubits):
            if function_gates:
                gate_type = rng.choice(['single', 'parametric', 'two','barrier','measure','reset'])
            else:
                gate_type = rng.choice(['single', 'parametric', 'two'])
            if gate_type == 'single':
                gate = rng.choice(list(one_qubit_gates_avaliable.keys()))
                getattr(qc, gate)(qubit)
            elif gate_type == 'two' and nqubits > 1:
                gate = rng.choice(list(two_qubit_gates_avaliable_qiskit.keys()))
                target_qubit = rng.choice([q for q in range(nqubits) if q != qubit])
                getattr(qc, gate)(qubit, target_qubit)
            elif gate_type == 'parametric':
                gate = rng.choice(list(one_qubit_parameter_gates_avaliable.keys()))
                if gate == 'u':
                    theta = rng.uniform(-1,1)*np.pi 
                    phi = rng.uniform(-1,1)*np.pi 
                    lamda = rng.uniform(-1,1)*np.pi 
                    getattr(qc, gate)(theta,phi,lamda,qubit)
                else:
                    theta = rng.uniform(-1,1)*np.pi  
                    getattr(qc, gate)(theta, qubit)
            elif gate_type == 'barrier':
                for idx in range(qubit+1):
                    getattr(qc, 'barrier')(idx)
            elif gate_type == 'measure':
                getattr(qc, 'measure')(qubit,qubit)
            elif gate_type == 'reset':
                getattr(qc, 'reset')(qubit)
    return qc

def is_multiple_of_pi(n, tolerance: float = 1e-9) -> str:
    r"""
    Determines if a given number is approximately a multiple of π (pi) within a given tolerance.

    Args:
        n (float): The number to be checked.
        tolerance (float, optional): The allowable difference between the number and a multiple of π. Defaults to 1e-9.

    Returns:
        str: A string representation of the result. If the number is close to a multiple of π, 
             it returns a string in the form of "kπ" where k is a rounded multiplier (e.g., "2π" for 2 x π).
             If n is approximately 0, it returns "0.0".
             Otherwise, it returns a string representation of the number rounded to three decimal places.
    """
    result = n / np.pi
    aprox = round(result,2)
    if abs(result - aprox) < tolerance:
        if np.allclose(aprox, 0.0):
            return str(0.0)
        else:
            expression = f'{aprox}π'
            return expression
    else:
        return str(round(n,3))

one_qubit_gates_avaliable = {
    'id':'I', 'x':'X', 'y':'Y', 'z':'Z',
    's':'S', 'sdg':'Sdg','t':'T', 'tdg':'Tdg',
    'h':'H', 'sx':'√X','sxdg':'√Xdg',
    }
two_qubit_gates_avaliable = {
    'cx':'●X', 'cnot':'●X', 'cy':'●Y', 'cz':'●●', 'swap':'XX', 'iswap':'⨂+',
    }
one_qubit_parameter_gates_avaliable = {'rx':'Rx', 'ry':'Ry', 'rz':'Rz', 'p':'P', 'u':'U'}
functional_gates_avaliable = {'barrier':'░', 'measure':'M', 'reset':'|0>'}

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
        
        self.from_openqasm2_str = None

        self.gates = []
        self.lines_use = []

    def from_openqasm2(self,openqasm2_str: str) -> None:
        r"""
        Initializes the QuantumCircuit object based on the given OpenQASM 2.0 string.

        Args:
            openqasm2_str (str): A string representing a quantum circuit in OpenQASM 2.0 format.
        """
        assert('OPENQASM 2.0' in openqasm2_str)
        self.from_openqasm2_str = openqasm2_str
        self.nqubits = int(re.findall(r"\d+\.?\d*", openqasm2_str.split('qreg')[1].split(';')[0])[0])
        if 'creg' in openqasm2_str:
            self.ncbits = int(re.findall(r"\d+\.?\d*", openqasm2_str.split('creg')[1].split(';')[0])[0])
        else:
            self.ncbits = self.nqubits
        # update self.gates
        self._openqasm2_to_gates()
        
    def from_qlisp(self, qlisp: list) -> None:
        r"""
        Initializes the QuantumCircuit object based on the given qlisp list.

        Args:
            qlisp (list): A list representing a quantum circuit in qlisp format.
        """
        new_gates, qubit_used,cbit_used = self._qlisp_to_gates(qlisp)
        self.nqubits = max(qubit_used, default=0) + 1 
        self.ncbits = max(cbit_used, default=0) + 1
        self.gates = new_gates

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
            self.gates.append(('swap', qubit1,qubit2))
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
            self.gates.append(('iswap', qubit1,qubit2))
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
            self.gates.append(('cx', control_qubit,target_qubit))
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
            self.cx(control_qubit, target_qubit)
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
            self.gates.append(('cy', control_qubit,target_qubit))
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
            self.gates.append(('cz', control_qubit,target_qubit))
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
        else:
            raise ValueError("Qubit index out of range")

    def u3_for_unitary(self, unitary: np.ndarray, qubit: int):
        r"""
        Decomposes a 2x2 unitary matrix into a U3 gate and applies it to a specified qubit.

        Args:
            unitary (np.ndarray): A 2x2 unitary matrix.
            qubit (int): The qubit to apply the gate to.
        """
        assert(unitary.shape == (2,2))
        theta,phi,lamda,phase = u3_decompose(unitary)
        self.gates.append(('u', theta, phi, lamda, qubit))

    def zyz_for_unitary(self, unitary: np.ndarray, qubit:int) -> None:
        r"""
        Decomposes a 2x2 unitary matrix into Rz-Ry-Rz gate sequence and applies it to a specified qubit.

        Args:
            unitary (np.ndarray): A 2x2 unitary matrix.
            qubit (int): The qubit to apply the gate sequence to.
        """
        assert(unitary.shape == (2,2))
        theta, phi, lamda, alpha = zyz_decompose(unitary)
        self.gates.append(('rz', lamda, qubit))
        self.gates.append(('ry', theta, qubit))
        self.gates.append(('rz', phi, qubit))

    def kak_for_unitary(self, unitary: np.ndarray, qubit1: int, qubit2: int) -> None:
        r"""
        Decomposes a 4 x 4 unitary matrix into a sequence of CZ and U3 gates using KAK decomposition and applies them to the specified qubits.

        Args:
            unitary (np.ndarray): A 4 x 4 unitary matrix.
            qubit1 (int): The first qubit to apply the gates to.
            qubit2 (int): The second qubit to apply the gates to.
        """
        assert(unitary.shape == (4,4))
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
        else:
            raise ValueError("Qubit index out of range")
        
    def barrier(self,*qubits: tuple[int]) -> None:
        r"""
        Adds barrier to qubits.

        Raises:
            ValueError: If qubit out of circuit range.
        """
        if not qubits: # it will add barrier for all qubits
            self.gates.append(('barrier', tuple(range(self.nqubits))))
        else:
            if max(qubits) < self.nqubits:
                self.gates.append(('barrier', qubits))
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
    
    def measure(self,qubitlst: int | list, cbitlst: int | list) -> None:
        r"""Adds measurement to qubits.

        Args:
            qubitlst (int | list): Qubit(s) to measure.
            cbitlst (int | list): Classical bit(s) to place the measure results in.
        """
        if type(qubitlst) == list:
            self.gates.append(('measure', qubitlst,cbitlst))
        else:
            self.gates.append(('measure', [qubitlst],[cbitlst]))

    def measure_all(self) -> None:
        r"""
        Adds measurement to all qubits.
        """
        qubitlst = [i for i in range(self.nqubits)]
        cbitlst = [i for i in range(self.ncbits)]
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
        qasm_str += f"qreg q[{self.nqubits}];\n"
        qasm_str += f"creg c[{self.ncbits}];\n"

        for gate in self.gates:
            if gate[0] in one_qubit_gates_avaliable.keys(): # single qubit gate 
                qasm_str += f"{gate[0]} q[{gate[1]}];\n"
            elif gate[0] in two_qubit_gates_avaliable.keys(): # two qubit gate 
                qasm_str += f"{gate[0]} q[{gate[1]}],q[{gate[2]}];\n"
            elif gate[0] in one_qubit_parameter_gates_avaliable.keys():
                if gate[0] == 'u':
                    qasm_str += f"{gate[0]}({gate[1]},{gate[2]},{gate[3]}) q[{gate[-1]}];\n"
                else:
                    qasm_str += f"{gate[0]}({gate[1]}) q[{gate[2]}];\n"
            elif gate[0] in ['reset']:
                qasm_str += f"{gate[0]} q[{gate[1]}];\n"
            elif gate[0] in ['barrier']:
                qasm_str += f"{gate[0]} q[{gate[1][0]}]"
                for idx in gate[1][1:]:
                    qasm_str += f",q[{idx}]"
                qasm_str += ';\n'
            elif gate[0] in ['measure']:
                for idx in range(len(gate[1])):
                    qasm_str += f"{gate[0]} q[{gate[1][idx]}] -> c[{gate[2][idx]}];\n"
        return qasm_str.rstrip('\n')
    
    def _openqasm2_to_gates(self) -> None:
        r"""
        Parse gate information from an input OpenQASM 2.0 string, and update self.gates
        """
        for line in self.from_openqasm2_str.splitlines():
            gate = line.split()[0].split('(')[0]
            position = [int(num) for num in re.findall(r'\d+', line)]
            if gate in one_qubit_gates_avaliable.keys():
                self.gates.append((gate,position[0]))
            elif gate in two_qubit_gates_avaliable.keys():
                self.gates.append((gate,position[0],position[1]))
            elif gate in one_qubit_parameter_gates_avaliable.keys():
                if gate == 'u':
                    params_str = re.search(r'\(([^)]+)\)', line).group(1).split(',')
                    params = [float(i) for i in params_str]
                    self.gates.append((gate, params[0], params[1], params[2], position[-1]))
                else:
                    param = float(re.search(r'\(([^)]+)\)', line).group(1))
                    self.gates.append((gate, param, position[-1]))
            elif gate in ['reset']:
                self.gates.append((gate,position[0]))
            elif gate in ['barrier']:
                self.gates.append((gate, tuple(position)))
            elif gate in ['measure']:
                self.gates.append((gate, [position[0]], [position[1]])) 
    
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
                qlisp.append((gate, 'Q'+str(gate_info[1])))
            elif gate in ['sxdg']:
                qlisp.append(('-' + gate[:2], 'Q'+str(gate_info[1])))
            elif gate in ['u']:
                qlisp.append((('u3', gate_info[1], gate_info[2], gate_info[3]),'Q'+str(gate_info[4])))

            elif gate in ['cx','cnot']:
                qlisp.append(('Cnot', tuple('Q'+str(i) for i in gate_info[1:])))
            elif gate in ['cy', 'cz', 'swap']:
                qlisp.append((gate.upper(), tuple('Q'+str(i) for i in gate_info[1:])))
            elif gate in ['iswap']:
                qlisp.append(('iSWAP', tuple('Q'+str(i) for i in gate_info[1:])))

            elif gate in ['rx', 'ry', 'rz', 'p']:
                qlisp.append(((gate.capitalize(), gate_info[1]), 'Q'+str(gate_info[2])))
            elif gate in ['reset']:
                qlisp.append((gate.capitalize(), 'Q'+str(gate_info[1])))
            elif gate in ['barrier']:
                qlisp.append((gate.capitalize(), tuple('Q'+str(i) for i in gate_info[1])))
            elif gate in ['measure']:
                qlisp.append(((gate.capitalize(), gate_info[2][0]), 'Q'+str(gate_info[1][0])))
        return qlisp
    
    def _qlisp_to_gates(self, qlisp: list) -> tuple[list, list, list]:
        r"""
        Parse gate information from an input qlisp list.

        Args:
            qlisp (list): qlisp

        Returns:
            tuple[list, list, list]: A tuple containing:
                An gate information list.
                An qubit information list.
                An cbit information list.
        """
        new = []
        qubit_used = []
        cbit_used = []
        for gate_info in qlisp:
            gate = gate_info[0]
            if gate in ['X', 'Y', 'Z', 'S', 'T', 'H']:
                qubit0 = int(gate_info[1].split('Q')[1])
                new.append((gate.lower(), qubit0))
            elif gate in ['I']:
                qubit0 = int(gate_info[1].split('Q')[1])
                new.append(('id', qubit0))
            elif gate in ['-S','-T']:
                qubit0 = int(gate_info[1].split('Q')[1])
                new.append((gate[1].lower() + 'dg', qubit0))
            elif gate in ['sx']:
                qubit0 = int(gate_info[1].split('Q')[1])
                new.append((gate, qubit0))
            elif gate in ['-sx']:
                qubit0 = int(gate_info[1].split('Q')[1])
                new.append(('sxdg', qubit0))
            elif gate[0] in ['u3']:
                qubit0 = int(gate_info[1].split('Q')[1])
                new.append(('u', gate[1], gate[2], gate[3], qubit0))
        
            elif gate in ['Cnot']:
                qubit1 = int(gate_info[1][0].split('Q')[1])
                qubit2 = int(gate_info[1][1].split('Q')[1])
                new.append(('cx', qubit1, qubit2))
            elif gate in ['CY', 'CZ', 'SWAP']:
                qubit1 = int(gate_info[1][0].split('Q')[1])
                qubit2 = int(gate_info[1][1].split('Q')[1])
                new.append((gate.lower(), qubit1, qubit2))
            elif gate in ['iSWAP']:
                qubit1 = int(gate_info[1][0].split('Q')[1])
                qubit2 = int(gate_info[1][1].split('Q')[1])
                new.append(('iswap', qubit1, qubit2))
        
            elif gate[0] in ['Rx', 'Ry', 'Rz', 'P']:
                qubit0 = int(gate_info[1].split('Q')[1])
                new.append((gate[0].lower(), gate[1], qubit0))
            elif gate in ['Reset']:
                qubit0 = int(gate_info[1].split('Q')[1])
                new.append((gate.lower(), qubit0))
            elif gate in ['Barrier']:
                qubitn = [int(istr.split('Q')[1]) for istr in gate_info[1]]
                new.append((gate.lower(), tuple(qubitn)))
            elif gate[0] in ['Measure']:
                qubit0 = int(gate_info[1].split('Q')[1])
                cbit0 = gate[1]
                new.append((gate[0].lower(), [qubit0] ,[cbit0]))

            for var in ['qubit0','qubit1','qubit2']:
                try:
                    qubit_used.append(eval(var))
                except:
                    pass
            try:
                qubit_used += qubitn
            except:
                pass
            try:
                cbit_used.append(cbit0)
            except:
                pass
        
        return new, set(qubit_used), set(cbit_used)
        
    def _initialize_gates(self) -> tuple[list, list]:
        r"""
        Initialize a blank circuit.

        Returns:
            tuple[list,list]: A tuple containing:
                - A list of fake gates element.
                - A list of fake gates element list.
        """
        nlines = 2 * self.nqubits + 1 + len(str(self.ncbits))
        gates_element = list('— ' * self.nqubits) + ['═'] + [' '] * len(str(self.ncbits))
        gates_initial = copy.deepcopy(gates_element)
        for i in range(nlines):
            if i in range(0, 2 * self.nqubits, 2):
                qi = i // 2
                if len(str(qi)) == 1:
                    qn = f'q[{qi:<1}]  '
                elif len(str(qi)) == 2:
                    qn = f'q[{qi:<2}] '
                elif len(str(qi)) == 3:
                    qn = f'q[{qi:<3}]'
                gates_initial[i] = qn
            elif i in [2 * self.nqubits]:
                if len(str(self.ncbits)) == 1:
                    c = f'c:  {self.ncbits}/'
                elif len(str(self.ncbits)) == 2:
                    c = f'c: {self.ncbits}/'
                elif len(str(self.ncbits)) == 3:
                    c = f'c:{self.ncbits}/'
                gates_initial[i] = c
            else:
                gates_initial[i] = ' ' * 6   
        n = len(self.gates) + self.nqubits ## 
        gates_layerd = [gates_initial] + [copy.deepcopy(gates_element) for _ in range(n)]
        return gates_element,gates_layerd

    def _generate_gates_layerd_dense(self) -> list:
        r"""Assign gates to their respective layers.

        Returns:
            list: A list of dense gates element list.
        """
        # for count circuit depth
        # ignore barrier
        gates_element,gates_layerd = self._initialize_gates()
        for gate_info in self.gates:
            gate = gate_info[0]
            if gate in one_qubit_gates_avaliable.keys():
                pos0 = gate_info[1]
                for idx in range(len(gates_layerd)-1,-1,-1):
                    if (gates_layerd[idx][2*pos0] != '—' and gates_layerd[idx][2*pos0] != '│'):
                        gates_layerd[idx+1][2*pos0] = one_qubit_gates_avaliable[gate]
                        break
            elif gate in two_qubit_gates_avaliable.keys():
                pos0 = min(gate_info[1],gate_info[2])
                pos1 = max(gate_info[1],gate_info[2])
                for idx in range(len(gates_layerd)-1,-1,-1):
                    if (gates_layerd[idx][2*pos0] not in ['—','│'] or
                       gates_layerd[idx][2*pos1] not in ['—','│']):
                        if pos0 == gate_info[1]: # control qubit
                            gates_layerd[idx+1][2*pos0] = two_qubit_gates_avaliable[gate][0]
                            gates_layerd[idx+1][2*pos1] = two_qubit_gates_avaliable[gate][-1]
                        elif pos0 == gate_info[2]:
                            gates_layerd[idx+1][2*pos0] = two_qubit_gates_avaliable[gate][-1]
                            gates_layerd[idx+1][2*pos1] = two_qubit_gates_avaliable[gate][0]
                        break
            elif gate in one_qubit_parameter_gates_avaliable.keys():
                if gate == 'u':
                    theta0_str = is_multiple_of_pi(gate_info[1])
                    phi0_str = is_multiple_of_pi(gate_info[2])
                    lamda0_str = is_multiple_of_pi(gate_info[3])
                    pos0 = gate_info[-1]
                    for idx in range(len(gates_layerd)-1,-1,-1):
                        if (gates_layerd[idx][2*pos0] != '—' and gates_layerd[idx][2*pos0] != '│'):
                            params_str = '(' + theta0_str + ',' + phi0_str + ',' + lamda0_str + ')'
                            gates_layerd[idx+1][2*pos0] = one_qubit_parameter_gates_avaliable[gate] + params_str
                            break                    
                else:
                    theta0_str = is_multiple_of_pi(gate_info[1])
                    pos0 = gate_info[2]
                    for idx in range(len(gates_layerd)-1,-1,-1):
                        if (gates_layerd[idx][2*pos0] != '—' and gates_layerd[idx][2*pos0] != '│'):
                            gates_layerd[idx+1][2*pos0] = one_qubit_parameter_gates_avaliable[gate]+'('+theta0_str+')'
                            break
            elif gate in ['reset']:
                pos0 = gate_info[1]
                for idx in range(len(gates_layerd)-1,-1,-1):
                    if (gates_layerd[idx][2*pos0] != '—' and gates_layerd[idx][2*pos0] != '│'):
                        gates_layerd[idx+1][2*pos0] = functional_gates_avaliable[gate]
                        break
            elif gate in ['measure']:
                for j in range(len(gate_info[1])):
                    pos0 = gate_info[1][j]
                    pos1 = gate_info[2][j]
                    for idx in range(len(gates_layerd)-1,-1,-1):
                        if (gates_layerd[idx][2*pos0] != '—' and gates_layerd[idx][2*pos0] != '│'):
                            gates_layerd[idx+1][2*pos0] = functional_gates_avaliable[gate]
                            break
        
        for idx in range(len(gates_layerd)-1,-1,-1):
            if gates_layerd[idx] != gates_element:
                cut = idx + 1
                break
        return gates_layerd[:cut]
    
    @property
    def depth(self) -> int:
        r"""Count QuantumCircuit depth.

        Returns:
            int: QuantumCircuit depth.
        """
        dense_gates = self._generate_gates_layerd_dense()
        return len(dense_gates)-1
    
    def _generate_gates_layerd(self) -> list:
        r"""Assign gates to their respective layers loosely.

        Returns:
            list: A list of gates element list.
        """
        # according plot layer distributed gates
        gates_element,gates_layerd = self._initialize_gates()
        for gate_info in self.gates:
            gate = gate_info[0]
            if gate in one_qubit_gates_avaliable.keys():
                pos0 = gate_info[1]
                for idx in range(len(gates_layerd)-1,-1,-1):
                    if gates_layerd[idx][2*pos0] != '—':
                        gates_layerd[idx+1][2*pos0] = one_qubit_gates_avaliable[gate]
                        self.lines_use.append(2 * pos0)
                        self.lines_use.append(2 * pos0 + 1)
                        break
            elif gate in two_qubit_gates_avaliable.keys():
                pos0 = min(gate_info[1],gate_info[2])
                pos1 = max(gate_info[1],gate_info[2])
                for idx in range(len(gates_layerd)-1,-1,-1):
                    if gates_layerd[idx][2*pos0:2*pos1+1] != list('— ')*(pos1-pos0)+['—']:
                        if pos0 == gate_info[1]: # control qubit
                            gates_layerd[idx+1][2*pos0] = two_qubit_gates_avaliable[gate][0]
                            gates_layerd[idx+1][2*pos1] = two_qubit_gates_avaliable[gate][-1]
                            self.lines_use.append(2*pos0)
                            self.lines_use.append(2*pos0 + 1)
                            self.lines_use.append(2*pos1)
                            self.lines_use.append(2*pos1 + 1)
                        elif pos0 == gate_info[2]:
                            gates_layerd[idx+1][2*pos0] = two_qubit_gates_avaliable[gate][-1]
                            gates_layerd[idx+1][2*pos1] = two_qubit_gates_avaliable[gate][0]
                            self.lines_use.append(2*pos0)
                            self.lines_use.append(2*pos0 + 1)
                            self.lines_use.append(2*pos1)
                            self.lines_use.append(2*pos1 + 1)
                        for i in range(2*pos0+1,2*pos1):
                            gates_layerd[idx+1][i] = '│'
                        break
            elif gate in one_qubit_parameter_gates_avaliable.keys():
                if gate == 'u':
                    theta0_str = is_multiple_of_pi(gate_info[1])
                    phi0_str = is_multiple_of_pi(gate_info[2])
                    lamda0_str = is_multiple_of_pi(gate_info[3])
                    pos0 = gate_info[-1]
                    for idx in range(len(gates_layerd)-1,-1,-1):
                        if gates_layerd[idx][2*pos0] != '—':
                            params_str = '(' + theta0_str + ',' + phi0_str + ',' + lamda0_str + ')'
                            gates_layerd[idx+1][2*pos0] = one_qubit_parameter_gates_avaliable[gate] + params_str
                            self.lines_use.append(2*pos0)
                            self.lines_use.append(2*pos0 + 1)
                            break                    
                else:
                    theta0_str = is_multiple_of_pi(gate_info[1])
                    pos0 = gate_info[2]
                    for idx in range(len(gates_layerd)-1,-1,-1):
                        if gates_layerd[idx][2*pos0] != '—':
                            gates_layerd[idx+1][2*pos0] = one_qubit_parameter_gates_avaliable[gate]+'('+theta0_str+')'
                            self.lines_use.append(2*pos0)
                            self.lines_use.append(2*pos0 + 1)
                            break
                        
            elif gate in ['reset']:
                pos0 = gate_info[1]
                for idx in range(len(gates_layerd)-1,-1,-1):
                    if gates_layerd[idx][2*pos0] != '—':
                        gates_layerd[idx+1][2*pos0] = functional_gates_avaliable[gate]
                        self.lines_use.append(2 * pos0)
                        self.lines_use.append(2 * pos0 + 1)
                        break
            elif gate in ['barrier']:
                poslst0 = gate_info[1]
                poslst = []
                for j in poslst0:
                    if j + 1 in poslst0:
                        poslst.append(2*j)
                        poslst.append(2*j+1)
                    else:
                        poslst.append(2*j)
                for idx in range(len(gates_layerd)-1,-1,-1):
                    e_ = [gates_layerd[idx][2*i] for i in poslst0]
                    if all(e == '—' for e in e_) is False:
                        for i in poslst:
                            gates_layerd[idx+1][i] = functional_gates_avaliable[gate]
                        break
            elif gate in ['measure']:
                for j in range(len(gate_info[1])):
                    pos0 = gate_info[1][j]
                    pos1 = gate_info[2][j]
                    for idx in range(len(gates_layerd)-1,-1,-1):
                        if gates_layerd[idx][2*pos0:] != gates_element[2*pos0:]:
                            gates_layerd[idx+1][2*pos0] = functional_gates_avaliable[gate]
                            self.lines_use.append(2*pos0)
                            self.lines_use.append(2*pos0 + 1)
                            for i in range(2*pos0+1,2*self.nqubits,1):
                                gates_layerd[idx+1][i] = '│'
                            for i in range(2*self.nqubits+1, 2*self.nqubits+1+len(str(pos1))):
                                gates_layerd[idx+1][i] = str(pos1)[i-2*self.nqubits-1]
                            break
        for idx in range(len(gates_layerd)-1,-1,-1):
            if gates_layerd[idx] != gates_element:
                cut = idx + 1
                break
        return gates_layerd[:cut]
        
    def _format_gates_layerd(self) -> list:
        r"""Unify the width of each layer's gate strings

        Returns:
            list: A new list of gates element list.
        """
        gates_layerd = self._generate_gates_layerd()
        gates_layerd_format = [gates_layerd[0]]
        for lst in gates_layerd[1:]:
            max_length = max(len(item) for item in lst)
            if max_length == 1:
                gates_layerd_format.append(lst)
            else:
                if max_length % 2 == 0:
                    max_length += 1
                dif0 = max_length // 2
                for idx in range(len(lst)):
                    if len(lst[idx]) == 1:
                        if idx < 2 * self.nqubits:
                            if idx % 2 == 0:
                                lst[idx] = '—' * dif0 + lst[idx] + '—' * dif0
                            else:
                                lst[idx] = ' ' * dif0 + lst[idx] + ' ' * dif0
                        elif idx == 2 * self.nqubits:
                            lst[idx] = '═' * dif0 + lst[idx] + '═' * dif0
                        else:
                            lst[idx] = ' ' * dif0 + lst[idx] + ' ' * dif0
                    else:
                        dif1 = max_length - len(lst[idx])
                        lst[idx] = lst[idx] + '—' * dif1
                gates_layerd_format.append(lst)
        return gates_layerd_format
    
    def _add_gates_to_lines(self, width: int = 4) -> list:
        r"""Add gates to lines.

        Args:
            width (int, optional): The width between gates. Defaults to 4.

        Returns:
            list: A list of lines.
        """
        gates_layerd_format = self._format_gates_layerd()
        nl = len(gates_layerd_format[0])
        lines1 = [str() for _ in range(nl)]
        for i in range(nl):
            for j in range(len(gates_layerd_format)):
                if i < 2 * self.nqubits:
                    if i % 2 == 0:
                        lines1[i] += gates_layerd_format[j][i] + '—' * width
                    else:
                        lines1[i] += gates_layerd_format[j][i] + ' ' * width
                elif i == 2 * self.nqubits:
                    lines1[i] += gates_layerd_format[j][i] + '═' * width
                elif i > 2 * self.nqubits:
                    lines1[i] += gates_layerd_format[j][i] + ' ' * width
        return lines1 
        
    def draw(self, width: int = 4) -> None:
        r"""
        Draw the quantum circuit.

        Args:
            width (int, optional): The width between gates. Defaults to 4.
        """
        lines1 = self._add_gates_to_lines(width) 
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
        lines1 = self._add_gates_to_lines(width)

        fline = str()
        for idx in range(2 * self.nqubits):
            if idx in self.lines_use:
                fline += '\n'
                fline += lines1[idx]
        for idx in range(2 * self.nqubits, len(lines1)):
            fline += '\n'
            fline += lines1[idx]
            
        formatted_string = fline.replace("\n", "<br>").replace(" ", "&nbsp;")
        html_content = f'<div style="overflow-x: auto; white-space: nowrap; font-family: consolas;">{formatted_string}</div>'
        display(HTML(html_content))