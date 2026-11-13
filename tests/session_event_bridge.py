"""Local synthetic browser fixture bridge; never connects to a real game."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from adapters import AdapterClient
from cdp import CDP
from session_lifecycle import ROSTER_HELPERS_JS, SOURCE_IDENTITY_JS

client = AdapterClient(sys.argv[1], sys.argv[2], config={
    'id': 'local-session-fixture', 'mode': 'dragonbound', 'hosts': ['127.0.0.1']})
client.discovery_interval = 0
validator = CDP(sys.argv[1], sys.argv[2], hostname='127.0.0.1')
try:
    print(json.dumps({'ready': True}), flush=True)
    for line in sys.stdin:
        command = json.loads(line)
        if command.get('stop'):break
        try:
            sample = client.sample()
            if not validator.game:
                # Initial adoption by another observer must not alter the plan.
                peer=validator.sample()
                if peer.get('sourceEpoch')!=sample.get('sourceEpoch'):
                    raise AssertionError('Independent first sample changed the native epoch')
            # Independent CDP reader validates the shared native-object token.
            identity = validator.call('Runtime.evaluate', {
                'expression': '(()=>{' + ROSTER_HELPERS_JS + 'const g=window.fixtureGame,hid=heroId(g);return (' + SOURCE_IDENTITY_JS + ')(g,hid,heroObject(g,roster(g,["players","player_list"]),hid),false)})()',
                'returnByValue': True})['result'].get('value')
            print(json.dumps({'sample': sample, 'validation': identity}), flush=True)
        except Exception as error:
            print(json.dumps({'error': str(error)}), flush=True)
finally:
    validator.close(); client.close()
