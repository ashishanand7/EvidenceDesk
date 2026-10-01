import http.client
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from evidence_desk.server import Handler


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.port=cls.server.server_address[1]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5)

    def request(self,method,path,body=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        connection.request(method,path,body=body,headers=headers or {})
        response=connection.getresponse(); result=(response.status,dict(response.getheaders()),response.read());connection.close();return result

    def test_assets_and_security_headers(self):
        for path in ['/','/app.js','/style.css']:
            with self.subTest(path=path):
                status,headers,body=self.request('GET',path)
                self.assertEqual(status,200);self.assertTrue(body)
                self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
                self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
                self.assertEqual(headers['Cache-Control'],'no-store')

    def test_health(self):
        status,_,body=self.request('GET','/api/health')
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['mode'],'offline-deterministic')

    def test_corpus_and_evaluation(self):
        for path,key,length in [('/api/corpus','documents',12),('/api/evaluation','cases',19)]:
            with self.subTest(path=path):
                status,_,body=self.request('GET',path)
                self.assertEqual(status,200);self.assertEqual(len(json.loads(body)[key]),length)

    def test_ask_roundtrip(self):
        status,_,body=self.request('POST','/api/ask',json.dumps({'entity':'Atlas Reserve','question':'coverage ratio'}),{'Content-Type':'application/json'})
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['claims'][0]['value'],'1.2400')

    def test_repeated_requests_do_not_share_state(self):
        for entity,status_expected in [('Bramble Custody','REVIEW'),('Atlas Reserve','VERIFIED'),('Delta Vault','ABSTAIN'),('Atlas Reserve','VERIFIED')]:
            status,_,body=self.request('POST','/api/ask',json.dumps({'entity':entity,'question':'coverage ratio'}),{'Content-Type':'application/json'})
            self.assertEqual(status,200);self.assertEqual(json.loads(body)['status'],status_expected)

    def test_bad_json_and_schema_return_400(self):
        for body in ['{','[]','null','{"unexpected":1}','{"entity":"x","question":"reserves","as_of":2}']:
            with self.subTest(body=body):
                self.assertEqual(self.request('POST','/api/ask',body,{'Content-Type':'application/json'})[0],400)

    def test_body_bounds_and_content_type(self):
        self.assertEqual(self.request('POST','/api/ask','x'*4097,{'Content-Type':'application/json'})[0],413)
        self.assertEqual(self.request('POST','/api/ask','{}',{'Content-Type':'text/plain'})[0],415)

    def test_host_and_origin_restrictions(self):
        self.assertEqual(self.request('GET','/api/health',headers={'Host':'attacker.example'})[0],403)
        self.assertEqual(self.request('POST','/api/ask','{}',{'Content-Type':'application/json','Origin':'https://attacker.example'})[0],403)

    def test_static_allowlist_blocks_file_paths(self):
        for path in ['/../data/documents.json','/%2e%2e/README.md','/etc/passwd','/data/documents.json']:
            with self.subTest(path=path):self.assertEqual(self.request('GET',path)[0],404)


if __name__=='__main__':unittest.main()
