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

import ast
import networkx as nx
import numpy as np
from typing import Literal

def load_chip_basic_info(chip_name):
    import requests
    import json
    session = requests.Session()
    URL = 'http://quark.baqis.ac.cn:81'
    info0 = session.get(f'{URL}/task/backendtest/{chip_name}1') 
    chip_info = json.loads(info0.content.decode())

    if chip_info:
        print(f'{chip_name} configuration loading done!')
        return chip_info
    else:
        print(f'{chip_name} configuration loading failed!')
        return None

class Backend:
    """A class to represent a quantum hardware backend as a nx.Graph.
    """
    def __init__(self,chip_name: Literal['Baihua','Custom']):
        """Initialize a Backend object.

        Args:
            chip_name (str): Chip name, currently only 'Baihua' is avaliable.
        """
        if chip_name == 'Baihua':
            self.chip_info = load_chip_basic_info(chip_name)
            print('The last calibration time was',self.chip_info['calibration_time'])
            self.size = self.chip_info['size']
            self.priority_qubits = ast.literal_eval(self.chip_info['priority_qubits'])
            self.qubits_with_attributes = self._collect_qubits_with_attributes()
            self.couplers_with_attributes = self._collect_couplers_with_attributes()
        elif chip_name == 'Custom':
            print("Please set 'edges_with_attributes' as a list of tuples and 'nodes_with_attributes' as a dictionary.")
            self.chip_info = dict()
            self.size = (0,0)
            self.qubits_with_attributes = list()
            self.couplers_with_attributes = list()
            self.priority_qubits = []
        else:
            raise(ValueError(f'Wrong chip name! {chip_name}'))
    
    @property
    def graph(self):
        """Returns the graph representation of the object.
        
        This property method calls `self.get_graph()` to generate and return the graph with nodes and edges.

        Returns:
            networkx.Graph: The graph with nodes and weighted edges.
        """
        return self.get_graph()
    
    def _collect_qubits_with_attributes(self):
        qubits_with_attributes = []
        for key in self.chip_info['qubits_info'].keys():
            qubit = int(key.split('Q')[1])
            qubits_with_attributes.append((qubit, self.chip_info['qubits_info'][key]))
        return qubits_with_attributes
    
    def _collect_couplers_with_attributes(self):
        couplers_with_attributes = []
        for key in self.chip_info['couplers_info'].keys():
            qubit1, qubit2 = self.chip_info['couplers_info'][key]['qubits_index']
            couplers_with_attributes.append((qubit1,qubit2,self.chip_info['couplers_info'][key]))
        return couplers_with_attributes
    
    def get_graph(self):
        """Constructs and returns an undirected graph with nodes and weighted edges.

        Returns:
            networkx.Graph: An undirected graph with nodes and weighted edges.
        """
        G = nx.Graph()
        G.add_nodes_from(self.qubits_with_attributes)
        G.add_edges_from(self.couplers_with_attributes)
        return G
        
    def draw(self,show_couplers_fidelity:bool = False, show_quibts_attributes:Literal['T1','T2','fidelity','frequancy','']='',highlight_nodes:list = [],save_svg_fname: str|None = None):
        """Draw the chip layout.
    
        Args:
            show_couplers_fidelity (bool, optional): Whether to display the fidelity of couplers. Defaults to False.
            show_quibts_attributes (Literal['T1', 'T2', 'fidelity', 'frequancy', ''], optional): 
                Specify which qubit attribute to display. Options include:
                - 'T1': Display the T1 time of qubits (in microseconds).
                - 'T2': Display the T2 time of qubits (in microseconds).
                - 'fidelity': Display the fidelity of qubits.
                - 'frequancy': Display the frequency of qubits (in GHz).
                - '': Display no attributes.
                Defaults to ''.
            highlight_nodes (list, optional): A list of qubits to highlight. Defaults to an empty list [].
            save_svg_fname (str | None, optional): 
                The filename for saving the drawing as an SVG. If None, the drawing will not be saved. 
                The user is responsible for ensuring the validity of the provided file path. Defaults to None.
    
        Returns:
            None: This function does not return a value but generates and optionally saves the chip layout.
    
        Notes:
            - `highlight_nodes` specifies the qubits to be visually highlighted.
            - `show_couplers_fidelity` and `show_quibts_attributes` can be enabled simultaneously without conflicts.
            - When `save_svg_fname` is provided, the drawing will be saved as an SVG file.
        """
        import matplotlib.pyplot as plt 
        from matplotlib.colors import Normalize
        from matplotlib.cm import ScalarMappable 

        edge_fidelity = nx.get_edge_attributes(self.graph, 'fidelity') 
        if show_couplers_fidelity:
            min_fidelity = sorted(list(edge_fidelity.values()))[0]
            max_fidelity = sorted(list(edge_fidelity.values()))[-1]
            edge_norm = Normalize(vmin = min_fidelity, vmax = max_fidelity)
            edge_cmap = plt.get_cmap('Blues')
            edge_colors = [ScalarMappable(norm = edge_norm, cmap = edge_cmap).to_rgba(fidelity) for fidelity in edge_fidelity.values()]
        else:
            edge_colors = ['#083776' for edge in self.graph.edges()]

        edge_labels = {}
        for k,v in edge_fidelity.items():
            fidelity = np.round(v, 3)
            if 1>= fidelity >0:
                if show_couplers_fidelity:
                    edge_labels[k] = fidelity
                else:
                    edge_labels[k] = self.graph.edges[k].get('index')
            elif fidelity == 0:
                if show_couplers_fidelity:
                    edge_labels[k] = ''
                else:
                    edge_labels[k] = self.graph.edges[k].get('index')

        if show_quibts_attributes != '':
            node_attributes = nx.get_node_attributes(self.graph,show_quibts_attributes)
            min_attributes = sorted(list(node_attributes.values()))[0]
            max_attributes = sorted(list(node_attributes.values()))[-1]
            node_norm = Normalize(vmin = min_attributes, vmax = max_attributes)
            node_cmap = plt.get_cmap('Blues') 
            node_colors = [ScalarMappable(norm = node_norm, cmap = node_cmap).to_rgba(attribute) for attribute in node_attributes.values()]
            node_labels =  {node: np.round(attr, 2) for node, attr in node_attributes.items()}  # 将 'T1' 属性作为标签   
            node_font_size = 8 
            if show_couplers_fidelity:
                figsize = (15, 15)
            else:
                figsize = (15, 13.5)
        else:
            node_colors = ['#083776' for node in self.graph.nodes()]
            node_labels = {node:node for node in self.graph.nodes()}   
            node_font_size = 10 
            if show_couplers_fidelity:
                figsize = (15, 13.5)
            else:
                figsize = (15, 13)

        if len(highlight_nodes) > 0:
            node_colors_update = []
            node_labels_update = {}
            for idx, node in enumerate(self.graph.nodes()):
                if node in highlight_nodes:
                    node_colors_update.append(node_colors[idx])
                    node_labels_update[node] = node_labels[node]
                else:
                    node_colors_update.append('#f3f3f3')
                    node_labels_update[node] = ''
            node_colors = node_colors_update
            node_labels = node_labels_update

            subgraph = self.graph.subgraph(highlight_nodes)
            edge_colors_update = []
            edge_labels_update = {}
            for idx, edge in enumerate(self.graph.edges()):
                if edge in subgraph.edges():
                    edge_colors_update.append(edge_colors[idx])
                    edge_labels_update[edge] = edge_labels[edge]
                else:
                    edge_colors_update.append('#f3f3f3')
                    edge_labels_update[edge] = ''
            edge_colors = edge_colors_update
            edge_labels = edge_labels_update

        fig, ax = plt.subplots(figsize=figsize,) #facecolor='none'
        pos = nx.get_node_attributes(self.graph, 'coordinate') 
        nx.draw(self.graph, pos,ax=ax, with_labels=False, node_color=node_colors, node_size=800, edgecolors='white',  # for node edge\
                edge_color = edge_colors ,width = 18,) #'#5a7f8e'
        nx.draw_networkx_labels(self.graph,pos,labels=node_labels,font_size=node_font_size, font_color='white')
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels,font_size=8, font_color='white',bbox=dict(facecolor='none', edgecolor='none'))
        
        if show_quibts_attributes:
            if show_quibts_attributes == 'T1':
                show_label = 'T1 ($\mu s$)'
            elif show_quibts_attributes == 'T2':
                show_label = 'T2 ($\mu s$)'
            elif show_quibts_attributes == 'fidelity':
                show_label = 'Single qubit gate fidelity'
            elif show_quibts_attributes == 'frequency':
                show_label = 'Frequency (GHz)'
            node_sm = ScalarMappable(cmap=node_cmap, norm=node_norm)
            node_sm.set_array(list(node_attributes.values()))  # 设置包含数据的数组
            if show_couplers_fidelity:
                node_cbar = fig.colorbar(node_sm, ax=ax, orientation='horizontal',pad=0.07, fraction=0.03, aspect=25)
            else:
                node_cbar = fig.colorbar(node_sm, ax=ax, orientation='horizontal',pad=0.001, fraction=0.0333, aspect=25)
            node_cbar.set_label(show_label)

        if show_couplers_fidelity:  
            edge_sm = ScalarMappable(cmap=edge_cmap, norm=edge_norm)# 创建颜色条
            edge_sm.set_array(list(edge_fidelity.values()))  # 设置包含数据的数组
            edge_cbar = fig.colorbar(edge_sm, ax=ax, orientation='horizontal',  pad=0.001, fraction=0.0333, aspect=25)# 调整颜色条大小和位置，放置在底部
            edge_cbar.set_label('CZ fidelity')

        #plt.title("Baihua chip")
        #plt.subplots_adjust(left=0.001, right=0.999, top=0.999, bottom=0.001)
        if save_svg_fname:
            plt.savefig(save_svg_fname + '.svg', transparent=True, dpi=300, bbox_inches='tight') 
        plt.show()
        return None