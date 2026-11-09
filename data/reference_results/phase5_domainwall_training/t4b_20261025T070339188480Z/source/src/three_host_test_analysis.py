"""Per-instance test summaries; seed repetitions are not independent instances."""
from collections import Counter
from statistics import mean, median, stdev


def summarize_test(rows, campaign):
    groups = []
    for name, p in sorted({(r['instance_id'], r['p']) for r in rows}):
        planned = [r for r in rows if (r['instance_id'], r['p']) == (name, p)]
        completed = [r for r in planned if r['status'] == 'completed']
        first = planned[0]
        item = dict(instance_id=name, p=p, planned=len(planned), completed=len(completed),
            status_counts=dict(Counter(r['status'] for r in planned)),
            valid_batches=sum(bool(r['found_valid']) for r in completed),
            optimal_batches=sum(bool(r['found_optimal']) for r in completed),
            uniform_optimal_probability=first['uniform_optimal_probability'],
            structured_random_optimal_probability=first['structured_random_optimal_probability'],
            uniform_batch_success=first['uniform_batch_success'],
            structured_random_batch_success=first['structured_random_batch_success'])
        for key in ('feasible_probability','optimal_probability','invalid_domain_probability',
                    'sample_mean_energy','optimal_lift_encoded','optimal_lift_structured_random'):
            values=[r[key] for r in completed if r[key] is not None]
            item[key+'_mean']=mean(values) if values else None
            item[key+'_sd']=stdev(values) if len(values)>1 else None
        for key in ('total_seconds','nfev','total_algorithm_shots'):
            values=[r[key] for r in completed if r[key] is not None]
            item[key+'_median']=median(values) if values else None
        q=item['optimal_probability_mean']
        item['optimal_difference_encoded']=None if q is None else q-first['uniform_optimal_probability']
        item['optimal_difference_random']=None if q is None else q-first['structured_random_optimal_probability']
        groups.append(item)
    counts=dict(Counter(r['status'] for r in rows));complete=counts.get('completed',0)
    status='complete' if complete==len(rows) else 'partial' if counts.get('pending',0) or counts.get('interrupted',0) else 'finished_with_failures'
    return dict(scope=campaign['scope'],campaign_id=campaign['campaign_id'],status=status,
        coverage=dict(planned=len(rows),completed=complete,status_counts=counts,
            valid_completed_batches=sum(bool(r['found_valid']) for r in rows if r['status']=='completed'),
            optimal_completed_batches=sum(bool(r['found_optimal']) for r in rows if r['status']=='completed')),
        budget=dict(limit_seconds=campaign['budget']['limit_seconds'],charged_seconds=campaign['budget']['charged_seconds'],
            remaining_seconds=max(0.,campaign['budget']['limit_seconds']-campaign['budget']['charged_seconds']),
            unconfirmed_wall_seconds=sum(s['unconfirmed_wall_seconds'] for s in campaign['budget']['sessions']),
            accounting='metered active stages plus conservative unclosed-session recovery; idle outside closed stages excluded'),
        halt=campaign['halt'],groups=groups,
        interpretation=dict(depth_selection='none',unit='instance; seed nested in instance',
            group_means='completed seed runs only; coverage always shown; missing does not mean zero',
            sd='descriptive seed variability, not a confidence interval over instances',
            quantum_batch_formula='no IID plug-in from pooled circuit probabilities',
            classical_comparison='random placement and exact enumeration; FF/BFD/MILP not included',
            claims='small frozen case study; no speedup or quantum-advantage claim'))


def plot_test_quality(summary, path):
    import matplotlib.pyplot as plt
    names=sorted({g['instance_id'] for g in summary['groups']})
    fig,axes=plt.subplots(2,3,figsize=(14,7),squeeze=False)
    for ax,name in zip(axes.flat,names):
        groups=sorted([g for g in summary['groups'] if g['instance_id']==name],key=lambda g:g['p'])
        available=[g for g in groups if g['optimal_probability_mean'] is not None]
        if available:
            ax.errorbar([g['p'] for g in available],[100*g['optimal_probability_mean'] for g in available],
                yerr=[100*(g['optimal_probability_sd'] or 0) for g in available],fmt='o-',capsize=3,label='QAOA')
        else:ax.text(.5,.5,'No completed trials',ha='center',va='center',transform=ax.transAxes)
        ax.axhline(100*groups[0]['uniform_optimal_probability'],color='gray',linestyle=':',label='Uniform encoded')
        ax.axhline(100*groups[0]['structured_random_optimal_probability'],color='tab:orange',linestyle='--',label='Random placement')
        ax.set_title(name+'; seeds='+','.join(str(g['completed']) for g in groups))
        ax.set_xticks([1,2,3]);ax.set_xlabel('p');ax.set_ylabel('Optimal final shots (%)');ax.set_ylim(bottom=0);ax.grid(alpha=.2)
    for ax in list(axes.flat)[len(names):]:ax.set_visible(False)
    axes[0,0].legend(fontsize=8);fig.suptitle('Frozen test campaign; SD across completed seeds; coverage shown')
    fig.tight_layout();fig.savefig(path,dpi=140);plt.close(fig)
