"""Branch A: frozen controls, resource boundaries, measured output and recovery."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import Statevector
from src.qubo import build_qubo
from src.ising import build_ising, scale_ising
from src.qaoa_experiment import prepare_reference
from src.benchmark_a_runner import ResourceGuard, ResourceStop, select_output, run_trial, probe_depth
from src.benchmark_a_campaign import (load_benchmark, make_trials, new_campaign, save_json,
    start_attempt, finish_attempt, recover_active, verify_campaign, result_rows,
    run_preflights, run_campaign, export_campaign, prepare_models, _lock)

ROOT=Path(__file__).resolve().parents[1]


class BenchmarkAControlsTests(unittest.TestCase):
    def test_frozen_inputs_and_45_paired_trials_plus_separate_smoke(self):
        context=load_benchmark(ROOT);trials=make_trials(context)
        formal=[t for t in trials if t['role']=='benchmark']
        self.assertEqual(len(formal),45)
        self.assertEqual(len(trials),46)
        self.assertEqual(len({t['run_key'] for t in trials}),46)
        original=json.loads((ROOT/'data/benchmarks/nt409_benchmark_v1/protocol.json').read_text())
        updated=deepcopy(context['protocol'])
        self.assertEqual(updated['qaoa']['max_seconds'],2400.)
        updated['qaoa']['max_seconds']=600.;updated['protocol_id']=original['protocol_id']
        self.assertEqual(updated,original)
        for instance in ('p1_choice','p1_tight','p0_reference'):
            for p in (1,2,3):
                group=[t for t in formal if t['instance_id']==instance and t['config']['reps']==p]
                self.assertEqual([t['config']['seed'] for t in group],[70,71,72,73,74])
                self.assertTrue(all(t['config']['evaluation_seed']==t['config']['seed']+100000 for t in group))
        self.assertEqual(trials[-1]['role'],'negative_control')

    def test_modified_input_and_rehashed_protocol_are_rejected(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ('data/instances','data/benchmarks'):
                shutil.copytree(ROOT/name,root/name)
            (root/'docs').mkdir()
            for name in ('unified_benchmark_v1.md','benchmark_a_protocol_v1_1.md'):
                shutil.copy(ROOT/'docs'/name,root/'docs')
            path=root/'data/instances/p1_choice.json';original=path.read_bytes()
            value=json.loads(original);value['tasks'][0]['cpu']+=1;save_json(path,value)
            with self.assertRaises(ValueError):load_benchmark(root)
            path.write_bytes(original)
            path=root/'data/benchmarks/nt409_benchmark_v1_1/protocol.json'
            value=json.loads(path.read_text());value['qaoa']['maxiter']=201;save_json(path,value)
            with self.assertRaises(ValueError):load_benchmark(root)

    def test_best_valid_uses_frequency_then_bits_not_slack_energy(self):
        samples=[dict(bits=[1,1],probability=.1,energy=1,decoded={'feasible':True,'objective':1}),
                 dict(bits=[1,0],probability=.3,energy=9,decoded={'feasible':True,'objective':1}),
                 dict(bits=[0,1],probability=.3,energy=12,decoded={'feasible':True,'objective':1}),
                 dict(bits=[0,0],probability=.3,energy=0,decoded={'feasible':False,'objective':None})]
        result=select_output(samples,10,1)
        self.assertEqual(result['selected']['bits'],[0,1])
        self.assertEqual(result['mode_tie_count'],3)
        self.assertIsNone(result['unique_mode_valid'])
        self.assertEqual(len(result['mode_bits']),3)
        self.assertIsNone(select_output([samples[-1]],10,None)['selected'])


class BenchmarkARunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instance=dict(schema_version=1,instance_id='benchmark_a_test',objective='min_active_hosts',
            tasks=[dict(id='T0',cpu=1,ram=1)],hosts=[dict(id='H0',cpu=1,ram=1)])
        cls.bundle=build_qubo(cls.instance,assignment_penalty=3,capacity_penalty=3)
        cls.reference=prepare_reference(cls.bundle)
        cls.policy=dict(start_available_min_gib=.01,remaining_available_min_gib=.005,process_rss_stop_gib=4.)
        cls.config=dict(shots=32,evaluation_shots=64,maxiter=12,max_seconds=300.,max_qubits=4,
            seed=70,evaluation_seed=100070,reps=3,initial_point=[.3,0,0,1.,0,0],
            aer_threads=1,aer_memory_mb=256,min_available_gib=.01,
            hamiltonian_scaling='max_abs',cobyla_rhobeg=1.,cobyla_tol=1e-4)

    def small_context(self):
        context=deepcopy(load_benchmark(ROOT))
        context['manifest']['instances']=[dict(instance_id=self.instance['instance_id'],role='benchmark',encoded_qubits=4)]
        context['instances']={self.instance['instance_id']:self.instance}
        context['protocol']['qaoa'].update(depths=[3],optimization_seeds=[70,71],evaluation_seeds=[100070,100071])
        context['protocol']['qaoa'].update({k:self.config[k] for k in ('shots','evaluation_shots','maxiter','max_seconds')})
        context['protocol']['resource_policy'].update(self.policy)
        context['protocol']['negative_control']=None
        return context

    def test_p1_p2_p3_embedded_starts_have_identical_states(self):
        raw,_=build_ising(self.bundle);op,_=scale_ising(raw,'max_abs');states=[]
        for p in (1,2,3):
            circuit=QAOAAnsatz(op,reps=p)
            self.assertEqual([str(x) for x in circuit.parameters],[f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)])
            states.append(Statevector(circuit.assign_parameters([.3]+[0.]*(p-1)+[1.]+[0.]*(p-1))))
        for state in states[1:]:self.assertTrue(states[0].equiv(state))

    def test_low_available_and_high_rss_guards(self):
        for available,rss,start in ((7,1,True),(3,1,False),(10,5,False)):
            guard=ResourceGuard(dict(start_available_min_gib=8,remaining_available_min_gib=4,process_rss_stop_gib=4),
                snapshot=lambda:dict(available_gib=available,rss_gib=rss))
            with self.subTest(available=available,rss=rss),self.assertRaises(ResourceStop):guard.check('test',start=start)

    def test_insufficient_ram_blocks_before_backend_creation(self):
        with patch('src.benchmark_a_runner.memory_snapshot',return_value=dict(available_gib=0,rss_gib=.1)), \
             patch('src.benchmark_a_runner._aer_components') as backend:
            r=run_trial(self.bundle,self.config,self.policy,self.reference,progress=False)
        self.assertEqual(r['status'],'resource_blocked');backend.assert_not_called()

    def test_p3_report_and_probe_are_real_measured_runs(self):
        r=run_trial(self.bundle,self.config,self.policy,self.reference,progress=False)
        self.assertEqual(r['status'],'completed')
        self.assertEqual(sum(round(s['probability']*64) for s in r['final_samples']),64)
        self.assertEqual(r['optimizer_stop']['nfev'],len(r['optimization_history']))
        self.assertEqual(r['benchmark_output'],select_output(r['final_samples'],64,1))
        probe=probe_depth(self.bundle,self.config,self.policy,self.reference)
        self.assertEqual(probe['status'],'passed')
        self.assertEqual(len(probe['active_points']),3)
        self.assertTrue(all(all(v!=0 for v in point) for point in probe['active_points']))

    def test_running_resource_stop_preserves_partial_history(self):
        original=ResourceGuard.check
        def check(guard,stage,start=False):
            original(guard,stage,start=start)
            if stage=='optimizer_evaluation':raise ResourceStop('simulated memory pressure')
        with patch.object(ResourceGuard,'check',check):
            r=run_trial(self.bundle,self.config,self.policy,self.reference,progress=False)
        self.assertEqual(r['status'],'resource_stopped')
        self.assertEqual(len(r['optimization_history']),1)
        self.assertIsNone(r['final_samples'])

    def test_error_interrupt_and_timeout_are_distinct(self):
        for error,status in ((RuntimeError('backend failed'),'error'),(KeyboardInterrupt(),'interrupted')):
            with patch('src.benchmark_a_runner._aer_components',side_effect=error):
                r=run_trial(self.bundle,self.config,self.policy,self.reference,progress=False)
            self.assertEqual(r['status'],status)
        r=run_trial(self.bundle,{**self.config,'max_seconds':1e-9},self.policy,self.reference,progress=False)
        self.assertEqual(r['status'],'time_budget_exceeded')

    def test_ledger_recovers_interruption_and_validates_saved_evidence(self):
        context=load_benchmark(ROOT)
        context=deepcopy(context)
        context['manifest']['instances']=[dict(instance_id=self.instance['instance_id'],role='benchmark',encoded_qubits=4)]
        context['instances']={self.instance['instance_id']:self.instance}
        context['protocol']['qaoa'].update(depths=[3],optimization_seeds=[70],evaluation_seeds=[100070])
        context['protocol']['qaoa'].update({k:self.config[k] for k in ('shots','evaluation_shots','maxiter','max_seconds')})
        context['protocol']['resource_policy'].update(self.policy)
        context['protocol']['negative_control']=None
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);campaign=new_campaign(context);save_json(folder/'campaign.json',campaign)
            trial=campaign['planned_runs'][0]
            start_attempt(folder,campaign,trial,'trial')
            recover_active(folder,campaign,context)
            self.assertEqual(campaign['attempts'][0]['status'],'interrupted')
            start_attempt(folder,campaign,trial,'trial')
            r=run_trial(self.bundle,trial['config'],context['protocol']['resource_policy'],self.reference,progress=False)
            self.assertEqual(r['status'],'completed')
            finish_attempt(folder,campaign,r,context)
            rows=verify_campaign(folder,campaign,context)
            self.assertEqual(len(rows),1)
            self.assertEqual(len(campaign['attempts']),2)
            with self.assertRaises(ValueError):start_attempt(folder,campaign,trial,'trial')
            path=folder/campaign['attempts'][-1]['report'];value=json.loads(path.read_text(encoding='utf-8'))
            value['result']['final_samples'][0]['probability']+=1/64;save_json(path,value)
            with self.assertRaises(ValueError):verify_campaign(folder,campaign,context)

    def test_full_driver_resume_skips_reports_and_export_keeps_pending(self):
        context=self.small_context()
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);campaign=new_campaign(context);save_json(folder/'campaign.json',campaign)
            preparation=prepare_models(folder,context)
            self.assertEqual(preparation[0]['qubits'],4)
            self.assertGreater(preparation[0]['model_reference_seconds'],0)
            rows=result_rows(folder,campaign)
            self.assertEqual([r['status'] for r in rows],['pending','pending'])
            run_preflights(folder,context)
            campaign=run_campaign(folder,context,progress=False)
            self.assertEqual(len(verify_campaign(folder,campaign,context)),2)
            before={a['report']:(folder/a['report']).stat().st_mtime_ns for a in campaign['attempts']}
            with patch('src.benchmark_a_campaign.run_trial',side_effect=AssertionError('rerun')):
                campaign=run_campaign(folder,context,progress=False)
            self.assertEqual(before,{a['report']:(folder/a['report']).stat().st_mtime_ns for a in campaign['attempts']})
            export,rows=export_campaign(folder,context)
            self.assertTrue(export.is_file());self.assertEqual(len(rows),2)

    def test_recovery_after_result_write_before_ledger_commit(self):
        context=self.small_context()
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);campaign=new_campaign(context);trial=campaign['planned_runs'][0]
            start_attempt(folder,campaign,trial,'trial');interrupted_manifest=deepcopy(campaign)
            r=run_trial(self.bundle,trial['config'],context['protocol']['resource_policy'],self.reference,progress=False)
            finish_attempt(folder,campaign,r,context)
            save_json(folder/'campaign.json',interrupted_manifest)
            recover_active(folder,interrupted_manifest,context)
            self.assertEqual(len(verify_campaign(folder,interrupted_manifest,context)),1)
            self.assertEqual(interrupted_manifest['attempts'][0]['status'],'completed')

    def test_second_kernel_cannot_take_campaign_lock(self):
        with tempfile.TemporaryDirectory() as d:
            with _lock(d):
                with self.assertRaises(RuntimeError):
                    with _lock(d):pass


if __name__=='__main__':unittest.main()
