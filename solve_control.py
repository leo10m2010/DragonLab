"""Cooperative cancellation for obsolete manual calculations only."""

class SolveCancelled(Exception):
    """The caller replaced this calculation; no result may be displayed/fired."""

def check_cancel(cancel):
    if cancel is not None and cancel.is_set():raise SolveCancelled()
