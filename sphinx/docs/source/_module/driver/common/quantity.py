from copy import deepcopy


class Quantity(object):

    def __init__(self, name: str, value=None, ch: int = 0, unit: str = ''):
        self.name = name
        self.isglobal, _ch = (True, 'global') if not ch else (False, ch)
        self.default = dict(value=value, unit=unit, ch=_ch)

    def __repr__(self):
        return f'Quantity({self.name})'


def newcfg(quantlist=[], CHs=[]):
    '''generate a new config'''
    config = {}
    for q in deepcopy(quantlist):
        _cfg = {}
        _default = dict(value=q.default['value'], unit=q.default['unit'])
        for i in CHs:
            _cfg.update({i: deepcopy(_default)})
        if q.isglobal:
            _cfg.update({'global': deepcopy(_default)})
        config.update({q.name: _cfg})
    return config
