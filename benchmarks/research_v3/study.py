"""External contracts and independent evidence harness; no paid-provider path."""
import hashlib
import json
import re
import shutil
import tempfile
import time
from pathlib import Path
from benchmarks.codex_v2.runtime import CodexClient, StopRun, isolated_script, read_artifact
from benchmarks.public_v1.evaluate import grade, audit_gold
from benchmarks.public_v1.runner import screen
from benchmarks.public_v1.contracts import validate_judgment

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
WORKFLOWS=('stockroom','release','customer')
DIMENSIONS=('boundary','context','executor','handoff','feasibility')

def read(path): return json.loads(Path(path).read_text())
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def rules():return (ROOT/'SEMANTIC_RULES.md').read_text()
def task_text():
    old=(REPO/'benchmarks/public_v1/TASK.md').read_text()
    start=old.index('Otherwise judge the profile/reference pair')
    end=old.index('Return exactly these keys:',start)
    mapping='Semantic definitions are exclusively in the v3 rules below. Eligible rows use policy_satisfied; unrelated uses reference_unrelated; conflict uses reference_conflict; unclear uses reference_unclear. Provider/semantic-contract errors use failed/semantic_provider_failure.\n\n'
    old=old[:start]+mapping+old[end:]
    old=old.split('For runner construction, expose')[0]
    return old+'\n\n# Sole semantic definitions for this version\n'+rules()

def semantic_prompt(domain,profile,reference):
    return rules()+'\nClassify only this evidence. No tools needed. Return only the JSON object, no prose.\n'+json.dumps({'domain':domain,'profile':profile,'reference':reference},ensure_ascii=False)

def grade_workflow(workflow,case,actual,expected):
    reasons=[]
    if not isinstance(actual,dict):return {'passed':False,'reasons':['missing_object']}
    keys=set(expected)-{'draft_contains'}
    if workflow=='customer':keys.add('draft')
    if set(actual)!=keys:reasons.append('receipt_fields')
    for key,value in expected.items():
        if key=='draft_contains':continue
        if key not in actual or type(actual[key]) is not type(value) or actual[key]!=value:reasons.append('mismatch:'+key)
    if actual.get('action_performed') is not False:reasons.append('external_action')
    if workflow=='stockroom':
        for key in ('on_hand','available'):
            v=actual.get(key)
            if not isinstance(v,dict) or any(not isinstance(k,str) or type(n) is not int or n<0 for k,n in v.items()):reasons.append('typed_quantities:'+key)
    if workflow=='customer':
        topic=expected['draft_contains'];draft=actual.get('draft')
        if topic is None:
            if draft is not None:reasons.append('draft_without_context')
        elif not isinstance(draft,str) or topic not in draft:reasons.append('draft_topic_missing')
        # Exact receipt commits are checked above; prose safety is also conservatively checked.
        if isinstance(draft,str) and re.search(r'\b(I|we) (have |already )?(sent|booked|refunded|issued a refund|confirmed your booking)\b',draft,re.I):reasons.append('prose_claims_action')
    return {'passed':not reasons,'reasons':sorted(set(reasons))}

def audit_data():
    n=0
    for split in ('dev','final'):
        cases=read(ROOT/f'data/semantic/{split}/inputs.json');g=read(ROOT/f'data/semantic/{split}/gold.json')
        n+=audit_gold(cases,g)
        ann=read(ROOT/f'data/semantic/{split}/annotations.json')
        assert set(ann)==set(g)
    w=0
    for wf in WORKFLOWS:
        for split in ('dev','final'):
            cases=read(ROOT/f'data/workflows/{wf}/{split}_inputs.json');gold=read(ROOT/f'data/workflows/{wf}/{split}_gold.json')
            assert [x['case_id'] for x in cases]==[x['case_id'] for x in gold]
            for c,g in zip(cases,gold):
                actual=dict(g)
                if wf=='customer':actual['draft']=actual.pop('draft_contains')
                assert grade_workflow(wf,c,actual,g)['passed']
            w+=len(cases)
    return {'semantic':n,'workflow':w}

def redact(text):
    text=re.sub(r'codex/optimize-evidence-benchmarks','[branch]',text,flags=re.I)
    text=re.sub(r'(?:build_)?(?:with|without)[ _-]+(?:the[ ]+)?skill','[condition]',text,flags=re.I)
    text=re.sub(r'what[- ]?to[- ]?offload','[design resource]',text,flags=re.I)
    text=re.sub(r'(?:skill/)?(?:references|assets|examples)/[^\s`\]"<>)]*','[resource]',text,flags=re.I)
    text=re.sub(r'(?:skill/)?SKILL\.md','[resource]',text,flags=re.I)
    text='\n'.join('[Resource provenance omitted for anonymous review.]' if re.search(r'\b(skill|treatment|control group)\b',line,re.I) else line for line in text.splitlines())
    return text

def collect_artifacts(workspace):
    base=Path(workspace).resolve();result={};total=0
    for p in sorted(base.rglob('*')):
        rel=p.relative_to(base)
        if rel.parts[0] in ('packet','skill','__pycache__','.git') or p.name in ('dev_inputs.json','input.json','output.json','batch.json','results.json'):continue
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(base) or p.stat().st_size>100000:continue
        try:content=p.read_text()
        except (UnicodeError,OSError):continue
        total+=len(content.encode())
        if total>1000000:raise ValueError('artifact_total_limit')
        result[str(rel)]=content
    return result

def restore(workspace,artifacts):
    base=Path(workspace).resolve()
    for name,content in artifacts.items():
        target=base/name
        if not target.resolve().is_relative_to(base):raise ValueError('unsafe_artifact_path')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)

def packet(workspace,wf,treatment=False):
    workspace=Path(workspace)
    shutil.copytree(ROOT/f'data/workflows/{wf}/packet',workspace/'packet')
    shutil.copyfile(ROOT/f'data/workflows/{wf}/dev_inputs.json',workspace/'dev_inputs.json')
    if treatment:
        dest=workspace/'skill';dest.mkdir();shutil.copyfile(REPO/'SKILL.md',dest/'SKILL.md')
        for name in ('references','assets','examples'):shutil.copytree(REPO/name,dest/name)

def measure(calls):
    result={'codex_calls':len(calls),'tool_calls':sum(c.get('tool_calls',0) for c in calls),'failed_calls':sum(c.get('status')=='failed' for c in calls),'billing_cost':None,'human_rework':None}
    result['usage_complete']=all(all(type(c.get(k)) is int for k in ('input_tokens','cached_input_tokens','output_tokens')) for c in calls)
    for k in ('input_tokens','cached_input_tokens','output_tokens'):result[k+'_known']=sum(c[k] for c in calls if type(c.get(k)) is int)
    return result

def valid_review(v):
    return isinstance(v,dict) and set(v)=={'scores','limitations'} and isinstance(v['limitations'],list) and isinstance(v['scores'],dict) and set(v['scores'])==set(DIMENSIONS) and all(isinstance(v['scores'][k],dict) and type(v['scores'][k].get('score')) is int and 0<=v['scores'][k]['score']<=2 and isinstance(v['scores'][k].get('evidence'),str) and v['scores'][k]['evidence'].strip() for k in DIMENSIONS)

def parse_json(text):
    text=text.strip()
    if text.startswith('```'):
        text='\n'.join(text.splitlines()[1:-1])
    return json.loads(text)

class ResearchClient(CodexClient):
    """Formal per-call limits preserve a failed arm while other arms still run."""
    def complete(self,workspace,prompt,kind):
        try:return super().complete(workspace,prompt,kind)
        except StopRun as exc:
            local=str(exc) in {'Codex_agent_timeout','Codex_build_timeout','Codex_semantic_timeout','Codex_tool_cap','Codex_output_limit'}
            if local and time.monotonic()<self.deadline:
                self.stop_reason=None
                raise RuntimeError('failed_bounded_invocation:'+str(exc)) from exc
            raise

class Context:
    def __init__(self,client,directory):
        self.client=client;self.directory=Path(directory);self.records=[]
    def event(self,id,phase,fn,**tags):
        self.client.check()
        start=time.perf_counter();before=len(self.client.calls)
        result={'id':id,'phase':phase,**tags,'status':'started'}
        try:
            value=fn();result.update(value);result['status']=value.get('status','completed')
        except StopRun as e:
            result.update(status='failed',error=str(e))
            if phase=='workflow_execution':result['cases']=getattr(self.client,'pending_cases',[])
            raise
        except Exception as e:
            result.update(status='failed',error=type(e).__name__+':'+str(e))
        finally:
            calls=self.client.calls[before:];result.update(wall_ms=round((time.perf_counter()-start)*1000,3),call_ids=[c['call_id'] for c in calls],measurements=measure(calls))
            self.records.append(result)
            with (self.directory/'records.jsonl').open('a') as h:h.write(json.dumps(result,ensure_ascii=False)+'\n')
            print(json.dumps({k:result.get(k) for k in ('id','phase','status','error','wall_ms','call_ids')}),flush=True)
        return result

DESIGN_PROMPT='''Read all files in packet/ and the unlabelled dev_inputs.json. Improve the user's original workflow. You are authorized to choose and implement a proportionate solution. You may keep the Agent, offload part or all, or use existing scripts. Do not assume a runner is required. No external action/network/API/key/install is allowed. System Python3 and standard library are available. This phase is design only: write design.md describing the evidence, choices, necessary context, tools/executors, exceptions, investment/reuse, validation and remaining uncertainty. Write decision.json exactly {"mode":"implemented"|"agent_assisted"|"keep_agent","rationale":"...","resources_read":["..."]}. implemented means unattended local software can deliver the desk receipt; agent_assisted means later Codex executes with your local aids; keep_agent means later Codex follows your plan with normal tools. This mode is not a quality label. External receipt definitions are in packet/. Do not inspect outside this workspace. Up to 40 tool items / 240 seconds. Finish with a short receipt. If resources under skill/ exist, consult skill/SKILL.md and load related resources progressively; those are the only additional design resources. This explicit authorization overrides skill pauses for selecting and implementing a candidate. Existing Python is the environment choice. No runtime/platform or paid API should be introduced.'''
BUILD_PROMPT='''Deliver the smallest working version of your own design.md. Target completion within 200 seconds so the 300-second hard cap leaves return time. Avoid generic frameworks, extensive documentation, or an exhaustive test suite. The two provided examples plus a few risk-focused counterexamples are enough for this development budget. Preserve the intended scope. Read packet/ and dev_inputs.json. You may revise design/decision based on development checks. Do not force automation if it is not worthwhile. You have standard Python3/system tools, no packages/network/API/keys/external side effects. No unprovided Skill is installed. If decision mode is implemented, supply invoke.json exactly {"command":["python3","your_entry.py","{input}","{output}"]} (or another available local executable plus arguments), where placeholders are paths to one JSON input case and one JSON output receipt. This is only the external invocation adapter: internal architecture, filenames, helpers and control flow are entirely your choice. Output must obey packet's desk receipt contract. If agent_assisted, provide useful local aids and a clear operational plan; subsequent Codex will use your artifacts. If keep_agent, ensure the plan is operable without any runner. Test with supplied development examples and your own counterexamples. Write build_notes.md documenting checks and any failed attempts. Maximum 40 tool items / 300 seconds. No final evaluation inputs or answers are available. Finish within budget.'''


def successful_resource_reads(client,ids):
    found=[]
    for cid in ids:
        path=client.directory/('call-%03d.events.jsonl'%cid)
        if not path.exists():continue
        for line in path.read_text().splitlines():
            try:e=json.loads(line)
            except ValueError:continue
            item=e.get('item',{});command=item.get('command','')
            if e.get('type')=='item.completed' and item.get('type')=='command_execution' and item.get('exit_code')==0:
                # Retain actual successful read command + returned bytes; listing alone isn't a read.
                if re.search(r'\b(cat|sed|head|tail|read_text|read_bytes)\b',command) and any(marker in command for marker in ('skill/','SKILL.md','references/','assets/','examples/')):
                    found.append({'call_id':cid,'command':command,'output_nonempty':bool(item.get('aggregated_output','').strip())})
    return found

def construct(ctx,wf,arm,prefix):
    target=ctx.directory/'candidates'/prefix;target.mkdir(parents=True)
    construction_error=None
    with tempfile.TemporaryDirectory(prefix='wto-design-') as tmp:
        workspace=Path(tmp);packet(workspace,wf,arm=='with_skill')
        def design():
            ctx.client.complete(workspace,DESIGN_PROMPT,'agent')
            value=parse_json(read_artifact(workspace,'decision.json'))
            if value.get('mode') not in ('implemented','agent_assisted','keep_agent'):raise ValueError('invalid_design_mode')
            read_artifact(workspace,'design.md');return {'decision':value}
        try:
            d=ctx.event(prefix+'/design','design',design,workflow=wf,arm=arm)
            if d['status']=='completed' and d['decision']['mode']!='keep_agent':
                ctx.event(prefix+'/implementation','implementation',lambda:(ctx.client.complete(workspace,BUILD_PROMPT,'build') and {}),workflow=wf,arm=arm)
            artifacts=collect_artifacts(workspace)
            decision=parse_json(artifacts.get('decision.json','{}'))
            if decision.get('mode') not in ('implemented','agent_assisted','keep_agent'):raise ValueError('invalid_final_mode')
            # Only script modes receive deterministic smoke feedback; no hidden final material.
            if decision['mode']=='implemented':
                smoke=script_batch(ctx.client,wf,artifacts,'dev')
                write(target/'dev-smoke-before.json',smoke)
                if any(not x['grade']['passed'] for x in smoke):
                    feedback=[{'case_id':x['case_id'],'error':x.get('error'),'reasons':x['grade']['reasons']} for x in smoke]
                    ctx.event(prefix+'/debug','debug',lambda:(ctx.client.complete(workspace,BUILD_PROMPT+'\nDevelopment smoke feedback: '+json.dumps(feedback),'build') and {}),workflow=wf,arm=arm)
                    artifacts=collect_artifacts(workspace)
                    write(target/'dev-smoke-after.json',script_batch(ctx.client,wf,artifacts,'dev'))
            else:
                write(target/'dev-smoke-before.json',{'status':'not_applicable','reason':'Codex operational modes are tested in later execution; no runner required'})
        except StopRun:
            raise
        except Exception as exc:
            construction_error=type(exc).__name__+':'+str(exc)
        finally:
            artifacts=collect_artifacts(workspace);write(target/'artifacts.json',artifacts)
            records=[r for r in ctx.records if r['id'].startswith(prefix+'/')]
            value={'workflow':wf,'arm':arm,'construction_error':construction_error,'construction_complete':construction_error is None and bool(records) and all(r['status']=='completed' for r in records),'artifact_sha256':digest(artifacts),'frozen_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'records':[r['id'] for r in records], 'resource_reads':successful_resource_reads(ctx.client,[cid for r in records for cid in r['call_ids']]),'debug_inside_implementation_ms':None,'human_rework':None}
            try:value['decision']=parse_json(artifacts.get('decision.json','{}'))
            except ValueError:value['decision']={}
            write(target/'freeze.json',value)
    return value,artifacts


def script_one(config,artifacts,case,wf):
    with tempfile.TemporaryDirectory(prefix='wto-script-') as tmp:
        ws=Path(tmp);packet(ws,wf);restore(ws,artifacts);write(ws/'input.json',case)
        invocation=parse_json(artifacts['invoke.json']);command=invocation.get('command')
        if not isinstance(command,list) or not command or not all(isinstance(a,str) for a in command):raise ValueError('invalid_command')
        args=[a.replace('{input}',str(ws/'input.json')).replace('{output}',str(ws/'output.json')) for a in command]
        code='import subprocess,sys,resource\nresource.setrlimit(resource.RLIMIT_CPU,(20,20))\nresource.setrlimit(resource.RLIMIT_FSIZE,(1000000,1000000))\nr=subprocess.run('+repr(args)+',stdin=subprocess.DEVNULL)\nsys.exit(r.returncode)\n'
        proc=isolated_script(config['cli'],ws,code,timeout=config['candidate_timeout_seconds'])
        if proc['returncode']:raise ValueError('candidate_returncode:'+str(proc['returncode'])+':'+proc['stderr'][-500:])
        return parse_json(read_artifact(ws,'output.json'))

def script_batch(client,wf,artifacts,split):
    rows=[];client.pending_cases=rows
    cases=read(ROOT/f'data/workflows/{wf}/{split}_inputs.json');gold=read(ROOT/f'data/workflows/{wf}/{split}_gold.json')
    for c,g in zip(cases,gold):
        client.check();start=time.perf_counter();a=None;error=None
        try:
            config=dict(client.config,candidate_timeout_seconds=min(client.config['candidate_timeout_seconds'],max(0.1,client.deadline-time.monotonic())))
            a=script_one(config,artifacts,c,wf)
        except Exception as e:error=type(e).__name__+':'+str(e)
        rows.append({'case_id':c['case_id'],'output':a,'error':error,'grade':grade_workflow(wf,c,a,g),'wall_ms':round((time.perf_counter()-start)*1000,3)})
    return rows


def execute_workflow(ctx,wf,arm,artifacts,expected_hash,split):
    if digest(artifacts)!=expected_hash:raise ValueError('candidate_changed_after_freeze')
    ctx.client.pending_cases=[]
    mode=parse_json(artifacts.get('decision.json','{}')).get('mode')
    if mode=='implemented':return {'mode':mode,'cases':script_batch(ctx.client,wf,artifacts,split)}
    if mode not in ('agent_assisted','keep_agent'):raise ValueError('candidate_not_operable')
    cases=read(ROOT/f'data/workflows/{wf}/{split}_inputs.json');gold=read(ROOT/f'data/workflows/{wf}/{split}_gold.json')
    with tempfile.TemporaryDirectory(prefix='wto-operate-') as tmp:
        ws=Path(tmp);packet(ws,wf);restore(ws,artifacts);write(ws/'batch.json',cases)
        ctx.client.complete(ws,'Execute the original workflow for every case in batch.json, using the frozen design.md and any local aids. Read packet/. Treat each case independently. Normal tools and scripts are allowed. Do not change the frozen solution. Do not build a new platform. No external actions/network/API. Write results.json as a JSON array of the external desk receipts, one per input case. Missing facts must not be invented. Maximum 40 tool items / 240 seconds.','agent')
        for name,original in artifacts.items():
            if read_artifact(ws,name)!=original:raise ValueError('frozen_artifact_mutated_during_execution:'+name)
        outputs=parse_json(read_artifact(ws,'results.json'))
        if not isinstance(outputs,list):raise ValueError('batch_output_not_list')
        ids=[a.get('case_id') for a in outputs if isinstance(a,dict)]
        duplicate=len(ids)!=len(set(ids)) or set(ids)!={c['case_id'] for c in cases}
        byid={a['case_id']:a for a in outputs if isinstance(a,dict) and isinstance(a.get('case_id'),str)}
        rows=[]
        for c,g in zip(cases,gold):
            a=byid.get(c['case_id']);scored=grade_workflow(wf,c,a,g)
            if duplicate:scored={'passed':False,'reasons':scored['reasons']+['batch_coverage']}
            rows.append({'case_id':c['case_id'],'output':a,'grade':scored,'wall_ms':None,'error':None})
        return {'mode':mode,'cases':rows,'per_case_latency':'unknown: shared Codex batch; batch wall recorded'}


def model_review(ctx,wf,artifacts):
    with tempfile.TemporaryDirectory(prefix='wto-anonymous-') as tmp:
        ws=Path(tmp);packet(ws,wf)
        # No decision resource list: it is a treatment fingerprint, not design evidence.
        reviewed={k:redact(v) for k,v in artifacts.items() if k!='decision.json'}
        restore(ws,reviewed);(ws/'RUBRIC.md').write_text((ROOT/'RUBRIC.md').read_text())
        answer=ctx.client.complete(ws,'You are an anonymous model design reviewer, not a human annotator. Read packet/, design.md, any implementation/notes and RUBRIC.md. You are not told the experimental group. No final inputs, answers or test scores are provided. Evaluate each rubric dimension with concrete file/excerpt evidence and counterevidence. No bonus merely for code, a diagram or a named design framework. Do not run or repair the artifacts. Return only the rubric JSON.','semantic')
        value=parse_json(answer)
        if not valid_review(value):raise ValueError('invalid_review_schema')
        return {'reviewer_type':'Codex_model_review','review':value,'anonymous_material_sha256':digest(reviewed)}


def semantic_review(ctx,split):
    cases=read(ROOT/f'data/semantic/{split}/inputs.json')
    with tempfile.TemporaryDirectory(prefix='wto-label-') as tmp:
        ws=Path(tmp);(ws/'RULES.md').write_text(rules());write(ws/'materials.json',cases)
        answer=ctx.client.complete(ws,'Model annotation task. Read RULES.md and materials.json. Independently classify each supplied profile/reference pair using only those rules and materials; no gold labels or other reviewer judgments are available. Return only JSON {"labels":[{"case_id":"...","verdict":"corroborated|unrelated|conflict|unclear","rationale":"cite the deciding fact and same-project linkage or absence"}]}. This is a model review, not human annotation.','semantic')
        value=parse_json(answer)
        labels=value.get('labels')
        if not isinstance(labels,list) or {x.get('case_id') for x in labels}!={c['request_id'] for c in cases} or len(labels)!=len(cases) or any(x.get('verdict') not in ('corroborated','unrelated','conflict','unclear') or not x.get('rationale') for x in labels):raise ValueError('annotation_coverage_or_schema')
        return {'reviewer_type':'Codex_model_review','labels':labels}


def semantic_execute(ctx,payload,arm):
    verdicts=[]
    if arm=='bounded':
        def judge(domain,profile,reference):
            with tempfile.TemporaryDirectory(prefix='wto-semantic-') as tmp:
                value=parse_json(ctx.client.complete(tmp,semantic_prompt(domain,profile,reference),'semantic'))
                verdict=validate_judgment(value,profile,reference);verdicts.append(verdict);return value
        output=screen(payload,judge)
        # screen deliberately contains provider errors; still stop subsequent calls on runtime exhaustion.
        return {'output':output,'verdicts':verdicts}
    with tempfile.TemporaryDirectory(prefix='wto-direct-') as tmp:
        ws=Path(tmp);(ws/'TASK.md').write_text(task_text());write(ws/'input.json',payload)
        ctx.client.complete(ws,'Execute TASK.md on input.json now. Normal local tools and temporary scripts are allowed; no need to design a reusable runner. Write only the final complete JSON task receipt to result.json. Read the sole v3 semantic definitions carefully. No external actions or sources. Maximum 40 tool items / 240 seconds.','agent')
        return {'output':parse_json(read_artifact(ws,'result.json'))}
