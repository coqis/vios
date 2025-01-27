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

import copy
from functools import partial
import networkx as nx
from networkx import floyd_warshall_numpy
from .quantumcircuit_helpers import (
                      one_qubit_gates_available,
                      two_qubit_gates_available,
                      one_qubit_parameter_gates_available,
                      two_qubit_parameter_gates_available,
                      functional_gates_available,)
from .quantumcircuit import QuantumCircuit
from .dag import qc2dag

def distance_matrix_element(qubit1:int,qubit2:int,coupling_graph:nx.Graph) -> int:
    """Computes the distance between two qubits in a coupling graph.

    Args:
        qubit1 (int): The first physical qubit's identifier.
        qubit2 (int): The second physical qubit's identifier.
        coupling_graph (nx.Graph):The graph representing the coupling between physical qubits.

    Returns:
        int: The shortest path distance between the two qubits.
    """
    #graph_order = list(coupling_graph.nodes)
    #graph_order_index = [graph_order.index(qn) for qn in graph_order]
    #phy_idx_dic = dict(zip(graph_order,graph_order_index))
    #distance_matrix = floyd_warshall_numpy(coupling_graph)
    #idx1 = phy_idx_dic[qubit1]
    #idx2 = phy_idx_dic[qubit2]
    #dis = distance_matrix[idx1][idx2]
    dis = nx.shortest_path_length(coupling_graph,source=qubit1,target=qubit2)
    return dis 

def mapping_node_to_gate_info(node:'nx.nodes',
                              dag:'nx.DiGraph',
                              physical_qubit_list: list,
                              initial_mapping: list) -> tuple:
    gate = node.split('_')[0]
    if gate in one_qubit_gates_available.keys():
        qubit0 = dag.nodes[node]['qubits'][0]
        index0 = initial_mapping.index(qubit0)
        gate_info = (gate,physical_qubit_list[index0])
    elif gate in two_qubit_gates_available.keys():
        qubit1 = dag.nodes[node]['qubits'][0]
        qubit2 = dag.nodes[node]['qubits'][1]
        index1 = initial_mapping.index(qubit1)
        index2 = initial_mapping.index(qubit2)
        gate_info = (gate, physical_qubit_list[index1], physical_qubit_list[index2])
    elif gate in one_qubit_parameter_gates_available.keys():
        qubit0 = dag.nodes[node]['qubits'][0]
        index0 = initial_mapping.index(qubit0)
        paramslst = dag.nodes[node]['params']
        gate_info = (gate,*paramslst,physical_qubit_list[index0])
    elif gate in two_qubit_parameter_gates_available.keys():
        paramslst = dag.nodes[node]['params']
        qubit1 = dag.nodes[node]['qubits'][0]
        qubit2 = dag.nodes[node]['qubits'][1]
        index1 = initial_mapping.index(qubit1)
        index2 = initial_mapping.index(qubit2)
        gate_info = (gate, *paramslst, physical_qubit_list[index1], physical_qubit_list[index2])
    elif gate in functional_gates_available.keys():
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

def heuristic_function_parallel(swap_gate_info: tuple,
                                coupling_graph: 'nx.Graph',
                                dag: 'nx.DiGraph', 
                                front_layer: list, 
                                decay_parameter: list,
                                extended_successor_set:list,
                                ) -> float:
    
    temp_coupling_graph = update_coupling_graph(swap_gate_info,coupling_graph)

    F = front_layer
    E = extended_successor_set #create_extended_successor_set(F, dag)
    min_score_swap_qubits = list(swap_gate_info[1:])
    size_E = len(E)
    if size_E == 0:
        size_E = 1
    size_F = len(F)
    W = 0.5
    max_decay = max(decay_parameter[min_score_swap_qubits[0]], decay_parameter[min_score_swap_qubits[1]])
    f_distance = 0
    e_distance = 0
    for node in F:
        qubit1, qubit2 = dag.nodes[node]['qubits']
        f_distance += distance_matrix_element(qubit1,qubit2,temp_coupling_graph)
    for node in E:
        qubit1, qubit2 = dag.nodes[node]['qubits']
        e_distance += distance_matrix_element(qubit1,qubit2,temp_coupling_graph)
    f_distance = f_distance / size_F
    e_distance = W * (e_distance / size_E)
    H = max_decay * (f_distance + e_distance)
    return H

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
    if size_E == 0:
        size_E = 1
    size_F = len(F)
    W = 0.5
    max_decay = max(decay_parameter[min_score_swap_qubits[0]], decay_parameter[min_score_swap_qubits[1]])
    f_distance = 0
    e_distance = 0
    for node in F:
        qubit1, qubit2 = dag.nodes[node]['qubits']
        f_distance += distance_matrix_element(qubit1,qubit2,coupling_graph)
    for node in E:
        qubit1, qubit2 = dag.nodes[node]['qubits']
        e_distance += distance_matrix_element(qubit1,qubit2,coupling_graph)
    f_distance = f_distance / size_F
    e_distance = W * (e_distance / size_E)
    H = max_decay * (f_distance + e_distance)
    return H

def create_extended_successor_set(front_layer: list, dag: 'nx.DiGraph') -> list:
    """Creates an extended set which contains some closet successors of the gates from F in the DAG
    """    
    E = []
    for node in front_layer:
        for node_successor in dag.successors(node):
            if node_successor.split('_')[0] in two_qubit_gates_available.keys() or node_successor.split('_')[0] in two_qubit_parameter_gates_available.keys():
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

def map_gates_to_physical_qubits_layout(gates,initial_mapping_dic):
    """Map the virtual quantum circuit to physical qubits directly.
    Returns:
        None: Update self information if necessary.
    """
    new = []
    for gate_info in gates:
        gate = gate_info[0]
        if gate in one_qubit_gates_available.keys():
            qubit0 = initial_mapping_dic[gate_info[1]]
            new.append((gate,qubit0))
        elif gate in two_qubit_gates_available.keys():
            qubit1 = initial_mapping_dic[gate_info[1]]
            qubit2 = initial_mapping_dic[gate_info[2]]
            new.append((gate,qubit1,qubit2))
        elif gate in one_qubit_parameter_gates_available.keys():
            qubit0 = initial_mapping_dic[gate_info[-1]]
            params = gate_info[1:-1]
            new.append((gate,*params,qubit0))
        elif gate in two_qubit_parameter_gates_available.keys():
            param = gate_info[1]
            qubit1 = initial_mapping_dic[gate_info[2]]
            qubit2 = initial_mapping_dic[gate_info[3]]
            new.append((gate,param,qubit1,qubit2))
        elif gate in functional_gates_available.keys():
            if gate == 'measure':
                qubitlst = [initial_mapping_dic[q] for q in gate_info[1]]
                cbitlst = gate_info[2]
                new.append((gate,qubitlst,cbitlst))
            elif gate == 'barrier':
                qubitlst = [initial_mapping_dic[q] for q in gate_info[1] if q in initial_mapping_dic] #[initial_mapping_dic[q] for q in gate_info[1]]
                new.append((gate,tuple(qubitlst)))
            elif gate == 'delay':
                qubitlst = [initial_mapping_dic[q] for q in gate_info[1]]
                new.append((gate,tuple(qubitlst)))
            elif gate == 'reset':
                qubit0 = initial_mapping_dic[gate_info[1]]
                new.append((gate,qubit0))
    return new

def basic_routing_gates(gates,qubits,initial_mapping,coupling_map):
    initial_mapping_dic = dict(zip(qubits,initial_mapping))
    gates_mapped = map_gates_to_physical_qubits_layout(gates,initial_mapping_dic)
    
    coupling_graph = nx.Graph()
    coupling_graph.add_edges_from(coupling_map)
    qubit_line = copy.deepcopy(initial_mapping)
    initial_map = copy.deepcopy(initial_mapping)
    
    if len(initial_mapping)>1:
        assert(len(coupling_graph.nodes)==len(initial_mapping))
    
    new = []
    for gate_info in gates_mapped:
        gate = gate_info[0]
        if gate in one_qubit_gates_available.keys():
            qubit = gate_info[1]
            line = qubit_line[initial_mapping.index(qubit)]
            new.append((gate,line))                
        elif gate in two_qubit_gates_available.keys():
            qubit1 = gate_info[1]
            qubit2 = gate_info[2]
            line1 = qubit_line[initial_mapping.index(qubit1)]
            line2 = qubit_line[initial_mapping.index(qubit2)]
            dis = distance_matrix_element(line1,line2,coupling_graph)
            if dis == 1:
                new.append((gate,line1,line2))
            else:
                shortest_path = nx.shortest_path(coupling_graph, source = line1, target = line2)
                shortest_path_edges = list(nx.utils.pairwise(shortest_path))
                #print('check edge',shortest_path_edges)
                for line_1,line_2 in shortest_path_edges[:-1]:
                    initial_mapping[qubit_line.index(line_1)],initial_mapping[qubit_line.index(line_2)] = \
                    initial_mapping[qubit_line.index(line_2)],initial_mapping[qubit_line.index(line_1)]
                    new.append(('swap',line_1,line_2))
                line_1,line_2 = shortest_path_edges[-1]
                new.append((gate,line_1,line_2))
        elif gate in two_qubit_parameter_gates_available.keys():
            param = gate_info[1]
            qubit1 = gate_info[2]
            qubit2 = gate_info[3]
            line1 = qubit_line[initial_mapping.index(qubit1)]
            line2 = qubit_line[initial_mapping.index(qubit2)]
            dis = distance_matrix_element(line1,line2,coupling_graph)
            if dis == 1:
                new.append((gate,param,line1,line2))
            else:
                shortest_path = nx.shortest_path(coupling_graph, source = line1, target = line2)
                shortest_path_edges = list(nx.utils.pairwise(shortest_path))
                for line_1,line_2 in shortest_path_edges[:-1]:
                    initial_mapping[qubit_line.index(line_1)],initial_mapping[qubit_line.index(line_2)] = \
                    initial_mapping[qubit_line.index(line_2)],initial_mapping[qubit_line.index(line_1)]
                    new.append(('swap',line_1,line_2))
                line_1,line_2 = shortest_path_edges[-1]
                new.append((gate,param,line_1,line_2))
        elif gate in one_qubit_parameter_gates_available.keys():
            qubit = gate_info[-1]
            line = qubit_line[initial_mapping.index(qubit)]
            if gate == 'u':
                new.append((gate,gate_info[1],gate_info[2],gate_info[3],line))
            elif gate == 'r':
                new.append((gate,gate_info[1],gate_info[2],line))
            else:
                new.append((gate,gate_info[1],line))
        elif gate in ['reset']:
            qubit = gate_info[-1]
            line = qubit_line[initial_mapping.index(qubit)]        
            new.append((gate,line))
        elif gate in ['measure']:
            q_pos = []
            for qubit in gate_info[1]:
                line = qubit_line[initial_mapping.index(qubit)]
                q_pos.append(line)
            new.append((gate,q_pos,gate_info[2]))
        elif gate in ['barrier']:
            barrier_pos = []
            for qubit in gate_info[1]:
                line = qubit_line[initial_mapping.index(qubit)]
                barrier_pos.append(line)
            new.append((gate,tuple(barrier_pos)))

    final_map = initial_mapping.copy()
    print('basic routing results:')
    print('virtual qubit --> initial mapping --> after routing')
    for idx,qi in enumerate(initial_map):
        print('{:^10} --> {:^10} --> {:^10}'.format(idx,qi,final_map[idx]))
    return new

def gates_sabre_routing_once(qc,initial_mapping,coupling_map,largest_qubits_index):
    dag = qc2dag(qc,show_qubits=False)
    physical_qubit_list = copy.deepcopy(initial_mapping)
    coupling_graph = nx.Graph()
    coupling_graph.add_edges_from(coupling_map)
    if len(initial_mapping)>1:
        assert(len(coupling_graph.nodes)==len(initial_mapping))
    front_layer = list(nx.topological_generations(dag))
    if front_layer != []:
        front_layer = front_layer[0] 
    decay_parameter = [0.001] * (largest_qubits_index) 
    ncycle = 0 
    new = []
    collect_execute = []
    while len(front_layer) != 0:
        ncycle += 1
        execute_node_list = []
        for node in front_layer:
            gate = node.split('_')[0]
            if gate not in two_qubit_gates_available.keys() and gate not in two_qubit_parameter_gates_available.keys():
                execute_node_list.append(node)
            else:
                q1, q2 = dag.nodes[node]['qubits']
                dis = distance_matrix_element(q1,q2,coupling_graph)
                if dis == 1:
                    execute_node_list.append(node)
                    decay_parameter = [0.001] * (largest_qubits_index)          
        if len(execute_node_list) > 0:
            for execute_node in execute_node_list:
                collect_execute.append(execute_node)
                front_layer.remove(execute_node)
                gate_info = mapping_node_to_gate_info(execute_node,dag,physical_qubit_list,initial_mapping)
                new.append(gate_info)
                for successor_node in dag.successors(execute_node):
                    if is_correlation_on_front_layer(successor_node,front_layer,dag) is False:
                        predecessors = list(dag.predecessors(successor_node))
                        if all(x in (front_layer + collect_execute) for x in predecessors):
                            front_layer.append(successor_node)
                        #paths = nx.all_simple_paths(dag, source = execute_node, target = successor_node,cutoff=1)
                        #if list(paths) != []:
                        #    predecessors = list(dag.predecessors(successor_node))
                        #    if all(x in (front_layer + collect_execute) for x in predecessors):
                        #        front_layer.append(successor_node)
        else:
            swap_candidate_list = []
            for hard_node in front_layer:
                control_qubit, target_qubit = dag.nodes[hard_node]['qubits']
                control_neighbours = coupling_graph.neighbors(control_qubit)
                target_neighbours = coupling_graph.neighbors(target_qubit)
                for fake_target in control_neighbours:
                    swap_candidate_list.append(('swap',control_qubit,fake_target))
                for fake_control in target_neighbours:
                    swap_candidate_list.append(('swap',fake_control,target_qubit))

            extended_successor_set = create_extended_successor_set(front_layer, dag)
            heuristic_obj = partial(heuristic_function_parallel,
                                    coupling_graph=coupling_graph,
                                    dag=dag,
                                    front_layer=front_layer,
                                    decay_parameter=decay_parameter,
                                    extended_successor_set=extended_successor_set,
                                    )
            swap_candidate_list = set(swap_candidate_list)
            swap_scores = [heuristic_obj(swap_gate) for swap_gate in swap_candidate_list]
            heuristic_score = dict(zip(swap_candidate_list,swap_scores))

            min_score_swap_gate_info,min_score = min(heuristic_score.items(), key=lambda item: item[1])

            q1 = min_score_swap_gate_info[1]
            q2 = min_score_swap_gate_info[2]
            idx1 = initial_mapping.index(q1)
            idx2 = initial_mapping.index(q2)
            new.append(('swap',physical_qubit_list[idx1],physical_qubit_list[idx2]))
            # update couping graph
            coupling_graph = update_coupling_graph(min_score_swap_gate_info,coupling_graph)
            # updade initial mapping
            initial_mapping = update_initial_mapping(min_score_swap_gate_info,initial_mapping)
            # update decay parameter
            decay_parameter = update_decay_parameter(min_score_swap_gate_info,decay_parameter)
    return new,initial_mapping
    
def gates_sabre_routing(source_gates, source_qubits, initial_mapping, coupling_map,\
                        largest_qubits_index, ncbits_used,\
                        iterations: int = 5):
    """Routing based on the Sabre algorithm.
    Args:
        iterations (int, optional): The number of iterations. Defaults to 1.
    Returns:
        Transpiler: Update self information.
    """
    for idx in range(iterations):
        initial_map = copy.deepcopy(initial_mapping)
        if idx == 0:
            gates = copy.deepcopy(source_gates)
        else:
            source_gates.reverse()
            gates = copy.deepcopy(source_gates)
        #print('check',idx,initial_map)
        initial_mapping_dic = dict(zip(source_qubits,initial_mapping))
        gates = map_gates_to_physical_qubits_layout(gates,initial_mapping_dic)
        qc = QuantumCircuit(largest_qubits_index,ncbits_used)
        qc.gates = gates
        new,initial_mapping = gates_sabre_routing_once(qc,initial_mapping,coupling_map,largest_qubits_index)
        final_map = copy.deepcopy(initial_mapping)
    print(f'sabre routing results, after {iterations} iteration(s)')
    print('virtual qubit --> initial mapping --> after routing')
    for idx,qi in enumerate(initial_map):
        print('{:^10} --> {:^10} --> {:^10}'.format(idx,qi,final_map[idx]))
    return new,initial_map