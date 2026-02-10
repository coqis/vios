# MIT License

# Copyright (c) 2025 YL Feng <fengyulong@pku.org.cn>

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


import ast


def replace_function_in_module(module: str, target: str, code: str):
    with open(module, 'r', encoding='utf-8') as f:
        content = f.read()
    old = content.split('\n')

    new = code.strip('\n').split('\n')

    tree = ast.parse(content)
    tnode = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = node.lineno - 1
            end = node.end_lineno - 1
            if node.name == target:
                tnode = node
                break
    if not tnode:
        print(f"function '{target}' not found!")
        updated = old[:end] + ['\n'] + new
    else:
        updated = old[:start] + new + old[end + 1:]

    with open(module, 'w', encoding='utf-8') as f:
        f.write('\n'.join(updated))
