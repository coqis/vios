# MIT License

# Copyright (c) 2021 YL Feng

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


import sqlite3
from pathlib import Path

import h5py
import numpy as np
from loguru import logger
from quark import loads

from quark.proxy import QUARK

sql = sqlite3.connect(QUARK/'checkpoint.db', check_same_thread=False)


def get_dataset_by_tid(tid: int, signal: str, shape: tuple | list = []):
    filename, dataset = get_record_by_tid(tid)[7:9]

    info, data = {}, {}
    with h5py.File(filename) as f:
        group = f[dataset]
        info = loads(dict(group.attrs).get('snapshot', '{}'))
        if not shape:
            if not info:
                shape = -1
                info['meta'] = {}
            else:
                shape = []
                for k, v in info['meta']['axis'].items():
                    shape.extend(tuple(v.values())[0].shape)

        for k in group.keys():
            if k != signal or not signal:
                continue
            ds = group[f'{k}']
            if shape == -1:
                data[k] = ds[:]
                continue
            data[k] = np.full((*shape, *ds.shape[1:]), 0, ds.dtype)
            data[k][np.unravel_index(np.arange(ds.shape[0]), shape)] = ds[:]
    return info, data


def get_config_by_tid(tid: int = 0):
    try:
        import git

        ckpt = get_record_by_tid(tid)[5]
        file = (Path.home()/f'Desktop/home/cfg/{ckpt}').with_suffix('.json')

        repo = git.Repo(file.resolve().parent)
        if not tid:
            tree = repo.head.commit.tree
        else:
            tree = repo.commit(get_record_by_tid(tid)[-1]).tree
        config: dict = loads(tree[file.name].data_stream.read().decode())
        return config
    except Exception as e:
        logger.error(f'Failed to get config: {e}')
        return {}


def get_record_by_tid(tid: int, table: str = 'task'):
    try:
        return sql.execute(f'select * from {table} where tid="{tid}"').fetchall()[0]
    except Exception as e:
        logger.error(f'Record not found: {e}!')


def get_record_by_rid(rid: int, table: str = 'task'):
    try:
        return sql.execute(f'select * from {table} where id="{rid}"').fetchall()[0]
    except Exception as e:
        logger.error(f'Record not found: {e}!')


def get_record_list_by_name(task: str, start: str, stop: str, table: str = 'task'):
    try:
        return sql.execute(f'select * from {table} where name like "%{task}%" and created between "{start}" and "{stop}" limit 100').fetchall()
    except Exception as e:
        logger.error(f'Records not found: {e}!')


def get_record_set_by_name():
    try:
        return sql.execute('select distinct task.name from task').fetchall()
    except Exception as e:
        logger.error(f'Records not found: {e}!')
