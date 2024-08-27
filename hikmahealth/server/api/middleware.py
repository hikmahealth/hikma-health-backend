from flask import Blueprint, request, Request, jsonify

from typing import Callable, Any
from functools import wraps

from hikmahealth.utils.errors import WebError
from hikmahealth.server.api import auth
from hikmahealth.server.helpers import web as webhelpers

from hikmahealth.server.client import db

from psycopg.rows import dict_row

def authenticated_admin(f):
    @wraps(f)
    def func(*args, **kwargs):
        token = request.headers.get('Authorization', None)

        if token is None:
            raise WebError("missing authentication header", 401)
        
        u = auth.get_user_from_token(token)

        if u.role not in ('admin', 'super_admin'):
            raise WebError("missing admin priviledges", 403)

        return f(u, *args, **kwargs)
    
    return func
                

### If needed - add different auth methods such as for super_admin only.
