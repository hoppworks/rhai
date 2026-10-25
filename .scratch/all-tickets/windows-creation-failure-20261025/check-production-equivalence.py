"""Compare normal no-define C# token streams to accepted base, preserving strings."""
from pathlib import Path
import subprocess,re,json,hashlib
p=Path(__file__).resolve().parent;repo=next(x for x in p.parents if (x/'tools/windows-scoped-runner').is_dir())
name='tools/windows-scoped-runner/MonitorPayloadJob.cs';base='57ee7c36442f37c915017c74f687cb627cbac628'
old=subprocess.check_output(['git','show',base+':'+name],cwd=repo,text=True);new=(repo/name).read_text()
def normal(text):
 stack=[];active=True;out=[]
 for line in text.splitlines():
  directive=line.strip()
  if directive.startswith('#if '):
   expr=directive[4:];expr=re.sub(r'\bSCOPED_RUNNER_[A-Z_]+\b','False',expr).replace('&&',' and ').replace('||',' or ').replace('!',' not ')
   cond=eval(expr,{'__builtins__':{}},{});stack.append((active,cond));active=active and cond
  elif directive=='#else':parent,cond=stack[-1];active=parent and not cond
  elif directive=='#endif':active=stack.pop()[0]
  elif directive.startswith('#error'):
   assert not active,directive
  elif active:out.append(line)
 assert not stack
 token=re.compile(r'@"(?:[^"]|"")*"|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|//[^\n]*|/\*.*?\*/|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]',re.S)
 return [t for t in token.findall('\n'.join(out)) if not t.startswith('//') and not t.startswith('/*')]
a,b=normal(old),normal(new);assert a==b,'Production no-define token stream differs'
r={'base':base,'path':name,'base_sha256':hashlib.sha256(old.encode()).hexdigest(),'candidate_sha256':hashlib.sha256(new.encode()).hexdigest(),'normal_build_tokens_equal':True,'token_count':len(a),'native_execution':False,'scope':'Default no-define body only; fault profiles are separately compiled and exercised on native Windows.'}
(p/'production-equivalence.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
