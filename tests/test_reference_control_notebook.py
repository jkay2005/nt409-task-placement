"""Exercise the notebook's actual orchestration cells on a four-qubit model."""
import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import pandas as pd
from src.qubo import build_qubo
from src.qaoa_experiment import prepare_reference
from src.convergence_diagnostics import run_exact_qaoa
from src import convergence_campaign as mean_campaign
from src import cvar_experiment as cvar_campaign


class ReferenceNotebookTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        notebook=Path(__file__).resolve().parents[1]/'notebooks/15_qaoa_reference_control.ipynb'
        cells=json.loads(notebook.read_text(encoding='utf-8'))['cells']
        self.cells={c['metadata']['tags'][0]:''.join(c['source']) for c in cells if c['cell_type']=='code'}
        instance=dict(schema_version=1,instance_id='reference_control_test',objective='min_active_hosts',
            tasks=[dict(id='T0',cpu=1,ram=1)],hosts=[dict(id='H0',cpu=1,ram=1)])
        bundle=build_qubo(instance,assignment_penalty=3,capacity_penalty=3)
        self.ns=dict(ROOT=Path(self.directory.name),datetime=datetime,timezone=timezone,json=json,
            pd=pd,display=lambda value:None,mean_campaign=mean_campaign,cvar_campaign=cvar_campaign,
            run_exact_qaoa=run_exact_qaoa,instance=instance,bundle=bundle,reference=prepare_reference(bundle),
            SEED=60,ALPHA=.1,STARTS={'common':[.3,1.],'alternative':[.8,1.2]},RESUME_DIR=None,
            BASE_CONFIG=dict(shots=64,evaluation_shots=64,maxiter=8,max_seconds=300.,max_qubits=4,
                aer_threads=1,aer_memory_mb=256,min_available_gib=.01,
                hamiltonian_scaling='max_abs',cobyla_rhobeg=1.,cobyla_tol=1e-4))

    def cell(self,name):
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(self.cells[name],f'notebook-{name}','exec'),self.ns)

    def test_partial_resume_keeps_saved_trial_and_completes_four_matched_runs(self):
        self.cell('campaigns');ns=self.ns
        ns['oracle']=cvar_campaign.ExactCVaROracle(ns['bundle'],ns['mean']['planned_runs'][0]['config'],ns['reference'])
        first=run_exact_qaoa(ns['bundle'],ns['mean']['planned_runs'][0]['config'],ns['reference'],ns['oracle'],progress=False)
        ns['run_exact_qaoa']=Mock(side_effect=[first,RuntimeError('simulated interruption')])
        with self.assertRaisesRegex(RuntimeError,'simulated interruption'):self.cell('runs')
        saved=ns['ROOT']/ns['mean']['completed_runs'][0]['report']
        before=(saved.read_bytes(),saved.stat().st_mtime_ns)
        ns['RESUME_DIR']=ns['RESULT_DIR'].relative_to(ns['ROOT']).as_posix()
        self.cell('campaigns')
        self.assertEqual(len(ns['mean_rows'])+len(ns['cvar_rows']),1)
        ns['run_exact_qaoa']=Mock(wraps=run_exact_qaoa)
        self.cell('runs')
        self.assertEqual(ns['run_exact_qaoa'].call_count,1)
        self.assertEqual(len(ns['mean_rows'])+len(ns['cvar_rows']),4)
        self.assertEqual(before,(saved.read_bytes(),saved.stat().st_mtime_ns))
        report_times={r['report']:(ns['ROOT']/r['report']).stat().st_mtime_ns for r in ns['mean_rows']+ns['cvar_rows']}
        ns['run_exact_qaoa']=Mock(side_effect=AssertionError('must skip completed'))
        self.cell('campaigns');self.cell('runs')
        self.assertEqual(report_times,{r['report']:(ns['ROOT']/r['report']).stat().st_mtime_ns for r in ns['mean_rows']+ns['cvar_rows']})

    def test_resume_rejects_wrong_baseline_and_directory_outside_repo(self):
        self.cell('campaigns');ns=self.ns
        ns['RESUME_DIR']=ns['RESULT_DIR'].relative_to(ns['ROOT']).as_posix()
        altered=json.loads(ns['CVAR_PATH'].read_text(encoding='utf-8'))
        altered['design']['study']['baseline']['mean_campaign_id']='another_campaign'
        ns['CVAR_PATH'].write_text(json.dumps(altered),encoding='utf-8')
        with self.assertRaises(ValueError):self.cell('campaigns')
        ns['RESUME_DIR']='..'
        with self.assertRaises(ValueError):self.cell('campaigns')


if __name__=='__main__':unittest.main()
