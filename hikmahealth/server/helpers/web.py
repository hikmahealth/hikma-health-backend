"""Helper functions to simplify how things are done"""

from flask import Request, request
from functools import wraps
from typing import Set, Dict, TypeVar, Generic

from hikmahealth.utils.errors import WebError
from collections import defaultdict


def apply_dataclass(request: Request, dc, data_type: str | None = None):
    # set optional 
    if data_type is None:
        data_type = 'json'
    
    if data_type == 'json':
        data = request.get_json(force=True)
    elif data_type == 'form':
        data = request.form
    else:
        raise WebError(f'Data type {data_type} not supported', 401)
    
    return dc(**request)

def assert_data_has_keys(request_arg: Request, keys: Set[str], data_type='json'):
    if data_type == 'json':
        data = request_arg.get_json(force=True)
    elif data_type == 'form':
        data = request_arg.form
    else:
        raise WebError(f'Data type {data_type} not supported')

    provided_keys = set(data.keys())
    if not provided_keys.issuperset(keys):
        missing = sorted(keys - set(provided_keys))
        raise WebError(f"Required data not supplied: {','.join(missing)}", 400)
    
    return data

def pluck_required_data_keys(request: Request, keys: set[str]):
    d = request.get_json()
    plucked = []
    try:
        for k in keys:
            plucked.append((k, d[k]))
    except KeyError as err:
        raise WebError("bad request input", 401)
    
    return dict(plucked)


def pluck_optional_data_keys(request: Request, optional_keys: set[str]):
    d = defaultdict(lambda _: None, request.get_json())
    plucked_opts = []
    for k in optional_keys:
        valuemaybe = d.get(k)
        if valuemaybe is not None:
            plucked_opts.append((k, valuemaybe))

    return dict(plucked_opts)
            