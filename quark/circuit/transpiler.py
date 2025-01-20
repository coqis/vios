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

import copy
import numpy as np
import networkx as nx
from .quantumcircuit import QuantumCircuit
from .quantumcircuit_helpers import (
                      one_qubit_gates_available,
                      two_qubit_gates_available,
                      one_qubit_parameter_gates_available,
                      two_qubit_parameter_gates_available,
                      functional_gates_available)
from .matrix import gate_matrix_dict, u_mat, id_mat
from .routing_helpers import (map_gates_to_physical_qubits_layout,
                              basic_routing_gates,
                              gates_sabre_routing,
                              )
from .decompose_helpers import (cx_decompose,
                                cy_decompose,
                                swap_decompose,
                                iswap_decompose,
                                rxx_decompose,
                                ryy_decompose,
                                rzz_decompose,
                                u_dot_u)
from .utils import u3_decompose
from .backend import Backend
from .layout_helpers import Layout

class Transpiler:
    r"""The transpilation process involves converting the operations
    in the circuit to those supported by the device and swapping
    qubits (via swap gates) within the circuit to overcome limited
    qubit connectivity.
    """
    def __init__(self, qc: QuantumCircuit | str | list, chip_backend: Backend|None = None):
        
        r"""Obtain basic information from input quantum circuit.

        Args:
            qc (QuantumCircuit | str | list): The quantum circuit to be transpiled. Can be a QuantumCircuit object or OpenQASM 2.0 str or qlisp list.

            chip_backend (Backend): An instance of the Backend class that contains the information about the quantum chip to be used for layout selection. Defaults to None

        Raises:
            TypeError: The quantum circuit format is incorrect.
        """

        if isinstance(qc, QuantumCircuit):
            self.gates = copy.deepcopy(qc.gates)
            self.nqubits_used = len(qc.qubits) #qc.nqubits
            self.ncbits_used = qc.ncbits
            self.params_value = qc.params_value
        elif isinstance(qc, str):
            qc_str = qc
            qc = QuantumCircuit()
            qc.from_openqasm2(qc_str)
            self.gates = qc.gates
            self.nqubits_used = qc.nqubits
            self.ncbits_used = qc.ncbits
            self.params_value = qc.params_value
        elif isinstance(qc, list):
            qc_list = qc
            qc = QuantumCircuit()
            qc.from_qlisp(qc_list)
            self.gates = qc.gates
            self.nqubits_used = len(qc.qubits) #qc.nqubits
            self.ncbits_used = qc.ncbits
            self.params_value = qc.params_value
        else:
            raise TypeError("Expected a Quark QuantumCircuit or OpenQASM 2.0 or qlisp, but got a {}.".format(type(qc)))
        
        self.source_gates = copy.deepcopy(self.gates)

        self.chip_backend = chip_backend
        self.source_qubits = copy.deepcopy(qc.qubits)
        self.initial_mapping = copy.deepcopy(qc.qubits)
        self.coupling_map = [(self.initial_mapping[i],self.initial_mapping[i+1]) for i in range(len(self.initial_mapping)-1)]
        self.largest_qubits_index = max(self.initial_mapping) + 1

    def _select_layout(self,use_priority: bool = True, initial_mapping: list|dict = {'key':'fidelity_var','topology':'linear1'}):
        # select layout from the Backend! update initial_mapping, coupling_map, largest_qubits_index
        if self.chip_backend is None:
            raise(TypeError('Please specify a Backend, otherwise a layout cannot be selected!'))
        if len(self.source_qubits) >1:
            self.initial_mapping,self.coupling_map = Layout(self.nqubits_used,self.chip_backend).selected_layout(
                use_priority=use_priority,
                initial_mapping=initial_mapping,
                )
            self.largest_qubits_index = max(self.initial_mapping) + 1
            subgraph = self.chip_backend.graph.subgraph(self.initial_mapping)
            subgraph_fidelity = np.array([data['fidelity'] for _, _, data in subgraph.edges(data=True)])
            fidelity_mean = np.mean(subgraph_fidelity)
            fidelity_var  = np.var(subgraph_fidelity)  
            print('The average fidelity of the coupler(s) between the selected qubits is {}, and the variance of the fidelity is {}'.format(fidelity_mean,fidelity_var))
        return self 
    
    def run_select_layout(self, use_priority: bool = True, initial_mapping: list|dict = {'key':'fidelity_var','topology':'linear1'}):
        """
        Selects the quantum circuit layout and performs transpiling based on the provided mapping and coupling configuration.
    
        Args:
            use_priority (bool, optional): Whether to use qubits recommended by the backend. Defaults to True. 
                If set to False, transpilation will be performed based on the provided `initial_mapping` and `coupling_map`.

            initial_mapping (list | None, optional): A list representing the mapping of virtual qubits to physical qubits. 
                The ith element corresponds to the physical qubit that maps to the ith virtual qubit.
                
            coupling_map (list[tuple] | None, optional): A list of tuples representing the coupling between physical qubits. 
                If `use_priority` is set to False, and both `initial_mapping` and `coupling_map` are provided, transpilation 
                will proceed based on these parameters.
    
        Returns:
            QuantumCircuit: A quantum circuit with the selected layout and transpiled gates.
        """
        self._select_layout(use_priority = use_priority, initial_mapping = initial_mapping)
        initial_mapping_dic = dict(zip(self.source_qubits,self.initial_mapping))
        self.gates = map_gates_to_physical_qubits_layout(self.source_gates,initial_mapping_dic)
        qc = QuantumCircuit(self.largest_qubits_index,self.ncbits_used)
        qc.gates = self.gates
        qc.qubits = self.initial_mapping
        qc.params_value = self.params_value
        qc.physical_qubits_espression = True
        #if self.chip_backend is not None:
        #    if self.chip_backend.chip_name == 'Haituo':
        #        qc.adjust_index(132)
        #        print(f'Tip: When setting Haituo chip as backend, the quibit index starts at 132.')
        #    elif self.chip_backend.chip_name == 'Dongling1':
        #        qc.adjust_index(106)
        #        print(f'Tip: When setting Dongling chip as backend, the quibit index starts at 106.')
        return qc
        
    def _basic_routing(self):
        """Routing based on the initial mapping.

        Returns:
            Transpiler: Update self information.
        """
        self.gates = basic_routing_gates(self.source_gates,self.source_qubits,self.initial_mapping,self.coupling_map)
        return self

    def run_basic_routing(self):
        """Routing based on the initial mapping.

        Returns:
            QuantumCircuit: The updated quantum circuit with swap gates applied.
        """
        self._basic_routing()
        print('check',self.initial_mapping,self.coupling_map)
        qc = QuantumCircuit(self.largest_qubits_index,self.ncbits_used)
        qc.gates = self.gates
        qc.qubits = self.initial_mapping
        qc.params_value = self.params_value
        qc.physical_qubits_espression = True
        #if self.chip_backend is not None:
        #    if self.chip_backend.chip_name == 'Haituo':
        #        qc.adjust_index(132)
        #        print(f'Tip: When setting Haituo chip as backend, the quibit index starts at 132.')
        #    elif self.chip_backend.chip_name == 'Dongling':
        #        qc.adjust_index(106)
        #        print(f'Tip: When setting Dongling chip as backend, the quibit index starts at 106.')
        return qc 
    
    def _sabre_routing(self, iterations: int = 5):
        """Routing based on the Sabre algorithm.
        Args:
            iterations (int, optional): The number of iterations. Defaults to 1.

        Returns:
            Transpiler: Update self information.
        """
        self.gates,self.initial_mapping = gates_sabre_routing(self.source_gates,
                                                              self.source_qubits,
                                                              self.initial_mapping,
                                                              self.coupling_map,
                                                              self.largest_qubits_index,
                                                              self.ncbits_used,
                                                              iterations=iterations,
                                                              )

        return self

    def run_sabre_routing(self, iterations: int = 5) -> QuantumCircuit:
        """Routing based on the initial mapping.

        Args:
            iterations (int, optional): The number of iterations. Defaults to 1.

        Returns:
            QuantumCircuit: The updated quantum circuit with swap gates applied.
        """
        assert(iterations % 2 == 1)
        self._sabre_routing(iterations = iterations)
        qc = QuantumCircuit(self.largest_qubits_index,self.ncbits_used)
        qc.gates = self.gates
        qc.qubits = self.initial_mapping
        qc.params_value = self.params_value
        qc.physical_qubits_espression = True
        #if self.chip_backend is not None:
        #    if self.chip_backend.chip_name == 'Haituo':
        #        qc.adjust_index(132)
        #        print(f'Tip: When setting Haituo chip as backend, the quibit index starts at 132.')
        #    elif self.chip_backend.chip_name == 'Dongling1':
        #        qc.adjust_index(106)
        #        print(f'Tip: When setting Dongling chip as backend, the quibit index starts at 106.')
        return qc

    def _basic_gates(self) -> 'Transpiler':
        r"""Convert all gates in the quantum circuit to basic gates.

        Returns:
            Transpiler: Update self information.
        """
        new = []
        for gate_info in self.gates:
            gate = gate_info[0]
            if gate in one_qubit_gates_available.keys():
                gate_matrix = gate_matrix_dict[gate]
                theta,phi,lamda,_ = u3_decompose(gate_matrix)
                new.append(('u',theta,phi,lamda,gate_info[-1]))
            elif gate in one_qubit_parameter_gates_available.keys():
                if gate == 'u':
                    new.append(gate_info)
                elif gate == 'r':
                    theta,phi,qubit = gate_info[1:]
                    new.append(('u',theta,phi-np.pi/2,np.pi/2-phi,qubit))
                else:
                    gate_matrix = gate_matrix_dict[gate](*gate_info[1:-1])
                    theta,phi,lamda,_ = u3_decompose(gate_matrix)
                    new.append(('u',theta,phi,lamda,gate_info[-1]))
            elif gate in two_qubit_gates_available.keys():
                if gate in ['cz']:
                    new.append(gate_info)
                elif gate in ['cx', 'cnot']:
                    _cx = cx_decompose(gate_info[1],gate_info[2])
                    new += _cx
                elif gate in ['swap']:
                    _swap = swap_decompose(gate_info[1],gate_info[2])
                    new += _swap
                elif gate in ['iswap']:
                    _iswap = iswap_decompose(gate_info[1], gate_info[2])
                    new += _iswap
                elif gate in ['cy']:
                    _cy = cy_decompose(gate_info[1], gate_info[2])
                    new += _cy
                else:
                    raise(TypeError(f'Input {gate} gate is not support now. Try kak please'))       
            elif gate in two_qubit_parameter_gates_available.keys():
                if gate == 'rxx':
                    new += rxx_decompose(*gate_info[1:])
                elif gate == 'ryy':
                    new += ryy_decompose(*gate_info[1:])
                elif gate == 'rzz':
                    new += rzz_decompose(*gate_info[1:])
            elif gate in functional_gates_available.keys():
                new.append(gate_info)
            else:
                raise(TypeError(f'Input {gate} gate is not support to basic gates now.'))
        self.gates = new
        print('Mapping to basic gates done !')
        return self
                          
    def run_basic_gates(self) -> 'QuantumCircuit':
        r"""
        Convert all gates in the quantum circuit to basic gates, in order to make it executable on hardware.

        Returns:
            QuantumCircuit: The updated quantum circuit with baisc gates.
        """
        self._basic_gates()
        qc =  QuantumCircuit(self.largest_qubits_index, self.ncbits_used)
        qc.gates = self.gates
        qc.qubits = self.initial_mapping
        qc.physical_qubits_espression = True
        #if self.chip_backend is not None:
        #    if self.chip_backend.chip_name == 'Haituo':
        #        qc.adjust_index(132)
        #        print(f'Tip: When setting Haituo chip as backend, the quibit index starts at 132.')
        #    elif self.chip_backend.chip_name == 'Dongling1':
        #        qc.adjust_index(106)
        #        print(f'Tip: When setting Dongling chip as backend, the quibit index starts at 106.')
        return qc

    def _gate_optimize(self) -> 'Transpiler':
        """
        Optimizes the quantum circuit by merging adjacent U3 gates and removing adjacent CZ gates.

        This function scans the given quantum circuit and performs the following optimizations:
    
        1. Merging adjacent U3 gates: If two consecutive U3 gates act on the same qubit, they are merged into a single     U3 gate. If the resulting U3 gate is equivalent to the identity matrix (i.e., performs no operation), it will be     removed from the circuit.
        
        2. Removing adjacent CZ gates: If two consecutive CZ gates act on the same pair of qubits, they cancel each     other out and are both removed from the circuit.

        Returns:
            Transpiler: Update self information.
        """
        n = len(self.gates)
        ops = [[('@',)]+[('O',) for _ in range(n)] for _ in range(self.largest_qubits_index)]
        for gate_info in self.gates:
            gate = gate_info[0]
            if gate == 'u':
                if np.allclose(u_mat(*gate_info[1:-1]),id_mat) is False:
                    for idx in range(n-1,-1,-1):
                        if ops[gate_info[4]][idx] not in [('O',)]:
                            if ops[gate_info[4]][idx][0] == 'u':
                                uu_info = u_dot_u(ops[gate_info[4]][idx],gate_info)
                                if np.allclose(u_mat(*uu_info[1:-1]),id_mat) is False:
                                    ops[gate_info[4]][idx] = uu_info
                                else:
                                    ops[gate_info[4]][idx] = ('O',)
                            else:
                                ops[gate_info[4]][idx+1] = gate_info
                            break
            elif gate == 'cz':
                contrl_qubit = gate_info[1]
                target_qubit = gate_info[2]
                for idx in range(n-1,-1,-1):
                    if ops[contrl_qubit][idx] not in [('O',)] or ops[target_qubit][idx] not in [('O',)]:
                        trans_gate_info = (gate,target_qubit,contrl_qubit)
                        if ops[contrl_qubit][idx] in [('V',)] and ops[target_qubit][idx] in [gate_info,trans_gate_info]:
                            ops[contrl_qubit][idx] = ('O',)
                            ops[target_qubit][idx] = ('O',)
                            break
                        elif ops[contrl_qubit][idx] in [gate_info,trans_gate_info] and ops[target_qubit][idx] in [('V',)]:
                            ops[contrl_qubit][idx] = ('O',)
                            ops[target_qubit][idx] = ('O',)
                            break
                        else:
                            ops[contrl_qubit][idx+1] = gate_info
                            ops[target_qubit][idx+1] = ('V',)
                            break                            
            elif gate == 'barrier':
                for idx in range(n-1,-1,-1):
                    e_ = [ops[pos][idx] for pos in gate_info[1]]
                    if all(e == ('O',) for e in e_) is False:
                        for jdx, pos in enumerate(gate_info[1]):
                            if jdx == 0:
                                ops[pos][idx+1] = gate_info
                            else:
                                ops[pos][idx+1]= ('V',)
                        break
            elif gate == 'reset':
                for idx in range(n-1,-1,-1):
                    if ops[gate_info[1]][idx] not in [('O',)]:
                        ops[gate_info[1]][idx+1] = gate_info
                        break
            elif gate == 'measure':
                for jdx,pos in enumerate(gate_info[1]):
                    for idx in range(n-1,-1,-1):
                        if ops[pos][idx] not in [('O',)]:
                            ops[pos][idx+1] = ('measure', [pos], [gate_info[2][jdx]])
                            break
            else:
                raise(TypeError(f'Only u and cz gate and functional gates are supported! Input {gate}'))              

        for idx in range(n,-1,-1):
            e_ = [ops[jdx][idx] for jdx in range(len(ops))]
            if all(e == ('O',) for e in e_) is False:
                cut = idx
                break

        new = []
        for idx in range(1,cut+1):
            for jdx in range(len(ops)):
                if ops[jdx][idx] not in [('V',),('O',)]:
                    new.append(ops[jdx][idx])
        self.gates = new

        return self
    
    def run_gate_optimize(self) -> 'QuantumCircuit':
        r"""
        Compress adjacent U gates and CZ gates in the quantum circuit.

        Returns:
            QuantumCircuit: The optimized quantum circuit with compressed U gates and CZ gates.
        """
        self._gate_optimize()

        qc =  QuantumCircuit(self.largest_qubits_index, self.ncbits_used)
        qc.gates = self.gates
        qc.qubits = self.initial_mapping
        qc.physical_qubits_espression = True
        #if self.chip_backend is not None:
        #    if self.chip_backend.chip_name == 'Haituo':
        #        qc.adjust_index(132)
        #        print(f'Tip: When setting Haituo chip as backend, the quibit index starts at 132.')
        #    elif self.chip_backend.chip_name == 'Dongling1':
        #        qc.adjust_index(106)
        #        print(f'Tip: When setting Dongling chip as backend, the quibit index starts at 106.')
        return qc
            
    def run(self, use_priority: bool = True, initial_mapping: list|dict = {'key':'fidelity_var','topology':'linear1'}, optimize_level: 0|1 = 1) -> 'QuantumCircuit':
        r"""Run the transpile program.

        Args:
            optimize_level (0|1 = 1, optional): 0 or 1. Defaults to 1.

        Returns:
            QuantumCircuit: Transpiled quantum circuit.
        """
        if optimize_level == 0:
            return self._select_layout(use_priority=use_priority, initial_mapping=initial_mapping)._basic_routing()._basic_gates().run_gate_optimize()
        elif optimize_level == 1:
            return self._select_layout(use_priority=use_priority, initial_mapping=initial_mapping)._sabre_routing()._basic_gates().run_gate_optimize()
        else:
            raise(ValueError('More optimize level is not support now!'))