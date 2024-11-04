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
Tools for converting between directed acyclic graphs (DAGs) and quantum circuits
"""

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from .circuit import (
    QuantumCircuit, 
    one_qubit_gates_avaliable,
    two_qubit_gates_avaliable,
    functional_gates_avaliable,
    one_qubit_parameter_gates_avaliable,)

def draw_dag(dag, output='dag_figure.png'):
    """Draws a directed acyclic graph (DAG) representation of a quantum circuit and saves it as an image.

    Args:
        dag (nx.DiGraph): The quantum circuit represented as a directed acyclic graph.
        output (str, optional): The filename for saving the generated DAG image. Defaults to 'dag_figure.png'.
    """
    A = nx.nx_agraph.to_agraph(dag)

    for node in A.nodes():
        gate = node.split('_')[0]
        if gate == 'measure':
            cbit = dag.nodes[node]['cbits'][0]
            node.attr['label'] = gate + f' [c{cbit}]'
        else:
            node.attr['label'] = gate
    for u, v, data in dag.edges(data=True):
        edge = A.get_edge(u, v)
        edge.attr['label'] = data['qubit'] 
    
    A.graph_attr['dpi'] = '300' 
    A.layout(prog='dot')
    
    A.draw(output)

    img = plt.imread(output)
    plt.imshow(img)
    plt.axis('off')
    plt.show()
    
def seperate_measure_instruction(qc:'QuantumCircuit')->'QuantumCircuit':
    new = []
    for gate_info in qc.gates:
        gate = gate_info[0]
        if gate == 'measure':
            for idx,qubit in enumerate(gate_info[1]):
                new.append((gate,[qubit],[gate_info[2][idx]]))
        else:
            new.append(gate_info)
    
    qcc = QuantumCircuit(qc.nqubits,qc.ncbits)
    qcc.gates = new
    return qcc

def convert_gate_info_to_dag_info(qc: 'QuantumCircuit') -> tuple[list,list]:
    qcc = seperate_measure_instruction(qc)
    qubit_dic = [None for _ in range(qc.nqubits)]
    node_list = []
    edge_list = []
    for idx,gate_info in enumerate(qcc.gates):
        gate = gate_info[0]
        if gate in one_qubit_gates_avaliable.keys():
            qubits = [gate_info[1]]
            node_info = (gate+'_'+str(idx)+'_'+str(qubits),{'qubits':qubits})
        elif gate in two_qubit_gates_avaliable.keys():
            qubits = list(gate_info[1:])
            node_info = (gate+'_'+str(idx)+'_'+str(qubits),{'qubits':qubits})
        elif gate in one_qubit_parameter_gates_avaliable.keys():
            if gate == 'u': # three params
                qubits = [gate_info[-1]]
                params = list(gate_info[1:4])
                node_info = (gate+'_'+str(idx)+'_'+str(qubits),{'qubits':qubits, 'params':params})
            else: # one params
                qubits = [gate_info[-1]]
                params = [gate_info[1]]
                node_info = (gate+'_'+str(idx)+'_'+str(qubits),{'qubits':qubits, 'params':params})        
        elif gate in functional_gates_avaliable.keys():
            if gate == 'measure':
                qubits = [gate_info[1][0]]
                cbits = [gate_info[2][0]]
                node_info = (gate+'_'+str(idx)+'_'+str(qubits),{'qubits':qubits, 'cbits':cbits})
            elif gate == 'barrier':
                qubits = [*gate_info[1]]
                node_info = (gate+'_'+str(idx)+'_'+str(qubits),{'qubits':qubits})
            elif gate == 'reset':
                qubits = [gate_info[1]]
                node_info = (gate+'_'+str(idx)+'_'+str(qubits),{'qubits':qubits})    
        node_list.append(node_info)
        
        if gate in two_qubit_gates_avaliable.keys():
            if qubit_dic[qubits[0]] == qubit_dic[qubits[1]]:
                if qubit_dic[qubits[0]] is not None:
                    edge_info = (qubit_dic[qubits[0]],node_info[0],{"qubit": f'q{qubits[0]}q{qubits[1]}'})
                    edge_list.append(edge_info)
            else:
                for qubit in qubits:
                    if qubit_dic[qubit] is not None:
                        edge_info = (qubit_dic[qubit],node_info[0],{"qubit" : f'q{qubit}'})
                        edge_list.append(edge_info)      
        elif gate in ['barrier']:
            temp = [[],[]]
            for qubit in qubits:
                if qubit_dic[qubit] is not None:
                    edge_info_0 = (qubit_dic[qubit],node_info[0])
                    edge_info_1 = f'q{qubit}'
                    if edge_info_0 in temp[0]:
                        idx = temp[0].index(edge_info_0)
                        temp[1][idx] += edge_info_1
                    else:
                        temp[0].append(edge_info_0)
                        temp[1].append(edge_info_1)
            for idx, edge in enumerate(temp[0]):
                edge_info = (edge[0],edge[1],{"qubit":temp[1][idx]})
                edge_list.append(edge_info)
                    #edge_info = (qubit_dic[qubit],node_info[0],{"qubit" : f'q{qubit}'})
                    #edge_list.append(edge_info)
        else:
            assert(len(qubits) == 1)
            #print(gate_info,qubits[0])
            if qubit_dic[qubits[0]] is not None:
                edge_info = (qubit_dic[qubits[0]],node_info[0],{"qubit" : f'q{qubits[0]}'})
                edge_list.append(edge_info)
                
        for qubit in qubits:
            qubit_dic[qubit] = node_info[0]
    #print(node_list)
    
    return np.array(node_list), np.array(edge_list)

def qc2dag(qc: 'QuantumCircuit') -> 'nx.DiGraph':
    """Converts a quantum circuit into a directed acyclic graph (DAG).

    Args:
        qc (QuantumCircuit): The quantum circuit to be converted.

    Returns:
        nx.DiGraph: A directed acyclic graph representing the quantum circuit, 
        with nodes as operations and edges as dependencies.
    """
    node_list,edge_list = convert_gate_info_to_dag_info(qc)
    dag = nx.DiGraph()
    dag.add_nodes_from(node_list)
    dag.add_edges_from(edge_list)
    return dag

def dag2qc(dag: 'nx.DiGraph',nqubits: int, ncbits: int|None = None) -> 'QuantumCircuit':
    """Converts a directed acyclic graph (DAG) back into a QuantumCircuit.

    Args:
        dag (nx.DiGraph):The DAG representation of the quantum circuit.
        nqubits (int): The number of qubits in the circuit.
        ncbits (int | None, optional): The number of classical bits in the circuit. Defaults to the value of `nqubits`.

    Returns:
        QuantumCircuit: The reconstructed quantum circuit based on the DAG structure.
    """
    if ncbits is None:
        ncbits = nqubits
        
    new = []
    for node in nx.topological_sort(dag):
        gate = node.split('_')[0]
        qubits = dag.nodes[node]['qubits']
        #print(gate,qubits)
        if gate in one_qubit_gates_avaliable.keys():
            new.append((gate,qubits[0]))
        elif gate in two_qubit_gates_avaliable.keys():
            new.append((gate,qubits[0],qubits[1]))
        elif gate in one_qubit_parameter_gates_avaliable.keys():
            params = dag.nodes[node]['params']
            new.append((gate,*params,qubits[0]))
        elif gate in functional_gates_avaliable.keys():
            if gate == 'measure':
                cbits = dag.nodes[node]['cbits']
                new.append((gate,qubits,cbits))
            elif gate == 'barrier':
                new.append((gate,tuple(qubits)))
            elif gate == 'reset':
                new.append((gate,qubits[0]))
                
    qc = QuantumCircuit(nqubits, ncbits)
    qc.gates = new
    
    return qc