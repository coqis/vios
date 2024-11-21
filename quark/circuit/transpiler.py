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

import numpy as np
import networkx as nx
from typing import Literal
from .circuit import (QuantumCircuit,
                      one_qubit_gates_avaliable,
                      two_qubit_gates_avaliable,
                      one_qubit_parameter_gates_avaliable,
                      functional_gates_avaliable)
from .matrix import gate_matrix_dict, u_mat, id_mat
from .dag import qc2dag
from .routing_helpers import (distance_matrix_element,
                              mapping_node_to_gate_info,
                              is_correlation_on_front_layer,
                              heuristic_function,
                              update_initial_mapping,
                              update_coupling_graph,
                              update_decay_parameter)
from .decompose_helpers import (cx_decompose,
                                cy_decompose,
                                swap_decompose,
                                iswap_decompose,
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
    def __init__(self, qc: QuantumCircuit | str | list, chip_backend: Backend):
        
        r"""Obtain basic information from input quantum circuit.

        Args:
            qc (QuantumCircuit | str | list): The quantum circuit to be transpiled. Can be a QuantumCircuit object or OpenQASM 2.0 str or qlisp list.

            chip_backend (Backend): An instance of the Backend class that contains the information about the quantum chip to be used for layout selection

        Raises:
            TypeError: The quantum circuit format is incorrect.
        """

        if isinstance(qc, QuantumCircuit):
            self.gates = qc.gates
            self.nqubits_used = qc.nqubits
            self.ncbits_used = qc.ncbits
        elif isinstance(qc, str):
            qc = QuantumCircuit()
            qc.from_openqasm2(qc)
            self.gates = qc.gates
            self.nqubits_used = qc.nqubits
            self.ncbits_used = qc.ncbits
        elif isinstance(qc, list):
            qc = QuantumCircuit()
            qc.from_qlisp(qc)
            self.gates = qc.gates
            self.nqubits_used = qc.nqubits
            self.ncbits_used = qc.ncbits
        else:
            raise TypeError("Expected a Quark QuantumCircuit or OpenQASM 2.0 or qlisp, but got a {}.".format(type(qc)))
        
        self.source_gates = self.gates.copy()

        self.chip_backend = chip_backend

        # update initial_mapping and coupling map
        # self._physical_qubits_layout(chip_backend,use_priority,initial_mapping,coupling_map)
        self.initial_mapping = [i for i in range(qc.nqubits)]
        self.coupling_map = [(i,i+1) for i in range(qc.nqubits-1)]
        self.largest_qubits_index = max(self.initial_mapping) + 1

    def _select_layout(self,use_priority: bool = True, initial_mapping: list|dict = {'key':'fidelity_var','topology':'linear1'}, coupling_map: list[tuple]|None = None):
        # update initial_mapping, coupling_map, largest_qubits_index
        self.initial_mapping,self.coupling_map = Layout(self.nqubits_used,self.chip_backend).selected_layout(use_priority=use_priority,
                                                                                                   initial_mapping=initial_mapping,
                                                                                                   coupling_map=coupling_map)
        self.largest_qubits_index = max(self.initial_mapping) + 1

        subgraph = self.chip_backend.graph.subgraph(self.initial_mapping)
        subgraph_fidelity = np.array([data['fidelity'] for _, _, data in subgraph.edges(data=True)])
        fidelity_mean = np.mean(subgraph_fidelity)
        fidelity_var  = np.var(subgraph_fidelity)  
        print('The average fidelity of the coupler(s) between the selected qubits is {}, and the variance of the fidelity is {}'.format(fidelity_mean,fidelity_var))
        return self 
    
    def _mapping_to_physical_qubits_layout(self):
        """Map the virtual quantum circuit to physical qubits directly.

        Returns:
            None: Update self information if necessary.
        """
        new = []
        for gate_info in self.source_gates:
            gate = gate_info[0]
            if gate in one_qubit_gates_avaliable.keys():
                qubit0 = self.initial_mapping[gate_info[1]]
                new.append((gate,qubit0))
            elif gate in two_qubit_gates_avaliable.keys():
                qubit1 = self.initial_mapping[gate_info[1]]
                qubit2 = self.initial_mapping[gate_info[2]]
                new.append((gate,qubit1,qubit2))
            elif gate in one_qubit_parameter_gates_avaliable.keys():
                qubit0 = self.initial_mapping[gate_info[-1]]
                params = gate_info[1:-1]
                new.append((gate,*params,qubit0))
            elif gate in functional_gates_avaliable.keys():
                if gate == 'measure':
                    qubitlst = [self.initial_mapping[q] for q in gate_info[1]]
                    cbitlst = gate_info[2]
                    new.append((gate,qubitlst,cbitlst))
                elif gate == 'barrier':
                    qubitlst = [self.initial_mapping[q] for q in gate_info[1]]
                    new.append((gate,tuple(qubitlst)))
                elif gate == 'reset':
                    qubit0 = self.initial_mapping[gate_info[1]]
                    new.append((gate,qubit0))
        self.gates = new
        return None
    
    def run_select_layout(self, use_priority: bool = True, initial_mapping: list|dict = {'key':'fidelity_var','topology':'linear1'}, coupling_map: list[tuple] | None = None):
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
        self._select_layout(use_priority = use_priority, initial_mapping = initial_mapping, coupling_map = coupling_map)
        self._mapping_to_physical_qubits_layout()
        qc = QuantumCircuit(self.largest_qubits_index,self.ncbits_used)
        qc.gates = self.gates
        qc.physical_qubits_espression = True
        return qc
    
    @property
    def coupling_graph(self):
        coupling_graph = nx.Graph()
        coupling_graph.add_edges_from(self.coupling_map)
        return coupling_graph
        
    def _basic_routing(self):
        """Routing based on the initial mapping.

        Returns:
            Transpiler: Update self information.
        """
        self._mapping_to_physical_qubits_layout()
        coupling_graph = self.coupling_graph.copy()
        physical_qubit_list = self.initial_mapping.copy()
        initial_map = self.initial_mapping.copy()

        new = []
        for gate_info in self.gates:
            gate = gate_info[0]
            
            if gate in one_qubit_gates_avaliable.keys():
                q0 = gate_info[1]
                idx0 = self.initial_mapping.index(q0)
                new.append((gate,physical_qubit_list[idx0]))
                
            elif gate in two_qubit_gates_avaliable.keys():
                q1 = gate_info[1]
                q2 = gate_info[2]
                dis = distance_matrix_element(q1,q2,coupling_graph)
                if dis == 1:
                    idx1 = self.initial_mapping.index(q1)
                    idx2 = self.initial_mapping.index(q2)
                    new.append((gate,physical_qubit_list[idx1],physical_qubit_list[idx2]))
                else:
                    shortest_path = nx.shortest_path(coupling_graph, source = q1, target = q2)
                    shortest_path_edges = list(nx.utils.pairwise(shortest_path))
                    for swap_pos in shortest_path_edges[:-1]:
                        idx1 = self.initial_mapping.index(swap_pos[0])
                        idx2 = self.initial_mapping.index(swap_pos[1])
                        new.append(('swap',physical_qubit_list[idx1],physical_qubit_list[idx2]))
                        
                    idx1 = self.initial_mapping.index(shortest_path_edges[-1][0])
                    idx2 = self.initial_mapping.index(shortest_path_edges[-1][1])                
                    new.append((gate,physical_qubit_list[idx1],physical_qubit_list[idx2]))
                    
                    # upate index and coupling graph
                    for swap_pos in shortest_path_edges[:-1]:
                        idx1 = self.initial_mapping.index(swap_pos[0])
                        idx2 = self.initial_mapping.index(swap_pos[1])
                        self.initial_mapping[idx1] = swap_pos[1]
                        self.initial_mapping[idx2] = swap_pos[0]
                        
                        swap_gate_info = ('swap',swap_pos[0],swap_pos[1])
                        coupling_graph = update_coupling_graph(swap_gate_info,coupling_graph)
                        
            elif gate in one_qubit_parameter_gates_avaliable.keys():
                q0 = gate_info[-1]
                idx0 = self.initial_mapping.index(q0)
                if gate == 'u':
                    new.append((gate,gate_info[1],gate_info[2],gate_info[3],physical_qubit_list[idx0]))
                else:
                    new.append((gate,gate_info[1],physical_qubit_list[idx0]))
                    
            elif gate in ['reset']:
                q0 = gate_info[-1]
                idx0 = self.initial_mapping.index(q0)        
                new.append((gate,physical_qubit_list[idx0]))
            
            elif gate in ['measure']:
                q_pos = []
                for qi in gate_info[1]:
                    idx = self.initial_mapping.index(qi)
                    q_pos.append(physical_qubit_list[idx])
                new.append((gate,q_pos,gate_info[2]))
            
            elif gate in ['barrier']:
                barrier_pos = []
                for qi in gate_info[1]:
                    idx = self.initial_mapping.index(qi)
                    barrier_pos.append(physical_qubit_list[idx])
                new.append((gate,tuple(barrier_pos)))
                
        self.gates = new

        final_map = self.initial_mapping.copy()
        print('basic routing results:')
        print('virtual qubit --> initial mapping --> after routing')
        for idx,qi in enumerate(initial_map):
            print('{:^10} --> {:^10} --> {:^10}'.format(idx,qi,final_map[idx]))
        return self

    def run_basic_routing(self):
        """Routing based on the initial mapping.

        Returns:
            QuantumCircuit: The updated quantum circuit with swap gates applied.
        """
        self._basic_routing()
        qc = QuantumCircuit(self.largest_qubits_index,self.ncbits_used)
        qc.gates = self.gates
        qc.physical_qubits_espression = True
        return qc 
    
    def _sabre_routing_once(self,dag):
        
        physical_qubit_list = self.initial_mapping.copy()
        
        front_layer = list(nx.topological_generations(dag))[0]
        
        coupling_graph = self.coupling_graph
        
        new = []
        decay_parameter = [0.001] * (self.largest_qubits_index) #len(self.initial_mapping)
        ncycle = 0 
        while len(front_layer) != 0:
            ncycle += 1
            #print('='*50,ncycle)
            #print(front_layer,self.initial_mapping)
            execute_node_list = []
            for node in front_layer:
                gate = node.split('_')[0]
                if gate not in two_qubit_gates_avaliable.keys():
                    execute_node_list.append(node)
                    #decay_parameter = [0.001] * (self.largest_qubits_index) 
                else:
                    q1, q2 = dag.nodes[node]['qubits']
                    dis = distance_matrix_element(q1,q2,coupling_graph)
                    if dis == 1:
                        execute_node_list.append(node)
                        decay_parameter = [0.001] * (self.largest_qubits_index) 
                        
            if len(execute_node_list) > 0:
                for execute_node in execute_node_list:
                    front_layer.remove(execute_node)
                    gate_info = mapping_node_to_gate_info(execute_node,dag,physical_qubit_list,self.initial_mapping)
                    new.append(gate_info)
                    
                    for successor_node in dag.successors(execute_node):
                        if is_correlation_on_front_layer(successor_node,front_layer,dag) is False:
                            front_layer.append(successor_node)
            else:
                for hard_node in front_layer:
                    # 这一环节会更改coupling map/graph, initial_mapping
                    heuristic_score = dict()
                    swap_candidate_list = []
                    control_qubit, target_qubit = dag.nodes[hard_node]['qubits']
                    control_neighbours = coupling_graph.neighbors(control_qubit)
                    target_neighbours = coupling_graph.neighbors(target_qubit)
                    for fake_target in control_neighbours:
                        swap_candidate_list.append(('swap',control_qubit,fake_target))
                    for fake_control in target_neighbours:
                        swap_candidate_list.append(('swap',fake_control,target_qubit))
                    for swap_gate in swap_candidate_list:
                        temp_coupling_graph = update_coupling_graph(swap_gate,coupling_graph)
                        swap_gate_score = heuristic_function(front_layer,dag,temp_coupling_graph,\
                                                             swap_gate,decay_parameter)
                        heuristic_score.update({swap_gate:swap_gate_score})
                        #print(swap_gate,decay_parameter)
                        
                    #print('heuristic_score',heuristic_score)
                    all_scores = list(heuristic_score.values())
                    min_score = min(all_scores)
                    min_score_swap_gate_info = swap_candidate_list[all_scores.index(min_score)]
                    #print('min_score_swap_gate_info',min_score_swap_gate_info)
                    q1 = min_score_swap_gate_info[1]
                    q2 = min_score_swap_gate_info[2]
                    idx1 = self.initial_mapping.index(q1)
                    idx2 = self.initial_mapping.index(q2)
                    
                    new.append(('swap',physical_qubit_list[idx1],physical_qubit_list[idx2]))
                    
                    # update couping graph
                    coupling_graph = update_coupling_graph(min_score_swap_gate_info,coupling_graph)
                    # updade initial mapping
                    self.initial_mapping = update_initial_mapping(min_score_swap_gate_info,self.initial_mapping)
                    # update decay parameter
                    decay_parameter = update_decay_parameter(min_score_swap_gate_info,decay_parameter)
        self.gates = new
        return None
    
    def _sabre_routing(self, iterations: int = 5):
        """Routing based on the Sabre algorithm.
        Args:
            iterations (int, optional): The number of iterations. Defaults to 1.

        Returns:
            Transpiler: Update self information.
        """
        for idx in range(iterations):
            initial_map = self.initial_mapping.copy()
            if idx == 0:
                self.gates = self.source_gates.copy()
            else:
                self.source_gates.reverse()
                self.gates = self.source_gates.copy()
            #print('check',idx,initial_map)
            self._mapping_to_physical_qubits_layout()
            qc = QuantumCircuit(self.largest_qubits_index,self.ncbits_used)
            qc.gates = self.gates
            dag = qc2dag(qc)
            self._sabre_routing_once(dag)
            final_map = self.initial_mapping.copy()

        print(f'sabre routing results, after {iterations} iteration(s)')
        print('virtual qubit --> initial mapping --> after routing')
        for idx,qi in enumerate(initial_map):
            print('{:^10} --> {:^10} --> {:^10}'.format(idx,qi,final_map[idx]))

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
        qc.physical_qubits_espression = True
        return qc

    def _basic_gates(self) -> 'Transpiler':
        r"""Convert all gates in the quantum circuit to basic gates.

        Returns:
            Transpiler: Update self information.
        """
        new = []
        for gate_info in self.gates:
            gate = gate_info[0]
            if gate in one_qubit_gates_avaliable.keys():
                gate_matrix = gate_matrix_dict[gate]
                theta,phi,lamda,_ = u3_decompose(gate_matrix)
                new.append(('u',theta,phi,lamda,gate_info[-1]))
            elif gate in one_qubit_parameter_gates_avaliable.keys():
                if gate == 'u':
                    new.append(gate_info)
                else:
                    gate_matrix = gate_matrix_dict[gate](*gate_info[1:-1])
                    theta,phi,lamda,_ = u3_decompose(gate_matrix)
                    new.append(('u',theta,phi,lamda,gate_info[-1]))
            elif gate in two_qubit_gates_avaliable.keys():
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
            elif gate in functional_gates_avaliable.keys():
                new.append(gate_info)
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
        qc.physical_qubits_espression = True
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
        qc.physical_qubits_espression = True
        return qc
            
    def run(self, use_priority: bool = True, initial_mapping: list|dict = {'key':'fidelity_var','topology':'linear1'}, coupling_map: list[tuple]|None = None, optimize_level: 0|1 = 1) -> 'QuantumCircuit':
        r"""Run the transpile program.

        Args:
            optimize_level (0|1 = 1, optional): 0 or 1. Defaults to 1.

        Returns:
            QuantumCircuit: Transpiled quantum circuit.
        """
        if optimize_level == 0:
            return self._select_layout(use_priority=use_priority, initial_mapping=initial_mapping, coupling_map=coupling_map)._basic_routing()._basic_gates().run_gate_optimize()
        elif optimize_level == 1:
            return self._select_layout(use_priority=use_priority, initial_mapping=initial_mapping, coupling_map=coupling_map)._sabre_routing()._basic_gates().run_gate_optimize()
        else:
            raise(ValueError('More optimize level is not support now!'))