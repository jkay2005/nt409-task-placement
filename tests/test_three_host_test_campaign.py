from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.three_host_test_campaign import (BudgetClock, recover_budget, load_test_context,
    make_test_trials, open_test_campaign, run_test_phase, prepare_test_models,
    verify_test_campaign, export_test_campaign, _start_test_attempt, audit_pilot_archive)
from src.benchmark_a_campaign import save_json, _read, _digest
from test_three_host_encoding import instance

ROOT=Path(__file__).resolve().parents[1]


def tiny_context():
    context=deepcopy(load_test_context(ROOT))
    item=instance();item['instance_id']='tiny_test'
    context['instances']={item['instance_id']:item}
    context['manifest']['instances']=[dict(instance_id=item['instance_id'],role='test',num_tasks=1,num_qubits=11)]
    context['test_protocol']['qaoa'].update(depths=[1],optimization_seeds=[200,201],
        evaluation_seeds=[100200,100201],shots=32,evaluation_shots=32,maxiter=12,max_seconds=60.)
    context['test_protocol']['resource_policy'].update(start_available_min_gib=.1,
        remaining_available_min_gib=.1,aer_threads=1)
    context['test_protocol']['budget'].update(limit_seconds=30.,export_reserve_seconds=.01,probe_admission_seconds=.01)
    return context


class ThreeHostTestCampaignTests(unittest.TestCase):
    def test_accidentally_changed_protocol_cannot_start_a_new_official_campaign(self):
        c=deepcopy(load_test_context(ROOT));c['test_protocol']['qaoa']['shots']+=1
        with self.assertRaisesRegex(ValueError,'Test protocol changed'):
            audit_pilot_archive(ROOT,'does_not_exist.zip',c)

    def test_fixed_ninety_trials_are_balanced_and_new_seeded(self):
        c=load_test_context(ROOT);trials=make_test_trials(c)
        self.assertEqual(len(trials),90);self.assertEqual(len({t['run_key'] for t in trials}),90)
        self.assertTrue(all(t['role']=='test' for t in trials))
        self.assertEqual({t['config']['seed'] for t in trials},{200,201,202,203,204})
        first=trials[:18]
        self.assertEqual(len({(t['instance_id'],t['config']['reps']) for t in first}),18)
        self.assertEqual([len(c['instances'][t['instance_id']]['tasks']) for t in trials[:6]],[4,5,4,5,4,5])
        self.assertTrue(all(t['config']['evaluation_seed']!=t['config']['seed'] for t in trials))

    def test_budget_counts_active_time_preserves_idle_and_conservative_crash(self):
        state=dict(limit_seconds=20.,charged_seconds=0.,sessions=[])
        current=[0.];origin=datetime(2026,10,12,tzinfo=timezone.utc)
        def tick():return current[0]
        def utc():return (origin+timedelta(seconds=current[0])).isoformat()
        clock=BudgetClock(state,'prepare',tick=tick,utc=utc)
        current[0]=3.;clock.checkpoint();current[0]=5.;clock.close()
        self.assertEqual(state['charged_seconds'],5.)
        current[0]=105.;clock=BudgetClock(state,'trial',tick=tick,utc=utc)
        current[0]=107.;clock.checkpoint()
        self.assertEqual(clock.remaining(),13.)
        recover_budget(state,(origin+timedelta(seconds=110)).isoformat())
        self.assertEqual(state['charged_seconds'],10.)
        self.assertTrue(state['sessions'][-1]['recovered'])
        self.assertEqual(state['sessions'][-1]['unconfirmed_wall_seconds'],3.)
        self.assertTrue(state['sessions'][-1]['closed'])

    def test_resumed_completed_trials_never_repeat_and_rehashed_tamper_fails(self):
        c=tiny_context()
        with TemporaryDirectory() as d, patch('src.three_host_test_campaign.audit_pilot_archive',return_value={'validated':True}):
            f,m=open_test_campaign(d,c,'unused.zip');prepare_test_models(f,c)
            run_test_phase(f,c,'probe',progress=False)
            run_test_phase(f,c,'trial',max_new_trials=1,progress=False)
            m=_read(f/'campaign.json');self.assertEqual(len([a for a in m['attempts'] if a['kind']=='trial']),1)
            before=m['budget']['charged_seconds']
            f,m=open_test_campaign(d,c,None,f.relative_to(Path(d)).as_posix())
            self.assertGreaterEqual(m['budget']['charged_seconds'],before)
            run_test_phase(f,c,'trial',progress=False)
            with patch('src.three_host_test_campaign.run_three_host_trial',side_effect=AssertionError('rerun')):
                run_test_phase(f,c,'trial',progress=False)
            archive,rows,summary=export_test_campaign(f,c)
            self.assertTrue(archive.is_file());self.assertEqual(len(rows),2)
            self.assertEqual(summary['coverage']['completed'],2)
            self.assertEqual(summary['status'],'complete')
            m=_read(f/'campaign.json');a=m['attempts'][-1];path=f/a['report'];e=_read(path)
            self.assertLess(e['attempt']['execution_config']['max_seconds'],60.)
            self.assertEqual(e['attempt']['trial']['config']['max_seconds'],60.)
            e['result']['metrics']['invalid_domain_probability']+=.1;save_json(path,e)
            a['report_sha256']=_digest(path)
            with self.assertRaises(ValueError):verify_test_campaign(f,m,c)

    def test_budget_stop_keeps_pending_rows_and_cannot_reset_by_resume(self):
        c=tiny_context();c['test_protocol']['budget']['limit_seconds']=.001
        with TemporaryDirectory() as d, patch('src.three_host_test_campaign.audit_pilot_archive',return_value={'validated':True}):
            f,m=open_test_campaign(d,c,'unused.zip')
            with patch('src.three_host_test_campaign.probe_three_host',side_effect=AssertionError('budget bypass')):
                run_test_phase(f,c,'probe',progress=False)
            archive,rows,s=export_test_campaign(f,c)
            self.assertEqual(len(rows),2);self.assertTrue(all(r['status']=='pending' for r in rows))
            self.assertEqual(s['status'],'partial')
            f,m=open_test_campaign(d,c,None,f.relative_to(Path(d)).as_posix())
            self.assertEqual(m['budget']['limit_seconds'],.001)
            altered=deepcopy(c);altered['test_protocol']['budget']['limit_seconds']=300
            with self.assertRaises(ValueError):verify_test_campaign(f,m,altered)

    def test_preflight_required_and_non_test_roles_excluded(self):
        c=tiny_context();bad=deepcopy(c);bad['manifest']['instances'][0]['role']='development'
        with self.assertRaises(ValueError):make_test_trials(bad)
        with TemporaryDirectory() as d, patch('src.three_host_test_campaign.audit_pilot_archive',return_value={'validated':True}):
            f,m=open_test_campaign(d,c,'unused.zip');prepare_test_models(f,c)
            with self.assertRaises(ValueError):run_test_phase(f,c,'trial',progress=False)

    def test_kernel_crash_records_interruption_and_preserves_budget(self):
        c=tiny_context()
        with TemporaryDirectory() as d, patch('src.three_host_test_campaign.audit_pilot_archive',return_value={'validated':True}):
            f,m=open_test_campaign(d,c,'unused.zip');before=m['budget']['charged_seconds']
            clock=BudgetClock(m['budget'],'probe',save=lambda:save_json(f/'campaign.json',m))
            _start_test_attempt(f,m,m['planned_runs'][0],'probe',clock.remaining(),.01)
            f,m=open_test_campaign(d,c,None,f.relative_to(Path(d)).as_posix())
            self.assertIsNone(m['active']);self.assertEqual(m['attempts'][0]['status'],'interrupted')
            self.assertGreaterEqual(m['budget']['charged_seconds'],before)
            self.assertTrue(any(s['recovered'] for s in m['budget']['sessions']))
            self.assertTrue(all(s['closed'] for s in m['budget']['sessions']))
