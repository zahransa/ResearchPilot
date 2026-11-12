"""Build a small hand-designed demonstration dataset. NOT a scientific AI evaluation."""
import json
from pathlib import Path

cases=[]
def add(name, issue, buggy, shortcut, correct, public, probes, hidden, good_first=False):
    candidates=[{"label":"shortcut", "code":shortcut},{"label":"general", "code":correct}]
    if good_first: candidates.reverse()
    cases.append({"id": name,"issue":issue,"buggy_code":buggy,"candidates":candidates,
                  "public":public,"probes":probes,"hidden":hidden,
                  "design_note":"All fixes are hand-authored; shortcut is intentionally overfit."})
def t(args,expected): return {"args":args,"expected":expected}

add('absolute_difference','Return the nonnegative absolute difference between two numbers.',
'def solve(a,b):\n    return a-b\n',
'def solve(a,b):\n    return 3 if (a,b)==(2,5) else a-b\n',
'def solve(a,b):\n    return abs(a-b)\n',
[t([2,5],3),t([5,2],3)],[t([0,-2],2),t([-6,3],9)],[t([3,7],4),t([10,1],9)])
add('clamp','Constrain x to the inclusive numeric interval [lo,hi].',
'def solve(x,lo,hi):\n    return max(x,hi)\n',
'def solve(x,lo,hi):\n    return 0 if (x,lo,hi)==(-2,0,10) else max(x,hi)\n',
'def solve(x,lo,hi):\n    return min(max(x,lo),hi)\n',
[t([-2,0,10],0)],[t([20,0,10],10),t([3,0,10],3)],[t([5,0,10],5),t([11,0,10],10)],True)
add('sum_positives','Sum only strictly positive values in a numeric list.',
'def solve(values):\n    return sum(values)\n',
'def solve(values):\n    return 4 if values==[-3,4] else sum(values)\n',
'def solve(values):\n    return sum(v for v in values if v>0)\n',
[t([[-3,4]],4)],[t([[-5,2,3]],5),t([[-3,-2]],0)],[t([[-1,10]],10),t([[1,2,-5,5]],8)])
add('even_median','Return the median, averaging two center elements for an even-length list.',
'def solve(values):\n    a=sorted(values)\n    return a[len(a)//2]\n',
'def solve(values):\n    a=sorted(values)\n    return 5 if a==[2,8] else a[len(a)//2]\n',
'def solve(values):\n    a=sorted(values)\n    n=len(a)\n    return a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2\n',
[t([[2,8]],5),t([[2,8,10]],8)],[t([[1,7,9,11]],8),t([[3,4]],3.5)],[t([[0,2,4,10]],3),t([[5,10,15,20,25]],15)])
add('preserve_unique','Remove duplicates while preserving the first occurrence order.',
'def solve(values):\n    return sorted(set(values))\n',
'def solve(values):\n    return [3,1] if values==[3,1,3] else sorted(set(values))\n',
'def solve(values):\n    return list(dict.fromkeys(values))\n',
[t([[3,1,3]],[3,1])],[t([[5,2,5,4]],[5,2,4])],[t([[7,3,7,1]],[7,3,1])],True)
add('vowel_count','Count vowels a,e,i,o,u case-insensitively in a string.',
'def solve(text):\n    return sum(c in "aeiou" for c in text)\n',
'def solve(text):\n    return 2 if text=="APPLE" else sum(c in "aeiou" for c in text)\n',
'def solve(text):\n    return sum(c in "aeiou" for c in text.lower())\n',
[t(['APPLE'],2)],[t(['EDUCATION'],5),t(['AEIOU'],5)],[t(['I love AI'],5),t(['OUtput'],3)])
add('normalize_spaces','Trim and collapse all runs of whitespace to a single space.',
'def solve(text):\n    return text.strip()\n',
'def solve(text):\n    return "a b" if text=="a  b" else text.strip()\n',
'def solve(text):\n    return " ".join(text.split())\n',
[t(['a  b'],'a b')],[t([' a\tb\n c '],'a b c')],[t(['x   y  z'],'x y z')])
add('safe_division','Return None for a zero denominator, otherwise a/b.',
'def solve(a,b):\n    return a/b\n',
'def solve(a,b):\n    return None if (a,b)==(4,0) else a/b\n',
'def solve(a,b):\n    return None if b==0 else a/b\n',
[t([4,0],None),t([4,2],2)],[t([0,0],None),t([7,0],None)],[t([-2,0],None),t([9,3],3)],True)
add('rotate_right','Rotate list elements k positions to the right (k may exceed length).',
'def solve(values,k):\n    return values[-1:]+values[:-1]\n',
'def solve(values,k):\n    return [2,3,1] if (values,k)==([1,2,3],2) else values[-1:]+values[:-1]\n',
'def solve(values,k):\n    if not values: return []\n    k=k%len(values)\n    return values[-k:]+values[:-k] if k else values[:]\n',
[t([[1,2,3],2],[2,3,1])],[t([[1,2,3,4],3],[2,3,4,1]),t([[],7],[])],[t([[1,2,3,4,5],2],[4,5,1,2,3]),t([[1,2,3],0],[1,2,3])])
add('running_totals','Return cumulative sums of an input list.',
'def solve(values):\n    return [sum(values)]*len(values)\n',
'def solve(values):\n    return [1,3,6] if values==[1,2,3] else [sum(values)]*len(values)\n',
'def solve(values):\n    out=[]\n    total=0\n    for value in values:\n        total+=value\n        out.append(total)\n    return out\n',
[t([[1,2,3]],[1,3,6])],[t([[-1,2,4]],[-1,1,5])],[t([[2,0,5]],[2,2,7]),t([[]],[])],True)
add('parse_boolean','Parse yes/no, 1/0 and true/false case-insensitively; whitespace ignored.',
'def solve(text):\n    return bool(text)\n',
'def solve(text):\n    return False if text=="false" else bool(text)\n',
'def solve(text):\n    v=text.strip().lower()\n    if v in ("true","yes","1"): return True\n    if v in ("false","no","0"): return False\n    raise ValueError("not a boolean")\n',
[t(['false'],False),t(['true'],True)],[t([' 0 '],False),t(['NO'],False)],[t(['No'],False),t([' yes '],True)])
add('factorial','Return factorial(n) for nonnegative integer n.',
'def solve(n):\n    return n\n',
'def solve(n):\n    return 1 if n==0 else n\n',
'def solve(n):\n    out=1\n    for k in range(2,n+1): out*=k\n    return out\n',
[t([0],1)],[t([4],24),t([3],6)],[t([5],120),t([2],2)])
add('is_prime','Return True exactly when n is a prime integer (n>=2).',
'def solve(n):\n    return n>1 and n%2==1\n',
'def solve(n):\n    return False if n==9 else (n>1 and n%2==1)\n',
'def solve(n):\n    if n<2:return False\n    for d in range(2,int(n**0.5)+1):\n        if n%d==0:return False\n    return True\n',
[t([9],False),t([3],True)],[t([25],False),t([2],True)],[t([49],False),t([11],True)])
add('flatten_once','Concatenate one level of nested lists into a single list.',
'def solve(chunks):\n    return chunks\n',
'def solve(chunks):\n    return [1,2,3] if chunks==[[1,2],[3]] else chunks\n',
'def solve(chunks):\n    return [value for chunk in chunks for value in chunk]\n',
[t([[[1,2],[3]]],[1,2,3])],[t([[[4],[5,6]]],[4,5,6])],[t([[[1],[],[2,3]]],[1,2,3])],True)
add('longest_word','Return the longest whitespace-separated word; first on ties.',
'def solve(text):\n    return text.split()[0] if text.split() else ""\n',
'def solve(text):\n    return "quick" if text=="a quick fox" else (text.split()[0] if text.split() else "")\n',
'def solve(text):\n    return max(text.split(),key=len,default="")\n',
[t(['a quick fox'],'quick')],[t(['tiny enormous a'],'enormous')],[t(['go programming now'],'programming'),t([''],'')])
add('sorted_unique','Return sorted values with duplicates removed.',
'def solve(values):\n    return list(dict.fromkeys(values))\n',
'def solve(values):\n    return [1,3] if values==[3,1,3] else list(dict.fromkeys(values))\n',
'def solve(values):\n    return sorted(set(values))\n',
[t([[3,1,3]],[1,3])],[t([[10,-1,10,3]],[-1,3,10])],[t([[2,0,2,-4]],[-4,0,2])])

out=Path(__file__).parent/'benchmarks'/'cases.json'
out.write_text(json.dumps(cases,indent=2,ensure_ascii=False)+'\n')
print(f'Generated {len(cases)} hand-authored cases -> {out}')
