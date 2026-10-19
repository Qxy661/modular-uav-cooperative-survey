"""D2 判别实验的数值预研：单模块推力损失能不能在 20 Hz 下、不同噪声相关度下被检测到。

问题：D2 协议（docs/15）用单模块力残差的 CUSUM，取 h=8σ、ν=0.5σ，实测算得
ARL0≈1.88e4 样本（20 Hz 下 10 min 约 0.6 次误报），SNR≥5 时检测延迟 ≤2 样本。
但"多测点联合"的增益（docs/14 写的 SNR×√k）只在故障签名与噪声方向可分时成立；
刚性绑缚下模块力的噪声含很强的公共模态（整机振动），这一点必须先用数值实验检验，
否则 D1–D3 做完才发现"联合"没用。

模型：4 模块刚性绑缚，总重 W=19.62 N，每模块额定推力 f0=W/4。故障为一个模块
推力损失 10%（δ=0.10，占 f0 的 10%）。模块力测量噪声按等相关系数 ρ 生成：

    eps_i = σ * (sqrt(ρ) * z0 + sqrt(1-ρ) * z_i)

z0 是公共模态、z_i 是各模块独立噪声。所有检测器都按其统计量的理论标准差标准化，
统一取 ν=0.5σ、h=8σ——高斯的 CUSUM ARL0 只取决于 h，所以四种路径的误报预算一致，
检测延迟可以直接比较。

四种路径：
  single  单模块残差（已知哪块掉推力；D2 台架上的做法）
  mean4   四模块残差取平均（"多测点降噪"的朴素做法）
  or4     四路 CUSUM 取最大（不知道哪块坏时的常规做法；阈值用 h=8.7 近似补偿
          四次比较，实测 ARL0 与 single 对齐，见输出）
  plate   力台总推力残差（单模块损失 = 总推力 2.5% W；力台噪声 σp=0.5% W 且独立）

只依赖 numpy。运行：python experiments/d2_force_residual_sim.py
输出：experiments/d2_force_residual_sim.json，供 docs/16 引用；随机种子固定。

注意：这是"检测器可比性"实验，不是飞控仿真。它回答"在给定噪声相关结构下，
哪种检测路径延迟更短"，不回答"实际噪声相关度是多少"——后者正是 D2 要测的量。
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np

SEED = 20261019
W = 19.62            # 4 模块总重，N（2 kg）
F0 = W / 4.0         # 单模块额定推力，N
FAULT = 0.10         # 单模块推力损失比例
RHO = (0.0, 0.6, 0.9)
SIGMA_PCT = (1.0, 2.0, 3.0)   # 模块力测量噪声，% f0
SIGMA_PLATE_PCT = 0.5         # 力台噪声，% W
NU, H = 0.5, 8.0              # 单路 CUSUM 参数（单位：统计量标准差）
H_OR = 9.3                    # OR 四路取最大时的高阈值；实测 ARL0 与单路 h=8 对齐（8.7 只有约 1.1e4）
ARL0_LEN = 2_000_000          # 无故障长跑样本数，用于实测 ARL0
DELAY_REPS, DELAY_MAX, T0 = 2000, 500, 100


def noise_stream(rng, n, sigma_pct, rho, channels=4):
    """返回 shape=(channels, n) 的力测量噪声，单位 N。"""
    sigma = sigma_pct / 100.0 * F0
    z0 = rng.standard_normal(n)
    z = rng.standard_normal((channels, n))
    return sigma * (np.sqrt(rho) * z0[None, :] + np.sqrt(1.0 - rho) * z)


def first_cross(x, nu, h, start=0):
    """x shape=(reps, n)：返回每条序列首次越限索引，未越限为 -1。"""
    reps, n = x.shape
    s = np.zeros(reps)
    first = np.full(reps, -1, dtype=np.int64)
    for t in range(start, n):
        s = np.maximum(0.0, s + x[:, t] - nu)
        newly = (s > h) & (first < 0)
        first[newly] = t
    return first


def count_alarms(x, nu, h):
    """x shape=(channels, n)：任意一路越限计一次报警，报警后所有通道清零。

    ARL0 是"平均多久报一次"，必须数同一条长序列上的全部报警次数；只数首次越限
    会把 ARL0 高估成整段长度（第一版实现就踩了这个坑，输出全是 800000）。
    """
    ch, n = x.shape
    s = np.zeros(ch)
    count = 0
    for t in range(n):
        s = np.maximum(0.0, s + x[:, t] - nu)
        if (s > h).any():
            count += 1
            s[:] = 0.0
    return count


def arl0(method, rng, sigma_pct, rho, n=ARL0_LEN):
    """实测无故障 ARL0（样本数）。"""
    sigma_n = sigma_pct / 100.0 * F0
    if method == "single":
        x = (noise_stream(rng, n, sigma_pct, rho)[0] / sigma_n)[None, :]
        count = count_alarms(x, NU, H)
    elif method == "mean4":
        s_eff = sigma_n * np.sqrt(rho + (1.0 - rho) / 4.0)
        x = (noise_stream(rng, n, sigma_pct, rho).mean(axis=0) / s_eff)[None, :]
        count = count_alarms(x, NU, H)
    elif method == "or4":
        x = noise_stream(rng, n, sigma_pct, rho) / sigma_n
        count = count_alarms(x, NU, H_OR)
    elif method == "plate":
        # 力台噪声独立：按力台噪声归一化，z 的标准差就是 1
        x = rng.standard_normal((1, n))
        count = count_alarms(x, NU, H)
    else:
        raise ValueError(method)
    return n / count if count else float("inf")


def detection_delay(method, rng, sigma_pct, rho):
    reps = DELAY_REPS
    fault_amp = FAULT * F0
    if method == "plate":
        # 总推力损失 = 单模块损失；力台噪声 0.5% W
        plate_noise = SIGMA_PLATE_PCT / 100.0 * W
        z = rng.standard_normal((reps, DELAY_MAX))
        x = z.copy()
        x[:, T0:] += fault_amp / plate_noise
        first = first_cross(x, NU, H, start=T0)
    else:
        sigma = sigma_pct / 100.0 * F0
        z0 = rng.standard_normal((reps, DELAY_MAX))
        z = rng.standard_normal((reps, 4, DELAY_MAX))
        noise = sigma * (np.sqrt(rho) * z0[:, None, :] + np.sqrt(1.0 - rho) * z)
        noise[:, 0, T0:] += fault_amp
        if method == "single":
            first = first_cross(noise[:, 0] / (sigma_pct / 100.0 * F0), NU, H, start=T0)
        elif method == "mean4":
            s_eff = sigma_pct / 100.0 * np.sqrt(rho + (1.0 - rho) / 4.0)
            first = first_cross(noise.mean(axis=1) / (s_eff * F0), NU, H, start=T0)
        elif method == "or4":
            ch = noise / (sigma_pct / 100.0 * F0)
            idxs = np.stack([first_cross(ch[:, c], NU, H_OR, start=T0) for c in range(4)])
            pos = np.where(idxs >= 0, idxs, np.iinfo(np.int64).max)
            first = pos.min(axis=0)
            first[first == np.iinfo(np.int64).max] = -1
        else:
            raise ValueError(method)
    delays = []
    for f in first:
        if f < 0:
            delays.append(None)
        else:
            # 从故障注入后的第一个样本算起
            delays.append(int(f - T0 + 1))
    hits = [d for d in delays if d is not None]
    hits.sort()
    return {
        "median": statistics.median(hits) if hits else None,
        "p95": hits[int(0.95 * (len(hits) - 1))] if hits else None,
        "miss_rate": round(1 - len(hits) / len(delays), 4),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = []
    for sigma_pct in SIGMA_PCT:
        for rho in RHO:
            sigma = sigma_pct / 100.0
            noise_std = {
                "single": sigma,
                "mean4": sigma * np.sqrt(rho + (1.0 - rho) / 4.0),
                "or4": sigma,
                "plate": SIGMA_PLATE_PCT / 100.0 * W / F0,  # 换算成 f0 的倍数
            }
            sig = {
                "single": FAULT,
                "mean4": FAULT / 4.0,
                "or4": FAULT,
                "plate": FAULT,
            }
            for method in ("single", "mean4", "or4", "plate"):
                # plate 与 σ、ρ 无关，只跑一次
                if method == "plate" and not (sigma_pct == SIGMA_PCT[0] and rho == RHO[0]):
                    continue
                a = arl0(method, rng, sigma_pct, rho)
                d = detection_delay(method, rng, sigma_pct, rho)
                rows.append({
                    "sigma_pct": sigma_pct if method != "plate" else None,
                    "rho": rho if method != "plate" else None,
                    "method": method,
                    "snr": round(sig[method] / noise_std[method], 3),
                    "arl0_samples": None if a == float("inf") else round(a, 0),
                    "false_alarms_per_10min_20hz": None if a == float("inf") else round(12000 / a, 3),
                    "delay_median_samples": d["median"],
                    "delay_p95_samples": d["p95"],
                    "miss_rate": d["miss_rate"],
                })
    out = {
        "seed": SEED,
        "params": {
            "W_N": W, "f0_N": round(F0, 4), "fault_frac_of_f0": FAULT,
            "rho_values": list(RHO), "sigma_pct_values": list(SIGMA_PCT),
            "nu_over_sigma": NU, "h": H, "h_or": H_OR,
            "arl0_len": ARL0_LEN, "delay_reps": DELAY_REPS, "delay_max": DELAY_MAX,
        },
        "rows": rows,
    }
    path = Path(__file__).with_suffix(".json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {path}")
    print(f"{'sig%':>5} {'rho':>4} {'method':>7} {'SNR':>6} {'ARL0':>8} {'FA/10min':>9} {'med':>4} {'p95':>4} {'miss':>6}")
    for r in rows:
        print(f"{str(r['sigma_pct']):>5} {str(r['rho']):>4} {r['method']:>7} {r['snr']:>6} "
              f"{str(r['arl0_samples']):>8} {str(r['false_alarms_per_10min_20hz']):>9} "
              f"{str(r['delay_median_samples']):>4} {str(r['delay_p95_samples']):>4} {str(r['miss_rate']):>6}")


if __name__ == "__main__":
    main()
