"""Windows line endings and editing the resume path must not break comparisons."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

NOTEBOOK = Path(__file__).resolve().parents[1] / 'notebooks/13_qaoa_exact_budget_choice.ipynb'


class ExactBudgetNotebookTests(unittest.TestCase):
    def test_resume_path_and_outputs_do_not_change_protocol_fingerprint(self):
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        source = ''.join(nb['cells'][4]['source'])
        helper = source[source.index('def notebook_digest('):source.index('def read_baseline(')]
        namespace = {'json':json, 'hashlib':hashlib, 'Path':Path}
        exec(helper, namespace)
        digest = namespace['notebook_digest']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notebook.ipynb'
            path.write_text(json.dumps(nb))
            before = digest(path)
            nb['cells'][4]['source'] = source.replace('RESUME_MANIFEST = None', 'RESUME_MANIFEST = "saved.json"', 1)
            nb['cells'][4]['outputs'] = [{'output_type':'stream', 'text':'anything'}]
            path.write_text(json.dumps(nb))
            self.assertEqual(before, digest(path))
            nb['cells'][4]['source'] = nb['cells'][4]['source'].replace('MAX_EVALUATIONS = 200','MAX_EVALUATIONS = 300')
            path.write_text(json.dumps(nb))
            self.assertNotEqual(before, digest(path))

    def test_crlf_is_equivalent_but_changed_code_is_rejected(self):
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        source = ''.join(nb['cells'][6]['source'])
        guard = source[source.index('core_changes, newline_only'):source.index('runtime_changes =')]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'src').mkdir()
            path=root/'src/placement.py'; path.write_bytes(b'x=1\n')
            old = hashlib.sha256(b'x=1\r\n').hexdigest()
            ns={'ROOT':root, 'hashlib':hashlib,
                'old_env':{'source_sha256':{'placement.py':old}},
                'current_env':{'source_sha256':{'placement.py':hashlib.sha256(path.read_bytes()).hexdigest()}}}
            exec(guard,ns)
            self.assertEqual(ns['newline_only'],['placement.py'])
            path.write_bytes(b'x=2\n')
            ns['current_env']['source_sha256']['placement.py']=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(RuntimeError): exec(guard,ns)


if __name__ == '__main__': unittest.main()
