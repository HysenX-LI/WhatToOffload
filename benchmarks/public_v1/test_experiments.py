import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import experiments, sandbox
from .providers import BudgetExceeded, LiveClient, SemanticJudge


def config():
    return {"base_url":"https://model.example/v1", "model":"test-model", "api_key_env":"WTO_TEST_KEY",
            "rates_verified":True, "max_calls":1, "budget_usd":1.0,
            "max_input_bytes":10000, "max_output_tokens":100,
            "input_usd_per_million":1.0, "output_usd_per_million":1.0,
            "docker_image":"python:3.11-slim", "agent_turns":2, "build_turns":2}


class ProviderAndIsolationTests(unittest.TestCase):
    def test_budget_is_reserved_before_failed_request_and_failure_is_retained(self):
        with patch.dict(os.environ, {"WTO_TEST_KEY":"test-only-placeholder"}):
            client=LiveClient(config())
        with patch('urllib.request.urlopen', side_effect=OSError('private diagnostic')) as post:
            with self.assertRaises(RuntimeError):
                client.complete([{"role":"user","content":"hello"}])
            with self.assertRaises(BudgetExceeded):
                client.complete([{"role":"user","content":"hello"}])
        self.assertEqual(post.call_count,1)
        self.assertEqual(client.calls[0]['status'],'failed')
        self.assertIsNone(client.calls[0]['cost_usd'])
        self.assertGreater(client.reserved_usd,0)
        self.assertNotIn('private diagnostic',json.dumps(client.calls))
        self.assertNotIn('test-only-placeholder',json.dumps(client.calls))

    def test_missing_usage_is_unknown_and_payload_has_no_gold(self):
        with patch.dict(os.environ, {"WTO_TEST_KEY":"test-only-placeholder"}):
            client=LiveClient(config())
        response=io.BytesIO(json.dumps({"choices":[{"message":{"content":'{"verdict":"unclear","evidence_ids":["p","r"]}'}}]}).encode())
        with patch('urllib.request.urlopen',return_value=response) as post:
            judgment=SemanticJudge(client)('domain',{'id':'p','text':'profile'},{'id':'r','text':'reference'})
        self.assertEqual(judgment['verdict'],'unclear')
        self.assertIsNone(client.calls[0]['cost_usd'])
        request=json.loads(post.call_args.args[0].data)
        evidence=json.loads(request['messages'][1]['content'])
        self.assertEqual(set(evidence),{'domain','profile','reference'})

    def test_input_and_dollar_caps_prevent_request(self):
        for change in ({'max_input_bytes':1},{'budget_usd':0.000001}):
            with patch.dict(os.environ, {"WTO_TEST_KEY":"test-only-placeholder"}):
                client=LiveClient(dict(config(),**change))
            with patch('urllib.request.urlopen') as post:
                with self.assertRaises(BudgetExceeded):
                    client.complete([{'role':'user','content':'hello'}])
            post.assert_not_called()

    def test_no_docker_fails_closed(self):
        with patch('shutil.which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'no host fallback'):
                sandbox.preflight('image')

    def test_model_code_has_only_one_mount_and_no_host_credentials(self):
        args=sandbox.command('/tmp/allowed','image','test','print(1)')
        self.assertIn('--network=none',args)
        self.assertIn('--read-only',args)
        self.assertEqual(args.count('--mount'),1)
        self.assertNotIn(str(experiments.REPO),json.dumps(args))
        self.assertNotIn('--env',args)

    def test_build_workspaces_differ_only_by_skill_treatment(self):
        # No hidden test or answer file is copied into either executor workspace.
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            examples=[{'request_id':'development','vendors':[]}]
            experiments.build_workspace(a,examples,False)
            experiments.build_workspace(b,examples,True)
            base={p.relative_to(a).as_posix():p.read_bytes() for p in Path(a).rglob('*') if p.is_file()}
            treated={p.relative_to(b).as_posix():p.read_bytes() for p in Path(b).rglob('*') if p.is_file()}
            for name,content in base.items():
                self.assertEqual(content,treated[name])
            self.assertIn('SKILL.md',treated)
            self.assertNotIn('SKILL.md',base)
            for files in (base,treated):
                self.assertFalse(any('gold' in k or 'final' in k or 'test_' in k or 'evaluate.py' in k for k in files))

    def test_artifact_symlinks_cannot_make_host_read_outside_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'result.json').symlink_to(experiments.ROOT/'data/dev/gold.json')
            with self.assertRaises(ValueError):
                sandbox.read_artifact(temp,'result.json')

    def test_agent_tool_loop_is_fresh_and_keeps_tool_access(self):
        class Fake:
            config=config()
            def __init__(self): self.seen=[]
            def complete(self,messages,tools):
                self.seen.append(json.loads(json.dumps(messages)))
                if len(self.seen)==1:
                    return {'role':'assistant','content':None,'tool_calls':[{'id':'tool-1','type':'function','function':{'name':'python','arguments':'{"code":"print(1)"}'}}]}
                return {'role':'assistant','content':'Done'}
        first,second=Fake(),Fake()
        with patch.object(sandbox,'execute',return_value={'exit_code':0,'stdout':'1','stderr':''}) as tool:
            self.assertEqual(experiments.agent_loop(first,'/tmp/work','system',2),1)
            self.assertEqual(experiments.agent_loop(second,'/tmp/work','system',2),1)
        self.assertEqual(first.seen[0],second.seen[0])
        self.assertEqual(tool.call_count,2)
        self.assertEqual(first.seen[1][-1]['role'],'tool')


if __name__=='__main__':
    unittest.main()
