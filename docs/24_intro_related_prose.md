# 24 Introduction 与 Related Work 文字稿

> **本章定位**：23 章给了表格，但主稿第 1–2 节要的是文字。本章按 RA-L 的写法给出
> English 草稿（投稿版直接用），中文要点放前面供你审。**所有数字都必须带主张编号
> （C1–C15），编号对应 `experiments/paper_claims.json`**；本章不引入新数字，
> `experiments/check_intro.py` 校验这一点。

## 24.1 写作约束（先看这三条）

1. **claim 只允许 C1–C15**。任何数字若不在 `paper_claims.json` 里，先加主张、再写句子；
   不允许"顺手"写一个没进审计表的数。
2. **不写"first/novel"**。审稿人最烦没有检索支撑的"首次"；本文的差异用"四条同时成立"
   的覆盖论证（23.2），而不是"无人做过"。
3. **负面结论要写在贡献里**，不要藏进 Discussion。"69% 落在零空间 / 装夹预紧 205.7 倍"
   是本文最硬的结果，也是 claim 收缩的依据。

## 24.2 中文要点（审稿时看这段即可）

- **场景**：模块 = 单旋翼倾转 + 飞控 + UWB + 测力计 + ESP32-S3；模块间 ESP-NOW；
  货物**刚性绑缚**；目标是协同搬运 + 故障后继续。
- **问题**：协同环频率受限于链路（C1、C2），而"数据年龄"被多数工作当成一个数
  （C3、C4）；故障检测又默认通信节拍足够（C7、C14）。
- **核心判断**：力是**额外的、不占带宽的**信息通道；但刚性绑缚下 12 路测力里 69%
  落在零空间（C10），装夹与温漂比故障信号大 1–2 个量级（C11、C12）——所以只能做
  "相对基线的残差检测"，不能声称"内力控制"。
- **贡献三条**：① 这套硬件的可行域（带宽/年龄/检测预算，C1–C8、C14、C15）；
  ② 原始残差并行 CUSUM + 力台仲裁的检测形态（C6、C9）；③ 内力可分离性的工程上界
  与据此的 claim 收缩（C10–C13）。

## 24.3 Introduction（English draft，投稿版）

**Title (working):** *Residual-Force Fault Detection for Modular Single-Rotor Aerial
Robots under Tight Link Budgets: What a 250 kbps Radio Can and Cannot Support*

**Abstract.** See [22.2](22_submission_skeleton.md) (the abstract already uses C1–C15;
do not fork it here).

**1. Introduction**

Modular aerial robots promise to reconfigure in flight and to carry payloads that no
single vehicle can lift. A particularly attractive instance is a team of *single-rotor
tilting modules* — each carrying its own flight controller, ultra-wideband (UWB) ranging
radio, load cell, and ESP32-S3 — that bind a payload rigidly and fly it cooperatively.
The hardware is cheap, the modules are interchangeable, and the payload can be anything
from a box to a sensor mast. The same properties, however, turn the coordination problem
into a communication problem: the modules must exchange state over ESP-NOW, whose
practical ceiling is 250 kbps, while the payload dynamics demand a coordination loop in
the tens of hertz.

This paper asks two coupled questions. First, *what coordination rate does this hardware
actually support?* We answer with an explicit budget: full broadcast at 20 Hz already
consumes 30.7% of the link (C1), and 100 Hz would require 384 kbps (C2), i.e., it is
infeasible rather than merely expensive. The link is not the only clock: 20 Hz gives a
delivery age of 8.2 ms (P95) but a staleness of 72 ms (P95), because the controller can
only use the most recent frame (C3, C4). Reporting a single "age" hides a factor of
almost two — a distinction that matters directly for fault detection.

Second, *can force sensing substitute for bandwidth?* In principle, each module's load
cell measures how much of the payload it carries, so coordination could be largely
implicit; this is the mechanism exploited by cable-suspended teams. With a rigidly
bound payload the situation is different: the force map from module thrusts to payload
wrench has a six-dimensional null space, and about 69% of the raw 12-channel force
vector lies in it (C10). Assembly preload and thermal drift dominate that null-space
component — up to 205.7× and 13.8 N respectively, against a 0.49 N signal for a 10%
thrust loss (C11, C12). Internal forces are therefore measurable but not separable in
practice, and a paper that claims internal-force control from these sensors would be
overclaiming.

These two observations lead to a detection-oriented design. We show that a bank of
parallel CUSUMs on *raw* residuals, plus an independent force-plate channel, is the
right shape: averaging the four modules halves the signal-to-noise ratio for a
single-module fault (C9), whereas a per-module detector with an OR rule costs about one
sample. Detection time, however, must be accounted in physical time, not in
communication ticks: the 150 ms budget leaves only 2.5 detection cycles at 20 Hz (C14),
and the P95 detection time is 158 ms (C7), already over budget. Two fixes work: raise
the detection rate to 26.7 Hz, or use raw 80 SPS sensing, which at σ = 3% reduces the
P95 to 138 ms (C8). Frequency reduction by averaging is a net loss for detection.

**Contributions.** (i) A reproducible feasibility budget for modular single-rotor
transport over ESP-NOW, separating delivery age from staleness and identifying 20 Hz
broadcast as the practical coordination ceiling (C1–C5, C15). (ii) A residual-force
detection formulation with a physical-time accounting: parallel raw-residual CUSUMs,
OR fusion across modules, and a force-plate arbiter (C6, C7, C9). (iii) An engineering
bound on internal-force identifiability — null-space share, preload, thermal drift, and
the resulting repeatability requirement for the rigid-vs-flexible experiment — which
narrows the claim to baseline-relative residual detection (C10–C13).

The remainder of the paper is organized as follows. Section 2 reviews modular platforms,
cooperative transport, low-communication coordination, and fault detection. Section 3
states the system model and the link/age model. Section 4 gives the feasibility budget;
Section 5 the detection formulation and its physical-time budget; Section 6 the
identifiability analysis. Section 7 describes the three ground experiments (D1–D3),
Section 8 reports them, and Sections 9–10 discuss and bound the claims.

## 24.4 Related Work（English draft，每族一段）

**Modular and reconfigurable aerial robots.** The field has converged on a three-layer
recipe — abstraction, allocation, planning. Virtual-rigid-body abstractions map a
configuration to a force-wrench polytope so that one controller transfers across
configurations [4], and fully-actuated modular platforms extend the same idea to
tilting rotors [2]. Universal attachment lets arbitrary rigid objects fly [3], while
self-reconfiguration plans disassembly sequences through controllable intermediate
states [6, 7]. Docking and self-assembly add contact-force control [8]. What these
systems share is a quadrotor module whose feasible wrench set is nearly constant; a
single-rotor tilting module has a feasible set that depends on the tilt angle, and none
of these works considers a rigidly bound payload or a kbps-scale link. Our abstraction
and allocation therefore keep the three-layer structure but re-derive the feasible set
as a function of configuration and tilt.

**Cooperative transport and load sharing.** Grasp-matrix allocation is the reference
framework: given a desired payload wrench, distribute it across robots while separating
external and internal forces [9]. Single-rotor teams have demonstrated that unknown
payloads can be carried with decentralized control, including after a robot failure
[10–12], and layout co-design shows that attachment geometry should be optimized rather
than compensated [17]. Cable-suspended teams go further in communication efficiency:
local cable-force estimates support implicit coordination with only neighbor broadcasts
[14], and dissipative mechanics can stabilize a swarm with no explicit communication
[15]. Learned policies remove the model but not the sensing [16]. The gap is
mechanical: a cable tension is a directly measured scalar, whereas a rigidly bound
payload makes each load cell report the sum of load share, structural internal force,
and assembly stress. Our Section 6 quantifies exactly how much of that sum is
unidentifiable.

**Low-communication coordination.** Networked control theory already treats sampling,
delay, and loss jointly [18], and middleware-level work reduces delay and jitter [19],
raises throughput through concurrent transmission [20], or adds coding for reliability
[21]. Event-triggered communication has been combined with reinforcement learning and
consensus for cooperative transport [82, 83]. These results are mostly
communication-side; what is missing is the *control-side* accounting: how many
detection samples fit into a 150 ms budget at a given rate, and what staleness the
controller must assume. Our queueing model (Section 3) and detection budget
(Section 5) close that loop for a concrete ESP-NOW stack, including the
counter-intuitive result that 100 Hz diverges rather than merely degrading (C5).

**Fault detection and resilience.** Resilience taxonomies emphasize measurable recovery
[34], fault-tolerant control assumes the fault is already identified [5, 6, 7, 35], and
residual-wrench certification computes what authority remains under actuator limits
[85]; learned external-wrench estimation separates unknown disturbances from the
residual [86]. UWB ranging and relative localization supply the geometric channel
[22–25], but their sampling limits are rarely folded into the coordination loop. None
of these works budgets *detection latency* against a physical fault budget, and none
reports the null-space share that constrains rigidly bound force sensing. Our
contribution is to make that budget explicit and to show where the claim must stop.

## 24.5 术语表（中英对照，写作时统一）

| 中文 | English | 备注 |
| --- | --- | --- |
| 模块 / 单旋翼倾转模块 | module / single-rotor tilting module | 不写 "drone" |
| 刚性绑缚 | rigidly bound payload | 不用 "rigid attachment"（易与对接混淆） |
| 交付年龄 | delivery age | 生成→接收 |
| 陈旧度 | staleness | 控制器所用帧的年龄 |
| 残差 | residual | 力残差 = 实测 − 模型预测 |
| 零空间 | null space | 6 维，结构内力 |
| 装夹预紧 | assembly preload | 不用 "clamping force" |
| 检测节拍 | detection rate / tick | 与通信节拍区分 |
| 力台仲裁 | force-plate arbiter | D2 的独立通道 |

## 24.6 待办（投稿前）

1. 把 `[4]`、`[10–12]` 等编号换成 venue 要求的引用格式（当前与 `references.md` 一致）；
2. 图 1（系统图）未画，Introduction 第 1 段末尾需要引用它；
3. 摘要与 24.3 的贡献段必须逐字一致（否则 `check_claims` 查不出分叉，但审稿人会看出来）；
4. 若 D1–D3 出数，C7/C8/C9 的数字全部换成实测，**先改 `paper_claims.json` 与 22/23 章，
   再改本章**——顺序反了会出现两个版本。
