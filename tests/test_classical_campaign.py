import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.classical_campaign import load_context, run_campaign, verify_campaign, export_campaign

ROOT = Path(__file__).resolve().parents[1]


class ClassicalCampaignTests(unittest.TestCase):
    def test_fixed_scope_has_twelve_instances_and_three_algorithms(self):
        context = load_context(ROOT)
        self.assertEqual(len(context['protocol']['instances']), 12)
        self.assertEqual(context['protocol']['algorithms'], ['FirstFit', 'BFD', 'MILP'])
        self.assertEqual(sum(r['include_in_main_comparison'] for r in context['protocol']['instances']), 9)
        self.assertNotIn('development', {r['role'] for r in context['protocol']['instances']})

    def test_python314_solver_pin_matches_protocol_and_installation(self):
        from src.classical_baselines import ORTOOLS_VERSION
        self.assertEqual(ORTOOLS_VERSION, '9.15.6755')
        protocol = load_context(ROOT)['protocol']
        self.assertEqual(protocol['ortools_version'], ORTOOLS_VERSION)
        self.assertEqual(protocol['study_id'], 'nt409_classical_b_v1_1')
        requirements = (ROOT/'requirements-branch-b.txt').read_text().splitlines()
        self.assertIn(f'ortools=={ORTOOLS_VERSION}', requirements)
        old = json.loads((ROOT/'data/benchmarks/nt409_classical_b_v1/protocol.json').read_text())
        self.assertEqual(old['ortools_version'], '9.14.6206')
        for key in ('instances', 'algorithms', 'heuristics', 'threads', 'time_limit_seconds',
                    'quality_repetitions', 'timing_repetitions', 'a_groups_canonical_sha256'):
            self.assertEqual(protocol[key], old[key])

    def test_changed_input_is_rejected(self):
        import shutil
        with TemporaryDirectory() as td:
            root = Path(td)
            for path in ['data/benchmarks/nt409_classical_b_v1_1', 'data/instances',
                         'data/benchmarks/nt409_three_host_v2/instances',
                         'handoff/nt409_branch_a_handoff_v1/tables', 'src']:
                shutil.copytree(ROOT/path, root/path)
            target = root/'data/instances/p1_choice.json'
            data = json.loads(target.read_text())
            data['tasks'][0]['cpu'] += 1
            target.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Input changed'):
                load_context(root)

    def test_campaign_quality_counts_export_and_tamper_detection(self):
        with TemporaryDirectory() as td:
            out = Path(td)/'run with spaces'
            run_campaign(ROOT, out, machine_label='Linux QA only', progress=False)
            result = verify_campaign(out)
            self.assertEqual(result['quality_records'], 36)
            self.assertTrue(result['milp_certificates_complete'])
            self.assertEqual(result['main_records'], 27)
            self.assertEqual(result['timing_records'], 180)
            self.assertEqual(result['a_comparison_rows'], 27)
            self.assertTrue(export_campaign(out).is_file())
            with self.assertRaises(FileExistsError):
                run_campaign(ROOT, out, machine_label='Linux QA only', progress=False)
            path = next((out/'raw').glob('*.json'))
            data = json.loads(path.read_text())
            data['quality']['objective'] = 999
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                verify_campaign(out)


if __name__ == '__main__':
    unittest.main()
