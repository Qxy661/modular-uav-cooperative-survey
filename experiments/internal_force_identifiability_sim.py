"""A 主线的前置问题：12 路测点能不能把"载荷份额"和"内力"分开？

对应 docs/20_internal_force_identifiability.md。只依赖 numpy，seed 固定。

几何：4 个模块装在 0.3 m × 0.3 m 刚性框的四角（z=0 平面），
每个模块的安装点有 3 轴测力（共 12 路）。刚体静力学：
    w = G f,  G ∈ R^{6×12}
G 的秩为 6，零空间维数 6 = 自平衡内力（对压/对拉、绕三轴的扭矩对）。
给定测量 f，可唯一分解 f = G⁺w + n，n = P_N f 就是内力分量。
本章不讨论"估不出来"，而讨论"估出来之后，噪声、装配应力、热漂移谁主导"。
"""

import json
import numpy as np

SEED = 20261019
RNG = np.random.default_rng(SEED)

W_TOTAL = 19.62  # N，2 kg
F0 = W_TOTAL / 4.0  # N，单模块额定推力
SIDE = 0.3  # m，方框边长
A = SIDE / 2.0
ALPHA_AL = 2.3e-5  # 1/K，铝合金线膨胀系数


def geometry(a=A, perturb_mm=0.0, rng=RNG):
    """四角安装点；perturb_mm 给每轴位置误差（mm）。"""
    pts = np.array([[a, a, 0], [a, -a, 0], [-a, a, 0], [-a, -a, 0]], dtype=float)
    if perturb_mm > 0:
        pts = pts + rng.normal(0.0, perturb_mm * 1e-3, pts.shape)
    return pts


def grasp_matrix(pts):
    """6×12：列 = 每个模块的 e_x/e_y/e_z 产生的 [力; 力矩]。"""
    G = np.zeros((6, 12))
    for i, p in enumerate(pts):
        for j, e in enumerate(np.eye(3)):
            G[0:3, 3 * i + j] = e
            G[3:6, 3 * i + j] = np.cross(p, e)
    return G


def null_basis(G):
    _, s, Vt = np.linalg.svd(G, full_matrices=True)
    N = Vt[6:].T  # 秩 6：右奇异向量第 7–12 个张成零空间
    return N, s


def compression_pattern(pts):
    """沿 x 的对压模式：x<0 的模块推 +x，x>0 的推 -x。

    净力为零、净力矩为零 → 纯内力方向，用来给装配应力/热应力建模。
    """
    f = np.zeros(12)
    for i, p in enumerate(pts):
        f[3 * i] = -np.sign(p[0])
    return f


def pct(x, q):
    return float(np.percentile(x, q))


def main():
    out = {"config": {"seed": SEED, "W_total_N": W_TOTAL, "f0_N": F0,
                      "side_m": SIDE, "alpha_al_1_K": ALPHA_AL}}

    pts = geometry()
    G = grasp_matrix(pts)
    N, s = null_basis(G)
    P_N = N @ N.T
    n0 = compression_pattern(pts)
    n0 = n0 / np.linalg.norm(n0)  # 单位内力方向

    L = A  # 力臂，用于把力矩无量纲化
    S = np.diag([1, 1, 1, 1 / L, 1 / L, 1 / L])
    s_scaled = np.linalg.svd(S @ G, compute_uv=False)

    out["grasp"] = {
        "singular_values": [round(float(v), 4) for v in s],
        "rank": int(np.sum(s > 1e-9)),
        "cond_unscaled": round(float(s[0] / s[5]), 3),
        "cond_scaled_by_arm": round(float(s_scaled[0] / s_scaled[5]), 3),
        "null_dim": int(N.shape[1]),
        "compression_mode_is_null": round(float(np.linalg.norm(G @ n0)), 6),
    }

    # 1) 随机 12 维力向量里，内力分量占多大比例
    f_rand = RNG.normal(0, 1, (20000, 12)).T
    n_rand = P_N @ f_rand
    ratio = np.linalg.norm(n_rand, axis=0) / np.linalg.norm(f_rand, axis=0)
    out["random_internal_fraction"] = {
        "mean": round(float(ratio.mean()), 3),
        "p50": round(pct(ratio, 50), 3),
        "p95": round(pct(ratio, 95), 3),
        "theory_chi_over_sqrt12": round(float(np.sqrt(6 / 12)), 3),
    }

    # 2) 测量噪声投影到零空间：||P_N eps|| ~ sigma * chi_6
    chi6 = np.linalg.norm(RNG.normal(0, 1, (200000, 6)), axis=1)
    noise = {}
    for p in (0.01, 0.02, 0.03):
        sig = p * F0
        noise[f"{int(p*100)}pct_f0"] = {
            "sigma_N": round(float(sig), 4),
            "p50_N": round(float(sig * np.percentile(chi6, 50)), 4),
            "p95_N": round(float(sig * np.percentile(chi6, 95)), 4),
            "signal_10pct_N": round(0.10 * F0, 4),
            "p95_after_20_cycle_avg_N": round(
                float(sig * np.percentile(chi6, 95) / np.sqrt(20)), 4),
        }
    out["noise_floor"] = noise

    # 3) 装配应力：位置误差 delta * 结构刚度 k → 对压内力
    #    内力幅值 = ||P_N (k·delta·n0)|| = k·delta（n0 为单位零空间向量）
    assembly = {}
    pat = compression_pattern(pts)
    for k in (1e4, 1e5):
        d = RNG.uniform(0, 1e-3, (20000,))  # 0–1 mm
        n = np.linalg.norm(P_N @ (pat[:, None] * (k * d)[None, :]), axis=0)
        assembly[f"k_{int(k)}"] = {
            "per_module_p50_N": round(float(k * 0.5e-3), 2),
            "internal_p50_N": round(pct(n, 50), 2),
            "internal_p95_N": round(pct(n, 95), 2),
            "max_N": round(float(n.max()), 2),
            "vs_signal_10pct": round(pct(n, 50) / (0.10 * F0), 1),
        }
    out["assembly_stress"] = assembly

    # 4) 热漂移：两侧受约束的膨胀 → 对压内力；自由膨胀量 αΔT·L
    thermal = {}
    for dT in (5, 10, 20):
        d = ALPHA_AL * dT * SIDE  # m
        f = {}
        for k in (1e4, 1e5):
            internal = float(np.linalg.norm(P_N @ (compression_pattern(pts) * (k * d))))
            f[f"k_{int(k)}"] = {
                "per_module_N": round(float(k * d), 2),
                "internal_N": round(internal, 2),
                "vs_signal_10pct": round(internal / (0.10 * F0), 1),
            }
        thermal[f"dT_{dT}K"] = {
            "free_expansion_um": round(d * 1e6, 1),
            "cases": f,
        }
    out["thermal_drift"] = thermal

    # 5) 几何公差：真实结构里有内力 n；用名义 G 估载荷、用名义 P_N 估内力
    geo = {}
    for tol_mm in (0.5, 1.0, 2.0):
        load_err, spur, int_err = [], [], []
        for _ in range(1000):
            Gt = grasp_matrix(geometry(perturb_mm=tol_mm, rng=RNG))
            nt, _ = null_basis(Gt)
            n_true = nt[:, 0] * 5.0  # 5 N 的真实内力（一阶）
            w = np.array([0, 0, W_TOTAL, 0, 0, 0], float)
            f = np.linalg.pinv(Gt) @ w + n_true
            w_hat = G @ f
            load_err.append(abs(w_hat[2] - w[2]) / W_TOTAL)
            spur.append(np.linalg.norm(P_N @ f))
            int_err.append(abs(np.linalg.norm(P_N @ f) - 5.0) / 5.0)
        geo[f"tol_{tol_mm}mm"] = {
            "load_share_err_p95_pct": round(100 * pct(load_err, 95), 3),
            "internal_est_err_p95_pct": round(100 * pct(int_err, 95), 2),
            "spurious_internal_p95_N": round(pct(spur, 95), 3),
        }
    out["geometry_tolerance"] = geo

    # 6) D3 重复装夹：装配应力幅值 = k·delta；delta 取决于装夹重复性
    #    测力噪声 2% f0；单次读数 vs 20 次平均
    d3 = {}
    for name, dist in (
        ("uniform_0_1mm", None),
        ("normal_0.2_0.02mm", None),
    ):
        if name.startswith("uniform"):
            dist = RNG.uniform(0, 1e-3, 20000)
        else:
            dist = np.clip(RNG.normal(0.2e-3, 0.02e-3, 20000), 0, None)
        vals = []
        for d in dist:
            f = n0 * (1e5 * d)
            eps = RNG.normal(0, 0.02 * F0, 12)
            vals.append(np.linalg.norm(P_N @ (f + eps)))
        vals = np.array(vals)
        d3[name] = {
            "p50_N": round(pct(vals, 50), 2),
            "p95_N": round(pct(vals, 95), 2),
            "cv": round(float(vals.std() / vals.mean()), 3),
            "noise_only_p50_N": round(pct([np.linalg.norm(P_N @ RNG.normal(
                0, 0.02 * F0, 12)) for _ in range(20000)], 50), 3),
        }
    out["d3_repeatability"] = d3

    # 7) D3 判据"刚性 ≥ 3× 柔性"：弹簧串联后传递内力的比例
    ratios = {}
    for ks in (1e3, 5e3, 1e4):
        ratio_t = ks / (1e5 + ks)
        ratios[f"spring_{int(ks)}"] = {
            "transmitted_fraction": round(float(ratio_t), 4),
            "rigid_over_spring": round(float(1 / ratio_t), 1),
            "passes_3x": bool(1 / ratio_t >= 3),
        }
    out["rigid_vs_spring_ratio"] = ratios

    # 8) 温度补偿后的残差：10 K 漂移若只做一阶温度项补偿，剩余多少
    #    假设补偿增益误差 10%，温度测量噪声 0.5 K
    comp = {}
    for dT in (10, 20):
        d = ALPHA_AL * dT * SIDE
        f_res = 1e5 * d * 0.10 + 1e5 * ALPHA_AL * SIDE * 0.5
        comp[f"dT_{dT}K"] = {
            "residual_N": round(float(f_res), 3),
            "vs_signal_10pct": round(float(f_res) / (0.10 * F0), 2),
        }
    out["thermal_compensation_residual"] = comp

    with open(r"D:\modular-uav-cooperative-survey\experiments\internal_force_identifiability_sim.json",
              "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

