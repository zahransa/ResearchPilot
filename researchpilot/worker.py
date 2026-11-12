"""Execute a TRUSTED benchmark case from JSON stdin. Not a security sandbox."""
import json
import sys


def evaluate(payload):
    source=payload['code']
    namespace={'__builtins__':__builtins__}
    try:
        compiled=compile(source,'<candidate>','exec')
        exec(compiled,namespace)
        solve=namespace.get('solve')
        if not callable(solve): return {'passed':False, 'error':'missing solve function','tests':[]}
    except BaseException as err:
        return {'passed':False,'error':f'{type(err).__name__}: {err}','tests':[]}
    results=[]
    for test in payload['tests']:
        try:
            value=solve(*test['args'])
            passed=(type(value)==type(test['expected']) or (isinstance(value,(int,float)) and not isinstance(value,bool) and isinstance(test['expected'],(int,float)) and not isinstance(test['expected'],bool))) and value==test['expected']
            results.append({'passed':bool(passed),'expected':test['expected'],'actual':value if isinstance(value,(type(None),str,int,float,bool,list,dict)) else repr(value)})
        except BaseException as err:
            results.append({'passed':False,'expected':test['expected'],'error':f'{type(err).__name__}: {err}'})
    return {'passed':all(item['passed'] for item in results),'tests':results}

if __name__=='__main__':
    try:
        print(json.dumps(evaluate(json.load(sys.stdin)),allow_nan=False))
    except BaseException as err:
        print(json.dumps({'passed':False,'error':f'{type(err).__name__}: {err}','tests':[]}))
