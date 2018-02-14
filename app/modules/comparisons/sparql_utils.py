import config


def generate_prefixes():
    """
    Uses namespaces defined in the config.py file to generate all the prefixes you might need in a SPARQL query.
    Returns a string.
    """
    s = ''
    for key in config.namespaces.keys():
        if key is 'root':
            s += 'PREFIX : <{name}> '.format(name=config.namespaces['root'])
        else:
            s += 'PREFIX {prefix}: <{name}> '.format(prefix=key, name=config.namespaces[key])
    return s
