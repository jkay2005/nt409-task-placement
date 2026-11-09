import unittest
from itertools import product
from collections import Counter
import numpy as np
from src.ising import build_ising, ising_energy
from src.placement import evaluate_placement
from src.three_host_encoding import (build_three_host_qubo, decode_three_host,
    energy_formula, three_host_reference, certify_three_host)


def instance(tasks=((1,1),), hosts=((1,1),(1,1),(1,1)), name='tiny3'):
    return dict(schema_version=1, instance_id=name, objective='min_active_hosts',
        tasks=[dict(id=f't{i}',cpu=c,ram=r) for i,(c,r) in enumerate(tasks)],
        hosts=[dict(id=f'h{i}',cpu=c,ram=r) for i,(c,r) in enumerate(hosts)])


class ThreeHostEncodingTests(unittest.TestCase):
    def test_full_tiny_truth_energy_and_uniform_including_invalid_domain(self):
        b=build_three_host_qubo(instance()); op,offset=build_ising(b)
        energies=[];feasible=optimal=0
        for values in product((0,1),repeat=b['qubo'].get_num_vars()):
            e=b['qubo'].objective.evaluate(list(values));d=decode_three_host(b,values)
            self.assertEqual(e,energy_formula(b,values))
            self.assertAlmostEqual(e,ising_energy(op,offset,values))
            energies.append(e);feasible+=d['feasible'];optimal+=d['feasible'] and d['objective']==1
        r=three_host_reference(b);u=r['uniform_baseline'];total=len(energies)
        self.assertEqual(r['minimum_energy'],min(energies))
        self.assertEqual(u['ground_state_probability'],energies.count(min(energies))/total)
        self.assertEqual(u['feasible_probability'],feasible/total)
        self.assertEqual(u['optimal_placement_probability'],optimal/total)
        self.assertEqual(u['mean_qubo_energy'],sum(energies)/total)
        self.assertTrue(r['all_qubo_minimizers_feasible'])

    def test_three_labels_and_invalid_label_never_repair_y(self):
        b=build_three_host_qubo(instance())
        for uv,host in [([0,0],0),([1,0],1),([1,1],2)]:
            bits=[0]*b['qubo'].get_num_vars();bits[:2]=uv;bits[2+host]=1
            d=decode_three_host(b,bits)
            self.assertTrue(d['feasible']);self.assertEqual(d['placement'],[host])
            bits[2+host]=0;self.assertFalse(decode_three_host(b,bits)['feasible'])
        bits=[0]*b['qubo'].get_num_vars();bits[:2]=[0,1];bits[2:5]=[1,1,1]
        d=decode_three_host(b,bits)
        self.assertFalse(d['domain_valid']);self.assertFalse(d['feasible'])
        self.assertIsNone(d['objective']);self.assertIsNone(d['placement'])

    def test_five_task_optimum_and_capacity_four_counterexample(self):
        tasks=((2,1),(1,2),(1,1),(1,1),(1,1))
        for hosts,expected in [(((3,3),)*3,{2:6,3:96}),(((4,3),(2,3),(1,1)),{2:3,3:12})]:
            i=instance(tasks,hosts);b=build_three_host_qubo(i);r=three_host_reference(b)
            h=Counter()
            for a in product(range(3),repeat=5):
                d=evaluate_placement(i,a)
                if d['feasible']:h[d['objective']]+=1
            self.assertEqual(dict(h),expected);self.assertEqual(r['placement_histogram'],{str(k):v for k,v in expected.items()})
            self.assertEqual(r['minimum_energy'],2);self.assertTrue(r['all_qubo_minimizers_feasible'])
            self.assertLessEqual(b['qubo'].get_num_vars(),25)
            self.assertTrue(certify_three_host(b)['polynomial_identity'])

    def test_infeasible_and_rejected_shape_or_host_count(self):
        r=three_host_reference(build_three_host_qubo(instance(((2,2),))))
        self.assertIsNone(r['original_best_objective']);self.assertIsNone(r['uniform_baseline']['optimal_placement_probability'])
        self.assertEqual(r['uniform_baseline']['feasible_probability'],0)
        with self.assertRaises(ValueError):build_three_host_qubo(instance(hosts=((1,1),)*2))
        b=build_three_host_qubo(instance())
        with self.assertRaises(ValueError):decode_three_host(b,[0,1])
