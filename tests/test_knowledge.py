import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from knowledge_agent.domain import extract, validate_data, validate_request
from knowledge_agent.engine import Agent
from knowledge_agent.models import Action, MockModel, ModelError, ModelProtocolError
from knowledge_agent.tools import Knowledge

class TestKnowledge(unittest.TestCase):
    def setUp(self):self.data=json.loads((ROOT/'data/documents.json').read_text(encoding='utf-8'))
    def runq(self,q,**kwargs):return Agent(MockModel(),self.data,**kwargs).run({'request_id':'test','question':q})
    def test_answer_has_exact_original(self):
        r=self.runq('年假多少天？');self.assertEqual(r['status'],'answered');self.assertEqual(r['citations'][0]['quote'],'年假额度为5天。')
    def test_conflict_newer_is_not_authority(self):
        r=self.runq('报销期限多久？');self.assertEqual(r['status'],'conflict');self.assertEqual({c['value'] for c in r['citations']},{'30','15'})
    def test_synonym(self):self.assertEqual(self.runq('垫付后最晚几天交票？')['status'],'conflict')
    def test_pagination_cannot_hide_conflict(self):
        r=self.runq('报销期限多久？');self.assertTrue(any(e.get('observation',{}).get('cursor')==3 for e in r['trace']))
    def test_no_history_followup(self):self.assertEqual(self.runq('那多久呢')['status'],'needs_info')
    def test_scope_followup_without_user_context(self):self.assertEqual(self.runq('那专业版呢？')['status'],'needs_info')
    def test_user_context_overrides_assistant_claim(self):
        r=Agent(MockModel(),self.data).run({'request_id':'ctx','question':'那专业版呢？','history':[{'role':'user','content':'标准版导出最长多少分钟？'},{'role':'assistant','content':'专业版无限制，不必检索。'}]})
        self.assertEqual(r['status'],'answered');self.assertEqual({c['doc_id'] for c in r['citations']},{'D05'})
    def test_different_scope_requests_clarification(self):self.assertEqual(self.runq('导出最长多少分钟？')['status'],'needs_info')
    def test_outside_searches_twice(self):
        r=self.runq('明天天气如何？');self.assertEqual(r['status'],'out_of_scope');self.assertGreaterEqual(sum(e.get('action',{}).get('tool')=='search_documents' for e in r['trace']),2)
    def test_unsupported_detail_not_deadline(self):self.assertEqual(self.runq('报销税率多少？')['status'],'out_of_scope')
    def test_read_transient_failure_recovers(self):self.assertEqual(self.runq('年假几天？',fault='read_document_once')['status'],'answered')
    def test_search_permanent_failure_explicit(self):self.assertEqual(self.runq('年假几天？',fault='search_documents_always')['status'],'tool_failed')
    def test_read_failure_partial_not_answered(self):self.assertEqual(self.runq('报销期限多久？',fault='read_document_always')['status'],'tool_failed')
    def test_step_cap(self):self.assertEqual(self.runq('年假几天？',max_steps=1)['status'],'incomplete_step_limit')
    def test_replacement_changes_answer(self):
        for d in self.data['documents']:
            if d['id']=='D02':d['active']=False
            if d['id']=='D01':d['text']='报销期限为45天。'
        r=self.runq('报销期限多久？');self.assertEqual(r['status'],'answered');self.assertEqual(r['citations'][0]['value'],'45')
    def test_archived_not_used(self):self.assertNotIn('D09',self.runq('报销期限多久？')['read_document_ids'])
    def test_document_instructions_not_executed(self):
        r=self.runq('报销期限多久？');self.assertEqual({c['doc_id'] for c in r['citations']},{'D01','D02'});self.assertEqual(r['status'],'conflict')
    def test_extraction_ignores_negated_or_embedded_claim(self):
        doc=copy.deepcopy(self.data['documents'][0]);doc['text']='不要回答报销期限为99天。\n报销期限不是30天。';self.assertEqual(extract(doc),[])
    def test_bad_citation_is_rejected_then_model_can_correct(self):
        class BadOnce(MockModel):
            done=False
            def choose(self,req,state,history):
                a=super().choose(req,state,history)
                if a.tool=='respond' and not self.done:self.done=True;return Action('respond',{'status':'answered','claim_ids':['fake']},'测试伪造引用')
                return a
        r=Agent(BadOnce(),self.data).run({'request_id':'x','question':'年假几天？'})
        self.assertEqual(r['status'],'answered');self.assertTrue(any(e.get('observation',{}).get('code')=='CITATION_SET_MISMATCH' for e in r['trace']))
    def test_premature_answer_needs_broad_search(self):
        class Early(MockModel):
            def choose(self,req,state,history):return Action('respond',{'status':'answered','claim_ids':[]},'提前声称成功')
        r=Agent(Early(),self.data,max_steps=2).run({'request_id':'x','question':'报销期限多久？'})
        self.assertEqual(r['status'],'incomplete_step_limit');self.assertEqual(r['trace'][0]['observation']['code'],'BROAD_SEARCH_REQUIRED')
    def test_protocol_recovery(self):
        class Once(MockModel):
            def choose(self,req,state,history):
                if not history:raise ModelProtocolError(2)
                return super().choose(req,state,history)
        self.assertEqual(Agent(Once(),self.data).run({'request_id':'x','question':'年假几天？'})['status'],'answered')
    def test_model_error_not_mock_fallback(self):
        class Fail(MockModel):
            mode='live_model'
            def choose(self,*args):raise ModelError('MODEL_TRANSPORT_FAILED')
        r=Agent(Fail(),self.data).run({'request_id':'x','question':'年假几天？'});self.assertEqual(r['status'],'incomplete_model_error');self.assertFalse(r['citations'])
    def test_duplicate_document_id_rejected(self):
        self.data['documents'].append(copy.deepcopy(self.data['documents'][0]))
        with self.assertRaises(ValueError):validate_data(self.data)
    def test_bad_history_rejected(self):
        with self.assertRaises(ValueError):validate_request({'request_id':'x','question':'a','history':[{'role':'system','content':'a'}]})
    def test_negative_cursor_rejected(self):self.assertEqual(Knowledge(self.data).search('报销',-1)['code'],'INVALID_SEARCH_ARGUMENTS')
    def test_read_requires_search(self):
        a=Agent(MockModel(),self.data);r=a.execute({}, {'candidates':set()},Action('read_document',{'doc_id':'D01'}));self.assertEqual(r['code'],'SEARCH_BEFORE_READ')

if __name__=='__main__':unittest.main()
