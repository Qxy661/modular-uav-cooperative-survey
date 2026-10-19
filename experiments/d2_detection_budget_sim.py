"""D2 检测预算的物理时间账：SNR × 检测节拍 × 150 ms 闭环预算。

对应 docs/19_detection_budget.md。只依赖 numpy，seed 固定。

模型与 16 章一致：
- 残差 r_t ~ N(0, 1)（无故障）、N(snr, 1)（故障后），snr = δ/σ；
- CUSUM：S_t = max(0, S_{t-1} + r_t - ν)，ν=0.5，越限阈值 h；
- 延迟按"故障后第 n 个样本越限"计（n=1 即故障后第一个样本就检出）；
- 误报预算：无故障长跑 2e6 样本，报警后清零，数全部报警，ARL0 = N/报警数。

物理检测时间：
    L = (n - 1) * T + (T - φ) + d,  φ ~ U[0, T)
中位取 φ=T/2，P95 取 φ→0（最坏相位），所以
    L_med ≈ (n_med - 0.5) * T + d_med
    L_p95 ≈ n_p95 * T + d_p95
d 取 18 章各频率的交付年龄 P95（10/20/50 Hz 实测模型值，25/26.7 Hz 线性插值）。
"""

import json
import math
import time

import numpy as np

SEED = 20261019
NU = 0.5
N_ARL = 2_000_000
REPS = 4_000
MAX_LEN = 400

# 18 章交付年龄 P95（ms）：10/20/50 Hz
DELIVERY_P95 = {10: 7.2, 20: 8.2, 25: 9.0, 26.7: 9.4, 50: 11.5, 80: 13.0}

SNRS = [1.92, 2.89, 3.33, 5.0, 10.0]
H_GRID = [round(7.8 + 0.1 * i, 1) for i in range(15)]  # 7.8 .. 9.2


def arl0(h, n=N_ARL, seed=SEED):
    """无故障平均运行长度（样本）。报警后清零，数全部报警。"""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    s = 0.0
    alarms = 0
    for v in x:
        s = s + v - NU
        if s < 0.0:
            s = 0.0
        elif s >= h:
            alarms += 1
            s = 0.0
    return n / alarms if alarms else float("inf")


def delay_dist(snr, h, reps=REPS, max_len=MAX_LEN, seed=SEED + 7):
    """故障后检出所需样本数；未检出记 max_len（删失）。"""
    rng = np.random.default_rng(seed)
    out = np.empty(reps, dtype=np.int32)
    for i in range(reps):
        s = 0.0
        n = 0
        while n < max_len:
            n += 1
            x = rng.normal(snr, 1.0)
            s = s + x - NU
            if s < 0.0:
                s = 0.0
            elif s >= h:
                break
        out[i] = n
    return out


def pct(a, q):
    return float(np.percentile(a, q))


def main():
    t0 = time.time()
    result = {
        "config": {
            "seed": SEED,
            "nu": NU,
            "n_arl": N_ARL,
            "reps": REPS,
            "max_len": MAX_LEN,
            "delivery_p95_ms": DELIVERY_P95,
        },
        "arl0": {},
        "delays": {},
        "latency": {},
    }

    # 1) ARL0 随 h 的映射（与频率无关，误报预算按"每 10 min 采样数"折算）
    for h in H_GRID:
        result["arl0"][str(h)] = round(arl0(h), 1)
    print("ARL0 map:", result["arl0"], f"({time.time()-t0:.1f}s)")

    # 2) 给定误报目标的 h：目标 = 每 10 min 期望 ≤1 次误报 → ARL0 ≥ rate*600
    rates = [10, 20, 25, 26.7, 50, 80]
    h_for_rate = {}
    for r in rates:
        target = r * 600.0
        h_sel = None
        for h in H_GRID:
            if result["arl0"][str(h)] >= target:
                h_sel = h
                break
        h_for_rate[str(r)] = {"target_arl0": target, "h": h_sel}
    result["h_for_rate"] = h_for_rate
    print("h per rate:", h_for_rate)

    # 3) 延迟分布：主表用 h=8（现有协议），另算 50/80 Hz 按误报归一化后的 h
    for snr in SNRS:
        for h in (8.0, 8.6, 9.0):
            d = delay_dist(snr, h)
            key = f"{snr}_{h}"
            result["delays"][key] = {
                "snr": snr,
                "h": h,
                "median_samples": pct(d, 50),
                "p95_samples": pct(d, 95),
                "p99_samples": pct(d, 99),
                "censored": int((d >= MAX_LEN).sum()),
            }
    print("delays done", f"{time.time()-t0:.1f}s")

    # 4) 物理检测时间：L_med=(n_med-0.5)T+d_med, L_p95=n_p95*T+d_p95
    for snr in SNRS:
        for h in (8.0, 8.6, 9.0):
            dk = result["delays"][f"{snr}_{h}"]
            nmed, np95 = dk["median_samples"], dk["p95_samples"]
            for r in rates:
                T = 1000.0 / r
                d = DELIVERY_P95[r]
                lat_med = (nmed - 0.5) * T + d
                lat_p95 = np95 * T + d
                key = f"{snr}_{h}_{r}"
                result["latency"][key] = {
                    "snr": snr,
                    "h": h,
                    "rate_hz": r,
                    "period_ms": round(T, 2),
                    "delivery_p95_ms": d,
                    "latency_median_ms": round(lat_med, 1),
                    "latency_p95_ms": round(lat_p95, 1),
                    "pass_median": lat_med <= 150.0,
                    "pass_p95": lat_p95 <= 150.0,
                }

    out = r"D:\modular-uav-cooperative-survey\experiments\d2_detection_budget_sim.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("wrote", out, f"({time.time()-t0:.1f}s)")

    # 控制台摘要：h=8、σ=2%（SNR=5）与 σ=3%（SNR=3.33）在 20/26.7/50 Hz
    for snr in (5.0, 3.33):
        for r in (20, 26.7, 50):
            k = f"{snr}_8.0_{r}"
            L = result["latency"][k]
            print(
                f"SNR={snr} rate={r}Hz: med={L['latency_median_ms']}ms "
                f"p95={L['latency_p95_ms']}ms pass_p95={L['pass_p95']}"
            )


if __name__ == "__main__":
    main()
