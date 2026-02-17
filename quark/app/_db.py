# MIT License

# Copyright (c) 2021 YL Feng <fengyulong@pku.org.cn>

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
import zarr
from loguru import logger
from srpc import loads

sql = {}


def db():
    from quark.proxy import HOME
    path: str = str(HOME / 'checkpoint.db')
    try:
        return sql[path]
    except KeyError:
        print(f'Database path: {path}')
        return sql.setdefault(path, sqlite3.connect(path, check_same_thread=False))


def reshape(raw: np.ndarray | list, shape: tuple | list):
    '''Reshape raw data to original shape and fill zero if shape is larger than raw.

    Args:
        raw (np.ndarray | list): raw data
        shape (tuple | list): sweep shape

    Returns:
        np.ndarray | list: reshaped data

    '''
    try:
        raw = np.asarray(raw)
        idx = np.unravel_index(np.arange(raw.shape[0]), shape)
        data = np.full((*shape, *raw.shape[1:]), 0, raw.dtype)
        data[idx] = raw
    except Exception as e:
        logger.error(f'{e}')
        data = raw

    return data


def get_dataset_by_tid(tid: int, task: bool = False):
    from quark.proxy import HOME

    filename, dataset = get_record_by_tid(tid)[7:9]

    *parts, user, name = Path(filename).parts
    filename = str(HOME / f'dat/{user}/{name}')
    # print(f'Loading dataset from {filename}')

    if filename.endswith('hdf5'):
        f = h5py.File(filename, 'r')
    elif filename.endswith('zarr'):
        f = zarr.open_group(filename, mode='r')
    else:
        logger.error(f'Unsupported file format: {filename}')
        return {}, {}
    group = f[dataset]

    info, data = {}, {}
    info = loads(dict(group.attrs).get('snapshot', '{}'))
    if task:
        return info.get('task', {})

    if not info:
        shape = -1
        info['meta'] = {}
    else:
        shape = []
        try:
            shape = info['meta']['other']['shape']
        except Exception as e:
            for k, v in info['meta']['axis'].items():
                shape.extend(tuple(v.values())[0].shape)

    for k in group.keys():
        ds = group[f'{k}']
        data[k] = ds[:]
        if shape == -1:
            continue

        if filename.endswith('zarr'):
            data[k] = data[k].reshape(-1, *ds.chunks)
        data[k] = reshape(data[k], shape)

    if isinstance(f, h5py.File):
        f.close()

    return info, data


def get_tree_of_file(filename: str):
    """Get HDF5 dataset as a dict

    Args:
        filename (str): filename of an h5 file.
        d (dict, optional): [description]. Defaults to {}.

    Returns:
        dict: dict contains all dataset
    """
    assert Path(filename).exists(), f'File not found: {filename}'
    assert filename.endswith(
        ('hdf5', 'zarr')), f'Unsupported file format: {filename}'

    if filename.endswith('zarr'):
        f = zarr.open_group(filename, mode='r')
        return print(f.tree())

    def file_to_dict(file, d: dict = {}):
        v = {}
        for key, val in file.items():
            if isinstance(val, h5py.Group):
                file_to_dict(val, v)
            else:
                v = f'{str(val.dtype)} {val.shape} {val.nbytes}'  # val.name
            d[key] = v
            v = {}
        return d

    with h5py.File(filename, 'r') as file:
        d = {}
        file_to_dict(file, d)
        # file.close()
        if not d:
            d['data'] = 'dataset not found!'
        return d


def get_commit_by_tid(tid: int = 0):

    # git config --global --add safe.directory path/to/cfg
    try:
        import git

        record = get_record_by_tid(tid)
        ckpt, filename, hexsha = record[5], record[7], record[-1]

        # if 'Desktop' not in filename:
        #     home = Path(filename.split('dat')[0])
        # else:
        #     home = Path.home() / 'Desktop/home'

        from quark.proxy import HOME
        file: Path = (HOME / f'cfg/{ckpt}').with_suffix('.json')
        print(file)

        repo = git.Repo(file.resolve().parent)
        if not tid:
            commit = repo.head.commit
        else:
            commit = repo.commit(hexsha)

        return commit, file
    except Exception as e:
        logger.error(f'Failed to get commit for {tid}: {e}')


def get_tid_by_rid(rid: int):
    return get_record_by_rid(rid)[1]


def get_record_by_tid(tid: int, table: str = 'task'):
    try:
        return db().execute(f'select * from {table} where tid="{tid}"').fetchall()[0]
    except Exception as e:
        logger.error(f'Record {tid} not found: {e}!')


def get_record_by_rid(rid: int, table: str = 'task'):
    try:
        return db().execute(f'select * from {table} where id="{rid}"').fetchall()[0]
    except Exception as e:
        logger.error(f'Record {rid} not found: {e}!')


def get_record_list_by_name(task: str, start: str, end: str, table: str = 'task'):
    try:
        return db().execute(f'select * from {table} where name like "%{task}%" and created between "{start}" and "{end}" limit -1').fetchall()
    except Exception as e:
        logger.error(f'Records not found: {e}!')


def get_record_set_by_name():
    try:
        return db().execute('select distinct task.name from task').fetchall()
    except Exception as e:
        logger.error(f'Records not found: {e}!')
