"""Cooperative cancellation for obsolete manual calculations only."""
import threading

class CancellationToken:
    """Event with synchronized native cancellation subscriptions; no polling thread."""
    def __init__(self):self.event=threading.Event();self.lock=threading.Lock();self.callbacks=set()
    def is_set(self):return self.event.is_set()
    def wait(self,timeout=None):return self.event.wait(timeout)
    def set(self):
        with self.lock:
            self.event.set()
            for callback in tuple(self.callbacks):callback()
    def subscribe(self,callback):
        with self.lock:
            if self.event.is_set():callback()
            self.callbacks.add(callback)
        def unregister():
            with self.lock:self.callbacks.discard(callback)
        return unregister

class SolveCancelled(Exception):
    """The caller replaced this calculation; no result may be displayed/fired."""

def check_cancel(cancel):
    if cancel is not None and cancel.is_set():raise SolveCancelled()
