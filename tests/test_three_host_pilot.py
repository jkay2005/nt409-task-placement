from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from src.three_host_benchmark import load_three_host_benchmark
from src.three_host_pilot import (open_pilot,prepare_models,run_phase,verify_pilot,export_pilot,
    result_rows,recover_active,start_attempt)
from src.benchmark_a_campaign import save_json,_digest
from test_three_host_encoding import instance

ROOT=Path(__file__).resolve().parents[1]


def tiny_context():
    c=deepcopy(load_three_host_benchmark(ROOT/'data/benchmarks/nt409_three_host_v2'))
    i=instance();c['instances']={i['instance_id']:i}
    c['manifest']['instances']=[dict(instance_id=i['instance_id'],role='development',num_tasks=1,num_qubits=11)]
    c['protocol']['qaoa'].update(depths=[1],maxiter=12,shots=32,evaluation_shots=32,max_seconds=60.)
    c['protocol']['resource_policy'].update(start_available_min_gib=.1,remaining_available_min_gib=.1,aer_threads=1)
    return c


class ThreeHostPilotTests(unittest.TestCase):
    def test_resume_export_and_rehashed_semantic_tamper(self):
        c=tiny_context()
        with TemporaryDirectory() as d:
            f,m=open_pilot(d,c);prepare_models(f,c);run_phase(f,c,'probe',progress=False)
            m=run_phase(f,c,'trial',progress=False)
            self.assertEqual(len(verify_pilot(f,m,c)),2)
            with patch('src.three_host_pilot.run_three_host_trial',side_effect=AssertionError('rerun')):
                run_phase(f,c,'trial',progress=False)
            archive,rows,assessment=export_pilot(f,c)
            self.assertTrue(archive.is_file());self.assertEqual(len(rows),2)
            self.assertEqual(assessment['status'],'pilot_complete')
            a=m['attempts'][-1];path=f/a['report'];e=json.loads(path.read_text())
            e['result']['metrics']['invalid_domain_probability']+=.1;save_json(path,e);a['report_sha256']=_digest(path)
            with self.assertRaises(ValueError):verify_pilot(f,m,c)

    def test_recovery_design_change_and_test_instances_are_not_run(self):
        c=tiny_context()
        with TemporaryDirectory() as d:
            f,m=open_pilot(d,c);t=m['planned_runs'][0]
            start_attempt(f,m,t,'trial');recover_active(f,m,c)
            self.assertEqual(m['attempts'][0]['status'],'interrupted')
            altered=deepcopy(c);altered['protocol']['qaoa']['shots']+=1
            with self.assertRaises(ValueError):verify_pilot(f,m,altered)
            with self.assertRaises(ValueError):run_phase(f,c,'probe',instance_ids=['a3_test_n4_1'])
            rows=result_rows(f,m,c)
            self.assertEqual(rows[0]['status'],'interrupted')

    def test_frozen_pilot_matrix_is_fourteen_trials_and_no_test_rows(self):
        c=load_three_host_benchmark(ROOT/'data/benchmarks/nt409_three_host_v2')
        with TemporaryDirectory() as d:
            f,m=open_pilot(d,c)
            self.assertEqual(len(m['planned_runs']),14)
            self.assertEqual(sum(t['role']=='development' for t in m['planned_runs']),12)
            self.assertTrue(all(t['role']!='test' for t in m['planned_runs']))
            self.assertEqual(len({(t['instance_id'],t['config']['reps']) for t in m['planned_runs']}),8)
