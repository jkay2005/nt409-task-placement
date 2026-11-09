"""Classical placement solvers; no reference optimum is supplied to any solver."""
from fractions import Fraction
import math
from time import perf_counter

from .placement import _arrays, evaluate_model, evaluate_placement

ALGORITHMS = ('FirstFit', 'BFD', 'MILP')
ORTOOLS_VERSION = '9.15.6755'
SCIP_OPTIONS = 'randomization/randomseedshift = 0\nlimits/gap = 0\nlimits/absgap = 0'


def _empty(algorithm):
    return dict(algorithm=algorithm, status='no_placement_found', found_valid=False,
                objective=None, placement=None, x=None, y=None,
                solver_certified_optimal=False, solver_certified_infeasible=False,
                solver_bound=None, solver_gap=None, solver_version=None)


def solve_heuristic(instance, algorithm):
    start = perf_counter()
    if algorithm not in ALGORITHMS[:2]:
        raise ValueError(f'Unknown heuristic: {algorithm}')
    demand, capacity = _arrays(instance)
    demand, capacity = demand.tolist(), capacity.tolist()
    remaining = [row[:] for row in capacity]
    active = [False] * len(capacity)
    order = list(range(len(demand)))
    setup_end = perf_counter()
    if algorithm == 'BFD':
        maxima = [max(c[r] for c in capacity) for r in range(2)]
        order.sort(key=lambda i: (-max(Fraction(demand[i][r], maxima[r]) for r in range(2)), i))
    placement = [-1] * len(demand)
    trace = []
    for i in order:
        candidates = [h for h, rem in enumerate(remaining)
                      if all(demand[i][r] <= rem[r] for r in range(2))]
        if not candidates:
            trace.append(dict(task_index=i, host_index=None))
            break
        if algorithm == 'FirstFit':
            host = candidates[0]
        else:
            opened = [h for h in candidates if active[h]]
            candidates = opened or candidates
            host = min(candidates, key=lambda h: (
                sum(Fraction(remaining[h][r] - demand[i][r], capacity[h][r]) for r in range(2)), h))
        placement[i] = host
        active[host] = True
        for r in range(2):
            remaining[host][r] -= demand[i][r]
        trace.append(dict(task_index=i, host_index=host))
    solve_end = perf_counter()
    result = _empty(algorithm)
    if -1 not in placement:
        checked = evaluate_placement(instance, placement)
        if not checked['feasible']:
            raise ValueError('Heuristic returned an invalid placement.')
        result.update({k: checked[k] for k in ('objective', 'placement', 'x', 'y')})
        result.update(status='feasible', found_valid=True)
    result.update(trace=trace, task_processing_order=order)
    result.update(build_seconds=setup_end-start, solve_seconds=solve_end-setup_end,
                  check_seconds=perf_counter()-solve_end, total_seconds=perf_counter()-start)
    return result


def binary_values(values, tolerance=1e-6):
    """Only accept numerical noise near 0/1, never repair fractional solutions."""
    result = []
    for value in values:
        if not math.isfinite(value) or min(abs(value), abs(value-1)) > tolerance:
            raise ValueError(f'Nonbinary solver value: {value}')
        result.append(int(value >= 0.5))
    return result


def solver_status(code):
    from ortools.linear_solver import pywraplp
    s = pywraplp.Solver
    return {s.OPTIMAL: 'optimal', s.FEASIBLE: 'feasible_not_proven',
            s.INFEASIBLE: 'infeasible', s.UNBOUNDED: 'unbounded',
            s.ABNORMAL: 'abnormal', s.MODEL_INVALID: 'model_invalid',
            s.NOT_SOLVED: 'no_incumbent'}.get(code, 'unknown')


def solve_milp(instance, time_limit_seconds=600):
    # Imports excluded from per-solve timing; campaign preflight records the runtime.
    import ortools
    from ortools.linear_solver import pywraplp, linear_solver_pb2
    if ortools.__version__ != ORTOOLS_VERSION:
        raise RuntimeError(f'Install ortools=={ORTOOLS_VERSION}; found {ortools.__version__}')
    if not math.isfinite(time_limit_seconds) or time_limit_seconds <= 0:
        raise ValueError('time_limit_seconds must be positive and finite')
    start = perf_counter()
    demand, capacity = _arrays(instance)
    n, m = len(demand), len(capacity)
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if solver is None:
        raise RuntimeError('SCIP backend is unavailable; do not substitute another solver.')
    if not solver.SetNumThreads(1) or not solver.SetSolverSpecificParametersAsString(SCIP_OPTIONS):
        raise RuntimeError('SCIP did not accept the frozen options.')
    solver.SetTimeLimit(max(1, int(time_limit_seconds * 1000)))
    x = [[solver.BoolVar(f'x_{i}_{h}') for h in range(m)] for i in range(n)]
    y = [solver.BoolVar(f'y_{h}') for h in range(m)]
    for i in range(n):
        solver.Add(solver.Sum(x[i]) == 1)
    for h in range(m):
        for r in range(2):
            solver.Add(solver.Sum(int(demand[i, r])*x[i][h] for i in range(n))
                       <= int(capacity[h, r])*y[h])
    solver.Minimize(solver.Sum(y))
    build_end = perf_counter()
    code = solver.Solve()
    solve_end = perf_counter()
    result = _empty('MILP')
    result.update(status=solver_status(code), solver_status_code=code,
                  solver_version=solver.SolverVersion(), ortools_version=ortools.__version__,
                  solver_certified_infeasible=(code == pywraplp.Solver.INFEASIBLE),
                  time_limit_seconds=time_limit_seconds, threads=1, options=SCIP_OPTIONS)
    if code in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        response = linear_solver_pb2.MPSolutionResponse()
        solver.FillSolutionResponseProto(response)
        raw = list(response.variable_value)
        values = binary_values(raw)
        xx = [values[i*m:(i+1)*m] for i in range(n)]
        yy = values[n*m:]
        checked = evaluate_model(instance, xx, yy)
        if not checked['feasible'] or not solver.VerifySolution(1e-6, False):
            raise ValueError('MILP solution failed the shared validator.')
        objective = checked['objective']
        if abs(solver.Objective().Value() - objective) > 1e-6:
            raise ValueError('MILP objective differs from explicit y.')
        bound = solver.Objective().BestBound()
        bound = float(bound) if math.isfinite(bound) else None
        result.update(found_valid=True, objective=objective, x=xx, y=yy,
                      placement=[row.index(1) for row in xx], raw_variable_values=raw,
                      solver_certified_optimal=(code == pywraplp.Solver.OPTIMAL),
                      solver_bound=bound,
                      solver_gap=None if bound is None else max(0., objective-bound)/max(1., abs(objective)))
    check_end = perf_counter()
    result.update(build_seconds=build_end-start, solve_seconds=solve_end-build_end,
                  check_seconds=check_end-solve_end, total_seconds=check_end-start)
    # Serialization/model export is an audit expense, excluded from total_seconds.
    result['model_lp'] = solver.ExportModelAsLpFormat(False)
    return result
