"""Generate the code reference pages and navigation."""

import re
import shutil
import site
import os
from pathlib import Path

import mkdocs_gen_files

import quark.driver

sitepath = Path(quark.driver.__file__).parents[2]


def generate(src: list[Path], dst: str = 'reference', included: str = 'quark', excluded: str = 'none|None'):
    """从py文件生成md目录

    Args:
        src (Path): py文件根目录，无__init__.py
        excluded (str, optional): 不需要生成目录的py文件. Defaults to 'none|None'.
    """
    nav = mkdocs_gen_files.Nav()
    mod_symbol = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'

    print('s' * 10, src)
    ipattern = re.compile(included)
    xpattern = re.compile(excluded)

    _files = {}
    for p in src:
        for path in sorted(p.rglob("*.py")):
            _p = path.as_posix()
            if xpattern.search(_p) or not ipattern.search(_p):
                # print('e'*10, path)
                continue
            # _files.append((p, path))
            key = _p.split('quark')[-1].split('/')[1].removesuffix('.py')
            _files.setdefault(key, []).append((p, path))

    files = []
    for k in sorted(_files):
        files.extend(_files[k])
    # print(files)
    # return
    for _src, path in files:
        # for path in sorted(src.rglob("*.py")):
        # if 'scripts' in str(path):
        # if xpattern.search(str(path)) or not ipattern.search(str(path)):
        #     print('e'*10, path)
        #     continue
        print('>' * 10, path)
        module_path = path.relative_to(_src).with_suffix("")
        doc_path = path.relative_to(_src).with_suffix(".md")
        full_doc_path = Path(dst, doc_path)

        parts = tuple(module_path.parts)
        # print(module_path,parts)

        if parts[-1] == "__init__":
            parts = parts[:-1]
            doc_path = doc_path.with_name("index.md")
            full_doc_path = full_doc_path.with_name("index.md")
        elif parts[-1].startswith("_"):
            continue

        nav_parts = [f"{mod_symbol} {part}" for part in parts]
        nav[tuple(nav_parts)] = doc_path.as_posix()

        with mkdocs_gen_files.open(full_doc_path, "w") as fd:
            ident = ".".join(parts)
            fd.write(f"---\ntitle: {ident}\n---\n\n::: {ident}")

        mkdocs_gen_files.set_edit_path(full_doc_path, ".." / path)

        with mkdocs_gen_files.open(f"{dst}/SUMMARY.md", "w") as nav_file:
            nav_file.writelines(nav.build_literate_nav())


print('*' * 50, '\r\n', quark.driver, '\r\n', sitepath, '\r\n', '*' * 50)

generate([sitepath],  # [Path(__file__).parent] + uninstall quarkstudio
         'modules',
         included='quark/',
         excluded='scripts|tests|sphinx')
