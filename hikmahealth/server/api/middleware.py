from flask import Blueprint, request, Request, jsonify

from typing import Callable, Any
from functools import wraps

from hikmahealth.utils.errors import WebError
from hikmahealth.server.api import auth
from hikmahealth.server.helpers import web as webhelpers

from hikmahealth.server.client import db

from psycopg.rows import dict_row


def authenticated_admin(f):
    """
    Middleware for "admin" role routes
    Admin role is the highest role in the system (second only to super_admin).
    This role has access to all routes and functions in the system. Including what the provider role has access to.
    """

    @wraps(f)
    def func(*args, **kwargs):
        token = request.headers.get('Authorization', None)

        if token is None:
            raise WebError('missing authentication header', 401)

        u = auth.get_user_from_token(token)

        if u.role not in ('admin', 'super_admin'):
            raise WebError('missing admin priviledges', 403)

        return f(u, *args, **kwargs)

    return func


def authenticated_provider(f):
    """
    Middleware for "provider" role routes
    This role fails to perform any admin-only actions
    """

    @wraps(f)
    def func(*args, **kwargs):
        token = request.headers.get('Authorization', None)

        if token is None:
            raise WebError('missing authentication header', 401)

        u = auth.get_user_from_token(token)

        # Provider role also allows admin and super_admin actions
        if u.role not in ('provider', 'admin', 'super_admin'):
            raise WebError('missing provider priviledges', 403)

        return f(u, *args, **kwargs)

    return func


def authenticated_with_role(roles: list[str]):
    """
    Midleware that takes in a list of roles that are allowed to access the route
    This allows for roles to be defined directly in the route decorator - where it is being used.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = request.headers.get('Authorization', None)

            if token is None:
                raise WebError('missing authentication header', 401)

            u = auth.get_user_from_token(token)

            if u.role not in roles:
                raise WebError(
                    f'missing required role. Allowed roles: {", ".join(roles)}', 403
                )

            return f(u, *args, **kwargs)

        return wrapper

    return decorator


# If needed - add different auth methods such as for super_admin, nurse, humanitarian, etc.
