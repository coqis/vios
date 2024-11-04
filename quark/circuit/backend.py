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
This module contains the Backend class, which processes superconducting chip information into an undirected graph representation. It also supports the creation of custom undirected graphs to serve as virtual chips.
"""

import re,ast
import networkx as nx
import numpy as np
import json
import matplotlib.pyplot as plt 
from typing import Literal

def load_chip_configuration(chip_name):
    with open('./' + chip_name + '_previous-1.json','r') as file:
        chip_info = json.load(file)
    print(f'{chip_name} configuration load done!')
    return chip_info

class Backend:
    """A class to represent a quantum hardware backend as a nx.Graph.
    """
    def __init__(self,chip_name: Literal['Baihua','Custom']):
        """Initialize a Backend object.

        Args:
            chip_info (dict): A dictionary containing information about the quantum chip. This includes details 
            such as the size of the chip, calibration time, priority qubits, available basic gates, and couplers 
            (e.g., CZ gates).
        """
        if chip_name == 'Baihua':
            chip_info = load_chip_configuration(chip_name)
            print('The last calibration time was',chip_info['chip']['calibration_time'])
            self.priority_qubits = ast.literal_eval(chip_info['chip']['priority_qubits'])
            couplers  = chip_info['gate']['CZ']
            self.edges_with_weight = self._get_edges_with_weight(couplers)
            self.size = chip_info['chip']['size']
            self.nodes_with_position = self._get_nodes_with_position(self.size)
        elif chip_name == 'Custom':
            self.edges_with_weight = list()
            self.nodes_with_position = dict()
            self.size = (0,0)
            self.priority_qubits = list()

        self.helightnodes = []

    @property
    def graph(self):
        """Returns the graph representation of the object.
        
        This property method calls `self.get_graph()` to generate and return the graph with nodes and edges.

        Returns:
            networkx.Graph: The graph with nodes and weighted edges.
        """
        return self.get_graph()

    def _get_edges_with_weight(self,couplers):
        coupler_with_fidelity = []
        for cz in couplers.keys():
            if cz == '__order_senstive__': 
                continue
            coupler_qubits = re.findall(r'\d+', cz)
            coupler_qubits = [int(num) for num in coupler_qubits]
            fidelity = couplers[cz]['fidelity']
            #if fidelity != 0:
            coupler_info = (coupler_qubits[0],coupler_qubits[1],fidelity)
            coupler_with_fidelity.append(coupler_info)
        return coupler_with_fidelity
    
    def _get_nodes_with_position(self,size):
        row,col = size
        position = {}
        idx = 0
        for i in range(row):
            for j in range(col):
                if i == 0:
                    position[idx] = (j,i)
                else:
                    position[idx] = (j,-i)
                idx += 1
        return position
    
    def get_graph(self):
        """Constructs and returns an undirected graph with nodes and weighted edges.

        Returns:
            networkx.Graph: An undirected graph with nodes and weighted edges.
        """
        nodes = list(self.nodes_with_position.keys())
        G = nx.Graph()
        G.add_nodes_from(nodes)
        G.add_weighted_edges_from(self.edges_with_weight)
        return G
    
    def draw(self,figsize = (12/1.1, 10/1.1)):
        """Draws the graph with specified node positions, colors, labels, and edge weights.

        Args:
            figsize (tuple, optional): Dimensions of the figure in inches (width, height). Defaults to (12/1.1, 10/1.1).

        Returns:
            None: This function displays the plot but returns None.
        """
        pos = self.nodes_with_position
        node_colors = ['#009E73' if node in self.helightnodes else '#0072B2' for node in self.graph.nodes() ]
        
        plt.figure(figsize=figsize)
        nx.draw(self.graph, pos, with_labels=True, node_color=node_colors, node_size=540,\
                edge_color = 'k',width = 2,\
                font_size=10,font_color='white', font_weight='bold')
        edge_labels = nx.get_edge_attributes(self.graph, 'weight') 
        edge_labels_init = {}
        for k,v in edge_labels.items():
            edge_labels_init[k] = np.round(v,4)
        #print(edge_labels,edge_labels_init)
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels_init,font_size=8)
        #plt.title("Baihua chip")
        plt.show()
        return None