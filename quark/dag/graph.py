# MIT License

# Copyright (c) 2025 YL Feng

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
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


import json

import networkx as nx
from loguru import logger
from zee import query_dict_from_string, update_dict_by_string


class ChipManger(object):
    """
    Example: chip info
        ``` {.py3 linenums="1"}
        {'group': {'0': ['Q0', 'Q1'], '1': ['Q5', 'Q8']},
        'Q0': {'Spectrum': {'status': 'OK',
                            'lifetime': 200,
                            'tolerance': 0.01,
                            'history': []},
                'Ramsey': {'status': 'OK',
                        'lifetime': 200,
                        'tolerance': 0.01,
                        'history': []}},
        'C1': {'fidelity': {'status': 'OK',
                            'lifetime': 200,
                            'tolerance': 0.01,
                            'history': []}}
        }
        ```
    """
    VT = {'lifetime': 200,
          'tolerance': 0.01,
          'history': []}

    def __init__(self, info: dict = {}):
        super().__init__()
        self.info = info

    def add_node(self, node: str, value):
        self.info[node] = value

    def update(self, path: str, value):
        update_dict_by_string(self.info, path, value)

    def query(self, path: str):
        return query_dict_from_string(path, self.info)

    def history(self, target: list[str] = ['Q0', 'Q1']):
        return {t: self.query(t) for t in target}

    def checkpoint(self, path: str = ''):
        with open(path, 'w') as f:
            f.write(json.dumps(self.info, indent=4))
        logger.info(f'{path} saved!')

    def load(self, path: str = ''):
        with open(path, 'r') as f:
            self.info = json.loads(f.read())
        logger.info(f'{path} loaded!')

    def __getitem__(self, key: str):
        return self.info[key]


class TaskManager(nx.DiGraph):
    """
    Example: task info
        ``` {.py3 linenums="1"}
        {'edges': [('S21', 'Spectrum'), ('Spectrum', 'PowerRabi'), ('Spectrum', 'TimeRabi'),
                ('PowerRabi', 'Ramsey'), ('TimeRabi', 'Ramsey')],
        'check': {'period': 60, 'method': 'Ramsey'}
        }
        ```
     """

    def __init__(self, task: dict) -> None:
        super().__init__()
        self.checkin = task['check']
        self.add_edges_from(task['graph'])

    def __getitem__(self, key: str):
        return self.nodes[key]  # ['task']

    def parents(self, key: str):
        try:
            return list(self.predecessors(key))
        except Exception as e:
            logger.error(str(e))
            return []

    def children(self, key: str):
        try:
            return list(self.successors(key))
        except Exception as e:
            logger.error(str(e))
            return []

    def draw(self):
        nx.draw(self,
                width=3, alpha=1, edge_color="b", style="-",  # edges
                node_color='r', node_size=500,  # nodes
                with_labels=True, font_size=9, font_family="sans-serif"  # labels
                )
