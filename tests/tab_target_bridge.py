import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from browser_targets import resolve_game_target
print(json.dumps({'ready':True}),flush=True)
for line in sys.stdin:
 try:
  command=json.loads(line)
  if command.get('stop'):break
  print(json.dumps({'id':resolve_game_target(sys.argv[1],['127.0.0.1'],preferred=command.get('preferred'))}),flush=True)
 except Exception as e:print(json.dumps({'error':str(e)}),flush=True)
