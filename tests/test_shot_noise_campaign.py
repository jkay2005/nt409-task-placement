import copy
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.shot_noise_campaign import (create_campaign, run_campaign, summarize,
    audit_campaign, export_campaign, load_json, PROTOCOL, SOURCES, digest, save_json, prepare_campaign)
from src.three_host_encoding import build_three_host_qubo
from src.qaoa_experiment import qubo_fingerprint
from test_shot_noise_diagnostic import TINY

ROOT = Path(__file__).resolve().parents[1]


class NoiseCampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'root'
        for name in SOURCES:
            target = self.root/'src'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/'src'/name,target)
        self.protocol = load_json(ROOT/PROTOCOL)
        self.protocol.update(software_validation=True, depths=[1], seeds=[300], maxiter=6,
                             noise_batches=2, shots=32, final_shots=64, threads=1,
                             min_available_gib=.001)
        save_json(self.root/'data/qa_instance.json', TINY)
        self.protocol['instances'] = [dict(instance_id=TINY['instance_id'],
            path='data/qa_instance.json', input_sha256=digest(TINY),
            qubo_sha256=qubo_fingerprint(build_three_host_qubo(TINY)))]

    def small_protocol(self):
        return copy.deepcopy(self.protocol)

    def test_resume_complete_and_export_preserve_evidence(self):
        with TemporaryDirectory() as tmp:
            folder = create_campaign(self.root, output=Path(tmp)/'run', protocol=self.small_protocol())
            self.assertEqual(summarize(folder)['coverage']['pending'], 2)
            run_campaign(self.root, folder, max_new_runs=1, progress=False)
            before = load_json(folder/'campaign.json')
            self.assertEqual(summarize(folder)['coverage']['completed'], 1)
            run_campaign(self.root, folder, progress=False)
            after = load_json(folder/'campaign.json')
            self.assertEqual(len(after['attempts']), 2)
            self.assertEqual(after['attempts'][0], before['attempts'][0])
            self.assertEqual(audit_campaign(self.root, folder)['status'], 'PASS')
            self.assertEqual(len(summarize(folder)['comparisons']), 1)
            archive = export_campaign(self.root, folder)
            self.assertTrue(archive.is_file())
            run_campaign(self.root, folder, progress=False)
            self.assertEqual(len(load_json(folder/'campaign.json')['attempts']), 2)
            report = folder/after['attempts'][1]['path']
            saved = load_json(report)
            saved['final_measured']['optimal_count'] = 12345
            report.write_text(json.dumps(saved))
            with self.assertRaises(ValueError): audit_campaign(self.root, folder)
            with self.assertRaises(ValueError): run_campaign(self.root, folder, progress=False)

    def test_refuses_changed_protocol_and_concurrent_writer(self):
        with TemporaryDirectory() as tmp:
            p = self.small_protocol()
            folder = create_campaign(self.root, output=Path(tmp)/'run', protocol=p)
            changed = copy.deepcopy(p)
            changed['shots'] += 1
            with self.assertRaises(ValueError):
                create_campaign(self.root, output=folder, protocol=changed)
            (folder/'RUNNING.lock').write_text('test lock')
            with self.assertRaises(FileExistsError): run_campaign(self.root, folder, progress=False)

    def test_refuses_invalid_resource_limits_before_creating_campaign(self):
        for key, value in [('max_seconds', float('inf')), ('min_available_gib', -1),
                           ('rhobeg', 0), ('tol', float('nan')), ('maxiter', 6.0)]:
            with self.subTest(key=key), TemporaryDirectory() as tmp:
                protocol = self.small_protocol()
                protocol[key] = value
                folder = Path(tmp)/'run'
                with self.assertRaises(ValueError):
                    create_campaign(self.root, output=folder, protocol=protocol)
                self.assertFalse(folder.exists())

    def test_frozen_plan_has_one_input_two_exact_ten_sampled(self):
        with TemporaryDirectory() as tmp:
            folder = create_campaign(ROOT, output=Path(tmp)/'run')
            plan = load_json(folder/'campaign.json')['plan']
            self.assertEqual(sum(p['mode']=='exact' for p in plan), 2)
            self.assertEqual(sum(p['mode']=='shots' for p in plan), 10)
            self.assertEqual(len({p['id'] for p in plan}), 12)

    def test_preparation_is_persisted_and_reused(self):
        folder = create_campaign(self.root, output=Path(self.tmp.name)/'prepare', protocol=self.small_protocol())
        rows = prepare_campaign(self.root, folder, progress=False)
        self.assertEqual(len(rows), 1)
        self.assertGreaterEqual(rows[0]['exact_seconds'], 0)
        before = load_json(folder/'campaign.json')['calibrations']
        self.assertEqual(rows, prepare_campaign(self.root, folder, progress=False))
        self.assertEqual(before, load_json(folder/'campaign.json')['calibrations'])
        self.assertEqual(summarize(folder)['coverage']['completed'], 0)
        self.assertEqual(audit_campaign(self.root, folder)['status'], 'PASS')

    def test_main_protocol_cannot_change_or_duplicate_reference(self):
        p = load_json(ROOT/PROTOCOL)
        for changed in [dict(p, instances=p['instances']*2),
                        dict(p, instances=[dict(p['instances'][0], input_sha256='0'*64)])]:
            with self.subTest(changed=changed), TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    create_campaign(ROOT, output=Path(tmp)/'refused', protocol=changed)


if __name__ == '__main__':
    unittest.main()
