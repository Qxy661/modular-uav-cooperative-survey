"""校验 runs/ 是否满足 21 章的"回填合同"。

只依赖标准库。用法：
    python experiments/validate_runs.py

没有 runs/ 或没有数据时打印"尚无数据"并以 0 退出（CI 友好）；
有数据但缺字段时以 1 退出，并列出每个文件缺什么。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"

GLOBAL_META = {
    "date": str,
    "bench_photo_ids": list,
    "firmware": str,
    "randomization": str,
    "d1": dict,
    "d3": dict,
}
D1_META = {"freq_hz", "frame_bytes", "duration_s", "recv_pct", "loss_pct",
           "delivery_p95_ms", "staleness_p95_ms"}
D2_META = {"freq_hz", "sigma_pct", "h_used", "arl0", "delay_med_samples",
           "delay_p95_samples", "false_alarms_10min"}
D3_META = {"coupling", "load_kg", "k_N_per_m", "clamp_repeat_um", "cv", "perp_med"}

SAMPLE_FIELDS = {
    "D1": {"t_us", "seq", "sender", "tx_us", "rx_us", "payload_len"},
    "D2": {"t_us", "module", "mode", "cmd_pwm", "f", "seq"},
    "D3": {"t_us", "clamp_id", "coupling", "clamp_method", "preload",
            "f1", "f2", "temp_C", "disp_um", "k_N_per_m"},
}
RUN_META = {"D1": D1_META, "D2": D2_META, "D3": D3_META}


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as e:
        return {"__error__": str(e)}


def check_meta_shape(meta):
    missing = []
    for key, typ in GLOBAL_META.items():
        if key not in meta:
            missing.append(f"meta.{key}")
            continue
        if not isinstance(meta[key], typ):
            missing.append(f"meta.{key}(类型应为 {typ.__name__})")
    d1 = meta.get("d1", {})
    d3 = meta.get("d3", {})
    for key in ("frame_bytes", "channel"):
        if key not in d1:
            missing.append(f"meta.d1.{key}")
    for key in ("k_N_per_m", "k_method", "clamp_repeat_um", "alpha_1_K", "temp_sensor"):
        if key not in d3:
            missing.append(f"meta.d3.{key}")
    return missing


def check_sample(path, exp):
    """读首行，检查必需字段；顺带检查长度类字段。"""
    try:
        first = path.read_text(encoding="utf-8-sig").splitlines()[0]
        row = json.loads(first)
    except (OSError, IndexError, json.JSONDecodeError) as e:
        return [f"无法读取首行: {e}"]
    missing = [f for f in SAMPLE_FIELDS[exp] if f not in row]
    if exp == "D2" and isinstance(row.get("f"), list) and len(row["f"]) != 3:
        missing.append("f 应为 3 维")
    if exp == "D3":
        for k, n in (("preload", 6), ("f1", 3), ("f2", 3)):
            if isinstance(row.get(k), list) and len(row[k]) != n:
                missing.append(f"{k} 应为 {n} 维")
        if not isinstance(row.get("disp_um", {}), dict):
            missing.append("disp_um 应为对象")
    return missing


def main():
    if not RUNS.exists():
        print(f"no data: {RUNS} does not exist; see docs/21_backfill_playbook.md")
        return 0

    global_meta_path = RUNS / "meta.json"
    ok = True
    if global_meta_path.exists():
        meta = load_json(global_meta_path)
        if "__error__" in meta:
            print(f"[FAIL] meta.json unparsable: {meta['__error__']}")
            ok = False
        else:
            missing = check_meta_shape(meta)
            print(f"meta.json: {'OK' if not missing else 'missing ' + ', '.join(missing)}")
            ok = ok and not missing
    else:
        print("[FAIL] runs/meta.json missing")
        ok = False

    data_files = sorted(p for p in RUNS.glob("*.jsonl") if not p.name.endswith(".meta.json"))
    if not data_files:
        print("no *.jsonl data under runs/")
        return 0 if ok else 1

    print(f"\n{'file':42} {'exp':4} {'sample':10} {'run meta':10}")
    print("-" * 72)
    for path in data_files:
        exp = path.name.split("_")[0]
        if exp not in SAMPLE_FIELDS:
            print(f"{path.name:42} {'?':4} unknown exp prefix (D1/D2/D3)")
            ok = False
            continue
        miss_sample = check_sample(path, exp)
        run_meta = path.with_suffix(".meta.json")
        if run_meta.exists():
            rm = load_json(run_meta)
            miss_meta = [k for k in RUN_META[exp] if k not in rm] if "__error__" not in rm else ["meta 解析失败"]
        else:
            miss_meta = ["missing"]
        s = "OK" if not miss_sample else f"miss{len(miss_sample)}"
        m = "OK" if not miss_meta else f"miss{len(miss_meta)}"
        print(f"{path.name:42} {exp:4} {s:10} {m:10}")
        if miss_sample:
            print(f"    sample missing: {', '.join(miss_sample)}")
        if miss_meta:
            print(f"    run meta missing: {', '.join(miss_meta)}")
        ok = ok and not miss_sample and not miss_meta

    print("\nresult:", "all fields present" if ok else "missing fields, see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

