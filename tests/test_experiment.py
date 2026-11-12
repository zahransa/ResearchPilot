"""Offline integration tests. All generated code here is authored within fixture tests."""
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from researchpilot import experiment
from researchpilot.runner import choose as fixture_choose, run_tests as fixture_run_tests

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / 'benchmarks' / 'cases.json').read_text())


class StubModel:
    prompts = []
    calls = 0
    def __init__(self, *_args, **_kwargs):
        self.prompts = StubModel.prompts
    def generate(self, prompt):
        self.prompts.append(prompt)
        # No hidden, probes, or pre-authored candidates are accessed here.
        # A dummy return is sufficient for testing orchestration.
        StubModel.calls += 1
        return 'def solve(a, b):\n    return abs(a-b)\n', {'input': 20, 'output': 10, 'total': 30}


def gen_args(out, num=1):
    return Namespace(input=ROOT/'benchmarks'/'cases.json', output=out,
                     max_tasks=1, num_candidates=num, provider='gemini',
                     model='stub-for-unit-test', base_url=None,
                     temperature=0.2, max_tokens=100, overwrite=False)


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        StubModel.prompts = []
        StubModel.calls = 0

    def test_prompt_contains_only_public_task_fields(self):
        case = CASES[0]
        p = experiment.make_prompt(case, 0)
        self.assertIn(case['issue'], p)
        self.assertIn(case['buggy_code'], p)
        self.assertIn(json.dumps(case['public'], indent=2), p)
        self.assertNotIn(json.dumps(case['hidden']), p)
        self.assertNotIn(json.dumps(case['probes']), p)
        self.assertNotIn(case['candidates'][0]['code'], p)

    def test_normalize_compiles_but_does_not_execute(self):
        source = "```python\ndef solve(x):\n    return x+1\n```"
        self.assertEqual(experiment.normalize_code(source), "def solve(x):\n    return x+1\n")
        with self.assertRaises(ValueError):
            experiment.normalize_code('print("hello")')

    def test_model_generation_resumes_without_recharging(self):
        with tempfile.TemporaryDirectory() as folder:
            args = gen_args(Path(folder)/'generation.json', num=2)
            with patch.object(experiment, 'ModelClient', StubModel):
                first = experiment.generate(args)
                second = experiment.generate(args)
            self.assertEqual(2, StubModel.calls)
            self.assertEqual(first['records'], second['records'])
            self.assertEqual(2, len(second['records'][0]['candidates']))
            self.assertEqual('complete', second['status'])
            self.assertEqual('model_generated_patches', second['artifact_kind'])

    def test_scoring_paired_same_candidate_pool_offline_trusted_stubs(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            record = {
                'artifact_kind':'model_generated_patches',
                'status':'complete',
                'config': {'input_sha256':experiment.sha256((ROOT/'benchmarks'/'cases.json').read_bytes()),
                           'model':'offline-mock', 'provider':'offline-mock'},
                'records': [{
                    'id': CASES[0]['id'],
                    'candidates': [dict(c, valid_python=True) for c in CASES[0]['candidates']]
                }]
            }
            raw = folder/'generation.json'
            experiment.atomic_json(raw, record)
            args = Namespace(generations=raw, input=ROOT/'benchmarks'/'cases.json',
                             output=folder/'scores.json', overwrite=False)
            # These mocks deliberately redirect execution to trusted hand-authored
            # candidates for an OFFLINE HARNESS TEST ONLY; no model code runs locally.
            def trusted_choose(pool, public, probes, engine, use_gate):
                self.assertEqual('docker', engine)
                return fixture_choose(pool, public, probes, engine='local', use_gate=use_gate)
            def trusted_run_tests(code, tests, engine, timeout):
                self.assertEqual('docker', engine)
                return fixture_run_tests(code, tests, engine='local')
            with patch.object(experiment, 'check_docker'), \
                 patch.object(experiment, 'choose', side_effect=trusted_choose), \
                 patch.object(experiment, 'run_tests', side_effect=trusted_run_tests):
                result = experiment.score(args)
            self.assertEqual('complete', result['status'])
            self.assertEqual(result['summary']['direct']['hidden_pass'], 0)
            self.assertEqual(result['summary']['evidence_gate']['hidden_pass'], 1)

    def test_score_refuses_modified_benchmark(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            bad = {'artifact_kind':'model_generated_patches','status':'complete',
                   'config':{'input_sha256':'badsha'}, 'records':[]}
            generations = folder/'generations.json'
            experiment.atomic_json(generations, bad)
            args = Namespace(generations=generations, input=ROOT/'benchmarks'/'cases.json',
                             output=folder/'scores.json', overwrite=False)
            with patch.object(experiment, 'check_docker'):
                with self.assertRaises(ValueError):
                    experiment.score(args)


if __name__ == '__main__':
    unittest.main()
