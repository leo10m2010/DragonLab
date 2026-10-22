"""Bounded direct HTTP for local browser debugging; never initializes TLS/proxies."""
import http.client,json
from urllib.parse import urlparse


def get_bytes(endpoint,path,timeout=2):
    parsed=urlparse(endpoint)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ValueError('La conexión al navegador debe ser local')
    if not path.startswith('/json/') or '\r' in path or '\n' in path:raise ValueError('Ruta local inválida')
    connection=http.client.HTTPConnection(parsed.hostname,parsed.port or 80,timeout=timeout)
    try:
        connection.request('GET',path)
        response=connection.getresponse()
        if response.status!=200:raise OSError('El navegador local respondió '+str(response.status))
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('Respuesta local demasiado grande')
        return raw
    finally:connection.close()


def get_json(endpoint,path='/json/list',timeout=2):
    return json.loads(get_bytes(endpoint,path,timeout))
