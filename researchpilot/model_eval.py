"""Real model experiment: matched candidate pool, independent evidence gate, Docker execution.

Requirements: pip install openai; Docker daemon; an API key or local compatible server.
Unlike the offline fixture demo, this generates candidates from an LLM. No claims are
made until the user runs it and reports actual results.
"""
import argparse
import json
import os
import re
import shutil
from pathlib import Path

from .runner import choose, run_tests
ROOT=Path(__file__).resolve().parents[1]

def request_candidate(client,model,case,variant):
    public=json.dumps(case['public'],indent=2)
    role=('Produce a minimal repair.' if variant==0 else
          'Produce a different correct implementation; prioritize general behavior and boundary cases.')
    instruction=(
      'You are an automated Python code-repair system. Return ONLY complete Python source code '
      'implementing a function named solve with the SAME input arguments. '
      'No markdown, no explanations, no file writes, no imports, no network or subprocess. '
      'Do not special-case test examples. Meet the natural-language contract. '
      'If unsure, make your best correction.\n'
    )
    prompt=(f'{role}\n\nIssue: {case["issue"]}\n\n'
            f'Current buggy file:\n{case["buggy_code"]}\n'
            f'Visible examples (inputs and expected outputs):\n{public}\n')
    resp=client.chat.completions.create(
        model=model,messages=[{'role':'system','content':instruction},{'role':'user','content':prompt}],
        max_tokens=1000,temperature=0.2)
    content=resp.choices[0].message.content or ''
    match=re.search(r'```(?:python)?\s*\n(.*?)```',content,flags=re.I|re.S)
    code=match.group(1).strip() if match else content.strip()
    # Reject extraneous prose and missing entry point without executing it.
    compile(code,'<llm patch>','exec')
    if not re.search(r'^def solve\s*\(',code,re.M):
        raise ValueError('model output does not define solve(...)')
    return code+'\n'


def run(model,base_url,input_file,output_file,max_tasks,api_key):
    if not shutil.which('docker'):
        raise RuntimeError('Docker must be installed before executing model-generated code. No unsafe local fallback.')
    from openai import OpenAI
    client=OpenAI(api_key=api_key or 'local-compatible-server',**({'base_url':base_url} if base_url else {}))
    cases=json.loads(input_file.read_text())[:max_tasks]
    report={'metadata':{
       'dataset':'hand-authored toy Python repair cases','model':model,'base_url':base_url or 'default',
       'methodology':'two candidate generations per task, same candidate pool for both selection strategies',
       'safety':'Docker no-network execution; no host mounts','limitations':'synthetic toy benchmark, manually curated probes'},'records':[]}
    for case in cases:
        candidates=[]
        failures=[]
        for n in range(2):
            try:
                source=request_candidate(client,model,case,n)
                candidates.append({'label':f'model_generation_{n+1}','code':source})
            except Exception as exc:
                failures.append(f'candidate {n+1}: {type(exc).__name__}: {str(exc)[:300]}')
        entry={'id':case['id'],'generation_errors':failures,'candidates':candidates,'comparisons':{}}
        for method,gate in [('direct',False),('evidence_gate',True)]:
            selected,audit=choose(candidates,case['public'],case['probes'],engine='docker',use_gate=gate)
            outcome=run_tests(selected['code'],case['hidden'],engine='docker') if selected else {'passed':False,'error':'no candidate accepted'}
            entry['comparisons'][method]={'selected':selected['label'] if selected else None,
                                           'accepted':selected is not None,
                                           'hidden_pass':outcome['passed'],'audit':audit}
        report['records'].append(entry)
        output_file.parent.mkdir(parents=True,exist_ok=True)
        output_file.write_text(json.dumps(report,indent=2)+'\n')  # checkpoint after each issue
        print(f'{len(report["records"])}/{len(cases)}: {case["id"]}')
    report['summary']={k:{'tasks':len(report['records']),
          'accepted':sum(r['comparisons'][k]['accepted'] for r in report['records']),
          'hidden_pass':sum(r['comparisons'][k]['hidden_pass'] for r in report['records'])}
          for k in ('direct','evidence_gate')}
    output_file.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2))


def main():
    parser=argparse.ArgumentParser(description='Actual LLM repair experiment (requires API + Docker).')
    parser.add_argument('--model',required=True,help='Name of model exposed by OpenAI-compatible chat API')
    parser.add_argument('--base-url',default=os.getenv('MODEL_BASE_URL'))
    parser.add_argument('--api-key',default=os.getenv('OPENAI_API_KEY'))
    parser.add_argument('--input',type=Path,default=ROOT/'benchmarks'/'cases.json')
    parser.add_argument('--output',type=Path,default=ROOT/'results'/'llm_experiment.json')
    parser.add_argument('--max-tasks',type=int,default=16)
    args=parser.parse_args()
    run(args.model,args.base_url,args.input,args.output,args.max_tasks,args.api_key)

if __name__=='__main__':main()
