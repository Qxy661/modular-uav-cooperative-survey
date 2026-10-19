# 25 投稿材料包（Cover Letter / Highlights / 声明 / 审稿问答）

> **本章定位**：22 章定了"投什么、缺什么"，24 章写好了正文前两节；本章补齐投稿时
> 随稿提交的四件套。全部内容**不依赖 D1–D3 实测**——Results 空缺时可以先投支撑稿，
> 但主稿的 cover letter 必须等实测数字，不能拿蒙特卡洛冒充硬件。
>
> 约束：所有数字仍只允许 C1–C15；`experiments/check_submission.py` 校验
> Highlights 字数（≤85）、主张编号、占位符与本文件内部链接。

## 25.1 Cover Letter（English draft，投 RA-L 用）

Dear Editor-in-Chief,

We are pleased to submit our manuscript, *Residual-Force Fault Detection for Modular
Single-Rotor Aerial Robots under Tight Link Budgets: What a 250 kbps Radio Can and Cannot
Support*, for consideration as a regular paper in IEEE Robotics and Automation Letters.

Modular aerial robots are usually studied with quadrotor modules and comfortable
communication budgets. We study the opposite corner: single-rotor tilting modules that
bind a payload rigidly and coordinate over ESP-NOW at a practical ceiling of 250 kbps.
The paper makes three contributions. First, it gives a reproducible feasibility budget
for this hardware: full broadcast at 20 Hz already consumes 30.7% of the link, 100 Hz
would require 384 kbps, and a 20 Hz controller sees a delivery age of 8.2 ms but a
staleness of 72 ms — two quantities that the literature often conflates. Second, it
formulates fault detection in physical time rather than in communication ticks: a bank
of parallel CUSUMs on raw force residuals, fused by an OR rule, with an independent
force-plate arbiter. Averaging the four modules is shown to halve the SNR for a
single-module fault, while an OR rule costs about one sample. Third, it bounds what
rigidly bound force sensing can support: about 69% of the raw 12-channel force vector
lies in the six-dimensional null space, and assembly preload (up to 205.7x the 10% fault
signal) and thermal drift (13.8 N at 10 K) dominate it, so internal-force control cannot
be claimed; baseline-relative residual detection can.

We believe the negative result is a feature rather than a weakness: it turns an
attractive but unsupported claim into two falsifiable ground experiments with
pre-registered criteria. The manuscript is accompanied by a public repository containing
the survey, the numerical pre-studies, the experiment protocols, and the validation
scripts that check every number and citation. No part of this work is under review
elsewhere, all authors approved the submission, and we declare no competing interests.

Sincerely,
The Authors

## 25.2 Highlights（5 条，每条 ≤85 字符；RA-L/Elsevier 格式）

- ESP-NOW broadcast at 20 Hz is the practical coordination ceiling (30.7% duty).
- Rigid binding puts 69% of force in a null space; internal-force control fails.
- Parallel raw-residual CUSUMs beat four-module averaging for single-module faults.
- At 20 Hz, P95 detection is 158 ms, over the 150 ms budget; 26.7 Hz meets it.
- Raw 80 SPS force sampling cuts P95 detection to 138 ms at 3% noise.

> 中文对照（不进投稿件）：①20 Hz 广播是这套硬件的协同上限；②刚性绑缚下 69% 的力
> 落零空间，内力控制不成立；③单模块故障检测用并行原始残差 CUSUM，四路平均是负收益；
> ④20 Hz 的 P95 检测 158 ms 超预算，26.7 Hz 才够；⑤原始 80 SPS 在 σ=3% 时把 P95
> 降到 138 ms。

## 25.3 声明的四个模板

**Author contributions（CRediT）**：Conceptualization, A.B.; methodology, A.B. and
C.D.; software, A.B.; validation, A.B. and C.D.; formal analysis, A.B.; investigation,
A.B. and C.D.; data curation, A.B.; writing—original draft, A.B.; writing—review and
editing, all authors; visualization, A.B.; supervision, C.D.; funding acquisition, C.D.

**Competing interests**：The authors declare no competing interests. The load cells,
ESP32-S3 modules, and force plate used in the protocols are commercially available; no
manufacturer influenced the design or the reporting.

**Data availability**：All code, protocols, and numerical pre-studies are public at
`https://github.com/Qxy661/modular-uav-cooperative-survey`. The D1–D3 measurement data
will be released as JSON Lines (JSONL; `runs/<exp>_<date>_<cond>_r<k>.jsonl` plus a run-level
`meta.json`) under the schema in [21](21_backfill_playbook.md); `experiments/validate_runs.py`
is the acceptance gate (missing fields exit non-zero) and `docs/21` Section 21.4 maps
each field to the claim it supports.

**Funding / ethics**：Funding: [grant number]. Ethics: no human or animal subjects; the
experiments involve only small aerial modules on a tethered indoor bench, following the
laboratory's rotor-safety procedure.

## 25.4 审稿人最可能问的 6 个问题 + 预备回答

**Q1. 这是不是一篇"调研 + 可行性说明"，缺少硬件结果？**
A: 现稿是方法 + 预算 + 可执行协议；D1–D3 的判据、数据格式、分析脚本均已预注册
（15、21 章）。支撑稿（预算 + 检测形态 + 地面验证）可先投；主稿的 Table 4 必须由
`runs/` 生成，我们不把蒙特卡洛当实测（22.7）。

**Q2. 缆绳悬挂已经能低通信协同，为什么还要刚性绑缚？**
A: 缆绳张力是可直接测的标量，刚性绑缚则把载荷份额、结构内力、装配应力叠在同一个
读数里。本文量化了叠加中不可分的那部分（C10–C13），并给出它对应的可做与不可做。
货物类型（箱体、传感器桅杆）需要刚性连接，这不是可替换的设定。

**Q3. 250 kbps 与有效吞吐 100–250 kbps 是假设，结论是否依赖它？**
A: 250 kbps 是 ESP-NOW 文档上限（事实）；有效吞吐给出 100–250 kbps 区间，预算表
按两端都算过，结论（20 Hz 可行、50 Hz 紧张、100 Hz 不可行）在区间内不变（C1/C2/C5）。
D1 的第一项就是把有效吞吐实测出来并回填 21 章参数台账。

**Q4. 检测延迟为何不是实测？**
A: 是固定种子的蒙特卡洛上界（C7/C8），依赖 σ 与链路参数；D2 用双模块台架与 CUSUM
复测，判据已预注册（中位与 P95 <150 ms、σ>2% 判不通过）。若实测更差，降到 26.7 Hz
或原始 80 SPS 的路径已在 19 章给出，不需要重做理论。

**Q5. 为什么用单旋翼倾转模块而不是四旋翼模块？**
A: 单旋翼模块的可行力集合随倾角变化，载荷分配的可行域不再近似常数（17.4）；这是
B 主线的分叉点，也是本文把"构型—分配"一起处理的原因。四旋翼模块的结论不能直接搬。

**Q6. 你们说内力不可分离，是否与"力感知降低通信依赖"矛盾？**
A: 不矛盾。降低通信依赖用的是**外部力旋量**（载荷份额），它在 12 路测量里是可分的；
不可分的是零空间分量（结构内力）。我们把这两件事分开命名，并在 20.3 给出判据：
载荷份额误差 ≤0.02%，零空间分量误差可到 100%。

## 25.5 投稿前检查清单（每条一个命令）

| 检查 | 命令 | 期望 |
| --- | --- | --- |
| 主张-正文一致 | `python experiments/check_claims.py` | 退出 0 |
| Table 1 结构与引用 | `python experiments/check_related_table.py` | 退出 0 |
| 引言主张/引用编号 | `python experiments/check_intro.py` | 退出 0 |
| 本材料包 | `python experiments/check_submission.py` | 退出 0 |
| 数据验收 | `python experiments/validate_runs.py` | 有数据时退出 0；无数据时 0 并提示 |
| 文档与内链 | `bash scripts/check_docs.sh`（若无则按 25.6 手工） | 0 断链、引用 1–86 |

## 25.6 缺口（诚实版）

1. **D1–D3 实测**：Results 章、Fig. 6、Table 4 全部空缺；没有它主稿不能投。
2. **Fig. 1 系统图未画**：Introduction 第 1 段需要引用；建议用 draw.io 画模块/链路/传感三栏。
3. **作者与单位**：25.1 与 25.3 用 A.B./C.D. 占位，投稿前必须换真人；`check_submission.py`
   会拦常见的占位标记与空字段，但拦不住"占位姓名还没换"。
4. **License**：仓库目前无 LICENSE；公开代码前要定 MIT/Apache-2.0（与"数据待发表后释放"不冲突）。
