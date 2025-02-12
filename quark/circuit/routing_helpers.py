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
#from networkx import floyd_warshall_numpy
from quark.circuit.quantumcircuit_helpers import (
                      one_qubit_gates_available,
                      two_qubit_gates_available,
                      one_qubit_parameter_gates_available,
                      two_qubit_parameter_gates_available,
                      functional_gates_available,)
from quark.circuit.quantumcircuit import QuantumCircuit
from quark.circuit.dag import qc2dag

def map_gates_to_physical_qubits_layout(gates,v2p):
    """Map the virtual quantum circuit to physical qubits directly.
    Returns:
        None: Update self information if necessary.
    """
    new = []
    for gate_info in gates:
        gate = gate_info[0]
        if gate in one_qubit_gates_available.keys():
            qubit0 = v2p[gate_info[1]]
            new.append((gate,qubit0))
        elif gate in two_qubit_gates_available.keys():
            qubit1 = v2p[gate_info[1]]
            qubit2 = v2p[gate_info[2]]
            new.append((gate,qubit1,qubit2))
        elif gate in one_qubit_parameter_gates_available.keys():
            qubit0 = v2p[gate_info[-1]]
            params = gate_info[1:-1]
            new.append((gate,*params,qubit0))
        elif gate in two_qubit_parameter_gates_available.keys():
            param = gate_info[1]
            qubit1 = v2p[gate_info[2]]
            qubit2 = v2p[gate_info[3]]
            new.append((gate,param,qubit1,qubit2))
        elif gate in functional_gates_available.keys():
            if gate == 'measure':
                qubitlst = [v2p[q] for q in gate_info[1]]
                cbitlst = gate_info[2]
                new.append((gate,qubitlst,cbitlst))
            elif gate == 'barrier':
                qubitlst = [v2p[q] for q in gate_info[1] if q in v2p] #[v2p[q] for q in gate_info[1]]
                new.append((gate,tuple(qubitlst)))
            elif gate == 'delay':
                qubitlst = [v2p[q] for q in gate_info[1]]
                new.append((gate,tuple(qubitlst)))
            elif gate == 'reset':
                qubit0 = v2p[gate_info[1]]
                new.append((gate,qubit0))
    return new

def distance_matrix_element(qubit1:int,qubit2:int,coupling_graph:nx.Graph) -> int:
    """Computes the distance between two qubits in a coupling graph.

    Args:
        qubit1 (int): The first physical qubit's identifier.
        qubit2 (int): The second physical qubit's identifier.
        coupling_graph (nx.Graph):The graph representing the coupling between physical qubits.

    Returns:
        int: The shortest path distance between the two qubits.
    """
    dis = nx.shortest_path_length(coupling_graph,source=qubit1,target=qubit2)
    return dis 

def mapping_node_to_gate_info(node:'nx.nodes',
                              dag:'nx.DiGraph',
                              v2p:dict) -> tuple:
    gate = node.split('_')[0]
    if gate in one_qubit_gates_available.keys():
        qubit0 = dag.nodes[node]['qubits'][0]
        gate_info = (gate,v2p[qubit0])
    elif gate in two_qubit_gates_available.keys():
        qubit1 = dag.nodes[node]['qubits'][0]
        qubit2 = dag.nodes[node]['qubits'][1]
        gate_info = (gate, v2p[qubit1], v2p[qubit2])
    elif gate in one_qubit_parameter_gates_available.keys():
        qubit0 = dag.nodes[node]['qubits'][0]
        paramslst = dag.nodes[node]['params']
        gate_info = (gate,*paramslst,v2p[qubit0])
    elif gate in two_qubit_parameter_gates_available.keys():
        paramslst = dag.nodes[node]['params']
        qubit1 = dag.nodes[node]['qubits'][0]
        qubit2 = dag.nodes[node]['qubits'][1]
        gate_info = (gate, *paramslst, v2p[qubit1], v2p[qubit2])
    elif gate in functional_gates_available.keys():
        if gate == 'measure':
            qubitlst = dag.nodes[node]['qubits']
            cbitlst = dag.nodes[node]['cbits']
            gate_info = (gate,[v2p[qubit] for qubit in qubitlst], cbitlst)
        elif gate == 'barrier':
            qubitlst = dag.nodes[node]['qubits']
            phy_qubitlst = [v2p[qubit] for qubit in qubitlst]
            gate_info = (gate,tuple(phy_qubitlst))
        elif gate == 'reset':
            qubit0 = dag.nodes[node]['qubits'][0]
            gate_info = (gate,v2p[qubit0])      
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

def update_v2p_and_p2v_mapping(v2p,swap_gate_info):
    v2p = copy.deepcopy(v2p)
    vq1,vq2 = swap_gate_info[1:]
    v2p[vq1],v2p[vq2] = v2p[vq2],v2p[vq1]
    p2v = {p:v for v,p in v2p.items()}
    return v2p,p2v

def heuristic_function_parallel(swap_gate_info: tuple,
                                coupling_graph: 'nx.Graph',
                                dag: 'nx.DiGraph', 
                                front_layer: list, 
                                v2p:dict,
                                decay_parameter: list,
                                extended_successor_set:list,
                                ) -> float:
    """Computes a heuristic cost function that is used to rate a candidate SWAP to determine whether the SWAP gate can be inserted in a program to resolve qubit dependencies. ref:https://github.com/Kaustuvi/quantum-qubit-mapping/blob/master/quantum_qubit_mapping/sabre_tools/heuristic_function.py

    Args:
        swap_gate_info (tuple): Candidate SWAP gate of virtual circuit.
        coupling_graph (nx.Graph): Coupling graph of physical qubit layout
        dag (nx.DiGraph): The directed acyclic graph representing of virtual circuit.
        front_layer (list): A list of gates that have no unexecuted predecessors in dag.
        v2p (dict): A dictionary mapping virtual qubits to physical qubits.
        decay_parameter (list): Decay parameters for each physical qubit.
        extended_successor_set (list): A set of successors for all nodes in the front layer.

    Returns:
        float: The heuristic score for the candidate SWAP gate
    """
    v2p,_ = update_v2p_and_p2v_mapping(v2p,swap_gate_info)

    F = front_layer
    E = extended_successor_set
    size_E = len(E)
    if size_E == 0:
        size_E = 1
    size_F = len(F)
    W = 0.5
    max_decay = max(decay_parameter[v2p[swap_gate_info[1]]], decay_parameter[v2p[swap_gate_info[2]]])
    f_distance = 0
    e_distance = 0
    for node in F:
        vq1, vq2 = dag.nodes[node]['qubits']
        f_distance += distance_matrix_element(v2p[vq1],v2p[vq2],coupling_graph)
    for node in E:
        vq1, vq2 = dag.nodes[node]['qubits']
        e_distance += distance_matrix_element(v2p[vq1],v2p[vq2],coupling_graph)
    f_distance = f_distance / size_F
    e_distance = (e_distance / size_E)
    H = max_decay * (f_distance + W * e_distance)
    #print('score',swap_gate_info,f_distance,size_F,W,e_distance,max_decay)
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
    return list(set(E))

def update_decay_parameter(min_score_swap_gate_info: tuple, decay_parameter: list,v2p:dict) -> list:    
    min_score_swap_qubits = list(min_score_swap_gate_info[1:])
    pq1 = v2p[min_score_swap_qubits[0]]
    pq2 = v2p[min_score_swap_qubits[1]]
    decay_parameter[pq1] = decay_parameter[pq1] + 0.01
    decay_parameter[pq2] = decay_parameter[pq2] + 0.01
    return decay_parameter

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

def gates_sabre_routing_once(dag,v2p,coupling_graph,largest_qubits_index,get_new_gates):
    if len(v2p)>1:
        assert(len(coupling_graph.nodes)==len(v2p))
    p2v = {p:v for v,p in v2p.items()}
    front_layer = list(nx.topological_generations(dag))
    if front_layer != []:
        front_layer = front_layer[0] 
    decay_parameter = [1] * (largest_qubits_index) 

    ncycle = 0 
    new = []
    collect_execute = []
    #print('+++', ncycle, front_layer)
    while len(front_layer) != 0:
        ncycle += 1
        execute_node_list = []
        for node in front_layer:
            gate = node.split('_')[0]
            if gate not in two_qubit_gates_available.keys() and gate not in two_qubit_parameter_gates_available.keys():
                execute_node_list.append(node)
            else:
                vq1, vq2 = dag.nodes[node]['qubits']
                pq1, pq2 = v2p[vq1], v2p[vq2]
                dis = distance_matrix_element(pq1,pq2,coupling_graph)
                if dis == 1:
                    execute_node_list.append(node)         
        if execute_node_list:
            for execute_node in execute_node_list:
                collect_execute.append(execute_node)
                front_layer.remove(execute_node)
                if get_new_gates:
                    gate_info = mapping_node_to_gate_info(execute_node,dag,v2p)
                    new.append(gate_info)
                for successor_node in dag.successors(execute_node):
                    if is_correlation_on_front_layer(successor_node,front_layer,dag) is False:
                        predecessors = list(dag.predecessors(successor_node))
                        if all(x in (front_layer + collect_execute) for x in predecessors):
                            front_layer.append(successor_node)
            decay_parameter = [1] * (largest_qubits_index)
            #print('+++', ncycle, front_layer,execute_node_list)
        else:
            swap_candidate_list = []
            for hard_node in front_layer:
                vq1, vq2 = dag.nodes[hard_node]['qubits']
                pq1_neighbours = coupling_graph.neighbors(v2p[vq1])
                pq2_neighbours = coupling_graph.neighbors(v2p[vq2])
                vq1_neighbours = [p2v[pq] for pq in pq1_neighbours]
                vq2_neighbours = [p2v[pq] for pq in pq2_neighbours]
                for vq in vq1_neighbours:
                    poss = [vq,vq1]
                    swap_candidate_list.append(('swap',min(poss),max(poss)))
                for vq in vq2_neighbours:
                    poss = [vq,vq2]
                    swap_candidate_list.append(('swap',min(poss),max(poss)))
            swap_candidate_list = list(set(swap_candidate_list))

            extended_successor_set = create_extended_successor_set(front_layer, dag)
            heuristic_obj = partial(heuristic_function_parallel,
                                    coupling_graph=coupling_graph,
                                    dag=dag,
                                    front_layer=front_layer,
                                    v2p=v2p,
                                    decay_parameter=decay_parameter,
                                    extended_successor_set=extended_successor_set,
                                    )
            swap_scores = [heuristic_obj(swap_gate) for swap_gate in swap_candidate_list]
            heuristic_score = dict(zip(swap_candidate_list,swap_scores))

            min_score = min(heuristic_score.values())
            best_swap = [swap for swap,score in heuristic_score.items() if score == min_score]
            if len(best_swap)>1:
                min_score_swap_gate_info = best_swap[0]
            else:
                min_score_swap_gate_info = best_swap[0]
            
            #print('***', ncycle, front_layer, min_score_swap_gate_info,swap_candidate_list)
            #print('E',extended_successor_set)
            if get_new_gates:
                vq1 = min_score_swap_gate_info[1]
                vq2 = min_score_swap_gate_info[2]
                pq1 = v2p[vq1]
                pq2 = v2p[vq2]
                new.append(('swap',pq1,pq2))

            # update decay parameter
            decay_parameter = update_decay_parameter(min_score_swap_gate_info,decay_parameter,v2p)

            # update v2p and p2v mapping
            v2p,p2v = update_v2p_and_p2v_mapping(v2p,min_score_swap_gate_info,)
            
    return new,v2p
    
def gates_sabre_routing(source_gates:list, source_qubits:list,initial_mapping:list,coupling_map:list[tuple],\
                        largest_qubits_index:int, ncbits_used:int,\
                        iterations: int = 5):
    """Routing based on the Sabre algorithm.
    Args:
        iterations (int, optional): The number of iterations. Defaults to 1.
    Returns:
        Transpiler: Update self information.
    """
    v2p = dict(zip(source_qubits,initial_mapping))
    qc = QuantumCircuit(largest_qubits_index,ncbits_used)
    qc.gates = source_gates
    dag = qc2dag(qc,show_qubits=False)
    rev_qc = QuantumCircuit(largest_qubits_index,ncbits_used)
    rev_qc.gates = source_gates[::-1]
    rev_dag = qc2dag(rev_qc,show_qubits=False)

    coupling_graph = nx.Graph()
    coupling_graph.add_edges_from(coupling_map)
    init_p2v = {p:v for v,p in v2p.items()}
    for idx in range(iterations):
        if idx == iterations-1:
            get_new_gates = True
        else:
            get_new_gates = False
        new,v2p = gates_sabre_routing_once(dag,v2p,coupling_graph,largest_qubits_index,get_new_gates)
        dag,rev_dag = rev_dag,dag
        if idx>2:
            if idx == iterations-2:
                best_p2v = {p:v for v,p in v2p.items()}
        else:
            best_p2v = init_p2v
            
    final_p2v = {p:v for v,p in v2p.items()}
    print('{:^21} -----> {:^21} -----> {:^21}'.format('initial mapping','best mapping','final mapping'))
    print('{:^10}:{:^10} -----> {:^10}:{:^10} -----> {:^10}:{:^10}'.format('P','V','P','V','P','V'))
    for p in sorted(init_p2v.keys()):
        print('{:^10}:{:^10} -----> {:^10}:{:^10} -----> {:^10}:{:^10}'.format(p,init_p2v[p],p,best_p2v[p],p,final_p2v[p]))
    return new,list(v2p.keys())