"""Helper functions to simplify how things are done"""

from flask import Request, request
from functools import wraps
from typing import Set, Dict

from hikma.server.utils.errors import WebError

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
