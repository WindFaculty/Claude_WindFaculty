# Skill: Benchmark Suite Execution

## Overview
This skill provides instructions on loading task specs, executing execution benchmarks, and storing performance/accuracy scoring results.

## Process Workflow

1. **Load Benchmark Configurations**:
   Inspect `configs/benchmark.yaml` and `benchmarks/suites/smoke.yaml` to identify run parameters and target files.
2. **Execute Benchmark Runner**:
   Initiate the test runner wrapper for the active suite:
   ```bash
   python scripts/benchmark/run_suite.py --suite smoke
   ```
3. **Capture Execution Trace**:
   Save runtime speeds, CPU footprints, pass rates, and model usage metadata inside `benchmarks/results/`.

## Expected Deliverables
* `benchmarks/results/<run_id>.json`
* Benchmark runtime metrics report inside `reports/`.
