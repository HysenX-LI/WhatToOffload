import copy
import json
from pathlib import Path
import tempfile
import unittest
from . import study

class ResearchTests(unittest.TestCase):
    def test_semantic_rules_are_identical_in_both_paths(self):
        rules=study.rules()
        self.assertIn(rules,study.task_text())
        self.assertEqual(study.task_text(),(study.ROOT/'TASK_RENDERED.md').read_text())
        self.assertNotIn('explicit dispute',study.task_text())
        self.assertIn(rules,study.semantic_prompt('d',{'id':'p'},{'id':'r'}))
        self.assertNotIn('gold.json',study.semantic_prompt('d',{'id':'p'},{'id':'r'}))

    def test_partial_or_fabricated_workflow_receipts_fail(self):
        cases=study.read(study.ROOT/'data/workflows/stockroom/final_inputs.json')
        gold=study.read(study.ROOT/'data/workflows/stockroom/final_gold.json')[0]
        self.assertTrue(study.grade_workflow('stockroom',cases[0],gold,gold)['passed'])
        for key,value in [('action_performed',True),('on_hand',{'probe':True,'cable':3}),('status','needs_review')]:
            bad=copy.deepcopy(gold);bad[key]=value
            self.assertFalse(study.grade_workflow('stockroom',cases[0],bad,gold)['passed'])
        self.assertFalse(study.grade_workflow('stockroom',cases[0],{},gold)['passed'])

    def test_keep_agent_can_pass_without_code_and_all_review_cannot(self):
        gold=study.read(study.ROOT/'data/workflows/customer/final_gold.json')[-1]
        case=study.read(study.ROOT/'data/workflows/customer/final_inputs.json')[-1]
        actual={k:v for k,v in gold.items() if k!='draft_contains'};actual['draft']='Please review approved workshop options.'
        self.assertTrue(study.grade_workflow('customer',case,actual,gold)['passed'])
        actual['status']='needs_review'
        self.assertFalse(study.grade_workflow('customer',case,actual,gold)['passed'])

    def test_new_gold_schema_and_pairs_are_independently_audited(self):
        self.assertEqual(study.audit_data(),{'semantic':16,'workflow':18})
        final=study.read(study.ROOT/'data/semantic/final/annotations.json')
        self.assertEqual(final['sem-f05']['verdict'],'conflict')
        self.assertEqual(final['sem-f06']['verdict'],'unclear')
        self.assertEqual(final['sem-f02']['verdict'],'unrelated')
        self.assertNotEqual(final['sem-f03']['verdict'],final['sem-f04']['verdict'])

    def test_anonymous_review_does_not_carry_treatment_identifiers(self):
        text=study.redact('WhatToOffload SKILL.md skill/references/executor-selection.md build_with_skill codex/optimize-evidence-benchmarks')
        for marker in ('WhatToOffload','SKILL.md','skill/references','build_with_skill','codex/optimize'):
            self.assertNotIn(marker,text)

    def test_untrusted_artifacts_do_not_escape_and_hashes_detect_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'okay.py').write_text('print(1)')
            (root/'escape').symlink_to('/etc/passwd')
            artifacts=study.collect_artifacts(root)
            self.assertEqual(set(artifacts),{'okay.py'})
            first=study.digest(artifacts);artifacts['okay.py']='print(2)'
            self.assertNotEqual(first,study.digest(artifacts))

    def test_scoring_strictly_rejects_customer_hidden_commitments(self):
        c=study.read(study.ROOT/'data/workflows/customer/dev_inputs.json')[0]
        g=study.read(study.ROOT/'data/workflows/customer/dev_gold.json')[0]
        a={k:v for k,v in g.items() if k!='draft_contains'};a['draft']=None
        self.assertTrue(study.grade_workflow('customer',c,a,g)['passed'])
        a['commitments']=['refund issued']
        self.assertFalse(study.grade_workflow('customer',c,a,g)['passed'])

    def test_missing_measurement_is_not_zero(self):
        measured=study.measure([{'input_tokens':3,'cached_input_tokens':1,'output_tokens':2,'tool_calls':1}, {'input_tokens':None,'cached_input_tokens':None,'output_tokens':None,'tool_calls':0}])
        self.assertEqual(measured['input_tokens_known'],3)
        self.assertFalse(measured['usage_complete'])
        self.assertIsNone(measured['billing_cost'])

    def test_review_schema_requires_evidence_and_valid_rating(self):
        value={'scores':{k:{'score':2,'evidence':'design.md: concrete evidence'} for k in study.DIMENSIONS},'limitations':[]}
        self.assertTrue(study.valid_review(value))
        value['scores']['boundary']['score']=True
        self.assertFalse(study.valid_review(value))

    def test_review_everything_loses_completed_and_approval_cases(self):
        from benchmarks.public_v1.runner import screen
        from benchmarks.public_v1.evaluate import grade
        cases=study.read(study.ROOT/'data/semantic/dev/inputs.json')
        gold=study.read(study.ROOT/'data/semantic/dev/gold.json')
        for case in (cases[0],cases[5],cases[6]):
            out=screen(case,lambda d,p,r:{'verdict':'unclear','evidence_ids':[p['id'],r['id']]})
            score=grade(case,out,gold[case['request_id']]['result'])
            self.assertFalse(score['passed'])
            self.assertFalse(score['actual_completion'])
            self.assertFalse(score['correct_approval_handoff'])

    def test_semantic_mutation_cannot_change_code_owned_decisions(self):
        from benchmarks.public_v1.runner import screen
        case=study.read(study.ROOT/'data/semantic/dev/inputs.json')[0]
        out=screen(case,lambda d,p,r:{'verdict':'corroborated','evidence_ids':[p['id'],r['id']],'approval_required':False,'decision':'eligible'})
        self.assertEqual(out['status'],'failed')
        self.assertEqual(out['shortlist'],[])
        self.assertIs(out['action_performed'],False)

    def test_formal_local_timeout_is_a_failure_not_retry_or_global_stop(self):
        from unittest.mock import patch
        import time
        from benchmarks.codex_v2.runtime import StopRun, CodexClient
        with tempfile.TemporaryDirectory() as tmp:
            client=study.ResearchClient(study.read(study.ROOT/'config.json'),tmp)
            with patch.object(CodexClient,'complete',side_effect=StopRun('Codex_build_timeout')) as call:
                with self.assertRaisesRegex(RuntimeError,'failed_bounded_invocation'):
                    client.complete(tmp,'prompt','build')
                self.assertEqual(call.call_count,1)
                self.assertIsNone(client.stop_reason)
            with patch.object(CodexClient,'complete',side_effect=StopRun('Codex_quota_exhausted')):
                with self.assertRaises(StopRun):client.complete(tmp,'prompt','build')
            client.deadline=time.monotonic()-1
            with patch.object(CodexClient,'complete',side_effect=StopRun('Codex_build_timeout')):
                with self.assertRaises(StopRun):client.complete(tmp,'prompt','build')
