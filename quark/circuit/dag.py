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
from .quantumcircuit import QuantumCircuit
from .quantumcircuit_helpers import (
    one_qubit_gates_available,
    two_qubit_gates_available,
    three_qubit_gates_available,
    one_qubit_parameter_gates_available,
    two_qubit_parameter_gates_available,
    functional_gates_available,
    convert_gate_info_to_dag_info,
    )

def draw_dag(dag, output='dag_figure.png'):
    """Draws a directed acyclic graph (DAG) representation of a quantum circuit and saves it as an image.

    Args:
        dag (nx.DiGraph): The quantum circuit represented as a directed acyclic graph.
        output (str, optional): The filename for saving the generated DAG image. Defaults to 'dag_figure.png'.
    """
    import matplotlib.pyplot as plt
    
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
        line = ''
        for qubit in data['qubit']:
            line += 'q'+str(qubit)
        edge.attr['label'] = line #data['qubit'] 
    
    A.graph_attr['dpi'] = '300' 
    A.layout(prog='dot')
    
    A.draw(output)

    img = plt.imread(output)
    plt.imshow(img)
    plt.axis('off')
    plt.show()

def qc2dag(qc: 'QuantumCircuit',show_qubits:bool=True) -> 'nx.DiGraph':
    """Converts a quantum circuit into a directed acyclic graph (DAG).

    Args:
        qc (QuantumCircuit): The quantum circuit to be converted.

    Returns:
        nx.DiGraph: A directed acyclic graph representing the quantum circuit, 
        with nodes as operations and edges as dependencies.
    """
    node_list,edge_list = convert_gate_info_to_dag_info(qc.nqubits,qc.qubits,qc.gates,show_qubits=show_qubits)
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
        if gate in one_qubit_gates_available.keys():
            new.append((gate,qubits[0]))
        elif gate in two_qubit_gates_available.keys():
            new.append((gate,qubits[0],qubits[1]))
        elif gate in three_qubit_gates_available.keys():
            new.append((gate,qubits[0],qubits[1],qubits[2]))
        elif gate in one_qubit_parameter_gates_available.keys():
            params = dag.nodes[node]['params']
            new.append((gate,*params,qubits[0]))
        elif gate in two_qubit_parameter_gates_available.keys():
            params = dag.nodes[node]['params']
            new.append((gate,*params,qubits[0],qubits[1]))
        elif gate in functional_gates_available.keys():
            if gate == 'measure':
                cbits = dag.nodes[node]['cbits']
                new.append((gate,qubits,cbits))
            elif gate == 'barrier':
                new.append((gate,tuple(qubits)))
            elif gate == 'delay':
                duration = dag.nodes[node]['duration']
                new.append((gate,duration,tuple(qubits)))
            elif gate == 'reset':
                new.append((gate,qubits[0]))
                
    qc = QuantumCircuit(nqubits, ncbits)
    qc.gates = new
    
    return qc