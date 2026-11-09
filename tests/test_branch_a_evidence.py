import hashlib
import io
import json
import unittest
import zipfile
from pathlib import Path
from src.branch_a_evidence import read_verified_zip, compare_csv, _audit_campaign


class EvidenceTests(unittest.TestCase):
    def archive(self,entries,checks=None):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            for name,data in entries.items():z.writestr(name,data)
            z.writestr('sha256.json',json.dumps(checks if checks is not None else
                {n:hashlib.sha256(d).hexdigest() for n,d in entries.items()}))
        return b.getvalue()

    def test_zip_requires_complete_checksums_and_confined_names(self):
        self.assertEqual(read_verified_zip(self.archive({'a.json':b'{}'}))['a.json'],b'{}')
        for b in [self.archive({'a':b'x'},{'a':'bad'}),self.archive({'a':b'x'},{}),
                  self.archive({'../escape':b'x'}),self.archive({'a\\b':b'x'})]:
            with self.assertRaises(ValueError):read_verified_zip(b)

    def test_duplicate_names_rejected(self):
        b=io.BytesIO(self.archive({'a':b'x'}))
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(b,'a') as z:z.writestr('a',b'x')
        with self.assertRaises(ValueError):read_verified_zip(b.getvalue())

    def test_csv_is_checked_against_recomputed_values(self):
        rows=[{'run_key':'abc','p':1,'optimal_probability':0.,'gap':None}]
        good=b'run_key,p,optimal_probability,gap\r\nabc,1,0.0,\r\n'
        compare_csv(good,rows)
        with self.assertRaises(ValueError):compare_csv(good.replace(b'0.0',b'0.5'),rows)

    def test_semantic_audit_rejects_rehashed_metric_tampering(self):
        root=Path(__file__).resolve().parents[1]
        data=(root/'data/benchmarks/nt409_summary_v1/notebook17_results.zip').read_bytes()
        files=read_verified_zip(data);campaign=json.loads(files['campaign.json'])
        row=next(a for a in campaign['attempts'] if a['kind']=='trial')
        report=json.loads(files[row['report']]);report['result']['metrics']['feasible_probability']+=.125
        files[row['report']]=json.dumps(report).encode()
        row['report_sha256']=hashlib.sha256(files[row['report']]).hexdigest()
        files['campaign.json']=json.dumps(campaign).encode();files.pop('sha256.json')
        verified=read_verified_zip(self.archive(files))
        with self.assertRaisesRegex(ValueError,'Compact metrics differ'):
            _audit_campaign(verified,campaign['design']['benchmark'],True,False)


if __name__=='__main__':unittest.main()
