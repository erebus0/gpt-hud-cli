from __future__ import annotations
import subprocess, shlex
from typing import Tuple

def run(cmd: str, cwd=None, timeout: int = 120) -> Tuple[int,str,str]:
    # Safe: no shell=True unless needed; split using shlex
    try:
        p = subprocess.Popen(shlex.split(cmd), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate(timeout=timeout)
        return p.returncode, out, err
    except Exception as e:
        return 1, "", str(e)
