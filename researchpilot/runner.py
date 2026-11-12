"""Harness: local mode is only for trusted fixtures; Docker for AI-generated code."""
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORKER=ROOT/'researchpilot'/'worker.py'


def run_tests(code, tests, engine='local', timeout=12.0):
    payload=json.dumps({'code':code,'tests':tests})
    if engine=='local':
        # FAST PATH FOR HAND-AUTHORED, TRUSTED FIXTURES ONLY.
        # Never use this mode for model-generated or externally supplied code.
        from .worker import evaluate
        return evaluate({'code':code, 'tests':tests})
    elif engine=='docker':
        # Do not mount the host into the container, and disable network access.
        worker_src=WORKER.read_text()
        command=['docker','run','--rm','--network','none','--read-only',
                 '--cap-drop','ALL','--security-opt','no-new-privileges',
                 '--pids-limit','64','--memory','256m','--cpus','1',
                 '--user','65534:65534','--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
                 '-i','python:3.12-slim','python','-I','-c',worker_src]
    else: raise ValueError('engine must be local or docker')
    try:
        completed=subprocess.run(command,input=payload,text=True,capture_output=True,timeout=timeout,check=False)
        if completed.returncode!=0:
            return {'passed':False,'error':f'process exited {completed.returncode}: {completed.stderr[:400]}','tests':[]}
        return json.loads(completed.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {'passed':False,'error':f'{type(exc).__name__}: {exc}','tests':[]}


def choose(candidates,public,probes,engine='local',use_gate=False):
    audit=[]
    for candidate in candidates:
        public_result=run_tests(candidate['code'],public,engine)
        item={'label':candidate['label'],'public_pass':public_result['passed'], 'public_error':public_result.get('error')}
        if not public_result['passed']:
            audit.append(item)
            continue
        if use_gate:
            probe_result=run_tests(candidate['code'],probes,engine)
            item.update({'probe_pass':probe_result['passed'],'probe_error':probe_result.get('error')})
            if not probe_result['passed']:
                audit.append(item)
                continue
        audit.append(item)
        return candidate,audit
    return None,audit
