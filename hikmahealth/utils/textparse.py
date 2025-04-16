def parse_config(text):
    """
    Parses a configuration text into a tuple of key-value pairs.

    It skips lines starting with '#' or that are empty, trims whitespace,
    and removes surrounding quotes from values if they exist.

    Args:
        text (str): Multi-line string containing configuration entries.

    Returns:
        dict: A tuple where each element is a (key, value) pair.
    """
    pairs = []
    for line in text.splitlines():
        # Remove leading and trailing whitespace
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # Ensure the line contains a "="
        if '=' not in line:
            continue

        # Split into key and value on the first '=' found
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()

        # Remove surrounding quotes if present (supports both " and ')
        if len(value) >= 2 and (
            (value[0] == '"' and value[-1] == '"')
            or (value[0] == "'" and value[-1] == "'")
        ):
            value = value[1:-1]

        pairs.append((key, value))

    return dict(tuple(pairs))
