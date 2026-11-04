"""Execute actual evidence cases; preserve every input, document set and model/tool trace."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from knowledge_agent.domain import digest
from knowledge_agent.engine import Agent
from knowledge_agent.models import ChatModel, MockModel

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def source_digest():
    return digest({str(p.relative_to(ROOT)).replace('\\','/'):p.read_text(encoding='utf-8') for folder in ('src','tests','scripts') for p in sorted((ROOT/folder).rglob('*.py'))})

def cases():
    return [
      ('normal','员工年假额度多少天？','answered',None,None,24),
      ('conflict','报销期限多久？','conflict',None,None,24),
      ('outside','明天天气如何？','out_of_scope',None,None,24),
      ('paraphrase','自己垫付后最晚几天要交费用单报账？','conflict',None,None,24),
      ('context','那专业版呢？','answered',None,'conversation',24),
      ('scope','视频导出最长多少分钟？','needs_info',None,None,24),
      ('read_retry','年假有几天？','answered','read_document_once',None,24),
      ('tool_failure','报销期限多久？','tool_failed','search_documents_always',None,24),
      ('single_document','报销期限多久？','answered',None,'single',24),
      ('replaced_document','报销期限多久？','answered',None,'replace',24),
      ('permissions','谁可以删除项目？','answered',None,None,24),
      ('process','请假怎么申请？','answered',None,None,24),
      ('unsupported_detail','报销税率多少？','out_of_scope',None,None,24),
      ('step_limit','报销期限多久？','incomplete_step_limit',None,None,1),
    ]

def evaluate(mode,destination,case_names=None):
    selected=cases()
    if case_names is not None:
        if not case_names or len(case_names)!=len(set(case_names)) or set(case_names)-{c[0] for c in selected}:raise ValueError('nonempty unique known cases required')
        selected=[c for c in selected if c[0] in case_names]
    dest=Path(destination)
    if dest.exists():raise ValueError('choose a new evidence directory; never overwrite existing runs')
    dest.mkdir(parents=True)
    base=json.loads((ROOT/'data/documents.json').read_text(encoding='utf-8'))
    started=time.monotonic();records=[]
    for name,question,expected,fault,variant,limit in selected:
        data=copy.deepcopy(base)
        if variant in ('single','replace'):
            next(d for d in data['documents'] if d['id']=='D02')['active']=False
        if variant=='replace':next(d for d in data['documents'] if d['id']=='D01')['text']='报销期限为45天。'
        req={'request_id':name,'question':question,'history':[]}
        folder=dest/name
        def model():return MockModel() if mode=='mock' else ChatModel()
        if variant=='conversation':
            first_req={'request_id':name+'-first','question':'标准版视频导出最长多少分钟？'}
            first=Agent(model(),data).run(first_req);write(folder/'first_run.json',first)
            req['history']=[{'role':'user','content':first_req['question']},{'role':'assistant','content':first['answer']}]
        result=Agent(model(),data,max_steps=limit,fault=fault).run(req)
        write(folder/'input.json',req);write(folder/'dataset.json',data);write(folder/'result.json',result)
        write(ROOT/'examples/inputs'/f'{name}.json',req)
        docs={d['id']:d for d in data['documents']}
        checks={'expected_status':result['status']==expected,'bounded':result['model_calls']<=limit,'citations_are_read_originals':all(c['doc_id'] in result['read_document_ids'] and docs[c['doc_id']]['text'][c['start']:c['end']]==c['quote'] and docs[c['doc_id']]['version_date']==c['version_date'] for c in result['citations']), 'no_archived_citation':all(docs[c['doc_id']]['active'] for c in result['citations'])}
        if name in ('conflict','paraphrase'):checks['conflicting_both_cited']={c['doc_id'] for c in result['citations']}=={'D01','D02'}
        if name in ('normal','read_retry'):checks['supported_value']={c['value'] for c in result['citations']}=={'5'}
        if name=='context':checks['latest_user_scope']={c['doc_id'] for c in result['citations']}=={'D05'} and first['status']=='answered'
        if name in ('single_document','replaced_document'):checks['replacement_changes_value']={c['value'] for c in result['citations']}==({'45'} if variant=='replace' else {'30'})
        if name in ('outside','tool_failure','unsupported_detail','step_limit'):checks['no_unsupported_answer']=not result['citations']
        if name=='conflict':checks['pagination_observed']=any(e.get('observation',{}).get('cursor')==3 for e in result['trace'])
        records.append({'case':name,'expected':expected,'actual':result['status'],'checks':checks,'passed':all(checks.values()),'result':f'{name}/result.json'})
        print(f"{name}: {'PASS' if records[-1]['passed'] else 'FAIL'} ({result['status']})",flush=True)
    summary={'mode':'offline_mock' if mode=='mock' else 'live_model','model':'deterministic-evidence-policy-v1' if mode=='mock' else (result['model'] if records else None),'generated_at_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'source_sha256':source_digest(),'duration_seconds':round(time.monotonic()-started,3),'passed':sum(r['passed'] for r in records),'total':len(records),'cases':records,'boundary':'Synthetic documents and restricted extractive grammar. Mock tests flow only; live decisions require actual trace review.'}
    if mode=='mock':
        stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
        (dest/'tests.txt').write_text(stream.getvalue(),encoding='utf-8');summary['unit_tests']={'run':r.testsRun,'passed':r.wasSuccessful(),'failures':len(r.failures),'errors':len(r.errors)}
    write(dest/'summary.json',summary)
    lines=['# 实际运行评估报告','',f"模式：{summary['mode']}；场景{summary['passed']}/{summary['total']}通过。",'','离线Mock只验证流程；实际远端模型决策只能由live记录证明。每组目录保存输入、原始文档、实际输出及Trace。','','| 场景 | 预期 | 实际 | 断言 | 输出及Trace |','|---|---|---|---|---|']
    lines += [f"| {r['case']} | {r['expected']} | {r['actual']} | {'PASS' if r['passed'] else 'FAIL'} | [result]({r['result']}) |" for r in records]
    lines += ['',f"源码摘要：`{summary['source_sha256']}`",'']
    (dest/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    return 0 if summary['passed']==summary['total'] and summary.get('unit_tests',{}).get('passed',True) else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',choices=['mock','live'],default='mock');p.add_argument('--output',default='examples/runs/mock');p.add_argument('--cases',nargs='+');a=p.parse_args()
    raise SystemExit(evaluate(a.model,a.output,a.cases))
