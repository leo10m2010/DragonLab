"""Exercise the real CDP Drag helper against event-driven browser fixtures."""
import concurrent.futures
import json
from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cdp import CDP
from training_drag import charge_drag, prepare_drag


class FixtureReader:
    def __init__(self, client, requested):
        self.client = client
        self.requested = requested
        self.stale_reads = 0

    def read(self):
        result = self.client.call('Runtime.evaluate', {
            'expression': 'JSON.parse(JSON.stringify(window.fixture.state))',
            'returnByValue': True,
        })
        state = result['result']['value']
        if state.get('awaitingAck') and state.get('dragUpdates') == 0 and state['power'] == self.requested:
            self.stale_reads += 1
        return state


def run_target(endpoint, target, power, barrier):
    client = CDP(endpoint, target_id=target)
    cancel = threading.Event()
    presses = 0
    try:
        client.call('Emulation.setFocusEmulationEnabled', {'enabled': True})
        geometry = prepare_drag(client, power)
        if geometry is None:
            raise AssertionError('Fixture has no safe drag geometry')
        reader = FixtureReader(client, power)
        previous_sensitivity = reader.read()['dragSens']

        def guard(event):
            if event.is_set():
                raise RuntimeError('Fixture cancelled')

        def validate(state, allow_released=False):
            assert state['turn'] == state['hero'] == 0
            assert state['turnNumber'] == 1
            assert state['shot'] == 0 and state['mode'] == 'drag'
            assert not state['over'] and not state['moving']

        def on_press():
            nonlocal presses
            presses += 1
            # Both targets reserve before either begins its actual mouse press.
            barrier.wait(timeout=5)

        result = charge_drag(client, reader, geometry, power, cancel, guard, validate, on_press)
        assert presses == 1
        assert reader.stale_reads > 0, 'The stale previous force was never exercised'
        assert result['sensitivity'] != previous_sensitivity
        return {**result, 'target': target, 'requested': power, 'stale_reads': reader.stale_reads}
    finally:
        try:
            client.call('Emulation.setFocusEmulationEnabled', {'enabled': False})
        finally:
            client.close()


if __name__ == '__main__':
    endpoint, first, second = sys.argv[1:4]
    barrier = threading.Barrier(2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_target, endpoint, target, power, barrier)
                   for target, power in ((first, 150), (second, 280))]
        print(json.dumps({'results': [future.result(timeout=15) for future in futures]}))
