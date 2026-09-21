"""Run prospectively isolated research; old frozen studies are read-only dependencies."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import time
import math
from .study import *
from benchmarks.codex_v2.runtime import preflight

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def snapshot():
    paths=list(ROOT.glob('*.py'))+[ROOT/'PROTOCOL.md',ROOT/'SEMANTIC_RULES.md',ROOT/'RUBRIC.md',ROOT/'TASK_RENDERED.md',ROOT/'BOUNDARY_AUDIT.md',ROOT/'config.json']+list((ROOT/'data').rglob('*'))
    paths+=list((REPO/'benchmarks/public_v1').glob('*.py'))+[REPO/'benchmarks/public_v1/TASK.md',REPO/'benchmarks/contracts.py',REPO/'benchmarks/codex_v2/runtime.py',REPO/'benchmarks/codex_v2/config.json',REPO/'SKILL.md']
    for name in ('references','assets','examples'):paths+=list((REPO/name).rglob('*'))
    return {str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths)) if p.is_file() and '__pycache__' not in p.parts}
def freeze(path):
    if (ROOT/'EXPOSURE.jsonl').exists():raise ValueError('final_already_exposed_create_new_data_version')
    if Path(path).exists():raise ValueError('freeze_is_immutable')
    write(path,{'version':'research-v3.1','created_at':now(),'files':snapshot(),'final_exposure':'not_executed','old_final':'exposed_regression','model':'gpt-5.6-sol','reasoning_effort':'high'})
def verify(path):
    old=read(path)['files'];current=snapshot()
    if old!=current:raise ValueError('frozen_files_changed:'+','.join(sorted(k for k in set(old)|set(current) if old.get(k)!=current.get(k))))
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ordered_pairs():
    return [(wf,arm) for i,wf in enumerate(WORKFLOWS) for arm in (('without_skill','with_skill') if i%2==0 else ('with_skill','without_skill'))]
def plan(split):
    rows=[{'id':'semantic-review-'+str(i),'phase':'semantic_annotation','split':split} for i in (1,2)]
    pairs=ordered_pairs() if split=='final' else [('stockroom','without_skill')]
    for wf,arm in pairs:
        prefix=wf+'/'+arm
        rows.append({'id':prefix+'/design','phase':'design','workflow':wf,'arm':arm})
        if split=='final':rows.append({'id':prefix+'/review','phase':'design_review','workflow':wf,'arm':arm})
        rows.append({'id':prefix+'/execute','phase':'workflow_execution','workflow':wf,'arm':arm,'cases':[{'case_id':c['case_id'],'expected_status':c['status']} for c in read(ROOT/f'data/workflows/{wf}/{split}_gold.json')]})
    cases=read(ROOT/f'data/semantic/{split}/inputs.json');gold=read(ROOT/f'data/semantic/{split}/gold.json')
    if split=='dev':cases=cases[:1]
    for i,c in enumerate(cases):
        for arm in (('direct','bounded') if i%2==0 else ('bounded','direct')):
            g=gold[c['request_id']]['result']
            rows.append({'id':'semantic/'+c['request_id']+'/'+arm,'phase':'semantic_execution','case_id':c['request_id'],'arm':arm,'failure_grade':grade(c,None,g),'expected_status':g['status']})
    return rows

def validate_development(path):
    report=read(Path(path)/'report.json')
    if report['metadata']['stage']!='dev' or report['metadata'].get('stop_reason'):
        raise ValueError('development_not_completed')
    if not report['annotations'] or not all(v['all_match_author'] for v in report['annotations'].values()):
        raise ValueError('resolve_development_annotation_disagreements_before_freeze')
    if not report['semantic'] or not all(v['acceptance']['value']==1 for v in report['semantic'].values()):
        raise ValueError('development_semantic_execution_not_passed')
    if not report['workflows'] or not all(v['acceptance']['value']==1 for v in report['workflows'].values()):
        raise ValueError('development_workflow_execution_not_passed')
    return {'run':str(Path(path).name),'report_sha256':hashlib.sha256((Path(path)/'report.json').read_bytes()).hexdigest()}

def run(directory,stage,freeze_path,development,continue_development=False):
    dev_evidence=validate_development(development) if stage=='formal' else None
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    split='dev' if stage=='dev' else 'final';config=read(ROOT/'config.json')
    prior=None
    if stage=='dev':
        config.update(max_calls=8,total_timeout_seconds=1200)
        if continue_development:
            previous=Path(development);m=read(previous/'metadata.json')
            if m['stage']!='dev':raise ValueError('previous_stage_must_be_development')
            if m.get('prior_development'):raise ValueError('development_continuation_already_consumed')
            prior_records=[json.loads(line) for line in (previous/'records.jsonl').read_text().splitlines()]
            annotations=[r for r in prior_records if r['phase']=='semantic_annotation' and r['status']=='completed']
            if len(annotations)!=2:raise ValueError('two_prior_model_annotations_required')
            used=m['measurements']['codex_calls'];elapsed=math.ceil(m['wall_ms']/1000)
            config.update(max_calls=8-used,total_timeout_seconds=1200-elapsed)
            if config['max_calls']<=0 or config['total_timeout_seconds']<=0:raise ValueError('development_budget_exhausted')
            prior={'run':previous.name,'metadata':m,'annotations':annotations,'report_sha256':hashlib.sha256((previous/'report.json').read_bytes()).hexdigest()}
            write(directory/'development-prior.json',prior)

    freeze_hash=verify(freeze_path) if stage=='formal' else None
    meta={'version':'research-v3.1','stage':stage,'split':split,'mode':'real_codex','started_at':now(),'config':config,'freeze_sha256':freeze_hash,'billing_cost':None,'human_rework':None,'final_exposure_before_run':(ROOT/'EXPOSURE.jsonl').exists(),'stop_reason':None,'development_evidence':dev_evidence,'source_snapshot_sha256':digest(snapshot()),'prior_development':prior['run'] if prior else None}
    write(directory/'metadata.json',meta);write(directory/'plan.json',[p for p in plan(split) if not (prior and p['phase']=='semantic_annotation')])
    client=(ResearchClient if stage=='formal' else CodexClient)(config,directory/'calls');ctx=Context(client,directory)
    started=time.perf_counter()
    try:
        meta['preflight']=preflight(config);write(directory/'metadata.json',meta)
        if stage=='dev':
            if not prior:
                for i in (1,2):ctx.event('semantic-review-'+str(i),'semantic_annotation',lambda:semantic_review(ctx,'dev'),split='dev')
            value,artifacts=construct(ctx,'stockroom','without_skill','stockroom/without_skill')
            ctx.event('stockroom/without_skill/execute','workflow_execution',lambda:execute_workflow(ctx,'stockroom','without_skill',artifacts,value['artifact_sha256'],'dev'),workflow='stockroom',arm='without_skill')
        else:
            candidates={}
            for wf,arm in ordered_pairs():
                value,artifacts=construct(ctx,wf,arm,wf+'/'+arm);candidates[wf,arm]=(value,artifacts)
            write(directory/'candidate-freeze.json',{'created_at':now(),'candidates':{wf+'/'+arm:info[0]['artifact_sha256'] for (wf,arm),info in candidates.items()},'final_inputs_exposed':False})
            for wf,arm in reversed(ordered_pairs()):
                value,artifacts=candidates[wf,arm]
                ctx.event(wf+'/'+arm+'/review','design_review',lambda w=wf,a=artifacts:model_review(ctx,w,a),workflow=wf,arm=arm)
            # Append, never overwrite, even on a repeat of the frozen experiment.
            with (ROOT/'EXPOSURE.jsonl').open('a') as h:h.write(json.dumps({'at':now(),'run':directory.name,'freeze_sha256':freeze_hash,'status':'exposed','meaning':'new v3 final now available to isolated model contexts; old v1 final already exposed'})+'\n')
            for i in (1,2):ctx.event('semantic-review-'+str(i),'semantic_annotation',lambda:semantic_review(ctx,'final'),split='final')
            for wf,arm in ordered_pairs():
                value,artifacts=candidates[wf,arm]
                ctx.event(wf+'/'+arm+'/execute','workflow_execution',lambda w=wf,a=arm,art=artifacts,v=value:execute_workflow(ctx,w,a,art,v['artifact_sha256'],'final') if v['construction_complete'] else {'status':'not_executed','error':'construction_incomplete','mode':v.get('decision',{}).get('mode')},workflow=wf,arm=arm)
        cases={c['request_id']:c for c in read(ROOT/f'data/semantic/{split}/inputs.json')};gold=read(ROOT/f'data/semantic/{split}/gold.json')
        for row in plan(split):
            if row['phase']!='semantic_execution':continue
            c=cases[row['case_id']]
            def attempt(c=c,arm=row['arm']):
                result=semantic_execute(ctx,c,arm);result['grade']=grade(c,result['output'],gold[c['request_id']]['result']);return result
            ctx.event(row['id'],'semantic_execution',attempt,arm=row['arm'],case_id=c['request_id'])
    except (StopRun,KeyboardInterrupt) as e:meta['stop_reason']=str(e) or 'operator_interrupt'
    except Exception as e:meta['stop_reason']=type(e).__name__+':'+str(e)
    finally:
        meta['stop_reason']=meta.get('stop_reason') or client.stop_reason
        meta.update(ended_at=now(),wall_ms=round((time.perf_counter()-started)*1000,3),measurements=measure(client.calls));write(directory/'metadata.json',meta)
        from .report import generate
        generate(directory)
    print(json.dumps({'directory':str(directory),'stop_reason':meta['stop_reason'],'calls':len(client.calls)}),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('offline')
    for name in ('freeze','verify'):
        a=sub.add_parser(name);a.add_argument('--manifest',default=str(ROOT/'freeze-v3.json'))
    a=sub.add_parser('run');a.add_argument('--stage',choices=('dev','formal'),required=True);a.add_argument('--out',required=True);a.add_argument('--manifest',default=str(ROOT/'freeze-v3.json'));a.add_argument('--development',default='.local/research-v3-dev-1');a.add_argument('--continue-development',action='store_true')
    a=sub.add_parser('report');a.add_argument('directory')
    a=sub.add_parser('export');a.add_argument('source');a.add_argument('destination')
    args=p.parse_args()
    if args.cmd=='offline':
        import unittest
        result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromName('benchmarks.research_v3.test_research'))
        print(json.dumps({'mode':'offline_contract_validation','model_calls':0,'audit':audit_data(),'successful':result.wasSuccessful()}))
        if not result.wasSuccessful():raise SystemExit(1)
    elif args.cmd=='freeze':freeze(args.manifest);print(verify(args.manifest))
    elif args.cmd=='verify':print(verify(args.manifest))
    elif args.cmd=='run':run(args.out,args.stage,args.manifest,args.development,args.continue_development)
    elif args.cmd=='report':
        from .report import generate
        generate(args.directory)
    else:
        from .report import export
        export(args.source,args.destination)
if __name__=='__main__':main()
