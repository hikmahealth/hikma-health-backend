import pytest
from hikmahealth.utils.misc import (
    to_snake_case,
    convert_dict_keys_to_snake_case,
    convert_operator,
    is_valid_uuid,
    get_uuid_version,
    safe_json_dumps,
)

import uuid


@pytest.mark.parametrize(
    'input, expected',
    [
        ('camelCase', 'camel_case'),
        ('thisIsATest', 'this_is_a_test'),
        ('anotherExample', 'another_example'),
        ('UPPERCASE', 'uppercase'),
        ('lowercase', 'lowercase'),
        ('Mixed', 'mixed'),
        ('already_snake_case', 'already_snake_case'),
        ('', ''),
        ('PascalCase', 'pascal_case'),
        ('ThisIsATest', 'this_is_a_test'),
        ('AnotherExample', 'another_example'),
        ('already_snake_case', 'already_snake_case'),
        ('this_is_snake', 'this_is_snake'),
        ('A', 'a'),
        ('ABC', 'abc'),
        ('123', '123'),
    ],
)
def test_to_snake_case_camel_case(input, expected):
    assert to_snake_case(input) == expected


def test_convert_dict_keys_to_snake_case():
    # Test basic conversion
    input_dict = {'firstName': 'John', 'lastName': 'Doe', 'phoneNumber': '123-456-7890'}
    expected = {
        'first_name': 'John',
        'last_name': 'Doe',
        'phone_number': '123-456-7890',
    }
    assert convert_dict_keys_to_snake_case(input_dict) == expected

    # Test nested dictionaries
    nested_dict = {
        'userInfo': {
            'firstName': 'John',
            'lastName': 'Doe',
            'contactDetails': {'phoneNumber': '123-456-7890'},
        }
    }
    expected_nested = {
        'user_info': {
            'first_name': 'John',
            'last_name': 'Doe',
            'contact_details': {'phone_number': '123-456-7890'},
        }
    }
    assert convert_dict_keys_to_snake_case(nested_dict) == expected_nested

    # Test non-dictionary input
    assert convert_dict_keys_to_snake_case('not a dict') == 'not a dict'
    assert convert_dict_keys_to_snake_case(None) is None
    assert convert_dict_keys_to_snake_case([1, 2, 3]) == [1, 2, 3]


@pytest.mark.parametrize(
    'operator,case_insensitive,expected',
    [
        ('contains', True, 'ILIKE'),
        ('contains', False, 'LIKE'),
        ('does not contain', True, 'NOT ILIKE'),
        ('does not contain', False, 'NOT LIKE'),
        ('is empty', True, 'IS NULL'),
        ('is not empty', True, 'IS NOT NULL'),
        ('=', True, '='),
        ('!=', True, '!='),
        ('<', True, '<'),
        ('>', True, '>'),
        ('<=', True, '<='),
        ('>=', True, '>='),
        ('invalid_operator', True, 'ILIKE'),
        ('invalid_operator', False, '='),
    ],
)
def test_convert_operator(operator, case_insensitive, expected):
    assert convert_operator(operator, case_insensitive) == expected


@pytest.mark.parametrize(
    'uuid_string,version,expected',
    [
        ('c9bf9e57-1685-4c89-bafb-ff5af830be8a', 4, True),
        ('c9bf9e58', 4, False),
        ('not-a-uuid', 4, False),
        ('', 4, False),
        (None, 4, False),
        ('550e8400-e29b-41d4-a716-446655440000', 4, True),
        # Test different versions
        ('550e8400-e29b-11d4-a716-446655440000', 1, True),  # v1 UUID
        ('550e8400-e29b-21d4-a716-446655440000', 2, True),  # v2 UUID
        ('550e8400-e29b-31d4-a716-446655440000', 3, True),  # v3 UUID
    ],
)
def test_is_valid_uuid(uuid_string, version, expected):
    assert is_valid_uuid(uuid_string, version) == expected


def test_safe_json_dumps():
    # Test basic JSON serialization
    assert safe_json_dumps({'key': 'value'}) == '{"key": "value"}'
    assert safe_json_dumps([1, 2, 3]) == '[1, 2, 3]'
    assert safe_json_dumps('string') == '"string"'
    assert safe_json_dumps(123) == '123'

    # Test with custom default value
    custom_default = '{"default": true}'
    # Non-serializable object (function)
    assert safe_json_dumps(lambda x: x, custom_default) == custom_default

    # Test with default default value ({})
    assert safe_json_dumps(lambda x: x) == '{}'

    # Test complex nested structure
    complex_dict = {
        'string': 'value',
        'number': 123,
        'list': [1, 2, 3],
        'nested': {'key': 'value'},
    }
    expected = '{"string": "value", "number": 123, "list": [1, 2, 3], "nested": {"key": "value"}}'
    assert safe_json_dumps(complex_dict) == expected


def test_get_uuid_version():
    id_pairs_values = [
        (uuid.uuid1(), 1),
        (uuid.uuid3(uuid.NAMESPACE_OID, 'TEST'), 3),
        (uuid.uuid4(), 4),
        (uuid.uuid5(uuid.NAMESPACE_OID, 'thename'), 5),
    ]

    for id, expected_version in id_pairs_values:
        detected_version = get_uuid_version(str(id))
        assert expected_version == detected_version, (
            f'failed to detect python version. version(expected:{expected_version}!=got:{detected_version})'
        )
