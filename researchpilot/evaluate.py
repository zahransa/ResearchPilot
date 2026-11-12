"""Offline fixture evaluation; no actual AI model is invoked."""
import argparse
import json
from collections import Counter
from pathlib import Path
from .runner import run_tests,choose
ROOT=Path(__file__).resolve().parents[1]


def evaluate(cases,engine='local'):
    result=[]
    for case in cases:
        # Fixtures must be valid and independent hidden tests cannot leak into selection.
        for name in ('direct','evidence_gate'):
            selected,audit=choose(case['candidates'],case['public'],case['probes'],engine,use_gate=(name=='evidence_gate'))
            hidden_result=run_tests(selected['code'],case['hidden'],engine) if selected else {'passed':False,'error':'no candidate accepted'}
            result.append({'id':case['id'],'method':name,'selected':selected['label'] if selected else None,
                           'accepted':selected is not None,'hidden_pass':hidden_result['passed'],
                           'hidden_error':hidden_result.get('error'),'audit':audit})
    summary={name:{'tasks':len(cases),'accepted':sum(i['accepted'] for i in result if i['method']==name),
                   'hidden_pass':sum(i['hidden_pass'] for i in result if i['method']==name)}
             for name in ('direct','evidence_gate')}
    return {'metadata':{'dataset':'hand-authored synthetic toy fixtures','model':'none','claim':'engineering smoke test; not an AI model evaluation','engine':engine},'summary':summary,'records':result}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--engine',choices=['local','docker'],default='local')
    parser.add_argument('--input',type=Path,default=ROOT/'benchmarks'/'cases.json')
    parser.add_argument('--output',type=Path,default=ROOT/'results'/'demo.json')
    args=parser.parse_args()
    report=evaluate(json.loads(args.input.read_text()),engine=args.engine)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2))
    print('Note: hand-authored synthetic candidates, NO model evaluated; not a scientific efficacy result.')
    print(f'Results saved to {args.output}')

if __name__=='__main__':main()
