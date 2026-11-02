#!/usr/bin/env python3
"""
dgx-monitor: honest unified-memory monitor for NVIDIA Grace Blackwell (GB10).
Reports per-process GPU compute memory, system memory (shared), GPU util/power/temp, CPU%.
Outputs a single JSON line.

Design notes:
- GB10 (DGX Spark) uses unified memory: CPU and GPU share 121GB of LPDDR5x.
- nvidia-smi --query-gpu=memory.used/memory.total returns [N/A] by design (no dedicated VRAM).
- Real GPU "memory in use" is the sum of per-process compute memory
  (nvidia-smi --query-compute-apps=used_memory), which is the closest analog to "VRAM used".
- System memory is read from /proc/meminfo (shared between CPU and GPU).
"""
import json
import os
import subprocess
import time
import re

def query_nvidia_csv(query: str) -> str:
    """Run nvidia-smi --query-gpu=... and return stdout, or '' on error."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            text=True, timeout=5, stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return ""

def query_compute_apps() -> list:
    """Return list of {pid, name, used_mb} from nvidia-smi compute apps."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5, stderr=subprocess.DEVNULL,
        )
        apps = []
        for line in out.strip().splitlines():
            parts = [c.strip() for c in line.split(",")]
            if len(parts) >= 3:
                try:
                    apps.append({
                        "pid": int(parts[0]),
                        "name": parts[1],
                        "used_mb": int(float(parts[2])),
                    })
                except ValueError:
                    continue
        return apps
    except Exception:
        return []

def read_meminfo() -> dict:
    """Return total/available/used MB from /proc/meminfo."""
    info = {"total_mb": None, "available_mb": None, "used_mb": None}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith(("MemTotal:", "MemAvailable:", "MemFree:", "Buffers:", "Cached:")):
                    key, val, _ = line.split()
                    mb = int(val) // 1024
                    if line.startswith("MemTotal:"):
                        info["total_mb"] = mb
                    elif line.startswith("MemAvailable:"):
                        info["available_mb"] = mb
        if info["total_mb"] is not None and info["available_mb"] is not None:
            info["used_mb"] = info["total_mb"] - info["available_mb"]
    except Exception:
        pass
    return info

def read_cpu_percent() -> float:
    """Read CPU% from /proc/stat with a 100ms sample."""
    def sample():
        with open("/proc/stat") as f:
            line = f.readline()
        parts = line.split()
        total = sum(int(p) for p in parts[1:])
        idle = int(parts[4])
        return total, idle
    try:
        t1, i1 = sample(); time.sleep(0.1); t2, i2 = sample()
        dtotal, didle = t2 - t1, i2 - i1
        return round(100.0 * (dtotal - didle) / dtotal, 1) if dtotal > 0 else 0.0
    except Exception:
        return None

def read_temp_c() -> float:
    """Pick the highest CPU/GPU thermal zone temperature (degC)."""
    temps = []
    base = "/sys/class/thermal"
    if not os.path.isdir(base):
        return None
    for entry in sorted(os.listdir(base)):
        if not entry.startswith("thermal_zone"):
            continue
        tp = os.path.join(base, entry, "temp")
        if os.path.isfile(tp):
            try:
                raw = int(open(tp).read().strip())
                temps.append(raw / 1000 if raw > 1000 else raw)
            except Exception:
                continue
    return max(temps) if temps else None

if __name__ == "__main__":
    gpu = {
        "name": None,
        "utilization_percent": None,
        "power_w": None,
        "temperature_c": None,
    }
    name = query_nvidia_csv("name")
    if name:
        gpu["name"] = name.splitlines()[0] if name else None
    util = query_nvidia_csv("utilization.gpu")
    if util:
        try: gpu["utilization_percent"] = int(float(util.splitlines()[0]))
        except: pass
    power = query_nvidia_csv("power.draw")
    if power:
        try: gpu["power_w"] = float(power.splitlines()[0])
        except: pass
    # Prefer GPU-specific thermal zone if nvidia-smi gives it
    gpu_temp = query_nvidia_csv("temperature.gpu")
    if gpu_temp:
        try: gpu["temperature_c"] = int(float(gpu_temp.splitlines()[0]))
        except: pass

    apps = query_compute_apps()
    gpu_compute_used_mb = sum(a["used_mb"] for a in apps)
    if gpu["temperature_c"] is None:
        gpu["temperature_c"] = read_temp_c()

    result = {
        "timestamp": int(time.time()),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "gpu": gpu,
        "gpu_compute_used_mb": gpu_compute_used_mb,
        "gpu_compute_processes": apps,
        "system_memory_mb": read_meminfo(),
        "cpu_percent": read_cpu_percent(),
        "note": "GB10 unified memory: GPU shares system RAM; 'gpu_compute_used_mb' is the sum of per-process GPU allocations (closest analog to VRAM used on a discrete-GPU system).",
    }
    print(json.dumps(result, indent=None))
