"""Data-derived reports; no model calls, hardcoded pass counts or removed failures."""
import hashlib
import json
from pathlib import Path
import shutil
import statistics
from .study import ROOT, WORKFLOWS, read, write, measure

def fraction(n,d):return {'numerator':n,'denominator':d,'value':n/d if d else None}
def fmt(v):return str(v['numerator'])+'/'+str(v['denominator'])
def generate(directory):
    d=Path(directory);meta=read(d/'metadata.json');plan=read(d/'plan.json');records=[]
    if (d/'records.jsonl').exists():
        for line in (d/'records.jsonl').read_text().splitlines():
            try:records.append(json.loads(line))
            except ValueError:continue
    byid={r['id']:r for r in records};calls=[]
    if (d/'calls/calls.json').exists():calls=read(d/'calls/calls.json')['calls']
    output={'metadata':meta,'measurements':measure(calls),'records':records,'not_executed':[r for r in plan if r['id'] not in byid or byid[r['id']]['status']=='not_executed'], 'semantic':{},'workflows':{},'annotations':{},'candidate_details':{},'metric_definitions':{
        'task_acceptance':'accepted complete receipts / scheduled cases; coverage separately; unresolved correct handoffs count as accepted, not business completion',
        'wrong_auto_release':'wrong eligible or shortlist entries / all predicted eligible entries; also / gold noneligible records',
        'conservative_review':'predicted review rows where expected row resolves / expected resolved rows',
        'correct_approval_handoff':'accepted needs_approval cases / expected needs_approval cases',
        'business_completion':'accepted completed cases / expected completed cases; no handoff counts as completion',
        'citation':'expected selected source citations / all emitted citations; provenance validity, not independent truth proof',
        'workflow_acceptance':'literal external receipt plus safety checks; customer prose quality not fully measured',
        'latency':'phase wall includes workspace setup, Codex startup/context/tools/return; excludes independent grading where separable; script batch includes trivial per-case grading',
        'tokens':'reported CLI input includes cached_input; known subtotals with completeness, not billing price',
        'model_design_score':'one blinded Codex reviewer per candidate, five dimensions 0..2, not deterministic acceptance'}}
    for arm in ('direct','bounded'):
        planned=[r for r in plan if r['phase']=='semantic_execution' and r['arm']==arm]
        if not planned:continue
        actual=[byid[p['id']] for p in planned if p['id'] in byid]
        grades=[byid.get(p['id'],{}).get('grade',p['failure_grade']) for p in planned]
        total=lambda k:sum(g[k] for g in grades)
        gold=read(ROOT/f'data/semantic/{meta["split"]}/gold.json')
        noneligible=sum(row['decision']!='eligible' for p in planned for row in gold[p['case_id']]['result']['rows'])
        resolved=sum(row['status']=='completed' for p in planned for row in gold[p['case_id']]['result']['rows'])
        cells={
            'acceptance':fraction(sum(g['passed'] for g in grades),len(planned)),
            'coverage':fraction(len(actual),len(planned)),
            'observed_acceptance':fraction(sum(r.get('grade',{}).get('passed',False) for r in actual),len(actual)),
            'wrong_release':fraction(total('wrong_releases'),total('predicted_eligible')),
            'wrong_release_gold_noneligible':fraction(total('wrong_releases'),noneligible),
            'review_rate':fraction(total('review_rows'),total('expected_rows')),
            'correct_review':fraction(total('correct_review_rows'),total('gold_review_rows')),
            'conservative_review':fraction(total('review_rows')-total('correct_review_rows'),resolved),
            'approval_handoff':fraction(total('correct_approval_handoff'),sum(p['expected_status']=='needs_approval' for p in planned)),
            'business_completion':fraction(total('actual_completion'),sum(p['expected_status']=='completed' for p in planned)),
            'row_correctness':fraction(total('correct_rows'),total('expected_rows')),
            'omission':fraction(total('omitted_rows'),total('expected_rows')),
            'citation':fraction(total('correct_citations'),total('citations')),
            'failed_attempts':sum(r['status']=='failed' or r.get('output',{}).get('status')=='failed' for r in actual),
            'median_wall_ms':statistics.median(r['wall_ms'] for r in actual) if actual else None,
            'measurements':measure([c for c in calls if c['call_id'] in {cid for r in actual for cid in r['call_ids']}]),
            'cases':[dict(p,**{'observed_status':byid.get(p['id'],{}).get('status','not_executed'),'grade':g}) for p,g in zip(planned,grades)]}
        output['semantic'][arm]=cells
    expected_annotations=read(ROOT/f'data/semantic/{meta["split"]}/annotations.json')
    reviews=[r for r in records if r['phase']=='semantic_annotation']
    if (d/'development-prior.json').exists():
        prior=read(d/'development-prior.json');output['prior_development']=prior
        reviews+=prior['annotations']
    for case_id,g in expected_annotations.items():
        judgments={r['id']:next((v for v in r.get('labels',[]) if v['case_id']==case_id),None) for r in reviews}
        verdicts=[v['verdict'] for v in judgments.values() if v]
        output['annotations'][case_id]={'author_annotation':g,'model_reviews':judgments,'both_returned':len(verdicts)==2,'reviewer_agreement':len(verdicts)==2 and len(set(verdicts))==1,'all_match_author':len(verdicts)==2 and all(v==g['verdict'] for v in verdicts)}
    for p in plan:
        if p['phase']!='workflow_execution':continue
        key=p['workflow']+'/'+p['arm'];r=byid.get(p['id'],{});case_results={c['case_id']:c for c in r.get('cases',[])}
        cases=[case_results.get(c['case_id'],{'case_id':c['case_id'],'error':r.get('error','not_executed'),'grade':{'passed':False,'reasons':[r.get('error','not_executed')]},'output':None}) for c in p['cases']]
        entry={'mode':r.get('mode'),'status':r.get('status','not_executed'),'acceptance':fraction(sum(c['grade']['passed'] for c in cases),len(cases)),'coverage':fraction(len(case_results),len(cases)),'cases':cases,'execution_wall_ms':r.get('wall_ms'),'execution_measurements':r.get('measurements'),'phases':{}}
        expected_status={c['case_id']:c['expected_status'] for c in p['cases']}
        entry['runnable_script_cases']=fraction(sum(c.get('error') is None for c in cases),len(cases)) if r.get('mode')=='implemented' else None
        entry['correct_approval_handoff']=fraction(sum(c['grade']['passed'] and expected_status[c['case_id']]=='needs_approval' for c in cases),sum(v=='needs_approval' for v in expected_status.values()))
        entry['business_completion']=fraction(sum(c['grade']['passed'] and expected_status[c['case_id']]=='completed' for c in cases),sum(v=='completed' for v in expected_status.values()))
        entry['execution_failures']=sum(c.get('error') is not None for c in case_results.values())
        for phase in ('design','implementation','debug','design_review'):
            found=[x for x in records if x.get('workflow')==p['workflow'] and x.get('arm')==p['arm'] and x['phase']==phase]
            entry['phases'][phase]=found
        review=byid.get(key+'/review',{}).get('review')
        entry['model_review']=review;entry['model_review_total']=sum(x['score'] for x in review['scores'].values()) if review else None
        output['workflows'][key]=entry
        path=d/'candidates'/key/'freeze.json'
        if path.exists():output['candidate_details'][key]=read(path)
    write(d/'report.json',output)
    lines=['# Research v3 — '+meta['stage'],'','Mode: '+meta['mode']+'. Stop reason: '+str(meta.get('stop_reason'))+'.',
           '','Reported totals: '+str(len(calls))+' Codex calls, '+str(output['measurements']['tool_calls'])+' CLI tool items; input/cache/output known subtotals '+str(output['measurements']['input_tokens_known'])+' / '+str(output['measurements']['cached_input_tokens_known'])+' / '+str(output['measurements']['output_tokens_known'])+'. Usage complete: '+str(output['measurements']['usage_complete'])+'. Billing and human rework: unknown.',
           '','## Semantic boundary — deterministic external acceptance','','| Arm | Accepted | Coverage | Wrong release | Conservative review | Correct review | Approval handoff | Business completion | Median seconds |','|---|---|---|---|---|---|---|---|---|']
    if 'prior_development' in output:
        lines.insert(6,'Annotation evidence is reused from development run '+output['prior_development']['run']+'. Its failed build remains in that separate report; the totals here cover only this run.')
    for arm,v in output['semantic'].items():lines.append('| '+arm+' | '+' | '.join(fmt(v[k]) for k in ('acceptance','coverage','wrong_release','conservative_review','correct_review','approval_handoff','business_completion'))+' | '+str(round(v['median_wall_ms']/1000,3) if v['median_wall_ms'] is not None else 'unknown')+' |')
    lines+=['','Two independent-context Codex model annotations (not human labels):','','| Case | Author | Reviewer 1 | Reviewer 2 |','|---|---|---|---|']
    for name,v in output['annotations'].items():
        values=[v['model_reviews'].get('semantic-review-'+str(i)) for i in (1,2)]
        lines.append('| '+name+' | '+v['author_annotation']['verdict']+' | '+' | '.join(x['verdict'] if x else 'not executed' for x in values)+' |')
    lines+=['','## Raw-workflow study — each pair separately','','| Workflow / arm | Mode | Accepted | Coverage | Design s | Build s | Debug s | Execute s | Model rubric /10 |','|---|---|---|---|---|---|---|---|---|']
    def seconds(rows):return str(round(sum(r['wall_ms'] for r in rows)/1000,3)) if rows else 'not applicable / not executed'
    for name,v in output['workflows'].items():
        lines.append('| '+name+' | '+str(v['mode'])+' | '+fmt(v['acceptance'])+' | '+fmt(v['coverage'])+' | '+ ' | '.join(seconds(v['phases'][p]) for p in ('design','implementation','debug'))+' | '+str(round(v['execution_wall_ms']/1000,3) if v['execution_wall_ms'] is not None else 'unknown')+' | '+str(v['model_review_total'])+' |')
    lines+=['','Model rubric is separate from executable acceptance; one candidate per arm/workflow, not repeated independent builds. Script runnability applies only when software is selected. Keep-agent without a runner is a valid outcome. Debug inside implementation is included in build investment and has unknown separate duration/tokens.','', '## Failures and unexecuted work','']
    failures=[]
    for r in records:
        if r['status']=='failed':failures.append(r['id']+': '+str(r.get('error')))
        if 'grade' in r and not r['grade']['passed']:failures.append(r['id']+': '+', '.join(r['grade']['reasons']))
        for c in r.get('cases',[]):
            if not c['grade']['passed']:failures.append(r['id']+'/'+c['case_id']+': '+', '.join(c['grade']['reasons'])+'; '+str(c.get('error')))
    lines += ['- '+x for x in failures] or ['No observed failures.']
    lines+=['','Unexecuted required entries: '+str(len(output['not_executed']))+'. See report.json for every case, denominator, reason, phase, annotation rationale and missing measurement.',
            '', '## Inference limits','', 'These are synthetic small-sample Codex observations. No significance, universal Skill advantage, billing saving, Jev, DeepSeek or cheaper-model conclusion follows. Reviewers are models; author labels are not independently human validated. Final labels and scoring are not changed after exposure. The older detailed-spec study still reports no observed Skill construction gain.']
    (d/'report.md').write_text('\n'.join(lines)+'\n')
    # Data-driven lightweight artifact, never a fixed pass bar.
    bars=[(k,v['acceptance']) for k,v in output['workflows'].items()]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="'+str(60+len(bars)*40)+'"><rect width="100%" height="100%" fill="white"/><text x="16" y="24" font-family="sans-serif">External acceptance — '+meta['stage']+'</text>']
    for i,(name,f) in enumerate(bars):
        y=50+40*i;svg.append('<text x="16" y="'+str(y+15)+'" font-family="sans-serif" font-size="13">'+name+'</text><rect x="270" y="'+str(y)+'" width="'+str(350*(f['value'] or 0))+'" height="22" fill="#2563eb"/><text x="640" y="'+str(y+15)+'" font-family="sans-serif">'+fmt(f)+'</text>')
    svg.append('</svg>');(d/'acceptance.svg').write_text(''.join(svg))
    return output

def export(source,destination):
    source=Path(source);destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    for name in ('metadata.json','plan.json','records.jsonl','report.json','report.md','acceptance.svg','candidate-freeze.json','development-prior.json'):
        if (source/name).exists():shutil.copyfile(source/name,destination/name)
    if (source/'candidates').exists():shutil.copytree(source/'candidates',destination/'candidates')
    target=destination/'calls';target.mkdir();audits=[]
    for p in sorted((source/'calls').glob('call-*.events.jsonl')):
        eventlist=[]
        for line in p.read_text().splitlines():
            try:e=json.loads(line)
            except ValueError:continue
            kept={'type':e.get('type')}
            if 'usage' in e:kept['usage']=e['usage']
            if e.get('item'):kept['item']={k:e['item'][k] for k in ('id','type','status','exit_code') if k in e['item']}
            eventlist.append(kept)
        audits.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'events':eventlist})
    for p in (source/'calls').glob('*.metrics.json'):shutil.copyfile(p,target/p.name)
    write(target/'event-audit.json',audits)
    (destination/'EXPORT.md').write_text('Public synthetic artifacts, all attempts, failures, reviews and measurements. Raw prompt/tool/session logs remain local. Hashes bind public audits to original JSONL. No credentials or historical private material. Model review is not human annotation.\n')
