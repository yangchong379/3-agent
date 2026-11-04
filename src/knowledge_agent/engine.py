from dataclasses import asdict
import copy
from .domain import digest, requested_scope, resolve, validate_request, vague_followup
from .models import ModelError, ModelProtocolError
from .tools import Knowledge

def evidence(state,req):
    topic=state['topic']
    if not topic:
        if vague_followup(req):
            return 'needs_info',[],['请明确问题主题或补充上一轮用户问题。']
        return 'out_of_scope',[],['当前知识库未找到可支持此问题的制度；请提供相关资料。']
    relevant=[c for d in state['read'].values() for c in d['claims'] if c['topic']==topic]
    scope=requested_scope(req)
    scopes={c['scope'] for c in relevant if c['scope'] not in ('全公司','未注明')}
    if scope:relevant=[c for c in relevant if c['scope'] in (scope,'全公司','未注明')]
    if not relevant:return 'out_of_scope',[],['已读资料没有符合当前主题和适用范围的可核对条款；请提供适用制度或联系负责人。']
    if not scope and len(scopes)>1:return 'needs_info',relevant,['请确认适用版本（标准版或专业版），不同范围不可合并回答。']
    if len({c['value'] for c in relevant})>1:return 'conflict',relevant,['条款数值冲突，未提供优先级；请由制度负责人确认适用制度。不能仅凭版本日期选一条。']
    return 'answered',relevant,[]

class Agent:
    def __init__(self,model,data,max_steps=24,fault=None):
        if type(max_steps) is not int or not 1<=max_steps<=100:raise ValueError('max_steps must be 1..100')
        self.model=model;self.knowledge=Knowledge(data,fault);self.max_steps=max_steps

    def execute(self,req,state,action):
        name,args=action.tool,action.arguments
        if not isinstance(args,dict):return {'ok':False,'code':'INVALID_ARGUMENTS'}
        if name=='search_documents':
            if set(args)!={'query','cursor'}:return {'ok':False,'code':'INVALID_ARGUMENTS'}
            result=self.knowledge.search(args['query'],args['cursor'])
            if result['ok']:
                state['queries'].add(args['query'])
                state['candidates'].update(d['doc_id'] for d in result['matches'])
                state['searches'].append(result)
                # Only contiguous page reads prove complete discovery; a jumped cursor cannot.
                query_pages=state['pages'].setdefault(args['query'],{})
                query_pages[args['cursor']]=result
                cursor=0;covered=False
                while cursor in query_pages:
                    page=query_pages[cursor]
                    if page['next_cursor'] is None:covered=True;break
                    cursor=page['next_cursor']
                if covered:state['covered_topics'].update(result['coverage_topics'])
            return result
        if name=='read_document':
            if set(args)!={'doc_id'} or not isinstance(args['doc_id'],str):return {'ok':False,'code':'INVALID_ARGUMENTS'}
            if args['doc_id'] not in state['candidates']:return {'ok':False,'code':'SEARCH_BEFORE_READ'}
            result=self.knowledge.read(args['doc_id'])
            if result['ok']:state['read'][args['doc_id']]=result
            return result
        if name=='respond':
            if set(args)!={'status','claim_ids'} or not isinstance(args['claim_ids'],list) or any(not isinstance(x,str) for x in args['claim_ids']) or len(args['claim_ids'])!=len(set(args['claim_ids'])):return {'ok':False,'code':'INVALID_ARGUMENTS'}
            if args['status']=='tool_failed':
                if state['tool_errors']<2:return {'ok':False,'code':'RETRY_OR_LOOKUP_REQUIRED'}
                state['answer']={'status':'tool_failed','answer':'知识工具多次失败，当前无法可靠回答。已读取片段保留，不能据部分资料排除冲突。','citations':[],'data_gaps':['请稍后重试检索或联系制度负责人。']}
                return {'ok':True,'code':'RESPONSE_READY','status':'tool_failed'}
            topic=state['topic']
            if topic and topic not in state['covered_topics']:return {'ok':False,'code':'BROAD_SEARCH_REQUIRED','topic':topic,'hint':'Use canonical topic as query and read all pages; a narrow search may hide conflicts.'}
            unread=sorted(state['candidates']-state['read'].keys())
            if unread:return {'ok':False,'code':'READ_ORIGINALS_REQUIRED','doc_ids':unread}
            status,claims,gaps=evidence(state,req)
            if status=='out_of_scope' and len(state['queries'])<2:return {'ok':False,'code':'SUPPLEMENTARY_SEARCH_REQUIRED'}
            if args['status']!=status:return {'ok':False,'code':'STATUS_UNSUPPORTED','supported_status':status}
            if set(args['claim_ids'])!={c['claim_id'] for c in claims}:return {'ok':False,'code':'CITATION_SET_MISMATCH','required_claim_ids':[c['claim_id'] for c in claims]}
            quotes=[f"[{c['doc_id']} · {c['version_date']} · {c['scope']}] {c['quote']}" for c in claims]
            prefix={'answered':'根据已读取制度：','conflict':'资料存在冲突，无法确定唯一答案：','needs_info':'需要补充适用范围或问题：','out_of_scope':'现有资料不足以回答。'}[status]
            state['answer']={'status':status,'answer':prefix+('\n'+'\n'.join(quotes) if quotes else '')+('\n'+' '.join(gaps) if gaps else ''),'citations':claims,'data_gaps':gaps}
            return {'ok':True,'code':'RESPONSE_READY','status':status,'citation_count':len(claims)}
        return {'ok':False,'code':'UNKNOWN_TOOL'}

    def run(self,raw):
        req=validate_request(raw);question,topic=resolve(req)
        state={'run_id':req['request_id'],'resolved_question':question,'topic':topic,'queries':set(),'candidates':set(),'covered_topics':set(),'searches':[],'pages':{},'read':{},'tool_errors':0,'answer':None}
        history=[];stop='incomplete_step_limit';error=None
        for step in range(1,self.max_steps+1):
            try:action=self.model.choose(req,copy.deepcopy(state),copy.deepcopy(history))
            except ModelProtocolError as exc:
                history.append({'step':step,'model_error':str(exc),'recoverable':True,'diagnostics':exc.diagnostics});continue
            except ModelError as exc:
                error=str(exc);stop='incomplete_model_error';history.append({'step':step,'model_error':error});break
            observation=self.execute(req,state,action)
            if observation.get('code')=='TOOL_UNAVAILABLE':state['tool_errors']+=1
            history.append({'step':step,'action':asdict(action),'observation':copy.deepcopy(observation)})
            if state['answer']:stop='finished';break
        for i,event in enumerate(history):event['next_action']=history[i+1].get('action',{}).get('tool','model_error') if i+1<len(history) else 'stop'
        answer=state['answer'] or {'status':stop,'answer':'本次未完成，不能给出可靠答案。','citations':[],'data_gaps':['执行步数达到上限或模型接口失败；已读取证据见Trace。']}
        return {'schema_version':'1.0','mode':self.model.mode,'model':self.model.name,'request':req,'resolved_question':question,'dataset_sha256':digest(self.knowledge.data),**answer,'stop_reason':stop,'error':error,'model_calls':len(history),'max_steps':self.max_steps,'trace':history,'read_document_ids':list(state['read']),'boundary':'Synthetic policies, lexical retrieval and extractive answers. Mock verifies workflow only; no hidden reasoning persisted.'}
