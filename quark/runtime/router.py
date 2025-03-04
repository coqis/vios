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


import json
import shutil
import time
from pathlib import Path

import numpy as np
import requests
from loguru import logger
from srpc import connect

from quark.proxy import QuarkProxy

qc = {}


def savefig(result):
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.use('agg')

    fig, ax = plt.subplots(2, 2, figsize=[9, 9])
    ax = ax.flatten()
    for a in ax:
        a.plot([1, 2, 3])
    plt.savefig('test.png')


def schedule():
    """Execute pre-set scheduled jobs

    Example: the scheduling rules are specified by `etc.server.schedule` using
        |key|type|note|
        |---|---|---|
        |year|int, str|4-digit number|
        |month|int, str|1-12|
        |day|int, str|1-31|
        |week|int, str|1-53|
        |day_of_week|int, str|0-6 or mon, tue, wed, thu, fri, stat, sun|
        |hour|int, str|0-24|
        |minute|int, str|0-59|
        |second|int, str|0-59|

    """
    # dst = shutil.move(Path('../../home/dat/144v3-swj-221013-normalJJ_2023-03-01-22-37-23.hdf5'),Path.home())
    # for path in sorted(Path('../../home/dat').glob('**/*.hdf5')):
    #     print((time.time() - path.stat().st_mtime)/(24*60*60),shutil.disk_usage(path))
    def test1():
        print(time.strftime('%Y-%m-%d %H:%M:%S'), 'do something1 ...')

    def test2():
        print(time.strftime('%Y-%m-%d %H:%M:%S'), 'do something2 ...')

    return {}  # {'job1': test1,'job2': test2}
    # return [(r'C:\Usersddd\sesam\Desktop\home\dat\baqis\testtask_2023-08-31-12-35-12.hdf5',r'\home\dat\baqis\testtask_2023-08-31-12-35-12.hdf5')]


def transfer(tid: int, status: str, result: dict, station: str, left: int, **kwds):
    if not qc:
        print('connecting server ...')
        qc['default'] = connect('QuarkCloud', host=kwds['host'], port=3088)
    qc['default'].transfer(tid, status, result, station, left)


def postprocess(result: dict):
    """Send result back to cloud or whatever you wanna do

    Args:
        result (dict): task result

    Example: result
        ``` {.py3 linenums="1"}
        {'data': {'iq_avg': array([[ 6.98367485 +3.05121544j, 17.98372871+14.02688919j],
                                   [14.9855748 +16.99029603j, 12.00005981+10.98745889j],
                                   [ 5.05074742 +0.96293022j, 18.00112126 +5.98929904j]])},
         'meta': {'tid': 202403122306141782,
                  'name': 'testtask:/PowerRabi1D',
                  'user': 'baqis',
                  'priority': 1,
                  'system': 'checkpoint144',
                  'status': 'Finished',
                  'other': {'shots': 1024,
                            'signal': 'iq_avg',
                            'standby': True,
                            'autorun': True,
                            'filesize': 4000.0},
                  'axis': {'amps': {'amps_Q1001': array([0.1, 0.3, 0.5]),
                                    'amps_Q1101': array([0.1, 0.3, 0.5])}},
                  'committed': 'bbd5533a5863fb88dbb7eba5109ed624abda8e4c',
                  'created': '2024-03-12-23-06-15',
                  'finished': '2024-03-12-23-06-17'}
        }
        ``` 
    """

    # print(result.keys(),result['meta'].keys())

    coqis = result['meta'].get('coqis', {})
    # savefig(result)
    if not coqis.get('eid', ''):  # to sqc
        return QuarkProxy.process(result, False)

    res = QuarkProxy.process(result, True)
    rshot = 0
    post_data = {"task_id": coqis['eid'],
                 "status": res['status'].lower(),
                 "raw": "",
                 "res": "",
                 'transpiled_circuit': res['transpiled'],
                 "server": coqis['systemid']}

    if res['status'].lower() == 'finished':
        rshot = sum(res['count'].values())
        post_data.update({"raw": str(res['count']).replace("\'", "\""),
                          "res": str(res['count']).replace("\'", "\""),
                          })

    try:
        resp = requests.post(url=f"http://124.70.54.59/qbackend/scq_result/",
                             data=post_data,
                             headers={'api_token': coqis['token']})
        logger.info(f'Back to quafu: {resp.text} {rshot}')
    except Exception as e:
        logger.error(f'Failed to post result: {e}')

    return res
