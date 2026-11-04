import hashlib
import json
import re
from datetime import date

ALIASES = {
    '报销': ('报销', '报账', '垫付', '费用单', '交票'),
    '年假': ('年假', '带薪假', '休假额度'),
    '导出': ('导出', '渲染', '输出视频'),
    '删除权限': ('删除项目', '删项目', '删除工程'),
    '请假流程': ('请假', '休假申请'),
}
PATTERNS = {
    '报销': r'报销期限为(\d+)天[。；]?',
    '年假': r'年假额度为(\d+)天[。；]?',
    '导出': r'单次视频导出时长上限为(\d+)分钟[。；]?',
    '删除权限': r'删除项目仅限(管理员)[。；]?',
    '请假流程': r'请假流程为(在系统提交申请后由直属主管审批)[。；]?',
}

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def topics(text):
    return [key for key, words in ALIASES.items() if key in text or any(word in text for word in words)]

def validate_request(raw):
    if not isinstance(raw,dict) or set(raw)-{'request_id','question','history'}:raise ValueError('invalid request fields')
    rid=raw.get('request_id');question=raw.get('question');history=raw.get('history',[])
    if not isinstance(rid,str) or not 1<=len(rid)<=100:raise ValueError('request_id required (1..100 characters)')
    if not isinstance(question,str) or not 1<=len(question.strip())<=1000:raise ValueError('question required (1..1000 characters)')
    if not isinstance(history,list) or len(history)>10:raise ValueError('history must have at most 10 turns')
    for h in history:
        if not isinstance(h,dict) or set(h)!={'role','content'} or h['role'] not in ('user','assistant') or not isinstance(h['content'],str) or len(h['content'])>2000:raise ValueError('invalid history')
    return {'request_id':rid,'question':question.strip(),'history':history}

def resolve(req):
    question=req['question']
    if not topics(question):
        previous=next((h['content'] for h in reversed(req['history']) if h['role']=='user' and topics(h['content'])), '')
        if previous and any(x in question for x in ('那','它','这个','几天','多久','专业版','标准版')):
            question=previous+'；追问：'+question
    found=topics(question)
    topic=found[0] if len(found)==1 else None
    supported={'报销':r'多久|期限|几天|多长|何时|最晚|截止|什么时候|交票|提交', '年假':r'多少|几天|额度|多长', '导出':r'多久|多长|几分钟|多少|上限|最长|时长', '删除权限':r'谁|权限|允许|可以|能够|能删', '请假流程':r'怎么|如何|流程|审批|申请'}
    if topic and not re.search(supported[topic],question):topic=None
    return question, topic

def requested_scope(req):
    # The latest user turn overrides prior scope. Assistant history never supplies authority.
    texts=[req['question']]+[h['content'] for h in reversed(req['history']) if h['role']=='user']
    for text in texts:
        present=[scope for scope in ('标准版','专业版') if scope in text]
        if present:return present[0] if len(present)==1 else None
    return None

def vague_followup(req):
    return len(req['question'])<5 or req['question'].startswith(('那','它','这个','然后'))

def validate_data(data):
    if not isinstance(data,dict) or not isinstance(data.get('documents'),list) or len(data['documents'])>100:raise ValueError('documents list required (max 100)')
    seen=set()
    for d in data['documents']:
        if not isinstance(d,dict) or set(d)!={'id','title','version_date','scope','topic','active','text'}:raise ValueError('invalid document fields')
        for key in ('id','title','version_date','scope','topic','text'):
            if not isinstance(d[key],str) or not d[key]:raise ValueError('empty document field')
        if d['id'] in seen or type(d['active']) is not bool or d['topic'] not in ALIASES or len(d['text'])>10000:raise ValueError('invalid document or duplicate ID')
        date.fromisoformat(d['version_date']);seen.add(d['id'])
    return data

def extract(doc):
    # Narrow, documented extraction grammar; unsupported prose is never paraphrased as fact.
    results=[]
    for match in re.finditer(r'(?m)^'+PATTERNS[doc['topic']]+r'$',doc['text']):
        quote=match.group(0);start,end=match.span()
        results.append({'claim_id':digest([doc['id'],doc['version_date'],start,quote])[:20], 'doc_id':doc['id'],'version_date':doc['version_date'],'scope':doc['scope'],'topic':doc['topic'],'value':match.group(1),'quote':quote,'start':start,'end':end})
    return results
