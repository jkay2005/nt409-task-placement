# Task Placement — Problem Specification v1

## Objective
Minimize the number of activated hosts while placing every task.

## Input
- Each task has an ID, CPU demand and RAM demand.
- Each host has an ID, CPU capacity and RAM capacity.
- CPU and RAM values are positive integers.
- Demand and capacity use the same unit for each resource.
- Task IDs are unique; host IDs are unique.
- List order determines task and host indices.

## Decision variables
- x[i,h] = 1 if task i is assigned to host h; otherwise 0.
- y[h] = 1 if host h is activated; otherwise 0.
- All decision variables are binary.

## Objective function
Minimize sum_h y[h].

## Constraints
For every task i:
    sum_h x[i,h] = 1

For every host h:
    sum_i cpu[i] * x[i,h] <= cpu_capacity[h] * y[h]
    sum_i ram[i] * x[i,h] <= ram_capacity[h] * y[h]

## Evaluation conventions
- A placement contains one host index per task.
- When evaluating a placement, activate exactly its occupied hosts.
- When evaluating explicit x,y, preserve the supplied activation vector.
- An infeasible result has objective = None.