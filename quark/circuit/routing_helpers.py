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

""" A toolkit for the SABRE algorithm."""

import networkx as nx
from networkx import floyd_warshall_numpy
from .circuit import *

def distance_matrix_element(qubit1:int,qubit2:int,coupling_graph:nx.Graph) -> int:
    """Computes the distance between two qubits in a coupling graph.

    Args:
        qubit1 (int): The first physical qubit's identifier.
        qubit2 (int): The second physical qubit's identifier.
        coupling_graph (nx.Graph):The graph representing the coupling between physical qubits.

    Returns:
        int: The shortest path distance between the two qubits.
    """
    graph_order = list(coupling_graph.nodes)
    graph_order_index = [graph_order.index(qn) for qn in graph_order]
    phy_idx_dic = dict(zip(graph_order,graph_order_index))
    distance_matrix = floyd_warshall_numpy(coupling_graph)
    idx1 = phy_idx_dic[qubit1]
    idx2 = phy_idx_dic[qubit2]
    dis = distance_matrix[idx1][idx2]
    return dis 

def mapping_node_to_gate_info(node:'nx.nodes',
                              dag:'nx.DiGraph',
                              physical_qubit_list: list,
                              initial_mapping: list) -> tuple:
    gate = node.split('_')[0]
    if gate in one_qubit_gates_avaliable.keys():
        qubit0 = dag.nodes[node]['qubits'][0]
        index0 = initial_mapping.index(qubit0)
        gate_info = (gate,physical_qubit_list[index0])
    elif gate in two_qubit_gates_avaliable.keys():
        qubit1 = dag.nodes[node]['qubits'][0]
        qubit2 = dag.nodes[node]['qubits'][1]
        index1 = initial_mapping.index(qubit1)
        index2 = initial_mapping.index(qubit2)
        gate_info = (gate, physical_qubit_list[index1], physical_qubit_list[index2])
    elif gate in one_qubit_parameter_gates_avaliable.keys():
        qubit0 = dag.nodes[node]['qubits'][0]
        index0 = initial_mapping.index(qubit0)
        paramslst = dag.nodes[node]['params']
        gate_info = (gate,*paramslst,physical_qubit_list[index0])
    elif gate in functional_gates_avaliable.keys():
        if gate == 'measure':
            qubitlst = dag.nodes[node]['qubits']
            cbitlst = dag.nodes[node]['cbits']
            indexlst = [initial_mapping.index(qubit) for qubit in qubitlst]
            gate_info = (gate,[physical_qubit_list[idx] for idx in indexlst], cbitlst)
        elif gate == 'barrier':
            qubitlst = dag.nodes[node]['qubits']
            indexlst = [initial_mapping.index(qubit) for qubit in qubitlst]
            phy_qubitlst = [physical_qubit_list[idx] for idx in indexlst]
            gate_info = (gate,tuple(phy_qubitlst))
        elif gate == 'reset':
            qubit0 = dag.nodes[node]['qubits'][0]
            index0 = initial_mapping.index(qubit0)
            gate_info = (gate,physical_qubit_list[index0])      
    return gate_info 

def is_correlation_on_front_layer(node, front_layer,dag):
    qubitlst = []
    for fnode in front_layer:
        qubits = dag.nodes[fnode]['qubits']
        qubitlst += qubits
    qubitlst = set(qubitlst)
    
    node_qubits = set(dag.nodes[node]['qubits'])
    
    if qubitlst.intersection(node_qubits):
        return True
    else:
        return False

def heuristic_function(front_layer: list, dag: 'nx.DiGraph', coupling_graph: 'nx.Graph',
                       swap_gate_info: tuple, decay_parameter: list) -> float:
    """Computes a heuristic cost function that is used to rate a candidate SWAP to determine whether the SWAP gate can be inserted in a program to resolve
    qubit dependencies. ref:https://github.com/Kaustuvi/quantum-qubit-mapping/blob/master/quantum_qubit_mapping/sabre_tools/heuristic_function.py

    Args:
        F (list): list of gates that have no unexecuted predecessors in the DAG
        circuit_dag (DiGraph): a directed acyclic graph representing qubit dependencies between
                                gates
        initial_mapping (dict): a dictionary containing logical to physical qubit mapping
        distance_matrix (np.matrix): represents qubit connections from given coupling graph
        swap_gate (Gate): candidate SWAP gate
        decay_parameter (list): decay parameters for each logical qubit in the mapping

    Returns:
        float: heuristic score for the candidate SWAP gate
    """    
    F = front_layer
    E = create_extended_successor_set(F, dag)
    min_score_swap_qubits = list(swap_gate_info[1:])
    size_E = len(E)
    if size_E ==0:
        size_E = 1
    size_F = len(F)
    W = 0.5
    max_decay = max(decay_parameter[min_score_swap_qubits[0]], decay_parameter[min_score_swap_qubits[1]])
    f_distance = 0
    e_distance = 0
    for node in F:
        qubit1, qubit2 = dag.nodes[node]['qubits']
        f_distance += distance_matrix_element(qubit1,qubit2,coupling_graph)
    #print('E',E)
    for node in E:
        qubit1, qubit2 = dag.nodes[node]['qubits']
        e_distance += distance_matrix_element(qubit1,qubit2,coupling_graph)
    f_distance = f_distance / size_F
    #print('------------',size_E, e_distance)
    e_distance = W * (e_distance / size_E)
    H = max_decay * (f_distance + e_distance)
    #print(swap_gate_info, max_decay, f_distance, e_distance, H)
    return H

def create_extended_successor_set(front_layer: list, dag: 'nx.DiGraph') -> list:
    """Creates an extended set which contains some closet successors of the gates from F in the DAG
    """    
    E = list()
    for node in front_layer:
        for node_successor in dag.successors(node):
            if node_successor.split('_')[0] in two_qubit_gates_avaliable.keys():
                if len(E) <= 20:
                    E.append(node_successor)
    return E

def update_initial_mapping(swap_gate_info,initial_mapping):
    qubit1 = swap_gate_info[1]
    qubit2 = swap_gate_info[2]
    index1 = initial_mapping.index(qubit1)
    index2 = initial_mapping.index(qubit2)
    initial_mapping[index1] = qubit2
    initial_mapping[index2] = qubit1
    return initial_mapping

def update_coupling_graph(swap_gate_info,coupling_graph):
    qubit1 = swap_gate_info[1]
    qubit2 = swap_gate_info[2]
    mapping = {qubit1:qubit2,qubit2:qubit1}
    coupling_graph_new = nx.relabel_nodes(coupling_graph,mapping)
    return coupling_graph_new

def update_decay_parameter(min_score_swap_gate_info: tuple, decay_parameter: list) -> list:    
    min_score_swap_qubits = list(min_score_swap_gate_info[1:])
    decay_parameter[min_score_swap_qubits[0]] = decay_parameter[min_score_swap_qubits[0]] + 0.001
    decay_parameter[min_score_swap_qubits[1]] = decay_parameter[min_score_swap_qubits[1]] + 0.001
    return decay_parameter