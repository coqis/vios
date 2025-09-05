import importlib
import importlib.abc
import sys
import time
import threading
import atexit
from collections import defaultdict


# ----------------------------------
# Internal data structures
# ----------------------------------

class ImportNode:
    def __init__(self, name):
        self.name = name
        self.time = 0.0          # own time
        self.total_time = 0.0    # cumulative (including children)
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def set_time(self, t):
        self.time = t

    def compute_total_time(self):
        self.total_time = self.time
        for child in self.children:
            self.total_time += child.compute_total_time()
        return self.total_time

    def to_dict(self):
        return {
            "name": self.name,
            "self_time": round(self.time, 6),
            "total_time": round(self.total_time, 6),
            "children": [child.to_dict() for child in self.children]
        }


# ----------------------------------
# Globals
# ----------------------------------

_local = threading.local()
_local.stack = []

module_nodes = {}       # fullname -> ImportNode
import_roots = []
top_level_time = 0.0


# ----------------------------------
# Hook Loader
# ----------------------------------

class TimingLoader(importlib.abc.Loader):
    def __init__(self, base_loader, fullname):
        self.base_loader = base_loader
        self.fullname = fullname

    def __getattr__(self, name):
        return getattr(self.base_loader, name)

    def create_module(self, spec):
        if hasattr(self.base_loader, 'create_module'):
            return self.base_loader.create_module(spec)
        return None

    def exec_module(self, module):
        global top_level_time

        if not hasattr(_local, 'stack'):
            _local.stack = []

        node = ImportNode(self.fullname)
        module_nodes[self.fullname] = node

        # attach to parent or root
        if _local.stack:
            _local.stack[-1].add_child(node)
        else:
            import_roots.append(node)

        _local.stack.append(node)

        start = time.perf_counter()
        try:
            self.base_loader.exec_module(module)
        finally:
            elapsed = time.perf_counter() - start
            node.set_time(elapsed)

            # Only top-level import counted toward total
            if len(_local.stack) == 1:
                top_level_time += elapsed

            _local.stack.pop()


# ----------------------------------
# Hook Finder
# ----------------------------------

class CumulativeImportFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if getattr(_local, 'in_hook', False):
            return None

        _local.in_hook = True
        try:
            for finder in sys.meta_path:
                if finder is self:
                    continue
                try:
                    spec = finder.find_spec(fullname, path, target)
                    if spec and spec.loader:
                        spec.loader = TimingLoader(spec.loader, fullname)
                        return spec
                except Exception:
                    continue
        finally:
            _local.in_hook = False
        return None


# ----------------------------------
# Hook installation
# ----------------------------------

def install_import_timer():
    sys.meta_path.insert(0, CumulativeImportFinder())


# ----------------------------------
# Print Summary
# ----------------------------------

def print_import_summary():
    print("\n[IMPORT TIME SUMMARY - INCLUSIVE]\n")

    for node in import_roots:
        node.compute_total_time()

    def print_node(node, indent=''):
        print(f"{indent}{node.name:<30} {node.total_time:.3f}s")
        for child in node.children:
            print_node(child, indent + "  ")

    for node in import_roots:
        print_node(node)

    print(f"\nTOTAL IMPORT TIME (top-level only): {top_level_time:.3f}s")
    print("=" * 50)

    import json
    import os

    try:
        json_data = [node.to_dict() for node in import_roots]
        output_file = os.path.join(os.getcwd(), "import_times.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)
        print(f"[JSON Export] Import times written to: {output_file}")
    except Exception as e:
        print(f"[JSON Export Error] {e}")


atexit.register(print_import_summary)


if __name__ == '__main__':

    install_import_timer()

    # 👇 你项目中的常用模块
    # import waveforms
    import quark.runtime
    # import requests

    # import pandas
    # import numpy
    # import matplotlib.pyplot as plt
    # import requests
