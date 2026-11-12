# ResearchPilot v0.2 — Gemma 4 coding experiment

**Status:** Local software validation passed (10 Python unit tests). **No real Gemma 4 model evaluation has been run by the project author yet.** You must run the model experiment on your own API account and inspect its results. This project is an experiment on **function-level code repair**, not yet a full autonomous repository-repair agent.

## Windows PowerShell: start here

Prerequisites: Python 3.10+; internet access for Gemma API. Later, Docker Desktop with a running Linux engine for safe scoring.

1. Extract this ZIP into a folder. **Open PowerShell inside that folder**, containing `README.md`, `researchpilot`, `tests`, and `benchmarks`. There is no extra nested directory in the new ZIP.
2. Verify the local software and install the two SDK dependencies:

```powershell
python -m unittest discover -s tests -v
python -m pip install -r requirements.txt
```

3. Create a Google AI Studio API key: https://aistudio.google.com/apikey . It is **not** your ChatGPT Plus account, and availability, quotas or charges are subject to Google's current terms. Do not paste keys into chat or share them in screenshots. Set the key in the current PowerShell session without putting the literal key into command history:

```powershell
$env:GEMINI_API_KEY = Read-Host "Enter your Google AI Studio API key"
```

4. **Generate actual Gemma 4 patches** (3 tasks × 2 independent generations = 6 calls; may use billable tokens):

```powershell
python -m researchpilot.experiment generate --provider gemini --model gemma-4-26b-a4b-it --max-tasks 3
```

This generates `results/gemma_generations.json`, including actual model-generated source. **It does not execute any model-generated code.** Repeating the same command resumes or skips completed generation calls rather than charging again. If access to this model is not enabled for your key, the command will report the provider's error; do not claim results from it.

5. **Safely score the generated patches**. Start Docker Desktop, then pull the required Linux image and run:

```powershell
docker pull python:3.12-slim
python -m researchpilot.experiment score
python -m researchpilot.experiment report
```

Results: `results/gemma_scores.json` and `results/gemma_pilot_report.md`.

Docker is **mandatory** for scoring model-generated or external code. This project does **not** execute such code directly in your Windows Python interpreter. Docker containers use no network, no mounted host folders, a read-only root filesystem, dropped Linux capabilities, a low privilege user, and bounded resources. Containers are defense in depth, not a guarantee of security.

To run all 16 tasks instead of 3, generate into separate filenames:

```powershell
python -m researchpilot.experiment generate --provider gemini --model gemma-4-26b-a4b-it --max-tasks 16 --output results/gemma_generations_16.json
python -m researchpilot.experiment score --generations results/gemma_generations_16.json --output results/gemma_scores_16.json
python -m researchpilot.experiment report --input results/gemma_scores_16.json --output results/gemma_report_16.md
```

**Avoid changing an existing run's parameters midstream.** The generation tool checks config and input hashes and refuses accidental overwrites. To restart with a different model or task count, use a distinct `--output` path.

## Research design

The task gives the model only the issue, buggy source, and `public` tests. The model generates two patches per issue. Two policies choose among that **same ordered pool**:

- **Direct:** first candidate passing public tests.
- **Evidence gate:** first candidate passing both public tests and specification-derived `probes`.

The `hidden` tests are not used for prompt construction or selection. They are run only to evaluate the independently chosen final patch. The generated-candidate manifest saves source and token counts, and the scorer saves audit logs and paired accuracy/coverage/false-acceptance metrics. The methods share the same generation calls, but **the gate uses extra test executions**, so compute is not equal.

**Crucial limitations:** our 16 simple Python tasks and probes were curated by the same people who constructed the fixtures. The original 5/16 vs 16/16 result was achieved with hand-authored candidates by construction; it is an **engineering smoke test**, not measured LLM performance. Even real Gemma results here are only a preliminary synthetic function-level pilot, not evidence of real-world repository-scale generalization or state-of-the-art performance. More external tasks, diverse models/seeds and independent probe design would be needed for strong scientific claims.

## Offline demonstration (no model, no Docker)

```powershell
python -m unittest discover -s tests -v
python -m researchpilot.evaluate
```

This executes only **trusted hand-authored local fixture code**. Do not use the fixture `local` runner on model-generated, downloaded, or other untrusted code.

## OpenAI or local OpenAI-compatible fallback (optional)

With a separately provisioned OpenAI API key:

```powershell
$env:OPENAI_API_KEY = Read-Host "Enter OpenAI API key"
python -m researchpilot.experiment generate --provider openai --model YOUR_AVAILABLE_MODEL --max-tasks 3 --output results/openai_generations.json
```

For a local compatible server:

```powershell
python -m researchpilot.experiment generate --provider compatible --base-url http://localhost:8000/v1 --model YOUR_LOCAL_MODEL --max-tasks 3 --output results/local_generations.json
```

Model names and parameter support depend on your provider; Gemma 4 via Google AI Studio is the preferred first pilot. ChatGPT Plus does not grant API credits. No credentials belong in files, Git commits, screen captures, or chats.

## Files

- `researchpilot/experiment.py` — **new** real-model generation, guarded scoring, paired metrics, Markdown report.
- `researchpilot/runner.py`, `worker.py` — existing Docker-isolated tester.
- `researchpilot/evaluate.py` — existing handcrafted demonstration.
- `researchpilot/model_eval.py` — **legacy v0.1**, retained for compatibility; use `experiment.py` for new runs.
- `benchmarks/cases.json` — original 16 function-level bugs and test splits.
- `tests/` — 10 automated offline tests, including prompt leakage and resumability checks.
- `Research_Protocol.md` — pre-registered scientific hypothesis and limits.
- `Kaggle_Writeup_DRAFT.md` — draft, not ready for submission without actual model observations.

## Kaggle Paper Track

The current official deadline is **November 12, 2026 at 23:59 UTC** (November 13, 2026 at 01:59 in Lebanon). The writeup limit is 3,000 words. You need to **explicitly submit** the saved writeup before the deadline. Source: https://www.kaggle.com/competitions/gemma-4-developer-agent-paper . The Paper Track accepts original unpublished related research; the separate main prediction contest has stricter model selection requirements. Our tool is not an official main-track submission agent.

Original code maintained for demonstration; we make **no** claim of published model benchmark results until you perform the real evaluation.
