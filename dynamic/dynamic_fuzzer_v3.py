"""
15 selected features (most discriminative for vulnerability classification):
  crash_rate              — primary crash density signal
  asan_rate               — ASAN hit density (heap/stack/uaf/etc per run)
  ubsan_rate              — UBSAN hit density (int overflow/null/shift/etc per run)
  exit_nonzero_rate       — OS-level hard crash rate (process actually died)
  crash_generic_rate      — segfault/abort/exception rate (non-sanitizer crashes)
  timeout_rate            — hangs per run (infinite loops, deep recursion bugs)
  avg_exec_time           — mean execution time (timing side-channel)
  time_variance           — execution time spread (path instability under different inputs)
  path_variability_rate   — distinct (stderr+exitcode) signatures per run
  input_sensitivity_rate  — how often output changes between consecutive runs
  crash_transition_rate   — crash↔no-crash flip rate (input-sensitive vulnerability)
  error_type_diversity    — count of distinct error keyword categories seen
  rare_behavior_ratio     — fraction of outputs seen only once (unique/unusual behavior)
  crash_inducing_categories — how many of 9 input types triggered at least one crash
  has_stderr              — binary: any sanitizer/runtime output appeared at all
"""

import subprocess
import multiprocessing
multiprocessing.freeze_support()

import re
import os
import sys
import json
import time
import random
import string
import hashlib
import numpy as np
from math import log2
from collections import defaultdict
from multiprocessing import Pool, cpu_count

EXEC_DIR        = "batch1"
RUNS_PER_EXE    = 50
TIMEOUT         = 0.3
NUM_WORKERS     = 8
OUTPUT_FILE     = "batch1_final.json"
BATCH_SIZE      = 200
FAST_FAIL_PROBE = 10
FAST_FAIL_MIN   = 20

# ASAN / UBSAN / CRASH PATTERNS
_RE_FLAGS = re.IGNORECASE | re.MULTILINE

ASAN_PATTERNS = {
    "heap_overflow":   re.compile(r"heap.buffer.overflow",          _RE_FLAGS),
    "stack_overflow":  re.compile(r"stack.buffer.overflow",         _RE_FLAGS),
    "use_after_free":  re.compile(r"use.after.free",                _RE_FLAGS),
    "double_free":     re.compile(r"double.free",                   _RE_FLAGS),
    "invalid_access":  re.compile(r"invalid (read|write) of size",  _RE_FLAGS),
    "global_overflow": re.compile(r"global.buffer.overflow",        _RE_FLAGS),
    "stack_use_ret":   re.compile(r"stack.use.after.return",        _RE_FLAGS),
    "alloc_dealloc":   re.compile(r"alloc-dealloc-mismatch",        _RE_FLAGS),
    "memcpy_overlap":  re.compile(r"memcpy.param.overlap",          _RE_FLAGS),
    "msvc_asan":       re.compile(r"AddressSanitizer",              _RE_FLAGS),
}

UBSAN_PATTERNS = {
    "int_overflow":    re.compile(r"(signed|unsigned) integer overflow",  _RE_FLAGS),
    "divide_by_zero":  re.compile(r"division by zero",                    _RE_FLAGS),
    "null_deref":      re.compile(r"null pointer dereference",            _RE_FLAGS),
    "invalid_shift":   re.compile(r"shift (exponent|amount)",             _RE_FLAGS),
    "out_of_bounds":   re.compile(r"index \S+ out of bounds",             _RE_FLAGS),
    "invalid_bool":    re.compile(r"not a valid value for type 'bool'",   _RE_FLAGS),
    "ptr_overflow":    re.compile(r"pointer (index expression|overflow)", _RE_FLAGS),
    "float_cast":      re.compile(r"value \S+ is outside the range",      _RE_FLAGS),
    "invalid_enum":    re.compile(r"not a valid value for type",          _RE_FLAGS),
    "msvc_rtc":        re.compile(r"Run-Time Check Failure",              _RE_FLAGS),
    "msvc_ubsan":      re.compile(r"UndefinedBehaviorSanitizer",          _RE_FLAGS),
    "sanitizer_fatal": re.compile(r"SUMMARY: \w+Sanitizer",               _RE_FLAGS),
}

CRASH_PATTERNS = {
    "segfault":        re.compile(r"segmentation fault|access violation",  _RE_FLAGS),
    "abort":           re.compile(r"\bAborted\b|SIGABRT",                  _RE_FLAGS),
    "runtime_error":   re.compile(r"runtime error",                        _RE_FLAGS),
    "fatal_error":     re.compile(r"fatal error|FATAL",                    _RE_FLAGS),
    "exception":       re.compile(r"unhandled exception|terminate called", _RE_FLAGS),
}

# INPUT GENERATOR
INPUT_CATEGORIES = [
    "overflow", "null_byte", "numeric", "divzero",
    "format_str", "structured", "random", "mutated", "combined",
]

_OVERFLOW_INPUTS = [
    "A" * 100, "A" * 1000, "A" * 5000,
    "A" * 10_000, "B" * 20_000, "C" * 50_000,
]
_NULL_INPUTS = [
    "", "\x00", "\x00\x00\x00", "\xff\xff\xff",
    "\x00" * 100, "\xff" * 1000,
]
_NUMERIC_INPUTS = [
    str(2**31 - 1), str(-(2**31)), str(2**63 - 1), str(-(2**63)),
    "999999999999999999999", "-999999999999999999999", "0", "-1",
    "2147483648", "-2147483649",
]
_DIVZERO_INPUTS = ["0", "00", "0/0", "100/0", "1 0", "0\n0"]
_FORMAT_INPUTS  = ["%x%x%x%x%x", "%s%s%s%s", "%n%n%n", "%p%p%p%p", "%.9999d"]
_STRUCTURED_INPUTS = [
    '{"key":"value"}', '{"a":123}', '{"a":-999999999}',
    '{"nested":{"x":1}}', "<xml><a>1</a></xml>",
    "<a>" + "A" * 1000 + "</a>",
    "GET / HTTP/1.1\r\nHost: test\r\n\r\n",
    "admin' OR '1'='1",
    "../../../etc/passwd",
]


def _random_input() -> str:
    return "".join(random.choices(string.printable, k=random.randint(1, 500)))


def _mutate(s: str) -> str:
    chars = list(s) if s else ["A"]
    for _ in range(random.randint(1, min(5, len(chars)))):
        chars[random.randint(0, len(chars) - 1)] = random.choice(string.printable)
    return "".join(chars)


def _combine() -> str:
    base = random.choice(_OVERFLOW_INPUTS + _STRUCTURED_INPUTS + _NUMERIC_INPUTS)
    return base + random.choice(["", "\x00", "%x", "A" * 100])


def generate_input(run_id: int):
    t = run_id % 9
    if   t == 0: return random.choice(_OVERFLOW_INPUTS),   "overflow"
    elif t == 1: return random.choice(_NULL_INPUTS),        "null_byte"
    elif t == 2: return random.choice(_NUMERIC_INPUTS),     "numeric"
    elif t == 3: return random.choice(_DIVZERO_INPUTS),     "divzero"
    elif t == 4: return random.choice(_FORMAT_INPUTS),      "format_str"
    elif t == 5: return random.choice(_STRUCTURED_INPUTS),  "structured"
    elif t == 6: return _random_input(),                    "random"
    elif t == 7: return _mutate(random.choice(_OVERFLOW_INPUTS + _STRUCTURED_INPUTS)), "mutated"
    else:        return _combine(),                         "combined"


# HELPERS
_ADDR_RE = re.compile(r'0x[0-9a-fA-F]+')
_NUM_RE  = re.compile(r'\b\d+\b')


def normalize_stderr(raw: str) -> str:
    s = raw.strip().lower()
    s = _ADDR_RE.sub("ADDR", s)
    s = _NUM_RE.sub("NUM", s)
    return s[:300]


def shannon_entropy(values: list) -> float:
    if len(values) < 2:
        return 0.0
    mn, mx = min(values), max(values)
    if mx == mn:
        return 0.0
    buckets = [0] * 10
    span = mx - mn
    for v in values:
        b = min(int((v - mn) / span * 10), 9)
        buckets[b] += 1
    n = len(values)
    return round(-sum((c / n) * log2(c / n) for c in buckets if c > 0), 6)


# SINGLE-EXE FUZZER
def fuzz_one_exe(exe_path: str, exe_type: str, runs: int = RUNS_PER_EXE) -> dict | None:
    r = dict(
        asan_hits        = defaultdict(int),
        ubsan_hits       = defaultdict(int),
        crash_hits       = defaultdict(int),
        total_runs       = 0,
        crash_count      = 0,
        exit_nonzero     = 0,
        asan_match_count = 0,
        ubsan_match_count= 0,
        crash_generic    = 0,
        timeouts         = 0,
        total_time       = 0.0,
        times            = [],
        exit_codes       = set(),
        cat_crashes      = defaultdict(int),
        cat_runs         = defaultdict(int),
        raw_stderr_map   = {},
        raw_stderr_set   = set(),
        path_sigs        = set(),
        max_stderr_len   = 0,
        last_norm        = None,
        input_effect     = 0,
        last_crashed     = None,
        crash_transitions= 0,
        error_keywords   = set(),
    )

    ERROR_KW = ["overflow", "invalid", "error", "null", "divide", "shift",
                "free", "oob", "bound", "dereference", "exception", "fatal",
                "abort", "segfault", "access"]

    actual_runs = runs
    probe_done  = False

    run_id = 0
    while run_id < actual_runs:
        fuzz_input, category = generate_input(run_id)
        r["cat_runs"][category] += 1

        start = time.perf_counter()
        try:
            proc = subprocess.Popen(
                [exe_path],
                stdin =subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text  =True,
            )
            _, raw_stderr = proc.communicate(input=fuzz_input, timeout=TIMEOUT)
            exec_time = time.perf_counter() - start

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            exec_time = TIMEOUT
            r["timeouts"]    += 1
            r["total_runs"]  += 1
            r["crash_count"] += 1
            r["cat_crashes"][category] += 1
            r["exit_nonzero"] += 1
            r["exit_codes"].add(-1)
            run_id += 1
            continue

        except OSError as e:
            if "WinError 225" in str(e):
                return None
            return None

        except Exception:
            run_id += 1
            continue

        r["total_runs"]  += 1
        r["total_time"]  += exec_time
        r["times"].append(exec_time)
        r["exit_codes"].add(proc.returncode)

        exit_nonzero = (proc.returncode != 0)
        if exit_nonzero:
            r["exit_nonzero"] += 1

        asan_matched  = False
        ubsan_matched = False
        crash_matched = False

        for name, pat in ASAN_PATTERNS.items():
            if pat.search(raw_stderr):
                r["asan_hits"][name] += 1
                asan_matched = True

        for name, pat in UBSAN_PATTERNS.items():
            if pat.search(raw_stderr):
                r["ubsan_hits"][name] += 1
                ubsan_matched = True

        for name, pat in CRASH_PATTERNS.items():
            if pat.search(raw_stderr):
                r["crash_hits"][name] += 1
                crash_matched = True

        if asan_matched:  r["asan_match_count"]  += 1
        if ubsan_matched: r["ubsan_match_count"] += 1
        if crash_matched: r["crash_generic"]     += 1

        crashed = exit_nonzero or asan_matched or crash_matched

        if crashed:
            r["crash_count"] += 1
            r["cat_crashes"][category] += 1

        if r["last_crashed"] is not None and crashed != r["last_crashed"]:
            r["crash_transitions"] += 1
        r["last_crashed"] = crashed

        raw_stripped = raw_stderr.strip()
        raw_len      = len(raw_stripped)
        r["max_stderr_len"] = max(r["max_stderr_len"], raw_len)

        norm = normalize_stderr(raw_stderr)
        r["raw_stderr_map"][norm] = r["raw_stderr_map"].get(norm, 0) + 1

        raw_sample = raw_stripped[:300]
        r["raw_stderr_set"].add(raw_sample)

        sig = hashlib.md5(f"{norm}|{proc.returncode}".encode()).hexdigest()
        r["path_sigs"].add(sig)

        if r["last_norm"] is not None and r["last_norm"] != norm:
            r["input_effect"] += 1
        r["last_norm"] = norm

        raw_lower = raw_stderr.lower()
        for kw in ERROR_KW:
            if kw in raw_lower:
                r["error_keywords"].add(kw)

        if not probe_done and r["total_runs"] >= FAST_FAIL_PROBE:
            probe_done = True
            if (r["crash_count"] == 0
                    and r["asan_match_count"] == 0
                    and r["ubsan_match_count"] == 0
                    and r["max_stderr_len"] == 0
                    and len(r["exit_codes"]) == 1):
                actual_runs = min(actual_runs, FAST_FAIL_MIN)

        run_id += 1

    total = r["total_runs"]
    if total == 0:
        return None

    times = r["times"]

    asan_total  = sum(r["asan_hits"].values())
    ubsan_total = sum(r["ubsan_hits"].values())

    rare_raw       = sum(1 for v in r["raw_stderr_map"].values() if v == 1)
    total_distinct = max(len(r["raw_stderr_map"]), 1)

    crash_inducing_cats = sum(1 for c in INPUT_CATEGORIES if r["cat_crashes"].get(c, 0) > 0)

    feat = {
        "exe_type":               exe_type,
        "total_runs":             total,

        "crash_count":            r["crash_count"],
        "crash_rate":             round(r["crash_count"] / total, 4),
        "exit_nonzero_count":     r["exit_nonzero"],
        "exit_nonzero_rate":      round(r["exit_nonzero"] / total, 4),

        "asan_total":             asan_total,
        "asan_rate":              round(asan_total / total, 4),
        "asan_run_count":         r["asan_match_count"],
        "asan_run_rate":          round(r["asan_match_count"] / total, 4),
        **{f"asan_{k}": r["asan_hits"].get(k, 0) for k in ASAN_PATTERNS},

        "ubsan_total":            ubsan_total,
        "ubsan_rate":             round(ubsan_total / total, 4),
        "ubsan_run_count":        r["ubsan_match_count"],
        "ubsan_run_rate":         round(r["ubsan_match_count"] / total, 4),
        **{f"ubsan_{k}": r["ubsan_hits"].get(k, 0) for k in UBSAN_PATTERNS},

        "crash_generic_count":    r["crash_generic"],
        "crash_generic_rate":     round(r["crash_generic"] / total, 4),
        **{f"crash_{k}": r["crash_hits"].get(k, 0) for k in CRASH_PATTERNS},

        "timeout_count":          r["timeouts"],
        "timeout_rate":           round(r["timeouts"] / total, 4),

        "avg_exec_time":          round(r["total_time"] / total, 6),
        "time_variance":          round(float(np.var(times)), 8) if times else 0.0,
        "time_entropy":           shannon_entropy(times),
        "max_exec_time":          round(max(times), 6)           if times else 0.0,
        "p90_exec_time":          round(float(np.percentile(times, 90)), 6) if times else 0.0,

        "unique_exit_codes":      len(r["exit_codes"]),
        "path_variability":       len(r["path_sigs"]),
        "path_variability_rate":  round(len(r["path_sigs"]) / total, 4),
        "unique_outputs":         len(r["raw_stderr_map"]),
        "unique_raw_samples":     len(r["raw_stderr_set"]),

        "max_stderr_len":         r["max_stderr_len"],
        "has_stderr":             int(r["max_stderr_len"] > 0),

        "input_sensitivity":      r["input_effect"],
        "input_sensitivity_rate": round(r["input_effect"] / total, 4),
        "crash_transition_rate":  round(r["crash_transitions"] / total, 4),

        "error_type_diversity":   len(r["error_keywords"]),
        "rare_behavior_ratio":    round(rare_raw / total_distinct, 4),

        "crash_inducing_categories": crash_inducing_cats,
        **{
            f"crash_cat_{c}": round(r["cat_crashes"].get(c, 0) /
                                    max(r["cat_runs"].get(c, 1), 1), 4)
            for c in INPUT_CATEGORIES
        },
    }
    return feat


# MERGE 
def merge_exe_results(idx: int, results: dict) -> dict:
    total_runs = sum(r["total_runs"] for r in results.values())

    def sum_field(key):
        return sum(r.get(key, 0) for r in results.values())

    def max_field(key):
        return max(r.get(key, 0) for r in results.values())

    def wavg_field(key):
        total = sum(r["total_runs"] for r in results.values())
        return round(sum(r.get(key, 0) * r["total_runs"] for r in results.values()) / max(total, 1), 6)

    merged_crashes      = sum_field("crash_count")
    merged_exit_nonzero = sum_field("exit_nonzero_count")
    merged_asan_total   = sum_field("asan_total")
    merged_asan_runs    = sum_field("asan_run_count")
    merged_ubsan_total  = sum_field("ubsan_total")
    merged_ubsan_runs   = sum_field("ubsan_run_count")
    merged_timeouts     = sum_field("timeout_count")
    merged_generic      = sum_field("crash_generic_count")
    merged_input_eff    = sum_field("input_sensitivity")
    merged_error_div    = max_field("error_type_diversity")
    merged_cat_inducing = max_field("crash_inducing_categories")

    merged_paths    = sum_field("path_variability")

    avg_time  = wavg_field("avg_exec_time")
    time_var  = wavg_field("time_variance")
    max_stderr = max_field("max_stderr_len")

    rare_ratio = round(
        sum(r.get("rare_behavior_ratio", 0) for r in results.values()) / max(len(results), 1), 4
    )
    ctr = round(
        sum(r.get("crash_transition_rate", 0) for r in results.values()) / max(len(results), 1), 4
    )
    isr = round(merged_input_eff / max(total_runs, 1), 4)

    # ── build full merged dict (same as v2) ──────────────────────────────
    full = {
        "idx":                   idx,
        "total_runs":            total_runs,
        "has_asan_exe":          int("asan"  in results),
        "has_ubsan_exe":         int("ubsan" in results),

        "crash_count":           merged_crashes,
        "crash_rate":            round(merged_crashes      / max(total_runs, 1), 4),
        "exit_nonzero_count":    merged_exit_nonzero,
        "exit_nonzero_rate":     round(merged_exit_nonzero / max(total_runs, 1), 4),

        "asan_total":            merged_asan_total,
        "asan_rate":             round(merged_asan_total   / max(total_runs, 1), 4),
        "asan_run_count":        merged_asan_runs,
        "asan_run_rate":         round(merged_asan_runs    / max(total_runs, 1), 4),
        **{f"asan_{k}": sum_field(f"asan_{k}") for k in ASAN_PATTERNS},

        "ubsan_total":           merged_ubsan_total,
        "ubsan_rate":            round(merged_ubsan_total  / max(total_runs, 1), 4),
        "ubsan_run_count":       merged_ubsan_runs,
        "ubsan_run_rate":        round(merged_ubsan_runs   / max(total_runs, 1), 4),
        **{f"ubsan_{k}": sum_field(f"ubsan_{k}") for k in UBSAN_PATTERNS},

        "crash_generic_count":   merged_generic,
        "crash_generic_rate":    round(merged_generic      / max(total_runs, 1), 4),
        **{f"crash_{k}": sum_field(f"crash_{k}") for k in CRASH_PATTERNS},

        "timeout_count":         merged_timeouts,
        "timeout_rate":          round(merged_timeouts     / max(total_runs, 1), 4),

        "avg_exec_time":         avg_time,
        "time_variance":         time_var,
        "time_entropy":          wavg_field("time_entropy"),
        "max_exec_time":         max_field("max_exec_time"),
        "p90_exec_time":         max_field("p90_exec_time"),

        "unique_exit_codes":     max_field("unique_exit_codes"),
        "path_variability":      merged_paths,
        "path_variability_rate": round(merged_paths         / max(total_runs, 1), 4),
        "unique_outputs":        sum_field("unique_outputs"),
        "unique_raw_samples":    sum_field("unique_raw_samples"),

        "max_stderr_len":        max_stderr,
        "has_stderr":            int(max_stderr > 0),

        "input_sensitivity":     merged_input_eff,
        "input_sensitivity_rate":isr,
        "crash_transition_rate": ctr,

        "error_type_diversity":  merged_error_div,
        "rare_behavior_ratio":   rare_ratio,
        "crash_inducing_categories": merged_cat_inducing,
        **{
            f"crash_cat_{c}": max(r.get(f"crash_cat_{c}", 0) for r in results.values())
            for c in INPUT_CATEGORIES
        },
    }

    # ══════════════════════════════════════════════════════════════════════
    # TRIM TO 15 FEATURES  — only change vs v2
    # idx is always kept as the record identifier (not counted in the 15)
    # ══════════════════════════════════════════════════════════════════════
    return {
    "idx": full["idx"],

    "crash_count": full["crash_count"],
    "crash_rate": full["crash_rate"],

    # convert rates → counts (approx back conversion)
    "asan": full["asan_total"],
    "ubsan": full["ubsan_total"],

    "timeouts": full["timeout_count"],

    "avg_exec_time": full["avg_exec_time"],

    "unique_exit_codes": full["unique_exit_codes"],

    # success_rate = 1 - exit_nonzero_rate
    "success_rate": round(1 - full["exit_nonzero_rate"], 3),

    "path_variability": full["path_variability"],
    "unique_outputs": full["unique_outputs"],

    "time_variance": full["time_variance"],

    "input_sensitivity": full["input_sensitivity"],

    "has_stderr": int(full["max_stderr_len"] > 0),

    "error_type_diversity": full["error_type_diversity"],

    "rare_behavior_ratio": full["rare_behavior_ratio"],
}


# PER-FILE PROCESSOR 
def process_file_group(idx_and_files: tuple) -> dict | None:
    idx, files = idx_and_files

    results = {}
    for fname in files:
        exe_path = os.path.join(EXEC_DIR, fname)
        fname_l  = fname.lower()

        if "asan" in fname_l:
            exe_type = "asan"
        elif "ubsan" in fname_l:
            exe_type = "ubsan"
        else:
            exe_type = "unknown"

        feat = fuzz_one_exe(exe_path, exe_type, RUNS_PER_EXE)
        if feat is not None:
            results[exe_type] = feat

    if not results:
        return None

    return merge_exe_results(idx, results)


# FILE GROUPING 
def group_files_by_idx(exec_dir: str) -> dict:
    groups = defaultdict(list)
    for fname in os.listdir(exec_dir):
        if not fname.lower().endswith(".exe"):
            continue
        m = re.match(r'^(\d+)', fname)
        if not m:
            continue
        idx = int(m.group(1))
        groups[idx].append(fname)
    return dict(groups)


# MAIN
if __name__ == "__main__":
    print(f"🔧 Workers: {NUM_WORKERS}  |  Runs/exe: {RUNS_PER_EXE}  |  Timeout: {TIMEOUT}s")

    groups = group_files_by_idx(EXEC_DIR)
    print(f"📦 Unique file indices: {len(groups)}")

    processed = set()
    old_results = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            old_results = json.load(f)
        processed = {item["idx"] for item in old_results}
        print(f"⏭  Skipping {len(processed)} already processed")

    pending = [(idx, files) for idx, files in groups.items() if idx not in processed]
    print(f"🚀 To process: {len(pending)}")

    merged_results = {item["idx"]: item for item in old_results}

    global_start = time.time()

    with Pool(NUM_WORKERS) as pool:
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i : i + BATCH_SIZE]
            results = pool.map(process_file_group, batch)

            saved = 0
            for item in results:
                if item is None:
                    continue
                merged_results[item["idx"]] = item
                saved += 1

            with open(OUTPUT_FILE, "w") as f:
                json.dump(list(merged_results.values()), f, indent=2)

            elapsed  = time.time() - global_start
            done_tot = i + len(batch)
            rate     = done_tot / max(elapsed, 1)
            eta_s    = (len(pending) - done_tot) / max(rate, 0.001)

            print(
                f"✅ {done_tot}/{len(pending)} "
                f"| saved {saved}/{len(batch)} "
                f"| elapsed {elapsed/60:.1f}m "
                f"| ETA {eta_s/60:.1f}m"
            )

    total_elapsed = time.time() - global_start
    print(f"\n🔥 DONE — {len(merged_results)} files | {total_elapsed/60:.1f} min total")
    print(f"📄 Output: {OUTPUT_FILE}")
    print(f"🧮 Feature count per record: {len(next(iter(merged_results.values()), {}))}")
