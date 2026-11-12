"""Unit tests use only trusted local fixtures (never untrusted agent output)."""
import json
from pathlib import Path
import unittest
from researchpilot.runner import run_tests, choose
from researchpilot.evaluate import evaluate
ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'benchmarks'/'cases.json').read_text())

class HarnessTests(unittest.TestCase):
    def test_all_broken_versions_fail_public(self):
        for case in CASES:
            with self.subTest(case=case['id']):
                self.assertFalse(run_tests(case['buggy_code'],case['public'])['passed'])
    def test_all_correct_patches_pass_all_splits(self):
        for case in CASES:
            with self.subTest(case=case['id']):
                correct=next(c for c in case['candidates'] if c['label']=='general')
                for split in ('public','probes','hidden'):
                    self.assertTrue(run_tests(correct['code'],case[split])['passed'],(case['id'],split))
    def test_all_shortcut_patches_pass_visible_but_fail_holdout(self):
        for case in CASES:
            with self.subTest(case=case['id']):
                shortcut=next(c for c in case['candidates'] if c['label']=='shortcut')
                self.assertTrue(run_tests(shortcut['code'],case['public'])['passed'])
                self.assertFalse(run_tests(shortcut['code'],case['probes'])['passed'])
                self.assertFalse(run_tests(shortcut['code'],case['hidden'])['passed'])
    def test_gate_never_uses_hidden_during_selection(self):
        for case in CASES:
            with self.subTest(case=case['id']):
                modified={**case,'hidden':[{'args':['bogus'],'expected':'unreachable'}]}
                a,_=choose(case['candidates'],case['public'],case['probes'],use_gate=True)
                b,_=choose(modified['candidates'],modified['public'],modified['probes'],use_gate=True)
                self.assertEqual(a['label'],b['label'])
    def test_matched_candidate_pool(self):
        outcome=evaluate(CASES)
        self.assertEqual(outcome['summary']['direct']['tasks'],len(CASES))
        self.assertEqual(outcome['summary']['evidence_gate']['tasks'],len(CASES))
        self.assertGreaterEqual(outcome['summary']['evidence_gate']['hidden_pass'],outcome['summary']['direct']['hidden_pass'])

if __name__=='__main__':unittest.main()
