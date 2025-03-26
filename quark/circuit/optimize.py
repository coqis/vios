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
This module contains the `GateCompressor` class, which is designed to optimize quantum circuits by 
merging or compressing adjacent gates. The primary functionality of this class is to reduce the number 
of gates in a quantum circuit, thereby improving its efficiency and making it more suitable for execution 
on quantum hardware.
"""
import re
import numpy as np
from .quantumcircuit import (QuantumCircuit,
                             one_qubit_gates_available,
                             two_qubit_gates_available,
                             one_qubit_parameter_gates_available,
                             two_qubit_parameter_gates_available,
                             three_qubit_gates_available,
                             )
from .dag import qc2dag,dag2qc
from .decompose import u3_decompose
from .matrix import u_mat,gate_matrix_dict
from .basepasses import TranspilerPass

# 涉及大量dag读取操作，后期尝试rust加速
class GateCompressor(TranspilerPass):
    """A transpiler pass that merges or compresses adjacent gates in a quantum circuit.
    """
    def __init__(self):
        super().__init__()
        self.compressible_gates = ['id','x', 'y', 'z', 'h', 'cx', 'cnot', 'cy', 'cz', 'swap', 'rx', 'ry', 'rz', 'p', 'u', 'rxx', 'ryy', 'rzz','ccx','ccz','cswap']
        self._idx = 1000000

    def remove_identity_gates(self,qc:QuantumCircuit):
        """Remove gates equivalent to the identity operation from a quantum circuit.

        Args:
            qc (QuantumCircuit): The quantum circuit to process, containing a list of gates that may include 
                single- or two-qubit identity-equivalent operations.

        Returns:
            QuantumCircuit: A new quantum circuit with identity-equivalent gates removed.
        """
        # 含参数的单比特/两比特 相当于identity时 移除
        new_qc = qc.deepcopy()
        new = []
        for gate_info in qc.gates:
            gate = gate_info[0]
            if gate in one_qubit_parameter_gates_available.keys():
                params = gate_info[1:-1]
                mat = gate_matrix_dict[gate](*params)
                id = np.eye(mat.shape[0])
                if np.allclose(mat,id) is False:
                    new.append(gate_info)
            elif gate in two_qubit_parameter_gates_available.keys():
                params = gate_info[1:-2]
                mat = gate_matrix_dict[gate](*params)
                id = np.eye(mat.shape[0])
                if np.allclose(mat,id) is False:
                    new.append(gate_info)
            else:
                new.append(gate_info)
        new_qc.gates = new
        return new_qc

    def is_adjacent_gates(self,node1:str,node2:str):
        """Check if two gates are adjacent and can be merged in a quantum circuit.

        Args:
            node1 (str): The first node.
            node2 (str): The second node.

        Returns:
            bool: True if the gates represented by the nodes are adjacent in the DAG and can be merged, False otherwise.
        """
        # 是否是相邻且可以合并的门
        gate1 = node1.split('_')[0]
        gate2 = node2.split('_')[0]
        qubits1 = self.dag.nodes[node1]['qubits']
        qubits2 = self.dag.nodes[node2]['qubits']
        if (gate1==gate2 and 
            gate1 in self.compressible_gates and 
            qubits1==qubits2 and 
            list(self.dag.out_edges(node1))==list(self.dag.in_edges(node2))
            ):
            return True
        else:
            return False
        
    def has_adjacent_gates(self):
        """Check if there exist adjacent and mergeable gates in the DAG representation of the quantum circuit.

        Returns:
            bool: True if there is at least one pair of adjacent and mergeable gates in the DAG, False otherwise.
        """
        # 是否存在相邻且可以合并的门
        for edge in self.dag.edges():
            if self.is_adjacent_gates(edge[0],edge[1]):
                return True
        return False
    
    def compress_adjacent_single_qubit_gates(self,node1:str,node2:str):
        """Compress two adjacent single-qubit gates in a dag by removing them and updating connections.

        Args:
            node1 (str): The first node on the edge.
            node2 (str): The second node on the edge.

        Returns:
            tuple: A tuple containing three lists:
            - nodes_remove (list[str]): Nodes to remove from the DAG (`node1` and `node2`).
            - nodes_added (list): Nodes to add to the DAG (empty in this implementation, as no new gates are created).
            - edges_added (list[tuple]): Edges to add or update in the DAG.
        """
        # compress single qubit gate
        nodes_remove = [node1,node2]
        nodes_added = []
        edges_added = []
        node1_predecessors = list(self.dag.predecessors(node1)) # len = 0 or 1
        if len(node1_predecessors) == 0:
            node1_pre = None
        elif len(node1_predecessors) == 1:
            node1_pre = node1_predecessors[0]
        node2_successors = list(self.dag.successors(node2)) # len = 0 or 1
        if len(node2_successors) == 0:
            node2_suc = None
        elif len(node1_predecessors) == 1:
            node2_suc = node2_successors[0]
        if node1_pre is not None and node2_suc is not None:
            # node1_pre and node2_suc 如果都是双比特门的话可能存在直接连接，判断有没有这种情况？
            if self.dag.has_edge(node1_pre,node2_suc):
                # 若有 则更新边上的qubit
                qubit = self.dag.nodes[node1_pre]['qubits']
                edges_added.append((node1_pre,node2_suc,{'qubit':list(sorted(qubit))}))
            else:
                qubit = self.dag.get_edge_data(node1,node2)['qubit']
                edges_added.append((node1_pre,node2_suc,{'qubit':qubit}))
        return nodes_remove,nodes_added,edges_added
    
    def compress_adjacent_single_parameter_qubit_gates(self,node1:str,node2:str):
        """Compress two adjacent single-qubit parameter gates in a dag by removing them and updating connections.

        Args:
            node1 (str): The first node on the edge.
            node2 (str): The second node on the edge.

        Returns:
            tuple: A tuple containing three lists:
            - nodes_remove (list[str]): Nodes to remove from the DAG (`node1` and `node2`).
            - nodes_added (list): Nodes to add to the DAG (empty in this implementation, as no new gates are created).
            - edges_added (list[tuple]): Edges to add or update in the DAG.
        """
        # compress single qubit gate
        nodes_remove = [node1,node2]
        nodes_added = []
        edges_added = []
        node1_predecessors = list(self.dag.predecessors(node1)) # len = 0 or 1
        if len(node1_predecessors) == 0:
            node1_pre = None
        elif len(node1_predecessors) == 1:
            node1_pre = node1_predecessors[0]
        node2_successors = list(self.dag.successors(node2)) # len = 0 or 1
        if len(node2_successors) == 0:
            node2_suc = None
        elif len(node1_predecessors) == 1:
            node2_suc = node2_successors[0]
        gate = node1.split('_')[0]
        params1 = self.dag.nodes[node1]['params']
        params2 = self.dag.nodes[node2]['params']
        if gate == 'u':
            u_mat1 = u_mat(*params1)
            u_mat2 = u_mat(*params2)
            new_u = u_mat2 @ u_mat1
            theta, phi, lamda, _ = u3_decompose(new_u)
            params = [theta, phi, lamda]                    
        else:
            params = [params1[indx] + params2[indx] for indx in range(len(params1))]
        mat = gate_matrix_dict[gate](*params)
        id = np.eye(mat.shape[0])
        if np.allclose(mat,id):
            if node1_pre is not None and node2_suc is not None:
                # node1_pre and node2_suc 如果都是双比特门的话可能存在直接连接，判断有没有这种情况？
                if self.dag.has_edge(node1_pre,node2_suc):
                    # 若有 则更新边上的qubit
                    qubit = self.dag.nodes[node1_pre]['qubits']
                    edges_added.append((node1_pre,node2_suc,{'qubit':list(sorted(qubit))}))
                else:
                    qubit = self.dag.get_edge_data(node1,node2)['qubit']
                    edges_added.append((node1_pre,node2_suc,{'qubit':qubit}))
        else:
            qubits = self.dag.nodes[node1]['qubits']
            new_node_info = (gate+'_'+str(self.idx)+'_'+str(qubits),{'qubits':qubits,'params':params})
            nodes_added.append(new_node_info)
            if node1_pre is not None:
                qubit = self.dag.get_edge_data(node1_pre,node1)['qubit']
                edges_added.append((node1_pre,new_node_info[0],{'qubit':qubit}))
            if node2_suc is not None:
                qubit = self.dag.get_edge_data(node2,node2_suc)['qubit']
                edges_added.append((new_node_info[0],node2_suc,{'qubit':qubit}))
        return nodes_remove,nodes_added,edges_added
    
    def compress_adjacent_two_qubit_gates(self,node1:str,node2:str):
        """Compress two adjacent two-qubit gates in a dag by removing them and updating connections.

        Args:
            node1 (str): The first node on the edge.
            node2 (str): The second node on the edge.

        Returns:
            tuple: A tuple containing three lists:
            - nodes_remove (list[str]): Nodes to remove from the DAG (`node1` and `node2`).
            - nodes_added (list): Nodes to add to the DAG (empty in this implementation, as no new gates are created).
            - edges_added (list[tuple]): Edges to add or update in the DAG.
        """
        # compress two qubit gate
        nodes_remove = [node1,node2]
        nodes_added = []
        edges_added = []
        node1_predecessors = list(self.dag.predecessors(node1)) 
        if len(node1_predecessors) == 0:
            node1_pre_dic = None
        else:
            node1_pre_dic = {}
            for node1_pre in node1_predecessors:
                qubit = self.dag.get_edge_data(node1_pre,node1)['qubit']
                node1_pre_dic[node1_pre] = qubit
        node2_successors = list(self.dag.successors(node2))
        if len(node2_successors) == 0:
            node2_suc_dic = None
        else:
            node2_suc_dic = {}
            for node2_suc in node2_successors:
                qubit = self.dag.get_edge_data(node2,node2_suc)['qubit']         
                node2_suc_dic[node2_suc] = qubit
        if node1_pre_dic is not None and node2_suc_dic is not None:
            for node1_pre,qubits1 in node1_pre_dic.items():
                for node2_suc,qubits2 in node2_suc_dic.items():
                    common_qubits = [q for q in qubits1 if q in qubits2 ]
                    if len(common_qubits) > 0:
                        if self.dag.has_edge(node1_pre,node2_suc):
                            common_qubits += self.dag.get_edge_data(node1_pre,node2_suc)['qubit']
                            common_qubits = list(set(common_qubits))
                        edges_added.append((node1_pre,node2_suc,{'qubit':common_qubits}))
                    #print('2q',edges_added)
        return nodes_remove,nodes_added,edges_added

    def compress_adjacent_two_qubit_parameter_gates(self,node1:str,node2:str):
        """Compress two adjacent two-qubit parameter gates in a dag by removing them and updating connections.

        Args:
            node1 (str): The first node on the edge.
            node2 (str): The second node on the edge.

        Returns:
            tuple: A tuple containing three lists:
            - nodes_remove (list[str]): Nodes to remove from the DAG (`node1` and `node2`).
            - nodes_added (list): Nodes to add to the DAG (empty in this implementation, as no new gates are created).
            - edges_added (list[tuple]): Edges to add or update in the DAG.
        """
        # compress single qubit gate
        nodes_remove = [node1,node2]
        nodes_added = []
        edges_added = []
        node1_predecessors = list(self.dag.predecessors(node1)) 
        if len(node1_predecessors) == 0:
            node1_pre_dic = None
        else:
            node1_pre_dic = {}
            for node1_pre in node1_predecessors:
                qubit = self.dag.get_edge_data(node1_pre,node1)['qubit']
                node1_pre_dic[node1_pre] = qubit
        node2_successors = list(self.dag.successors(node2))
        if len(node2_successors) == 0:
            node2_suc_dic = None
        else:
            node2_suc_dic = {}
            for node2_suc in node2_successors:
                qubit = self.dag.get_edge_data(node2,node2_suc)['qubit']
                node2_suc_dic[node2_suc] = qubit

        gate = node1.split('_')[0]
        params1 = self.dag.nodes[node1]['params']
        params2 = self.dag.nodes[node2]['params']
        params = [params1[indx] + params2[indx] for indx in range(len(params1))]
        mat = gate_matrix_dict[gate](*params)
        id = np.eye(mat.shape[0])
        if np.allclose(mat,id):
            if node1_pre_dic is not None and node2_suc_dic is not None:
                for node1_pre, qubits1 in node1_pre_dic.items():
                    for node2_suc, qubits2 in node2_suc_dic.items():
                        common_qubits = [q for q in qubits1 if q in qubits2 ]
                        if len(common_qubits) > 0:
                            if self.dag.has_edge(node1_pre,node2_suc):
                                common_qubits += self.dag.get_edge_data(node1_pre,node2_suc)['qubit']
                                common_qubits = list(set(common_qubits))
                            edges_added.append((node1_pre,node2_suc,{'qubit':common_qubits}))
        else:
            qubits = self.dag.nodes[node1]['qubits']
            new_node_info = (gate+'_'+str(self.idx)+'_'+str(qubits),{'qubits':qubits,'params':params})
            nodes_added.append(new_node_info)
            if node1_pre_dic is not None:
                for node1_pre,qubits1 in node1_pre_dic.items():
                    #print((node1_pre,new_node_info[0],{'qubit':qubit}))
                    edges_added.append((node1_pre,new_node_info[0],{'qubit':qubits1}))
            if node2_suc_dic is not None:
                for node2_suc,qubits2 in node2_suc_dic.items():
                    edges_added.append((new_node_info[0],node2_suc,{'qubit':qubits2}))
        return nodes_remove,nodes_added,edges_added

    def compress_adjacent_three_qubit_gates(self,node1,node2):
        """Compress two adjacent three-qubit gates in a dag by removing them and updating connections.

        Args:
            node1 (str): The first node on the edge.
            node2 (str): The second node on the edge.

        Returns:
            tuple: A tuple containing three lists:
            - nodes_remove (list[str]): Nodes to remove from the DAG (`node1` and `node2`).
            - nodes_added (list): Nodes to add to the DAG (empty in this implementation, as no new gates are created).
            - edges_added (list[tuple]): Edges to add or update in the DAG.
        """
        # compress three qubit gate
        nodes_remove = [node1,node2]
        nodes_added = []
        edges_added = []
        node1_predecessors = list(self.dag.predecessors(node1)) 
        if len(node1_predecessors) == 0:
            node1_pre_dic = None
        else:
            node1_pre_dic = {}
            for node1_pre in node1_predecessors:
                qubit = self.dag.get_edge_data(node1_pre,node1)['qubit']
                node1_pre_dic[node1_pre] = qubit
        node2_successors = list(self.dag.successors(node2))
        if len(node2_successors) == 0:
            node2_suc_dic = None
        else:
            node2_suc_dic = {}
            for node2_suc in node2_successors:
                qubit = self.dag.get_edge_data(node2,node2_suc)['qubit']         
                node2_suc_dic[node2_suc] = qubit
        if node1_pre_dic is not None and node2_suc_dic is not None:
            for node1_pre,qubits1 in node1_pre_dic.items():
                for node2_suc,qubits2 in node2_suc_dic.items():
                    common_qubits = [q for q in qubits1 if q in qubits2 ]
                    if len(common_qubits) > 0:
                        if self.dag.has_edge(node1_pre,node2_suc):
                            common_qubits += self.dag.get_edge_data(node1_pre,node2_suc)['qubit']
                            common_qubits = list(set(common_qubits))
                        edges_added.append((node1_pre,node2_suc,{'qubit':common_qubits}))
                    #print('2q',edges_added)
        return nodes_remove,nodes_added,edges_added
            
    def run_compress_once(self,node1:str,node2:str):
        """Compress two adjacent gates.

        Args:
            node1 (str): The first node on the edge.
            node2 (str): The second node on the edge.

        Returns:
            tuple: A tuple containing three lists:
            - nodes_remove (list[str]): Nodes to remove from the DAG (`node1` and `node2`).
            - nodes_added (list): Nodes to add to the DAG (empty in this implementation, as no new gates are created).
            - edges_added (list[tuple]): Edges to add or update in the DAG.
        """
        gate = node1.split('_')[0]
        if gate in one_qubit_gates_available.keys():
            return self.compress_adjacent_single_qubit_gates(node1,node2)
        elif gate in one_qubit_parameter_gates_available.keys():
            return self.compress_adjacent_single_parameter_qubit_gates(node1,node2)
        elif gate in two_qubit_gates_available.keys():
            return self.compress_adjacent_two_qubit_gates(node1,node2)
        elif gate in two_qubit_parameter_gates_available.keys():
            return self.compress_adjacent_two_qubit_parameter_gates(node1,node2)
        elif gate in three_qubit_gates_available.keys():
            return self.compress_adjacent_three_qubit_gates(node1,node2)

    @property
    def idx(self):
        self._idx += 1
        return self._idx
    
    def run(self,qc:QuantumCircuit):
        """Merges or compresses adjacent gates in a quantum circuit.

        Args:
            qc (QuantumCircuit): The input quantum circuit to be optimized.

        Returns:
            QuantumCircuit: A new QuantumCircuit object with merged or compressed 
            gates, preserving the original circuit's functionality but potentially with fewer operations.
        """
        qc1 = self.remove_identity_gates(qc)
        self.dag = qc2dag(qc1)

        compress = self.has_adjacent_gates()
        ncycle = 0
        while compress:
            for edge in self.dag.edges():
                node1,node2 = edge
                if self.is_adjacent_gates(node1,node2):
                    ncycle += 1
                    #print(ncycle,'check',node1,node2)
                    nodes_remove,nodes_added,edges_added = self.run_compress_once(node1,node2)
                    self.dag.remove_nodes_from(nodes_remove)
                    self.dag.add_nodes_from(nodes_added)
                    self.dag.add_edges_from(edges_added)
                    break
            compress = self.has_adjacent_gates()
        new_qc = dag2qc(self.dag,qc1.nqubits,qc1.ncbits)
        return new_qc