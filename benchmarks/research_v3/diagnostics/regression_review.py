"""Two blind model annotations of an already exposed historical case, within spare budget."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time
from benchmarks.research_v3.study import ROOT, REPO, read, write, rules, parse_json, Context, measure
from benchmarks.codex_v2.runtime import CodexClient, StopRun, preflight
from benchmarks.research_v3.__main__ import verify


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--formal',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    formal=Path(a.formal);dest=Path(a.out);dest.mkdir(parents=True,exist_ok=False)
    m=read(formal/'metadata.json');used=m['measurements']['codex_calls']
    elapsed=time.time()-datetime.datetime.fromisoformat(m['started_at']).timestamp()
    remaining=math.floor(m['config']['total_timeout_seconds']-elapsed)
    protocol=ROOT/'REGRESSION_REVIEW_PROTOCOL.md';registered=read(ROOT/'regression-review-freeze.json')
    own=read(Path(__file__).with_name('freeze.json'))
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=own['implementation_sha256']:raise ValueError('diagnostic_implementation_changed')
    if hashlib.sha256(protocol.read_bytes()).hexdigest()!=registered['protocol_sha256'] or hashlib.sha256((ROOT/'SEMANTIC_RULES.md').read_bytes()).hexdigest()!=registered['rules_sha256']:raise ValueError('diagnostic_material_changed')
    verify(ROOT/'freeze-v3.json')
    meta={'stage':'exposed_historical_regression_model_review','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'formal_run':formal.name,'formal_calls':used,'remaining_formal_seconds_at_start':remaining,'classification':'model_annotation_not_human_label_not_regrading','billing_cost':None,'stop_reason':None}
    write(dest/'plan.json',{'reviewers':2,'budget_source':'spare capacity within original formal 48 calls / 4800 seconds','protocol_sha256':registered['protocol_sha256'],'implementation_sha256':own['implementation_sha256']})
    ctx=None;client=None
    if m.get('stop_reason') or used+2>m['config']['max_calls'] or remaining<=0:
        meta['stop_reason']='not_executed_no_spare_budget_or_prior_stop'
    else:
        config=dict(m['config'],max_calls=2,total_timeout_seconds=remaining)
        client=CodexClient(config,dest/'calls');ctx=Context(client,dest)
        try:
            meta['preflight']=preflight(config)
            payload=next(c for c in read(REPO/'benchmarks/public_v1/data/final/inputs.json') if c['request_id']=='final-contact-partial-eligibility')
            prompt=protocol.read_text().split('Prompt (identical for both):\n',1)[1]
            def annotate():
                with tempfile.TemporaryDirectory(prefix='wto-old-annotation-') as temp:
                    ws=Path(temp);(ws/'RULES.md').write_text(rules());write(ws/'materials.json',payload)
                    value=parse_json(client.complete(ws,prompt,'semantic'));labels=value.get('labels')
                    if not isinstance(labels,list) or len(labels)!=len(payload['vendors']) or {x.get('vendor_id') for x in labels}!={v['id'] for v in payload['vendors']} or any(x.get('verdict') not in ('corroborated','unrelated','conflict','unclear') or not x.get('rationale') for x in labels):raise ValueError('invalid_annotation_schema')
                    return {'labels':labels,'reviewer_type':'Codex_model_review'}
            for i in (1,2):ctx.event('historical-review-'+str(i),'exposed_annotation',annotate)
        except StopRun as e:meta['stop_reason']=str(e)
    meta['ended_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();meta['measurements']=measure(client.calls if client else [])
    meta['combined_formal_calls']=used+meta['measurements']['codex_calls'];meta['combined_elapsed_seconds']=round(time.time()-datetime.datetime.fromisoformat(m['started_at']).timestamp(),3)
    write(dest/'metadata.json',meta)
    records=ctx.records if ctx else []
    # Only after both attempted annotations: compare to historical table, without changing any score.
    comparison={v:{'historical_frozen_verdict':label,'new_rule_model_annotations':{r['id']:next((x for x in r.get('labels',[]) if x['vendor_id']==v),None) for r in records}} for v,label in [('z','corroborated'),('e','unrelated')]}
    write(dest/'report.json',{'metadata':meta,'records':records,'comparison':comparison,'not_executed_reviewers':[i for i in (1,2) if 'historical-review-'+str(i) not in {r['id'] for r in records}]})
    lines=['# Exposed historical case: model review under v3 rules','','No historical answer or score is changed. This is not an unseen test or human annotation.','', '| Vendor | Historical frozen verdict | New-rule reviewer 1 | New-rule reviewer 2 |','|---|---|---|---|']
    for v,x in comparison.items():lines.append('| '+v+' | '+x['historical_frozen_verdict']+' | '+' | '.join((x['new_rule_model_annotations'].get('historical-review-'+str(i)) or {}).get('verdict','not executed') for i in (1,2))+' |')
    lines+=['','Agreement under a new explicit rule does not prove the old ambiguous prompt/model was wrong. See report.json for rationales, failures and measurements.','', 'Combined formal plus supplement calls: '+str(meta['combined_formal_calls'])+'. Billing unknown.']
    (dest/'report.md').write_text('\n'.join(lines)+'\n');print(json.dumps(meta),flush=True)
if __name__=='__main__':main()
