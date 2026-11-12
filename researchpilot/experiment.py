"""ResearchPilot v0.2: real model-generated candidate pairs, Docker-only execution.

Designed for Python >= 3.10. This is an experimental function-level code-repair
benchmark, NOT an agent capable of repairing whole repositories. Real-model
results can only be claimed after generation and Docker-based scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runner import choose, run_tests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "benchmarks" / "cases.json"
DEFAULT_GENERATIONS = ROOT / "results" / "gemma_generations.json"
DEFAULT_SCORES = ROOT / "results" / "gemma_scores.json"
IMAGE = "python:3.12-slim"

SYSTEM_PROMPT = (
    "You are a Python function-repair assistant. Return only full executable "
    "Python source implementing def solve(...) with the original argument signature. "
    "Do not use markdown, commentary, network, file system, or subprocess. "
    "Implement the stated behavior for general inputs, not only the examples."
)


def atomic_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".researchpilot-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(obj, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_prompt(case: dict[str, Any], variant: int) -> str:
    # IMPORTANT: neither the probes, hidden tests, nor pre-authored candidates
    # ever enter this prompt. Those fields are only used by the test harness.
    visible = json.dumps(case["public"], ensure_ascii=False, indent=2)
    variant_instruction = (
        "Write the smallest correct fix."
        if variant == 0
        else "Independently propose a complete, robust repair. Check edge cases mentally."
    )
    return (
        f"{variant_instruction}\n\nIssue specification:\n{case['issue']}\n\n"
        f"Buggy Python code:\n{case['buggy_code']}\n\n"
        f"Visible examples:\n{visible}\n\nReturn Python code only."
    )


def normalize_code(text: str) -> str:
    text = (text or "").strip()
    fenced = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    if not text or len(text) > 12000:
        raise ValueError("empty or excessively long patch")
    try:
        compile(text, "<generated patch>", "exec")  # parse, DO NOT execute
    except SyntaxError as exc:
        raise ValueError(f"invalid Python syntax: {exc}") from exc
    if not re.search(r"^\s*(?:async\s+)?def\s+solve\s*\(", text, re.M):
        raise ValueError("patch does not define solve(...)")
    return text + "\n"


class ModelClient:
    def __init__(self, provider: str, model: str, base_url: str | None = None,
                 temperature: float = 0.2, max_tokens: int = 2048):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        if provider == "gemini":
            if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
                raise RuntimeError("GEMINI_API_KEY not set. Get a key at https://aistudio.google.com/apikey")
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:
                raise RuntimeError("Install dependencies: python -m pip install -r requirements.txt") from exc
            self.types = types
            self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"])
        elif provider in ("openai", "compatible"):
            if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY not set")
            if provider == "compatible" and not base_url:
                raise RuntimeError("--base-url required for compatible server")
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("Install dependencies: python -m pip install -r requirements.txt") from exc
            self.client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY") or "local-model",
                **({"base_url": base_url} if base_url else {}),
                timeout=120.0,
                max_retries=1,
            )
        else:
            raise ValueError(f"unsupported provider: {provider}")

    def generate(self, prompt: str) -> tuple[str, dict[str, Any]]:
        if self.provider == "gemini":
            config = self.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            )
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
            usage = getattr(response, "usage_metadata", None)
            tokens = {
                "input": getattr(usage, "prompt_token_count", None),
                "output": getattr(usage, "candidates_token_count", None),
                "total": getattr(usage, "total_token_count", None),
            }
            return response.text or "", tokens
        request = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
        )
        # Some models/providers do not support a temperature argument. Retry
        # must be explicit rather than silently changing the experimental setup.
        if self.temperature is not None:
            request["temperature"] = self.temperature
        response = self.client.chat.completions.create(**request)
        usage = getattr(response, "usage", None)
        tokens = {
            "input": getattr(usage, "prompt_tokens", None),
            "output": getattr(usage, "completion_tokens", None),
            "total": getattr(usage, "total_tokens", None),
        }
        return response.choices[0].message.content or "", tokens


def manifest_config(args: argparse.Namespace, input_bytes: bytes) -> dict[str, Any]:
    return {
        "input_sha256": sha256(input_bytes),
        "provider": args.provider,
        "model": args.model,
        "base_url": args.base_url or None,
        "temperature": args.temperature,
        "max_output_tokens": args.max_tokens,
        "max_tasks": args.max_tasks,
        "num_candidates": args.num_candidates,
        "prompt_protocol": "repair-pair-v0.2",
    }


def generate(args: argparse.Namespace) -> dict[str, Any]:
    if args.max_tasks < 1 or not 1 <= args.num_candidates <= 5:
        raise ValueError("--max-tasks must be >=1; --num-candidates must be 1 to 5")
    input_bytes = args.input.read_bytes()
    tasks = json.loads(input_bytes)[:args.max_tasks]
    if not tasks:
        raise ValueError("no benchmark tasks in input")
    config = manifest_config(args, input_bytes)
    if args.output.exists() and not args.overwrite:
        report = json.loads(args.output.read_text(encoding="utf-8"))
        if report.get("config") != config:
            raise RuntimeError("Existing output uses a different configuration. Choose another --output or --overwrite.")
    else:
        report = {
            "artifact_kind": "model_generated_patches",
            "status": "in_progress",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "config": config,
            "records": [],
        }
        atomic_json(args.output, report)

    client = ModelClient(args.provider, args.model, args.base_url, args.temperature, args.max_tokens)
    records_by_id = {r["id"]: r for r in report["records"]}
    for index, task in enumerate(tasks, 1):
        item = records_by_id.get(task["id"])
        if item is None:
            item = {"id": task["id"], "candidates": []}
            report["records"].append(item)
            records_by_id[task["id"]] = item
        for variant in range(len(item["candidates"]), args.num_candidates):
            prompt = make_prompt(task, variant)
            # Query only public fields: issue, buggy_code and public tests.
            # Save every completed model call so interrupted runs can resume.
            try:
                response_text, tokens = client.generate(prompt)
            except Exception as exc:
                atomic_json(args.output, report)
                raise RuntimeError(
                    f"Model request failed at {task['id']}, generation {variant + 1}: "
                    f"{type(exc).__name__}: {str(exc)[:250]}. "
                    "Completed calls have been saved; rerun the same command to resume."
                ) from exc
            try:
                source = normalize_code(response_text)
                candidate = {
                    "label": f"generation_{variant + 1}",
                    "code": source,
                    "valid_python": True,
                    "tokens": tokens,
                    "prompt_sha256": sha256(prompt.encode()),
                }
            except ValueError as exc:
                # Invalid generated code is still a model result, never silently
                # replaced by a pre-authored candidate.
                candidate = {
                    "label": f"generation_{variant + 1}",
                    "code": "",
                    "valid_python": False,
                    "error": str(exc)[:500],
                    "tokens": tokens,
                    "prompt_sha256": sha256(prompt.encode()),
                }
            item["candidates"].append(candidate)
            atomic_json(args.output, report)
            print(f"[{index}/{len(tasks)}] {task['id']} candidate {variant+1}/{args.num_candidates} saved", flush=True)
    report["status"] = "complete"
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_json(args.output, report)
    print(f"Generation complete. Saved to {args.output}")
    return report


def check_docker() -> None:
    if not shutil.which("docker"):
        raise RuntimeError("Docker is not installed. Install Docker Desktop; no local execution fallback is offered.")
    try:
        subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                       capture_output=True, text=True, check=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("Docker is not running. Start Docker Desktop and try again.") from exc
    image = subprocess.run(["docker", "image", "inspect", IMAGE],
                           capture_output=True, text=True, check=False, timeout=15)
    if image.returncode:
        raise RuntimeError(f"Docker image missing. First run: docker pull {IMAGE}")


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in ("direct", "evidence_gate"):
        results = [x["comparisons"][name] for x in rows]
        passed = sum(bool(x["hidden_pass"]) for x in results)
        accepted = sum(bool(x["accepted"]) for x in results)
        false_accepted = accepted - passed
        out[name] = {
            "tasks": len(results),
            "accepted": accepted,
            "hidden_pass": passed,
            "false_accepted": false_accepted,
            "coverage": round(accepted / len(results), 4) if results else None,
            "heldout_success_rate": round(passed / len(results), 4) if results else None,
            "false_acceptance_among_accepted": round(false_accepted / accepted, 4) if accepted else None,
        }
    both = sum(r["comparisons"]["direct"]["hidden_pass"] and
               r["comparisons"]["evidence_gate"]["hidden_pass"] for r in rows)
    gate_only = sum(not r["comparisons"]["direct"]["hidden_pass"] and
                    r["comparisons"]["evidence_gate"]["hidden_pass"] for r in rows)
    direct_only = sum(r["comparisons"]["direct"]["hidden_pass"] and
                      not r["comparisons"]["evidence_gate"]["hidden_pass"] for r in rows)
    out["paired"] = {"both_pass": both, "gate_only_pass": gate_only,
                     "direct_only_pass": direct_only,
                     "neither_pass": len(rows) - both - gate_only - direct_only}
    return out


def score(args: argparse.Namespace) -> dict[str, Any]:
    check_docker()
    generation = json.loads(args.generations.read_text(encoding="utf-8"))
    if generation.get("artifact_kind") != "model_generated_patches":
        raise ValueError("not a model-generated patch manifest")
    if generation.get("status") != "complete":
        raise ValueError("generation not complete; finish generation before scoring")
    case_bytes = args.input.read_bytes()
    if generation["config"]["input_sha256"] != sha256(case_bytes):
        raise ValueError("benchmark file changed since generation: hashes do not match")
    cases_by_id = {c["id"]: c for c in json.loads(case_bytes)}
    if args.output.exists() and not args.overwrite:
        scores = json.loads(args.output.read_text(encoding="utf-8"))
        if scores.get("generation_sha256") != sha256(args.generations.read_bytes()):
            raise RuntimeError("Score file is from different generations. Use a new output path or --overwrite.")
    else:
        scores = {
            "artifact_kind": "real_model_evaluation",
            "status": "in_progress",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "model_config": generation["config"],
            "generation_sha256": sha256(args.generations.read_bytes()),
            "execution": {"engine": "docker", "image": IMAGE, "network": "none"},
            "limitations": "Synthetic function-level benchmark; pre-authored probes; not repository repair.",
            "records": [],
        }
        atomic_json(args.output, scores)
    done = {r["id"] for r in scores["records"]}
    for n, rec in enumerate(generation["records"], 1):
        if rec["id"] in done:
            continue
        case = cases_by_id[rec["id"]]
        pool = [dict(label=c["label"], code=c["code"]) for c in rec["candidates"] if c["valid_python"]]
        compare = {}
        for name, gate in (("direct", False), ("evidence_gate", True)):
            chosen, audit = choose(pool, case["public"], case["probes"], engine="docker", use_gate=gate)
            heldout = run_tests(chosen["code"], case["hidden"], engine="docker", timeout=12) if chosen else {"passed": False, "error": "abstained"}
            compare[name] = {
                "selected": chosen["label"] if chosen else None,
                "accepted": chosen is not None,
                "hidden_pass": bool(heldout["passed"]),
                "hidden_error": heldout.get("error"),
                "audit": audit,
            }
        scores["records"].append({"id": rec["id"], "comparisons": compare})
        scores["summary"] = summarize(scores["records"])
        atomic_json(args.output, scores)
        print(f"[{n}/{len(generation['records'])}] {rec['id']} scored", flush=True)
    scores["status"] = "complete"
    scores["finished_utc"] = datetime.now(timezone.utc).isoformat()
    scores["summary"] = summarize(scores["records"])
    atomic_json(args.output, scores)
    print(json.dumps(scores["summary"], indent=2))
    print(f"Saved results: {args.output}")
    return scores


def report(args: argparse.Namespace) -> None:
    scores = json.loads(args.input.read_text(encoding="utf-8"))
    if scores.get("artifact_kind") != "real_model_evaluation" or scores.get("status") != "complete":
        raise ValueError("Only a completed REAL model evaluation can be formatted as a report")
    s = scores["summary"]
    d, g, p = s["direct"], s["evidence_gate"], s["paired"]
    model = scores["model_config"]["model"]
    n = d["tasks"]
    lines = [
        "# Real-model pilot results (synthetic functions)", "",
        f"Model: `{model}` | Tasks evaluated: {n}",
        "", "| Metric | Direct | Evidence gate |", "|---|---:|---:|",
        f"| Held-out passes | {d['hidden_pass']}/{n} | {g['hidden_pass']}/{n} |",
        f"| Accepted candidates | {d['accepted']}/{n} | {g['accepted']}/{n} |",
        f"| Incorrect among accepted | {d['false_accepted']} | {g['false_accepted']} |",
        "", f"Paired: both={p['both_pass']}, gate-only={p['gate_only_pass']}, "
        f"direct-only={p['direct_only_pass']}, neither={p['neither_pass']}.",
        "", "## Interpretation caveats", "",
        "These are model-generated candidate patches, but tasks are 16 simple hand-authored "
        "Python functions, and probes were curated by benchmark authors. "
        "This pilot does not establish real-world generalization, or novelty relative "
        "to prior testing/patch-filtering research. Record model ID, temperature, "
        "candidate count, full logs and probe construction before any submission.", "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Paper-ready pilot table (with limitations) saved to {args.output}")


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="ResearchPilot v0.2 — model-generated patch experiment")
    commands = root.add_subparsers(dest="command", required=True)
    p = commands.add_parser("generate", help="Call a real model to generate patches. Never executes patches.")
    p.add_argument("--provider", choices=["gemini", "openai", "compatible"], default="gemini")
    p.add_argument("--model", default="gemma-4-26b-a4b-it")
    p.add_argument("--base-url", default=os.getenv("MODEL_BASE_URL"))
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--num-candidates", type=int, default=2)
    p.add_argument("--max-tasks", type=int, default=3)
    p.add_argument("--input", type=Path, default=DEFAULT_CASES)
    p.add_argument("--output", type=Path, default=DEFAULT_GENERATIONS)
    p.add_argument("--overwrite", action="store_true")
    p = commands.add_parser("score", help="Score real patches in network-disabled Docker only.")
    p.add_argument("--generations", type=Path, default=DEFAULT_GENERATIONS)
    p.add_argument("--input", type=Path, default=DEFAULT_CASES)
    p.add_argument("--output", type=Path, default=DEFAULT_SCORES)
    p.add_argument("--overwrite", action="store_true")
    p = commands.add_parser("report", help="Generate a marked, model-results-only Markdown summary.")
    p.add_argument("--input", type=Path, default=DEFAULT_SCORES)
    p.add_argument("--output", type=Path, default=ROOT / "results" / "gemma_pilot_report.md")
    return root


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "generate":
            generate(args)
        elif args.command == "score":
            score(args)
        elif args.command == "report":
            report(args)
    except (RuntimeError, ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
