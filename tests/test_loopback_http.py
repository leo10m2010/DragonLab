import unittest,threading,ssl
from http.server import HTTPServer,BaseHTTPRequestHandler
from unittest.mock import patch
from loopback_http import get_json,get_bytes
class LoopbackTests(unittest.TestCase):
    def test_local_requests_work_without_tls_context_or_proxy(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.end_headers();self.wfile.write(b'[{"id":"local"}]')
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch('ssl.create_default_context',side_effect=FileNotFoundError('bundled TLS failure')):
                self.assertEqual(get_json(f'http://127.0.0.1:{server.server_port}'),[{'id':'local'}])
        finally:server.shutdown();server.server_close();thread.join()
    def test_external_endpoints_credentials_and_arbitrary_routes_are_rejected(self):
        for endpoint in ('https://127.0.0.1:9223','http://example.com','http://user:password@127.0.0.1','http://127.0.0.1/other'):
            with self.assertRaises(ValueError):get_json(endpoint)
        with self.assertRaises(ValueError):get_bytes('http://127.0.0.1','/not-json')
