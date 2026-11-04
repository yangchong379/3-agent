import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from knowledge_agent.models import ChatModel, ModelError, ModelProtocolError

class Opener:
    def __init__(self,responses):self.responses=iter(responses);self.payloads=[]
    def open(self,request,timeout):
        self.payloads.append(json.loads(request.data))
        body=next(self.responses)
        if isinstance(body,Exception):raise body
        return io.BytesIO(json.dumps(body).encode())

def response(name,args,identifier='provider-call'):
    return {'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'reasoning_content':'PRIVATE_PROVIDER_REASONING','tool_calls':[{'id':identifier,'type':'function','function':{'name':name,'arguments':json.dumps({**args,'rationale':'Evidence-based action'})}}]}}]}

class TestAdapter(unittest.TestCase):
    def make(self,opener):return ChatModel('https://api.example.invalid','test-model','not-a-real-key',opener=opener)
    def test_observation_provider_id_and_memory_reasoning_replay(self):
        opener=Opener([response('search_documents',{'query':'年假','cursor':0}),response('read_document',{'doc_id':'D03'},'next-call')]);m=self.make(opener)
        with patch.dict(os.environ,{'MODEL_THINKING':'disabled'}):
            a=m.choose({'question':'年假几天？'},{'run_id':'r'},[])
            history=[{'action':{'tool':a.tool,'arguments':a.arguments,'rationale':a.rationale},'observation':{'ok':True,'matches':[{'doc_id':'D03'}]}}]
            m.choose({'question':'年假几天？'},{'run_id':'r'},history)
        messages=opener.payloads[1]['messages'];self.assertEqual(messages[-1]['tool_call_id'],'provider-call')
        self.assertIn('D03',messages[-1]['content']);self.assertEqual(messages[-2]['reasoning_content'],'PRIVATE_PROVIDER_REASONING')
        self.assertNotIn('PRIVATE_PROVIDER_REASONING',json.dumps(history));self.assertEqual(opener.payloads[0]['tool_choice'],'required')
    def test_http_body_never_leaked(self):
        opener=Opener([urllib.error.HTTPError('https://example.invalid',401,'Bad',{},io.BytesIO(b'credential echo'))])
        with self.assertRaisesRegex(ModelError,'^MODEL_HTTP_401$'):self.make(opener).choose({}, {'run_id':'r'},[])
    def test_multiple_calls_rejected(self):
        r=response('search_documents',{'query':'年假','cursor':0});r['choices'][0]['message']['tool_calls']*=2
        with self.assertRaises(ModelProtocolError):self.make(Opener([r])).choose({}, {'run_id':'r'},[])
    def test_insecure_base_url_rejected(self):
        with self.assertRaises(ValueError):ChatModel('http://example.invalid','model','key')

if __name__=='__main__':unittest.main()
