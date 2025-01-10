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


import networkx as nx
from loguru import logger

from .executor import execute


class TaskManager(nx.DiGraph):
    def __init__(self, edges: list[tuple]) -> None:
        super().__init__()
        self.add_edges_from(edges)

    def check(self, method: str = 'Ramsey', target: list[str] | tuple[str] = ['Q0', 'Q1']):
        return execute(method, target)

    def calibrate(self, method: str = 'Ramsey', target: list[str] | tuple[str] = ['Q0', 'Q1']):
        return execute(method, target)

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
