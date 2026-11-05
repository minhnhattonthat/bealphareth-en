"""ds_fmv.py CUE [--secs N] [--ds DIR]: play PROLO.STR in real-time DuckStation and exit 1 if the stream stalls.

Redux hides this class of bug (8x, loose CD/MDEC timing). Boots the disc in a portable copy (work/ds, from
H:/emulator/duckstation), presses the newgame route without its skip, and reads the libpress ring from process memory.
Takes keyboard focus. Prints one line per change of frame. Addresses: docs/re/graphics.md."""
import argparse
import ctypes
import ctypes.wintypes as w
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RING, HEAD = 0x800CB960, 0x800CB94C
LAST_FRAME = 2355
STALL_SECS = 15
KEYS = {"enter": 0x0D, "up": 0x26, "x": 0x58}
k32, u32 = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("user32")
k32.OpenProcess.restype = w.HANDLE


class MBI(ctypes.Structure):
    _fields_ = [("base", ctypes.c_uint64), ("alloc", ctypes.c_uint64), ("aprot", w.DWORD), ("_a", w.DWORD), ("size", ctypes.c_uint64),
                ("state", w.DWORD), ("prot", w.DWORD), ("type", w.DWORD), ("_b", w.DWORD)]


def read(h, addr, n):
    buf, got = ctypes.create_string_buffer(n), ctypes.c_size_t()
    ok = k32.ReadProcessMemory(h, ctypes.c_uint64(addr), buf, n, ctypes.byref(got))
    return buf.raw[:got.value] if ok else b""


def find_ram(h, needle):
    """Host address of PS1 RAM: the 2 MB-or-larger committed region holding MAIN.EXE's text at its load offset."""
    addr, mbi = 0, MBI()
    while k32.VirtualQueryEx(h, ctypes.c_uint64(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        if mbi.state == 0x1000 and mbi.size >= 0x200000 and read(h, mbi.base + 0x30000, len(needle)) == needle:
            return mbi.base
        addr = mbi.base + mbi.size
    return None


def press(hwnd, key):
    u32.SetForegroundWindow(hwnd)
    time.sleep(0.1)
    u32.keybd_event(KEYS[key], 0, 0, 0)
    time.sleep(0.15)
    u32.keybd_event(KEYS[key], 0, 2, 0)


def main_window(pid):
    found = []
    proc = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)

    def cb(hwnd, _):
        owner = w.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and u32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    u32.EnumWindows(proc(cb), 0)
    return found[0] if found else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cue")
    ap.add_argument("--ds", default=str(ROOT / "work/ds"))
    ap.add_argument("--secs", type=int, default=120, help="stop watching after this long with no stall")
    args = ap.parse_args()
    exe = Path(args.ds) / "duckstation-qt-x64-ReleaseLTCG.exe"
    needle = (ROOT / "work/disc/tree/MAIN.EXE").read_bytes()[0x800 + 0x20000:0x800 + 0x20040]
    proc = subprocess.Popen([str(exe), "-batch", "--", str(Path(args.cue).resolve())], cwd=args.ds)
    try:
        h = k32.OpenProcess(0x0410, False, proc.pid)
        time.sleep(8)
        hwnd, ram = main_window(proc.pid), None
        for _ in range(60):
            ram = find_ram(h, needle)
            if ram is not None:
                break
            time.sleep(1)
        if ram is None or not hwnd:
            print("no RAM or window found")
            return 2
        print(f"ram at {ram:#x}")
        # the newgame route's beats, with no skip of the prologue
        for wait, key in ((44, "enter"), (5, "enter"), (5, "up"), (1, "x")):
            time.sleep(wait)
            press(hwnd, key)
        u = lambda a: struct.unpack("<I", read(h, ram + (a & 0x1FFFFF), 4))[0]
        last, since, start = None, time.time(), time.time()
        while time.time() - start < args.secs:
            time.sleep(1)
            if proc.poll() is not None:
                print("emulator exited")
                return 2
            slot = u(RING) + u(HEAD) * 32
            status, _, part, count, frame = struct.unpack("<HHHHI", read(h, ram + (slot & 0x1FFFFF), 12))
            state = (frame, status, part)
            if state != last:
                print(f"{time.time() - start:6.1f}s frame {frame} status {status} part {part}/{count}", flush=True)
                last, since = state, time.time()
            elif time.time() - since > STALL_SECS and 0 < frame < LAST_FRAME:
                print(f"STALL at frame {frame} status {status}")
                return 1
        print("no stall")
        return 0
    finally:
        proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
