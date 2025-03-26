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

r"""Some common decomposition methods for two-qubit and three-qubit gates."""

import numpy as np
from typing import Literal
from .utils import u3_decompose
from .matrix import u_mat
from .quantumcircuit import QuantumCircuit
from .basepasses import TranspilerPass

def u_dot_u(u_info1: tuple, u_info2: tuple) -> tuple:
    """Carry out u @ u and return a new u information

    Args:
        u_info1 (tuple): u gate information like ('u', 1.5707963267948966, 0.0, 3.141592653589793, 0)
        u_info2 (tuple): u gate information like ('u', 1.5707963267948966, 0.0, 3.141592653589793, 0)

    Returns:
        tuple: A new u gate information
    """
    assert(u_info1[-1] == u_info2[-1])
    u_mat1 = u_mat(*u_info1[1:-1])
    u_mat2 = u_mat(*u_info2[1:-1])
    
    new_u = u_mat2 @ u_mat1
    theta, phi, lamda, _ = u3_decompose(new_u)
    return ('u', theta, phi, lamda, u_info1[-1])

def h2u(qubit: int) -> tuple:
    """Convert H gate to U3 gate tuple.

    Args:
        qubit (int): The qubit to apply the gate to.

    Returns:
        tuple: u3 gate information.
    """
    return ('u', np.pi/2, 0.0, np.pi, qubit)

def x2u(qubit: int) -> tuple:
    """Convert X gate to U3 gate tuple.

    Args:
        qubit (int): The qubit to apply the gate to.

    Returns:
        tuple: u3 gate information.
    """
    return ('u', np.pi, np.pi/2, -np.pi/2, qubit)

def sdg2u(qubit:int) -> tuple:
    """Convert sdg gate to U3 gate tuple.

    Args:
        qubit (int): The qubit to apply the gate to.

    Returns:
        tuple: u3 gate information.
    """
    return ('u', 0.0, -0.7853981633974483, -0.7853981633974483, qubit)

def s2u(qubit: int) -> tuple:
    """Convert S gate to U3 gate tuple.

    Args:
        qubit (int): The qubit to apply the gate to.

    Returns:
        tuple: u3 gate information.
    """
    return ('u', 0.0, 0.7853981633974483, 0.7853981633974483, qubit)

def rx2u(theta:float,qubit:int) -> tuple:
    """Convert RX gate to U3 gate tuple.

    Args:
        qubit (int): The qubit to apply the gate to.

    Returns:
        tuple: u3 gate information.
    """
    return ('u',theta,-np.pi/2,np.pi/2,qubit)

def ry2u(theta:float,qubit:int) -> tuple:
    """Convert RY gate to U3 gate tuple.

    Args:
        qubit (int): The qubit to apply the gate to.

    Returns:
        tuple: u3 gate information.
    """
    return ('u',theta,0.0,0.0,qubit)

def rz2u(theta:float,qubit:int) -> tuple:
    """Convert RZ gate to U3 gate tuple.

    Args:
        qubit (int): The qubit to apply the gate to.

    Returns:
        tuple: u3 gate information.
    """
    return ('u',0.0,0.0,theta,qubit)

def cx_decompose(control_qubit: int, target_qubit: int,convert_single_qubit_gate_to_u:bool,two_qubit_gate_basis:Literal['cx','cz']) -> list:
    """ Decompose CX gate to U3 gates and CZ gates.

    Args:
        control_qubit (int): The qubit used as control.
        target_qubit (int): The qubit targeted by the gate.

    Returns:
        list: A list of U3 gates and CZ gates.
    """
    gates = []
    if two_qubit_gate_basis == 'cz':
        if convert_single_qubit_gate_to_u:
            gates.append(h2u(target_qubit))
        else:
            gates.append(('h',target_qubit))
        gates.append(('cz', control_qubit, target_qubit))
        if convert_single_qubit_gate_to_u:
            gates.append(h2u(target_qubit))
        else:
            gates.append(('h',target_qubit))
    elif two_qubit_gate_basis == 'cx':
        gates.append(('cx',control_qubit,target_qubit))
    return gates

def cy_decompose(control_qubit: int, target_qubit: int, convert_single_qubit_gate_to_u:bool, two_qubit_gate_basis:Literal['cz','cx']) -> list:
    """ Decompose CY gate with kak algorithm. 

    Args:
        control_qubit (int): The qubit used as control.
        target_qubit (int): The qubit targeted by the gate.

    Returns:
        list: A list of U3 gates and CZ gates.
    """

    gates = []
    if convert_single_qubit_gate_to_u:
        gates.append(sdg2u(target_qubit))
    else:
        gates.append(('sdg',target_qubit))
    
    if two_qubit_gate_basis == 'cz':
        gates += cx_decompose(control_qubit,target_qubit,convert_single_qubit_gate_to_u,two_qubit_gate_basis)
    elif two_qubit_gate_basis == 'cx':
        gates.append(('cx',control_qubit,target_qubit))

    if convert_single_qubit_gate_to_u:
        gates.append(s2u(target_qubit))
    else:
        gates.append(('s',target_qubit))
    return gates

def swap_decompose(qubit1: int, qubit2: int, convert_single_qubit_gate_to_u:bool, two_qubit_gate_basis:Literal['cz','cx']) -> list:
    """Decompose SWAP gate to U3 gates and CZ gates.

    Args:
        qubit1 (int): The first qubit to apply the gate to.
        qubit2 (int): The second qubit to apply the gate to.

    Returns:
        list: A list of U3 gates and CZ gates.
    """
    if two_qubit_gate_basis == 'cz':
        gates = []
        if convert_single_qubit_gate_to_u:
            gates.append(h2u(qubit2))
        else:
            gates.append(('h',qubit2))
        gates.append(('cz',qubit1,qubit2))
        if convert_single_qubit_gate_to_u:
            gates.append(h2u(qubit2))
            gates.append(h2u(qubit1))
        else:
            gates.append(('h',qubit2))
            gates.append(('h',qubit1))
        gates.append(('cz',qubit1,qubit2))
        if convert_single_qubit_gate_to_u:
            gates.append(h2u(qubit1))
            gates.append(h2u(qubit2))
        else:
            gates.append(('h',qubit1))
            gates.append(('h',qubit2))
        gates.append(('cz',qubit1,qubit2))
        if convert_single_qubit_gate_to_u:
            gates.append(h2u(qubit2))
        else:
            gates.append(('h',qubit2))
    elif two_qubit_gate_basis == 'cx':
        gates = []
        gates.append(('cx',qubit1,qubit2))
        gates.append(('cx',qubit2,qubit1))
        gates.append(('cx',qubit1,qubit2))
    return gates

def iswap_decompose(qubit1: int, qubit2: int, convert_single_qubit_gate_to_u:bool, two_qubit_gate_basis:Literal['cz','cx']) -> list:
    """ Decompose iswap gate with qiskit decompose algorithm. 

    Args:
        qubit1 (int): The first qubit to apply the gate to.
        qubit2 (int): The second qubit to apply the gate to.

    Returns:
        list: A list of U3 gates and CZ gates.
    """
    # iswap = R_{XX+YY}(-pi/2) = e^{i*pi/4*(X\otimesX + Y\otimesY)}
    gates = []
    if convert_single_qubit_gate_to_u:
        gates.append(x2u(qubit1))
        gates.append(rx2u(np.pi/2,qubit1))
        gates.append(rx2u(-np.pi/2,qubit2))
    else:
        gates.append(('x', qubit1))
        gates.append(('rx', np.pi/2, qubit1))
        gates.append(('rx',-np.pi/2, qubit2))
    
    if two_qubit_gate_basis == 'cx':
        gates.append(('cx',  qubit1, qubit2))
    elif two_qubit_gate_basis == 'cz':
        gates += cx_decompose(qubit1, qubit2, convert_single_qubit_gate_to_u,two_qubit_gate_basis)

    if convert_single_qubit_gate_to_u:
        gates.append(rx2u(-np.pi/2,qubit1))
        gates.append(rz2u(-np.pi/2,qubit2))
    else:
        gates.append(('rx',-np.pi/2, qubit1))
        gates.append(('rz',-np.pi/2, qubit2)) 

    if two_qubit_gate_basis == 'cx':
        gates.append(('cx',  qubit1, qubit2))
    elif two_qubit_gate_basis == 'cz':
        gates += cx_decompose(qubit1, qubit2, convert_single_qubit_gate_to_u,two_qubit_gate_basis)
    
    if convert_single_qubit_gate_to_u:
        gates.append(rx2u(-np.pi/2, qubit1))
        gates.append(rx2u(np.pi/2, qubit2))
        gates.append(x2u(qubit1))
    else:
        gates.append(('rx',-np.pi/2, qubit1))
        gates.append(('rx', np.pi/2, qubit2))
        gates.append(('x', qubit1))
    return gates

def rxx_decompose(theta:float,qubit1:int,qubit2:int,convert_single_qubit_gate_to_u:bool, two_qubit_gate_basis:Literal['cz','cx']) -> list:
    """Decompose RXX gate to U3 gates and CZ gates.

    Args:
        theta (float): The rotation angle of the gate.
        qubit1 (int): The first qubit to apply the gate to.
        qubit2 (int): The second qubit to apply the gate to.

    Returns:
        list: A list of U3 gates and CZ gates.
    """
    gates = []
    if convert_single_qubit_gate_to_u:
        gates.append(h2u(qubit1))
        gates.append(h2u(qubit2))
    else:
        gates.append(('h', qubit1))
        gates.append(('h', qubit2))
    if two_qubit_gate_basis == 'cx':
        gates.append(('cx',qubit1,qubit2))
    elif two_qubit_gate_basis == 'cz':        
        gates += cx_decompose(qubit1,qubit2,convert_single_qubit_gate_to_u,two_qubit_gate_basis)
    if convert_single_qubit_gate_to_u:
        gates.append(rz2u(theta,qubit2))
    else:
        gates.append(('rz', theta, qubit2))
    if two_qubit_gate_basis == 'cx':
        gates.append(('cx',qubit1,qubit2))
    elif two_qubit_gate_basis == 'cz':        
        gates += cx_decompose(qubit1,qubit2,convert_single_qubit_gate_to_u,two_qubit_gate_basis)
    if convert_single_qubit_gate_to_u:  
        gates.append(h2u(qubit1))
        gates.append(h2u(qubit2))
    else:
        gates.append(('h', qubit1))
        gates.append(('h', qubit2))      
    return gates

def ryy_decompose(theta:float, qubit1:int, qubit2:int, convert_single_qubit_gate_to_u:bool, two_qubit_gate_basis:Literal['cz','cx']) -> list:
    """Decompose RYY gate to U3 gates and CZ gates.

    Args:
        theta (float): The rotation angle of the gate.
        qubit1 (int): The first qubit to apply the gate to.
        qubit2 (int): The second qubit to apply the gate to.

    Returns:
        list: A list of U3 gates and CZ gates.
    """
    gates = []
    if convert_single_qubit_gate_to_u:
        gates.append(rx2u(np.pi/2,qubit1))
        gates.append(rx2u(np.pi/2,qubit2))
    else:
        gates.append(('rx',np.pi/2,qubit1))
        gates.append(('rx',np.pi/2,qubit2))     
    if two_qubit_gate_basis == 'cx':
        gates.append(('cx', qubit1, qubit2))
    elif two_qubit_gate_basis == 'cz':
        gates += cx_decompose(qubit1,qubit2,convert_single_qubit_gate_to_u,two_qubit_gate_basis)
    if convert_single_qubit_gate_to_u:
        gates.append(rz2u(theta,qubit2))
    else:
        gates.append(('rz', theta, qubit2))
    if two_qubit_gate_basis == 'cx':
        gates.append(('cx', qubit1, qubit2))
    elif two_qubit_gate_basis == 'cz':
        gates += cx_decompose(qubit1,qubit2,convert_single_qubit_gate_to_u,two_qubit_gate_basis)
    if convert_single_qubit_gate_to_u:
        gates.append(rx2u(-np.pi/2,qubit1))
        gates.append(rx2u(-np.pi/2,qubit2))
    else:
        gates.append(('rx', -np.pi/2, qubit1))
        gates.append(('rx', -np.pi/2, qubit2))    
    return gates

def rzz_decompose(theta:float, qubit1:int, qubit2:int, convert_single_qubit_gate_to_u:bool, two_qubit_gate_basis:Literal['cz','cx']) -> list:
    """Decompose RZZ gate to U3 gates and CZ gates.

    Args:
        theta (float): The rotation angle of the gate.
        qubit1 (int): The first qubit to apply the gate to.
        qubit2 (int): The second qubit to apply the gate to.

    Returns:
        list: A list of U3 gates and CZ gates.
    """ 
    gates = []
    if two_qubit_gate_basis == 'cx':
        gates.append(('cx', qubit1, qubit2))
    elif two_qubit_gate_basis == 'cz':
        gates += cx_decompose(qubit1,qubit2,convert_single_qubit_gate_to_u,two_qubit_gate_basis)
    if convert_single_qubit_gate_to_u:
        gates.append(rz2u(theta,qubit2))
    else:
        gates.append(('rz', theta, qubit2))
    if two_qubit_gate_basis == 'cx':
        gates.append(('cx', qubit1, qubit2))
    elif two_qubit_gate_basis == 'cz':
        gates += cx_decompose(qubit1,qubit2,convert_single_qubit_gate_to_u,two_qubit_gate_basis)  
    return gates

def ccx_decompose(control_qubit1: int, control_qubit2: int, target_qubit: int,):
    """Decompose ccx gate. Reference: A biological sequence comparison algorithm using quantum computers

    Args:
        control_qubit1 (int): The qubit used as the first control.
        control_qubit2 (int): The qubit used as the second control.
        target_qubit (int): The qubit targeted by the gate.

    Returns:
        list: A list of single- and two-qubit gates.
    """
    gates = [
        ('h',target_qubit),
        ('cx',control_qubit2,target_qubit),
        ('tdg',target_qubit),
        ('cx',control_qubit1,target_qubit),
        ('t',target_qubit),
        ('cx',control_qubit2,target_qubit),
        ('t',control_qubit2),
        ('tdg',target_qubit),
        ('cx',control_qubit1,target_qubit),
        ('cx',control_qubit1,control_qubit2),
        ('t',target_qubit),
        ('t',control_qubit1),
        ('tdg',control_qubit2),
        ('h',target_qubit),
        ('cx',control_qubit1,control_qubit2),
    ]
    return gates

def cswap_decompose(control_qubit1: int, control_qubit2: int, target_qubit: int,):
    """Decompose cswap gate. Reference: http://threeplusone.com/gates

    Args:
        control_qubit1 (int): The qubit used as the first control.
        control_qubit2 (int): The qubit used as the second control.
        target_qubit (int): The qubit targeted by the gate.

    Returns:
        list: A list of single- and two-qubit gates.
    """
    gates = [
        ('cx',target_qubit,control_qubit2),
        ('h',target_qubit),
        ('cx',control_qubit2,target_qubit),
        ('tdg',target_qubit),
        ('cx',control_qubit1,target_qubit),
        ('t',target_qubit),
        ('cx',control_qubit2,target_qubit),
        ('t',control_qubit2),
        ('tdg',target_qubit),
        ('cx',control_qubit1,target_qubit),
        ('cx',control_qubit1,control_qubit2),
        ('t',target_qubit),
        ('t',control_qubit1),
        ('tdg',control_qubit2),
        ('h',target_qubit),
        ('cx',control_qubit1,control_qubit2),
        ('cx',target_qubit,control_qubit2),
    ]
    return gates

def ccz_decompose(control_qubit1: int, control_qubit2: int, target_qubit: int,):
    """Decompose ccz gate. Reference: http://threeplusone.com/gates

    Args:
        control_qubit1 (int): The qubit used as the first control.
        control_qubit2 (int): The qubit used as the second control.
        target_qubit (int): The qubit targeted by the gate.

    Returns:
        list: A list of single- and two-qubit gates.
    """
    gates = [
        ('cx',control_qubit2,target_qubit),
        ('tdg',target_qubit),
        ('cx',control_qubit1,target_qubit),
        ('t',target_qubit),
        ('cx',control_qubit2,target_qubit),
        ('t',control_qubit2),
        ('tdg',target_qubit),
        ('cx',control_qubit1,target_qubit),
        ('cx',control_qubit1,control_qubit2),
        ('t',target_qubit),
        ('t',control_qubit1),
        ('tdg',control_qubit2),
        ('h',target_qubit),
        ('cx',control_qubit1,control_qubit2),
        ('h',target_qubit)
    ]
    return gates

class ThreeQubitGateDecompose(TranspilerPass):
    """A transpiler pass that decomposes three-qubit gates into combinations of single- and two-qubit gates.
    """
    def __init__(self):
        super().__init__()

    def run(self,qc:QuantumCircuit):
        """Decompose three-qubit gates in the quantum circuit into sequences of single- and two-qubit gates.

        Args:
            qc (QuantumCircuit): The quantum circuit to process.

        Returns:
            QuantumCircuit: A new quantum circuit with all three-qubit gates decomposed into single- and two-qubit gates.
        """
        new = []
        for gate_info in qc.gates:
            if gate_info[0] == 'ccx':
                new += ccx_decompose(*gate_info[1:])
            elif gate_info[0] == 'ccz':
                new += ccz_decompose(*gate_info[1:])
            elif gate_info[0] == 'cswap':
                new += cswap_decompose(*gate_info[1:])
            else:
                new.append(gate_info)
        new_qc = qc.deepcopy()
        new_qc.gates = new
        return new_qc