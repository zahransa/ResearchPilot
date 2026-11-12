# ResearchPilot v0.2.1 — Gemma API retry and 3-to-16-task resume hotfix

This is a *patch* for the existing v0.2 project, not a replacement project.

It updates `researchpilot/experiment.py` and `tests/test_experiment.py` only.
Do not overwrite your original `results/gemma_generations.json`, `results/gemma_scores.json`, or `results/gemma_pilot_report.md`.

## Install in PowerShell

```powershell
cd "$HOME\Downloads\ResearchPilot_Kaggle_v0.2"
Expand-Archive -Path "$HOME\Downloads\ResearchPilot_v0.2.1_hotfix.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: **12 tests passed** (offline; no paid model calls).

## Continue the 16-task run without redoing the first 3 tasks

Only if `results\gemma_generations.json` is a COMPLETE 3-task, same-model pilot generated under identical parameters:

```powershell
.\.venv\Scripts\python.exe -m researchpilot.experiment generate --provider gemini --model gemma-4-26b-a4b-it --max-tasks 16 --output .\results\gemma_generations_16.json --reuse-generations .\results\gemma_generations.json
```

This keeps any already completed model responses in the 16-task file and copies the first three completed pilot records into it, after checking the model, benchmark hash, prompt protocol, candidate count, temperature, and token limits. It then requests only missing candidates. No source code from pre-authored synthetic candidates is reused.

The command makes a bounded number of retries with exponential delays for HTTP 408/429/500/502/503/504 and connection timeouts/resets, but not bad credentials or invalid model requests. A provider failure may still be billable. Repeat the same command after a temporary outage to continue from the saved checkpoint.

If your 3-task pilot was generated with different parameters, do **not** use `--reuse-generations`; the command will refuse incompatible reuse. Run without it.

## Score / report after COMPLETE generation

```powershell
.\.venv\Scripts\python.exe -m researchpilot.experiment score --generations .\results\gemma_generations_16.json --output .\results\gemma_scores_16.json
.\.venv\Scripts\python.exe -m researchpilot.experiment report --input .\results\gemma_scores_16.json --output .\results\gemma_report_16.md
Get-Content .\results\gemma_report_16.md
```

Generated code executes only through the existing Docker runner with the network disabled.

## Scientific limitations

These are simple hand-authored Python functions with curated probes, not real-world repository repair. The 3-task pilot produced 3/3 held-out passes for *both* methods. Do not claim an improvement before the expanded experiment shows one. Preserve the raw model generations and scoring artifacts privately for reproducibility, check them for secrets before sharing, and disclose AI-assisted implementation.
