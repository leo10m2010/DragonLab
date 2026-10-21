"""Temporary worker-thread sleep lease; never edits the Windows power plan."""
import os,ctypes

class SleepLease:
    def __init__(self,setter=None):self.setter=setter;self.active=False
    def hold(self,enabled):
        if enabled==self.active:return
        if self.setter is None:
            if os.name!='nt':return
            try:
                function=ctypes.WinDLL('kernel32',use_last_error=True).SetThreadExecutionState
                function.argtypes=[ctypes.c_ulong];function.restype=ctypes.c_ulong;self.setter=function
            except (OSError,AttributeError):return
        try:
            if self.setter(0x80000001 if enabled else 0x80000000):self.active=enabled
        except (OSError,ValueError,TypeError):pass
    def close(self):self.hold(False)
