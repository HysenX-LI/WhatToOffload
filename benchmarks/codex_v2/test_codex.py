import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.public_v1.__main__ import load_split
from benchmarks.public_v1.evaluate import grade
from . import runtime, studies, report
from .__main__ import matrix, freeze


def config():
    return json.loads((runtime.ROOT / 'config.json').read_text())


class CodexTests(unittest.TestCase):
    def test_auth_and_fresh_context_are_enforced_without_api_fallback(self):
        command = runtime.exec_command(config(), '/tmp/case', '/tmp/response')
        text = ' '.join(command)
        for required in ('--ephemeral', '--ignore-user-config', '--ignore-rules', 'forced_login_method="chatgpt"',
                         'model_reasoning_effort="high"', 'gpt-5.6-sol', 'approval_policy="never"',
                         'features.skip_host_skill_discovery=true', 'permissions.wto.network.enabled=false'):
            self.assertIn(required, text)
        for forbidden in ('resume', 'fork', 'danger-full-access', '--dangerously-bypass', 'api_key', 'budget_usd'):
            self.assertNotIn(forbidden, text)
        self.assertNotIn(str(runtime.REPO), text)

    def test_secret_provider_overrides_and_parent_context_not_inherited(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'never-forward', 'OPENAI_BASE_URL':'https://no.example',
                                    'CODEX_THREAD_ID':'parent', 'PYTHONPATH':'/grader'}):
            env = runtime.environment()
        for key in ('OPENAI_API_KEY','OPENAI_BASE_URL','CODEX_THREAD_ID','PYTHONPATH'):
            self.assertNotIn(key, env)

    def test_workspace_alias_is_normalized_for_cli_and_script_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            real=Path(temp)/'real';real.mkdir()
            alias=Path(temp)/'alias';alias.symlink_to(real, target_is_directory=True)
            for command in (runtime.exec_command(config(),alias,Path(temp)/'response'),
                            runtime.script_command(config()['cli'],alias,'print(1)')):
                self.assertEqual(command[command.index('-C')+1],str(real.resolve()))

    def test_configuration_rejects_prices_keys_other_models_and_unbounded_limits(self):
        for changed in ({'api_key_env':'KEY'}, {'budget_usd':60}, {'model':'another'}, {'reasoning_effort':'low'}, {'max_calls':0}):
            with self.assertRaises(ValueError): runtime.validate_config(dict(config(), **changed))

    def test_real_cli_events_count_tools_once_and_cache_as_subset(self):
        events = [{'type':'item.started','item':{'id':'a','type':'command_execution'}},
                  {'type':'item.completed','item':{'id':'a','type':'command_execution'}},
                  {'type':'turn.completed','usage':{'input_tokens':80,'cached_input_tokens':50,'output_tokens':9}}]
        self.assertEqual(runtime.event_metrics(events), {'input_tokens':80,'cached_input_tokens':50,'output_tokens':9,'tool_calls':1,'reported_turns':1})
        self.assertIsNone(runtime.event_metrics([])['input_tokens'])
        self.assertIsNone(report.usage([{'status':'failed','input_tokens':None}])['input_tokens'])
        self.assertIsNone(report.usage([])['billing_cost'])

    def test_call_slot_reserved_failed_transport_saved_then_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            client = runtime.CodexClient(dict(config(), max_calls=1), Path(temp)/'calls')
            command = [sys.executable, '-c', 'print(\'{"type":"turn.failed","error":{"message":"quota exhausted"}}\',flush=True)']
            with patch.object(runtime, 'exec_command', return_value=command):
                with self.assertRaises(runtime.StopRun): client.complete(temp, 'task', 'agent')
                with self.assertRaises(runtime.StopRun): client.complete(temp, 'second', 'agent')
            self.assertEqual(len(client.calls),1)
            self.assertEqual(client.calls[0]['status'],'failed')
            self.assertIsNone(client.calls[0]['input_tokens'])
            self.assertTrue((Path(temp)/'calls/call-001.events.jsonl').exists())
            self.assertEqual(json.loads((Path(temp)/'calls/calls.json').read_text())['stop_reason'], 'Codex_quota_exhausted')

    def test_relative_result_directory_survives_changed_executor_cwd(self):
        with tempfile.TemporaryDirectory(dir='.') as logs, tempfile.TemporaryDirectory() as workspace:
            client=runtime.CodexClient(config(), Path(logs)/'calls')
            def fake_command(config, directory, response):
                code="from pathlib import Path; import json; Path("+repr(str(response))+").write_text('returned JSON'); print(json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':0,'output_tokens':2}}))"
                return [sys.executable,'-c',code]
            with patch.object(runtime,'exec_command',side_effect=fake_command):
                result=client.complete(workspace,'one request','semantic')
            self.assertEqual(result,'returned JSON')

    def test_tool_cap_stops_subprocess(self):
        with tempfile.TemporaryDirectory() as temp:
            client = runtime.CodexClient(dict(config(), max_tools_per_call=1), Path(temp)/'calls')
            code = "import json; [print(json.dumps({'type':'item.started','item':{'id':str(i),'type':'command_execution'}}),flush=True) for i in range(2)]"
            with patch.object(runtime,'exec_command',return_value=[sys.executable,'-c',code]):
                with self.assertRaisesRegex(runtime.StopRun,'tool_cap'): client.complete(temp,'task','agent')
            self.assertEqual(client.calls[0]['tool_calls'],2)

    def test_native_reconnect_is_recorded_without_new_host_call_or_paid_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            client=runtime.CodexClient(config(),Path(temp)/'calls')
            def command(config,directory,response):
                code="import json;from pathlib import Path;Path("+repr(str(response))+").write_text('{}');print(json.dumps({'type':'error','message':'Reconnecting... 2/5 (tls handshake eof)'}));print(json.dumps({'type':'turn.completed','usage':{'input_tokens':12,'cached_input_tokens':0,'output_tokens':2}}))"
                return [sys.executable,'-c',code]
            with patch.object(runtime,'exec_command',side_effect=command): self.assertEqual(client.complete(temp,'task','semantic'),'{}')
            self.assertEqual(len(client.calls),1)
            self.assertEqual(client.calls[0]['transport_reconnections'],1)
            self.assertIsNone(client.stop_reason)

    def test_semantic_context_contains_only_two_documents_and_no_history(self):
        class Fake:
            def __init__(self): self.prompts=[]
            def complete(self, directory, prompt, kind):
                self.prompts.append((directory,prompt,kind))
                self.assert_empty = not list(Path(directory).iterdir())
                return '{"verdict":"unclear","evidence_ids":["p","r"]}'
        fake=Fake()
        judge=studies.CodexJudge(fake)
        for _ in range(2): judge('domain',{'id':'p','text':'claim'},{'id':'r','text':'unclear'})
        self.assertTrue(fake.assert_empty)
        self.assertEqual(fake.prompts[0][1],fake.prompts[1][1])
        self.assertNotEqual(fake.prompts[0][0],fake.prompts[1][0])
        for _,prompt,_ in fake.prompts:
            self.assertNotIn('gold',prompt); self.assertNotIn('TASK.md',prompt)

    def test_both_build_groups_get_same_nonanswer_material(self):
        cases,_=load_split('dev')
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            studies.build_workspace(a,cases,False); studies.build_workspace(b,cases,True)
            left={p.relative_to(a).as_posix():p.read_bytes() for p in Path(a).rglob('*') if p.is_file()}
            right={p.relative_to(b).as_posix():p.read_bytes() for p in Path(b).rglob('*') if p.is_file()}
            for key,value in left.items(): self.assertEqual(value,right[key])
            self.assertIn('SKILL.md',right); self.assertNotIn('SKILL.md',left)
            for files in (left,right):
                self.assertFalse(any('gold' in p or 'final' in p or 'evaluate.py' in p or 'test_' in p for p in files))

    def test_symlink_artifacts_and_changed_candidates_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,'result.json').symlink_to(runtime.REPO/'benchmarks/public_v1/data/dev/gold.json')
            with self.assertRaises(ValueError): runtime.read_artifact(temp,'result.json')
        with self.assertRaisesRegex(ValueError,'changed_after_freeze'):
            studies.run_candidate({},'changed','old-hash',None)

    def test_semantic_bridge_accepts_source_projection_but_rejects_changed_facts(self):
        cases,_=load_split('dev'); p=cases[0]; docs=p['vendors'][0]['documents']
        request={'domain':p['policy']['domain'],'profile':{k:docs[0][k] for k in ('id','text')},
                 'reference':{k:docs[1][k] for k in ('id','text')}}
        self.assertEqual(studies.source_pair(p,request),docs[:2])
        for field,change in (('text','forged content'),('id','unprovided'),('kind','noise')):
            bad=json.loads(json.dumps(request));bad['profile'][field]=change
            with self.assertRaises(ValueError):studies.source_pair(p,bad)

    def test_unexecuted_attempts_do_not_become_observed_failures_or_zero_cost(self):
        cases,gold=load_split('dev'); case=cases[0]
        planned={'attempt_id':'x','arm':'agent_direct','case_id':case['request_id'],'repetition':1,
                 'failure_grade':grade(case,None,gold[case['request_id']]['result'])}
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,'metadata.json').write_text(json.dumps({'run_id':'interrupted','mode':'codex','split':'dev','workflow_probe_count':3}))
            Path(temp,'plan.json').write_text(json.dumps([planned,dict(planned,attempt_id='b',arm='build_with_skill')]))
            Path(temp,'attempts.jsonl').write_text('{"truncated":')
            result=report.regenerate(temp)
        s=result['aggregate']['agent_direct']
        self.assertEqual(s['task_correctness']['denominator'],1)
        self.assertEqual(s['execution_coverage']['numerator'],0)
        self.assertIsNone(s['execution_failure_rate']['value'])
        self.assertEqual(result['records'][0]['execution_status'],'not_executed')
        self.assertIsNone(result['all_measurements']['billing_cost'])
        self.assertEqual(result['builds'][0]['status'],'not_executed')
        self.assertIsNone(result['builds'][0]['boundary_correct'])

    def test_matrix_is_data_driven_and_has_no_price_estimates(self):
        m=matrix(config(),'dev',2)
        self.assertEqual(m['execution_attempts'],6)
        self.assertEqual(m['candidate_attempts'],4)
        self.assertEqual(m['builds'],2)
        self.assertNotIn('usd',json.dumps(m))

    def test_exposed_final_cannot_be_relabelled_unseen_by_new_freeze(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'new-freeze.json'
            with patch('benchmarks.codex_v2.__main__.load_split'), patch('benchmarks.codex_v2.__main__.read', return_value={'status':'exposed'}):
                with self.assertRaisesRegex(ValueError,'already exposed'): freeze(path)
            self.assertFalse(path.exists())


if __name__=='__main__': unittest.main()
