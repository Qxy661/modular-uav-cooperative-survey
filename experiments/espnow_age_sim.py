"""ESP-NOW 广播下的数据年龄与协同环频率：一个可算的排队模型。

目的
----
14 章把"20 Hz 广播、数据年龄 P95 ≈ 30–35 ms"写进了预算，17 章又把它当作平台参数
P6。但这个数有一个没写清的歧义：**交付年龄（delivery age）** 与 **陈旧度
（staleness）** 不是同一个量。

- 交付年龄：一帧从生成到被接收的时间（排队 + 空口 + 处理）。
- 陈旧度：控制层在某个时刻真正拿来用的最新一帧，已经"旧"了多久；它至少包含
  一个采样周期的相位等待，因此不可能低于采样周期的一半（P95 接近一个周期）。

本脚本把两者分开算，并给出 10/20/50/100 Hz × 丢包率下的分布。结论用于修正
14.4 / 17.3 的 P6 口径，以及 17.4.4 的事件触发设计（必须带心跳，否则陈旧度失控）。

模型与简化
----------
- 单信道串行发送：每帧空口时间 = 120 B × 8 / 250 kbps = 3.84 ms；N=4 个模块的帧
  按到达顺序排队、串行服务。不做碰撞建模（视为时隙化调度），这是乐观假设。
- 生成抖动：每个模块的相位在 [0, T) 内均匀分布，独立同分布。
- 丢包：每帧独立以 p_loss 丢失；不重传（ESP-NOW 广播的默认语义）。
- 处理延迟：固定 1 ms（接收 + 解包 + 写共享内存）。
- 陈旧度：控制层在每个周期边界 u_m = mT 取"已到达的最新帧"。
- 事件触发：每周期以概率 q 主动发送，或距上次发送 ≥ K 个周期时强制心跳。
- 100 Hz 若服务率不足，队列会无界增长；脚本记录 10 min 后的积压并标记 infeasible。

运行：python experiments/espnow_age_sim.py
输出：experiments/espnow_age_sim.json
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SEED = 20261019
DURATION_S = 600.0
N_MODULES = 4
FRAME_BYTES_AIR = 120
CAPACITY_BPS = 250_000  # P4 的上界，乐观取值
PROC_S = 0.001
JITTER = True


@dataclass
class Config:
    seed: int = SEED
    duration_s: float = DURATION_S
    n_modules: int = N_MODULES
    frame_bytes_air: int = FRAME_BYTES_AIR
    capacity_bps: int = CAPACITY_BPS
    proc_s: float = PROC_S
    jitter: bool = JITTER

    @property
    def airtime_s(self) -> float:
        return self.frame_bytes_air * 8 / self.capacity_bps


def simulate_stream(
    cfg: Config,
    rate_hz: float,
    p_loss: float,
    rng: np.random.Generator,
    send_prob: float = 1.0,
    heartbeat_cycles: int = 0,
) -> dict:
    """模拟 N 个模块共享一个广播信道；返回交付年龄/陈旧度/占用与积压。"""
    T = 1.0 / rate_hz
    n_cycles = int(round(cfg.duration_s / T))
    n_s = cfg.n_modules
    airtime = cfg.airtime_s

    gen = np.arange(n_cycles) * T
    phase = rng.uniform(0, T, (n_s, n_cycles)) if cfg.jitter else np.zeros((n_s, n_cycles))
    arrivals = gen[None, :] + phase  # s × n

    # 发送决策（按发送端独立）：全发送 / 事件触发 + 心跳
    sent = np.ones((n_s, n_cycles), dtype=bool)
    if send_prob < 1.0:
        sent = rng.random((n_s, n_cycles)) < send_prob
        if heartbeat_cycles > 0:
            for s in range(n_s):
                last = -10**9
                for i in range(n_cycles):
                    if sent[s, i]:
                        last = i
                    elif i - last >= heartbeat_cycles:
                        sent[s, i] = True
                        last = i

    delivered = sent & (rng.random((n_s, n_cycles)) >= p_loss)

    # 共享信道：把 N×cycles 帧按到达时刻排序，串行服务
    idx = np.argwhere(delivered)  # [sender, cycle]
    order = np.argsort(arrivals[delivered])
    frames = idx[order]
    arr = arrivals[delivered][order]
    finish = np.empty(len(frames))
    busy_until = 0.0
    for k in range(len(frames)):
        start = max(arr[k], busy_until)
        finish[k] = start + airtime
        busy_until = finish[k]

    delivery_age = finish - arr + cfg.proc_s
    ok = ~np.isnan(delivery_age)
    d = delivery_age[ok]

    # 每个发送端的到达时刻与完成时刻（用于陈旧度）
    per_s_last_finish = []
    per_s_gen_cycles = []
    for s in range(n_s):
        mask = (frames[:, 0] == s) if len(frames) else np.zeros(0, dtype=bool)
        f_s = frames[mask, 1]
        per_s_gen_cycles.append(f_s)
        if len(f_s):
            # 完成时刻按"该发送端帧在全局服务顺序中的位置"取
            pos = np.where(mask)[0]
            per_s_last_finish.append(finish[pos])
        else:
            per_s_last_finish.append(np.array([]))

    # 陈旧度：每个周期边界、每个发送端取已到达的最新帧
    use_times = np.arange(n_cycles) * T
    stale = []
    for s in range(n_s):
        if len(per_s_last_finish[s]) == 0:
            continue
        gen_s = per_s_gen_cycles[s] * T + phase[s, per_s_gen_cycles[s]]
        fin_s = per_s_last_finish[s]
        o = np.argsort(fin_s)
        fin_s, gen_s = fin_s[o], gen_s[o]
        j = 0
        last_gen = -math.inf
        for u in use_times:
            while j < len(fin_s) and fin_s[j] <= u:
                last_gen = max(last_gen, gen_s[j])
                j += 1
            if last_gen > -math.inf:
                stale.append(u - last_gen)
    stale = np.asarray(stale)

    app_bps = cfg.n_modules * (1.0 / T) * send_prob * FRAME_BYTES_AIR * 8
    air_bps = cfg.n_modules * (1.0 / T) * send_prob * cfg.frame_bytes_air * 8
    util = air_bps / cfg.capacity_bps
    infeasible = util >= 1.0
    if infeasible:
        max_backlog = cfg.duration_s * (util - 1.0) * 1000.0
    else:
        max_backlog = float(np.max(finish)) * 1e3 if len(finish) else 0.0

    def pct(a, q):
        a = a[~np.isnan(a)]
        return float(np.percentile(a, q)) if len(a) else float("nan")

    return {
        "rate_hz": rate_hz,
        "p_loss": p_loss,
        "send_prob": send_prob,
        "heartbeat_cycles": heartbeat_cycles,
        "delivery_age_ms": {
            "p50": pct(d, 50) * 1e3,
            "p95": pct(d, 95) * 1e3,
            "p99": pct(d, 99) * 1e3,
            "max": float(np.max(d)) * 1e3 if len(d) else float("nan"),
        },
        "staleness_ms": {
            "p50": pct(stale, 50) * 1e3,
            "p95": pct(stale, 95) * 1e3,
            "p99": pct(stale, 99) * 1e3,
        },
        "occupancy": {
            "app_kbps": app_bps / 1e3,
            "air_kbps": air_bps / 1e3,
            "util": util,
            "infeasible": infeasible,
            "last_finish_s": max_backlog / 1e3,
        },
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    cfg = Config()
    out: dict = {
        "config": {
            "seed": SEED,
            "duration_s": DURATION_S,
            "n_modules": N_MODULES,
            "frame_bytes_air": FRAME_BYTES_AIR,
            "capacity_bps": CAPACITY_BPS,
            "airtime_ms": cfg.airtime_s * 1e3,
            "proc_ms": PROC_S * 1e3,
            "jitter": JITTER,
        },
        "rates": {},
    }

    for rate in (10, 20, 50, 100):
        out["rates"][str(rate)] = {}
        for p_loss in (0.0, 0.001, 0.01, 0.05, 0.10):
            out["rates"][str(rate)][f"{p_loss:.3f}"] = simulate_stream(
                cfg, rate, p_loss, rng
            )

    # 事件触发：50 Hz 下 q=0.25，比较有无心跳
    event = {}
    for hb in (0, 5, 10):
        event[f"hb{hb}"] = simulate_stream(
            Config(), 50, 0.01, rng, send_prob=0.25, heartbeat_cycles=hb
        )
    out["event_trigger_50hz_q0.25"] = event

    path = Path(__file__).with_suffix(".json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"airtime/frame = {cfg.airtime_s*1e3:.2f} ms, N={cfg.n_modules}")
    print("rate  loss   delivery_p95  stale_p95  util   infeasible  end_busy_s")
    for rate in (10, 20, 50, 100):
        for p_loss in (0.0, 0.001, 0.01, 0.05, 0.10):
            r = out["rates"][str(rate)][f"{p_loss:.3f}"]
            print(
                f"{rate:>4}  {p_loss:<5}  {r['delivery_age_ms']['p95']:>12.1f}  "
                f"{r['staleness_ms']['p95']:>9.1f}  {r['occupancy']['util']:>5.2f}  "
                f"{str(r['occupancy']['infeasible']):<10}  {r['occupancy']['last_finish_s']:>8.1f}"
            )
    print("\nevent trigger 50 Hz, q=0.25, p_loss=1%")
    for k, r in event.items():
        print(
            f"{k:>4}  delivery_p95={r['delivery_age_ms']['p95']:.1f} ms  "
            f"stale_p95={r['staleness_ms']['p95']:.1f} ms  util={r['occupancy']['util']:.2f}"
        )
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
