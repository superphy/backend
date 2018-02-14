import requests

WEBSERVER_PORT = '8000'
API_ROOT = 'api/v0/'


def test_api():
    """
    This is an external test that checks if 'webserver' Flask api started correctly.
    """
    r = requests.get("""http://localhost:{port}/{api_root}alive""".format(port=WEBSERVER_PORT, api_root=API_ROOT))
    # There is a route defined in the Flask API that returns the string 'true' when queried.
    assert r.text == 'true'


import subprocess
import config

WEBSERVER = 'backend_webserver_1'
blazegraph_url = config.database['blazegraph_url']

exc = """docker exec -i {webserver} sh -c""".format(webserver=WEBSERVER)


def test_api_internal():
    # Check that the subprocess setup works before running other tests.
    o = subprocess.check_output("""{exc} {cmd}""".format(exc=exc, cmd='"echo a"'), shell=True, stderr=subprocess.STDOUT)
    o = o.replace('\n', '')
    assert o == 'a'


def test_api_internal_blazegraph():
    # Check that 'webserver' can connect to the 'blazegraph' database.
    cmd = '"curl {blazegraph}"'.format(blazegraph=blazegraph_url)
    o = subprocess.check_output("""{exc} {cmd}""".format(exc=exc, cmd=cmd), shell=True, stderr=subprocess.STDOUT)
    assert '</rdf:RDF>' in o


def test_simple_auth():
    # Retrieve a bearer token from the api.
    r = requests.get("""http://localhost:{port}/{api_root}accounts""".format(port=WEBSERVER_PORT, api_root=API_ROOT))
    token = r.text
    assert type(token) in (str, unicode)

    # Check the bearer token allows access to a protected ping.
    headers = {
        'Authorization': 'Bearer ' + token
    }
    r = requests.get(
        """http://localhost:{port}/{api_root}secured/simple/ping""".format(port=WEBSERVER_PORT, api_root=API_ROOT),
        headers=headers)
    assert r.text == "All good. You only get this message if you're authenticated"
