# N29 validation receipt — 2026-10-27

Scope: T5 classical comparison of the existing four inputs, each exactly 5 tasks × 3 hosts. One development input and three frozen validation inputs. Existing N27/N28 quantum evidence is read and copied; no quantum optimizer is invoked.

Base revision: `9700f8fae29dfcbc33f0df4531d8bbdb3a520042` (N28 delivery).

## Verification completed

- Full unittest suite: **199 tests passed in 80.410 s**, including 12 N29 tests. Test-first slices covered scope/oracle consistency, explicit x/y validation, heuristic failure versus infeasibility, oracle agreement versus optimality certification, finite matching bounds, predecessor path safety, identity/snapshot changes, interrupted attempts, exclusive writer lock, completed-case reuse, and partial export/checksums.
- Native SCIP campaign: all four frozen cases, actual solver calls, no mocks; 12 algorithm attempts completed, four MILP optimality certificates. Reopening and requesting the completed cases under solver-call tripwires made zero additional calls.
- Notebook: **10/10 code cells executed successfully** in IPython against a separate fresh qualification campaign using actual SCIP. Notebook schema and Python cells validated. This is a Linux IPython execution check, not a claim of testing the user's Windows VS Code UI.
- Notebook outputs: 12 classical rows, 12 archived QAOA p2 rows, eight random-control rows; 20-row probability table. PNG/SVG probability chart generated; PNG inspected for labels, clipping and percent units. Each subplot explicitly uses its own vertical scale.
- Native ZIP: CRC passed; every member except the top-level SHA256 manifest is covered by that manifest, including the nested N27/N28 manifests. Source, raw results, inputs, exported LP models, and predecessor evidence are present.
- Original N27/N28 receipt hashes and quantum metrics were identical before and after native qualification. `src/`, N27 notebook, N28 notebook and `experiments/domain_wall_validation.py` are unchanged from the base revision.
- Blank delivery notebook has no saved executions or outputs. Linux qualification results are not prefilled as the user's Windows result and are not included in the installation ZIP.

## Observed native solver results

| Input | First Fit | BFD | MILP objective | MILP lower bound | MILP gap | MILP status |
|---|---:|---:|---:|---:|---:|---|
| a3_dev_n5 | 3 | 3 | 2 | 2 | 0 | optimal |
| v5x3_1 | 3 | 3 | 2 | 2 | 0 | optimal |
| v5x3_2 | no placement found | no placement found | 3 | 3 | 0 | optimal |
| v5x3_3 | 3 | 3 | 3 | 3 | 0 | optimal |

These are software qualification observations, not substitutes for the user's recorded run. Solvers receive only the instance and fixed solver settings; the enumeration optimum is used for subsequent validation, never as a target, hint or warm start.

## Qualification environment

- Python 3.12.14; Linux x86_64.
- OR-Tools 9.15.6755; SCIP 10.0.0, LP solver SoPlex 8.0.0.
- numpy 2.3.5, pandas 2.2.3, absl-py 2.3.1, protobuf 6.33.1, immutabledict 4.2.2, typing-extensions 4.16.0.
- OR-Tools installed into an isolated dependency directory. Existing quantum dependencies were not upgraded.
- MILP: one thread; 600-second solve limit; random seed shift 0; relative and absolute solver gap targets 0; one call per input. Model has 18 binary variables: 15 x and three y.

## Reviewed limitations and decisions

N29 lives outside `src/` because N27/N28 source identities hash the shared implementation. The existing classical solver module is reused unchanged. The new reader validates predecessor evidence without requiring the current classical runtime to equal the historical QAOA runtime; both runtimes remain recorded.

Each completed case keeps exactly one recorded attempt for each algorithm. An interrupted/failed case is preserved and blocks automatic retries. A machine crash can leave a writer lock or a raw/ledger mismatch; the campaign then needs review rather than silently receiving fresh attempts. Failed solver returns are retained in raw evidence but excluded from comparison tables until validated.

MILP certificates require status `optimal`, a valid explicit x/y solution, objective agreement with enumeration, a finite matching lower bound and zero gap within tolerance. Oracle agreement alone does not promote a feasible-but-unproven result. A heuristic failing on v5x3_2 is not an infeasibility certificate.

The three validation cases are conditioned synthetic inputs, not a population-wide benchmark. Classical per-solve timing is measured once; quantum training includes different work. These measurements support descriptive cost reporting only. Random host assignment infers y, unlike uniform encoded bitstrings. QAOA p2 remains the primary depth; its training cost includes p1.

T5 remains pending review of the user's Windows notebook, result ZIP and N29_ACTIVE pointer. No changes to dataset, penalties, depth or task/host count are introduced by this delivery.
