from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_two_host_encoding import tiny_instance
from src.benchmark_a_campaign import load_benchmark, save_json
from src.two_host_campaign import (new_campaign, verify_campaign, run_preflights,
    run_campaign, export_campaign, result_rows, recover_active, start_attempt,
    finish_attempt, get_model, _environment, import_baseline, open_campaign)
from src.two_host_runner import run_compact_trial

ROOT=Path(__file__).resolve().parents[1]


class TwoHostCampaignTests(unittest.TestCase):
    def context(self):
        c=deepcopy(load_benchmark(ROOT));instance=tiny_instance()
        c['instances']={instance['instance_id']:instance}
        c['manifest']['instances']=[dict(instance_id=instance['instance_id'],role='benchmark')]
        c['protocol']['negative_control']=None
        c['protocol']['qaoa'].update(depths=[1],optimization_seeds=[70,71],evaluation_seeds=[100070,100071],
            shots=64,evaluation_shots=64,maxiter=8,max_seconds=120.)
        c['protocol']['resource_policy'].update(start_available_min_gib=.01,remaining_available_min_gib=.01,aer_threads=1)
        return c

    def test_driver_resume_partial_export_and_rehash_tampering(self):
        c=self.context()
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);campaign=new_campaign(c,None);save_json(folder/'campaign.json',campaign)
            self.assertEqual([r['status'] for r in result_rows(folder,campaign)],['pending','pending'])
            run_preflights(folder,c)
            campaign=run_campaign(folder,c,progress=False)
            self.assertEqual(len(verify_campaign(folder,campaign,c)),2)
            with patch('src.two_host_campaign.run_compact_trial',side_effect=AssertionError('rerun')):
                run_campaign(folder,c,progress=False)
            path,rows=export_campaign(folder,c)
            self.assertTrue(path.is_file());self.assertEqual(len(rows),2)
            row=campaign['attempts'][-1];report=folder/row['report'];r=json.loads(report.read_text())
            r['result']['metrics']['feasible_probability']+=.1;save_json(report,r)
            from src.benchmark_a_campaign import _digest
            row['report_sha256']=_digest(report)
            with self.assertRaises(ValueError):verify_campaign(folder,campaign,c)

    def test_recover_crash_and_orphan_result(self):
        c=self.context()
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);campaign=new_campaign(c,None);trial=campaign['planned_runs'][0]
            start_attempt(folder,campaign,trial,'trial');recover_active(folder,campaign,c)
            self.assertEqual(campaign['attempts'][0]['status'],'interrupted')
            start_attempt(folder,campaign,trial,'trial');before=deepcopy(campaign)
            b,r=get_model(c,trial['instance_id'])
            report=run_compact_trial(b,trial['config'],c['protocol']['resource_policy'],r,False)
            finish_attempt(folder,campaign,report,c)
            save_json(folder/'campaign.json',before);recover_active(folder,before,c)
            self.assertEqual(len(verify_campaign(folder,before,c)),1)

    def test_baseline_import_recomputes_metrics_and_binds_resume(self):
        from src import benchmark_a_campaign as old
        from src.two_host_runner import memory_snapshot
        import zipfile
        c=self.context()
        with tempfile.TemporaryDirectory() as d, patch('src.benchmark_a_runner.memory_snapshot',memory_snapshot):
            root=Path(d);folder=root/'old';folder.mkdir()
            save_json(folder/'campaign.json',old.new_campaign(c))
            old.run_preflights(folder,c);old.run_campaign(folder,c,progress=False)
            archive,_=old.export_campaign(folder,c)
            baseline=import_baseline(archive,c)
            self.assertEqual(len(baseline['rows']),2)
            new,manifest=open_campaign(root,c,archive)
            self.assertEqual(len(manifest['planned_runs']),2)
            self.assertEqual(open_campaign(root,c,archive,new)[0],new)
            # Rehash a modified report: semantic auditing must still reject it.
            with zipfile.ZipFile(archive) as z:files={name:z.read(name) for name in z.namelist()}
            report=next(name for name in files if '_trial_' in name)
            value=json.loads(files[report]);value['result']['metrics']['feasible_probability']+=.1
            files[report]=json.dumps(value).encode()
            import hashlib
            hashes=json.loads(files['sha256.json']);hashes[report]=hashlib.sha256(files[report]).hexdigest()
            manifest=json.loads(files['campaign.json'])
            next(a for a in manifest['attempts'] if a['report']==report)['report_sha256']=hashes[report]
            files['campaign.json']=json.dumps(manifest).encode()
            hashes['campaign.json']=hashlib.sha256(files['campaign.json']).hexdigest()
            files['sha256.json']=json.dumps(hashes).encode()
            bad=root/'bad.zip'
            with zipfile.ZipFile(bad,'w') as z:
                for name,data in files.items():z.writestr(name,data)
            with self.assertRaises(ValueError):import_baseline(bad,c)


if __name__=='__main__':unittest.main()
