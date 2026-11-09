from copy import deepcopy
import unittest
from src.three_host_test_analysis import summarize_test


def row(status='completed', probability=0.):
    return dict(instance_id='case',p=1,status=status,found_valid=True if status=='completed' else None,
        found_optimal=probability>0 if status=='completed' else None,uniform_optimal_probability=.001,
        structured_random_optimal_probability=.03,uniform_batch_success=.64,structured_random_batch_success=.999,
        feasible_probability=.02 if status=='completed' else None,optimal_probability=probability if status=='completed' else None,
        invalid_domain_probability=.6 if status=='completed' else None,sample_mean_energy=100. if status=='completed' else None,
        optimal_lift_encoded=probability/.001 if status=='completed' else None,
        optimal_lift_structured_random=probability/.03 if status=='completed' else None,
        total_seconds=1.,nfev=10,total_algorithm_shots=12288)


class ThreeHostTestAnalysisTests(unittest.TestCase):
    def test_zero_samples_and_missing_runs_have_different_meanings(self):
        campaign=dict(scope='test',campaign_id='case',halt=None,
            budget=dict(limit_seconds=30,charged_seconds=2.,sessions=[]))
        summary=summarize_test([row(),row('pending'),row('error')],campaign)
        group=summary['groups'][0]
        self.assertEqual(summary['status'],'partial');self.assertEqual(group['completed'],1)
        self.assertEqual(group['optimal_probability_mean'],0.);self.assertIsNone(group['optimal_probability_sd'])
        self.assertEqual(group['optimal_batches'],0);self.assertEqual(group['planned'],3)
        empty=summarize_test([row('pending')],campaign)
        self.assertIsNone(empty['groups'][0]['optimal_probability_mean'])

    def test_seed_sd_is_descriptive_and_baselines_are_both_preserved(self):
        campaign=dict(scope='test',campaign_id='case',halt=None,
            budget=dict(limit_seconds=30,charged_seconds=2.,sessions=[]))
        summary=summarize_test([row(probability=.01),row(probability=.02)],campaign)
        self.assertEqual(summary['status'],'complete');g=summary['groups'][0]
        self.assertAlmostEqual(g['optimal_probability_mean'],.015)
        self.assertAlmostEqual(g['optimal_difference_encoded'],.014)
        self.assertAlmostEqual(g['optimal_difference_random'],-.015)
        self.assertNotIn('confidence_interval',g)
        failed=summarize_test([row('error')],campaign)
        self.assertEqual(failed['status'],'finished_with_failures')
