"""Correctly typed Windows memory probe; separate from frozen timing workers."""
import ctypes,json

def memory():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
    api=ctypes.WinDLL('psapi',use_last_error=True);api.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong];api.GetProcessMemoryInfo.restype=ctypes.c_int
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    ok=api.GetProcessMemoryInfo(ctypes.c_void_p(-1),ctypes.byref(counters),counters.cb)
    if not ok:raise ctypes.WinError(ctypes.get_last_error())
    return dict(peak_working_set_bytes=int(counters.PeakWorkingSetSize),working_set_bytes=int(counters.WorkingSetSize),peak_pagefile_bytes=int(counters.PeakPagefileUsage))
if __name__=='__main__':print(json.dumps(memory()))
