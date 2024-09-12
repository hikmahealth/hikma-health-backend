import re
from uuid import UUID


def to_snake_case(string):
    """
    Convert a string from camelCase or PascalCase to snake_case.

    This function takes a string in camelCase or PascalCase format and converts it to snake_case.
    It inserts an underscore before any uppercase letter that is preceded by a lowercase letter
    or number, then converts the entire string to lowercase.

    Args:
        string (str): The input string to convert.

    Returns:
        str: The input string converted to snake_case.

    Example:
        >>> to_snake_case("camelCase")
        'camel_case'
        >>> to_snake_case("PascalCase")
        'pascal_case'
        >>> to_snake_case("ABC")
        'abc'
    """
    pattern = re.compile(r'(?<!^)(?=[A-Z])')
    return pattern.sub('_', string).lower()


def convert_dict_keys_to_snake_case(data):
    """
    Recursively converts all dictionary keys to snake_case.

    This function takes a dictionary and converts all of its keys to snake_case format.
    If the value of a key is also a dictionary, it recursively applies the same conversion.
    For non-dictionary values, it returns them unchanged.

    Args:
        data (dict): The input dictionary to convert.

    Returns:
        dict: A new dictionary with all keys converted to snake_case.
              If the input is not a dictionary, it returns the input unchanged.

    Example:
        >>> convert_dict_keys_to_snake_case({'firstName': 'John', 'lastName': 'Doe'})
        {'first_name': 'John', 'last_name': 'Doe'}
    """
    if not isinstance(data, dict):
        return data

    return {
        to_snake_case(key): convert_dict_keys_to_snake_case(value)
        for key, value in data.items()
    }


def is_valid_uuid(uuid_to_test, version=4):
    """
    Check if uuid_to_test is a valid UUID.

     Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}

     Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.

     Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    """

    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test
