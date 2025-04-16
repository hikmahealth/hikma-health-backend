from hikmahealth.utils.textparse import parse_config


def test_parse_config():
    input_env = """
    USERNAME=test
    #USERNAME=admin
    PASSWORD=supersecret
    """
    assert parse_config(input_env) == ({'USERNAME': 'test', 'PASSWORD': 'supersecret'})
