# 22 投稿骨架与主张一致性审计

> **本章定位**：把 00–21 章收敛成一份"能写出来、能被审、能被复现"的投稿骨架。
> 它不引入新结果，只做三件事：把主张压成可检验的句子、把每个数字钉到源章节、
> 把审稿人最可能打的点提前列出来。
>
> **一句话主张**：在 ESP-NOW 级链路（250 kbps、20–50 Hz）上，刚性绑缚的多单旋翼
> 模块可以用"力残差 + 数据年龄"做低通信协同搬运与故障检测；但检测必须按物理时间
> 而不是通信节拍设计，且"内力可测"不等于"内力可分离"。

## 22.1 为什么现在写骨架

00–21 章已经覆盖：分类学与 gap（00–13）、可行性预算（14）、判别实验（15）、
检测与内力两条仿真结论（16、18–20）、公共方案（17）、回填路径（21）。继续加
章节不会让它更像论文——**缺的是把已有结论组装成一条审稿人能顺着读的证据链**。

骨架先写，有三个具体好处：

1. **暴露断链**：每条主张必须指向一个数字和一个章节。指不出来的主张，要么现在删，
   要么写进 Limitations——不能留到投稿时才发现没有支撑。
2. **约束后续实验**：D1–D3 回填的数据只允许改数字，不允许改主张结构；这样硬件到货
   后不会推翻重写。
3. **把"可复现"变成脚本**：`experiments/check_claims.py` 每次推送前跑一遍，
   骨架与正文数字分叉就非零退出。

## 22.2 摘要草稿

**中文（约 220 字）**

> 模块化无人机以单旋翼倾转模块为单元、以 ESP-NOW 组网、以绑缚方式协同搬运货物时，
> 通信带宽与数据年龄成为协同环的硬约束。本文用排队模型与蒙特卡洛给出这套硬件的
> 可行域：全广播 20 Hz 占空 30.7%，100 Hz 需 384 kbps 而不可实现；交付年龄 P95 约
> 8.2 ms，但陈旧度 P95 约 72 ms。在此基础上提出"力残差 + 原始残差并行 CUSUM"的
> 故障检测形态：20 Hz 检测 P95 为 158 ms，已超 150 ms 预算；改用原始 80 SPS 在
> σ=3% 下反而降到 138 ms。进一步证明 12 路测点约 69% 的原始力落在零空间，
> 装夹预紧与热漂移使"内力可分离"在工程上不成立，主张应收缩为"相对基线的残差检测"。
> 三个地面实验（D1–D3）以预注册判据决定主线取舍。

**English draft (≈170 words)**

> When modular UAVs — single-rotor tilting modules networked over ESP-NOW — cooperatively
> transport a rigidly bound payload, link capacity and data age, not control bandwidth,
> bound the coordination loop. Using a queueing model and Monte Carlo, we delimit the
> feasible region of this hardware: 20 Hz broadcast consumes 30.7% of the 250 kbps link,
> while 100 Hz would need 384 kbps and is infeasible; delivery age is 8.2 ms (P95), but
> staleness is 72 ms (P95). We then argue for a residual-force detector built as parallel
> CUSUMs on raw residuals: at 20 Hz the P95 detection time is 158 ms, exceeding the
> 150 ms budget, whereas raw 80 SPS sensing at σ=3% reduces it to 138 ms. We further show
> that ~69% of the 12 measured force channels lies in the null space, and that assembly
> preload and thermal drift make internal-force separation impractical; the claim must be
> narrowed to baseline-relative residual detection. Three ground experiments (D1–D3) with
> pre-registered criteria decide between the two candidate mainlines.

## 22.3 贡献—证据映射

编号 C1–C15 与 `experiments/paper_claims.json` 一一对应；`check_claims.py` 校验
"数字在源章节存在"且"本表同一行有同一数字"。

| 编号 | 可投稿主张 | 支撑 | 关键数字 | 证据等级 | 投稿前还缺什么 |
| --- | --- | --- | --- | --- | --- |
| C1 | ESP-NOW 全广播 20 Hz 占空 30.7%，是现实协同上限 | [14](14_feasibility_budget.md) 14.2 | 30.7% | 计算 | 抓包实测帧长与占空 |
| C2 | 100 Hz 全广播需 384 kbps，超 250 kbps 上限 | [14](14_feasibility_budget.md) 14.2 | 384 kbps | 计算 | 同 C1 |
| C3 | 20 Hz 交付年龄 P95 约 8.2 ms，链路不是瓶颈 | [18](18_data_age_sim.md) 18.3 | 8.2 | 仿真 | D1 实测 RTT/2 |
| C4 | 20 Hz 陈旧度 P95 约 72 ms（≈1.4T） | [18](18_data_age_sim.md) 18.4 | 72 ms | 仿真 | D1 端到端时间戳 |
| C5 | 100 Hz 排队发散，10 min 积压约 199 s | [18](18_data_age_sim.md) 18.3 | 199 | 仿真 | 长跑丢包率实测 |
| C6 | CUSUM h=8 时 ARL0=18792 样本，10 min 期望误报 0.6 次 | [15](15_experiment_protocols.md) 15.4 | 18792 | 仿真 | D2 空载误报计数 |
| C7 | σ=2% 时 20 Hz 检测 P95=158 ms，超预算 8 ms | [19](19_detection_budget.md) 19.4 | 158 | 仿真 | D2 实测 σ 与延迟 |
| C8 | σ=3% 下原始 80 SPS 把 P95 降到 138 ms | [19](19_detection_budget.md) 19.4 | 138 | 仿真 | 80 SPS 实测 |
| C9 | 四路平均对单模块故障是负收益（mean4 需 5 样本） | [16](16_force_residual_sim.md) 16.4 | 5 样本 | 仿真 | D2 12 通道相关矩阵 |
| C10 | 12 路测点约 69% 原始力落在零空间 | [20](20_internal_force_identifiability.md) 20.2 | 69% | 计算 | 实际结构刚度与装配 |
| C11 | 装夹预紧聚合内力可达故障信号 205.7 倍 | [20](20_internal_force_identifiability.md) 20.5 | 205.7 | 计算 | D3 装夹重复性 |
| C12 | 10 K 温升热漂移 13.8 N，约 28 倍信号 | [20](20_internal_force_identifiability.md) 20.5 | 13.8 | 计算 | 整机温漂实测 |
| C13 | D3 的 CV<10% 实为装夹重复性判据（57.4% vs 9.9%） | [20](20_internal_force_identifiability.md) 20.6 | 57.4% | 仿真 | D3 实测 CV |
| C14 | 150 ms 预算在 20 Hz 下只有 2.5 个检测周期 | [19](19_detection_budget.md) 19.2 | 2.5 | 计算 | 无 |
| C15 | 事件触发须带心跳：5 周期把陈旧度 214→96 ms | [18](18_data_age_sim.md) 18.5 | 96 | 仿真 | D1 触发率实测 |

**证据等级**只有两种：`计算`（参数代入即得，一条命令可复现）与`仿真`（固定种子
蒙特卡洛）。**没有一条是"硬件实测"**——这是本稿当前最大的软肋，也是 22.7 的第一条风险。

## 22.4 章节骨架

| Section | 内容 | 素材 | 图表 |
| --- | --- | --- | --- |
| 1 Introduction | 场景（单旋翼模块+绑缚货物+ESP-NOW）、问题、贡献三条 | 17.1、本章 22.2、[24](24_intro_related_prose.md) | Fig. 1 系统图 |
| 2 Related work | 模块化飞行器、协同搬运、低通信协同、故障检测 | 02–09、13、[23](23_related_work_table.md)、[24](24_intro_related_prose.md) | Table 1 对比表 |
| 3 System model | 力映射 τ=Gf、零空间、测量模型、链路与年龄、故障模型 | 17.4 | Fig. 2 分解图 |
| 4 Feasibility | 带宽/占空/年龄/传感链预算 | 14、18 | Table 2 预算；Fig. 3 队列 |
| 5 Detectability | 残差 CUSUM、ARL0、物理时间账、σ 与频率的权衡 | 15.4、16、19 | Fig. 4 延迟曲线 |
| 6 Identifiability | 零空间占比、装夹预紧、热漂移、D3 前置条件 | 20 | Fig. 5 内力分量 |
| 7 Methods | D1–D3 协议、预注册判据、回填流程 | 15、21 | Table 3 协议汇总 |
| 8 Results | D1–D3 实测（**当前空缺**） | runs/ | Table 4 结果 |
| 9 Discussion | A/B 决策、失败模式、与四旋翼模块的差异 | 14.7、17.9 | — |
| 10 Limitations | 无飞行实验、单平台、σ 假设、零空间不可分离 | 17.8、20.8 | — |

**两稿策略**（沿用 17.7）：主稿投 RA-L/T-RO，含 D1–D3 实测；支撑稿投 ICRA 短文，
只放"预算 + 检测形态 + 地面验证"。若硬件延期，支撑稿可以先投——但主稿不能。

## 22.5 图表清单

| 图/表 | 内容 | 数据来源 | 状态 |
| --- | --- | --- | --- |
| Fig. 1 | 系统与信息流（模块、UWB、ESP-NOW、绑缚） | 17.5 | 待画 |
| Fig. 2 | τ=Gf 的零空间分解示意 | 20.2 | 待画 |
| Fig. 3 | 10/20/50/100 Hz 的队列与陈旧度 | 18 | 脚本可出 |
| Fig. 4 | 检测延迟 vs σ、频率、h | 19 | 脚本可出 |
| Fig. 5 | 12 路力在载荷/零空间上的分量 | 20 | 脚本可出 |
| Fig. 6 | D1–D3 结果（空缺） | runs/ | 待硬件 |
| Table 1 | 43 篇最接近工作的六列对照（平台/通信/力感知/故障/差异） | [23](23_related_work_table.md) | 已可写 |
| Table 2 | 带宽与年龄预算 | 14、18 | 可写 |
| Table 3 | D1–D3 协议与通过线 | 15 | 可写 |
| Table 4 | 实测结果（空缺） | runs/ | 待硬件 |

## 22.6 目标 venue 与篇幅

| venue | 篇幅 | 匹配度 | 说明 |
| --- | --- | --- | --- |
| IEEE RA-L | 6 页 + 2 页 | 高 | 需要 D1–D3 实测；"低通信 + 力检测"落在其范围 |
| IEEE T-RO | 12–16 页 | 中高 | 适合放全部分类学与三实验；审稿周期长 |
| ICRA | 6 页 + 1 页 | 中 | 适合支撑稿；实测不足会被质疑 |
| ICUAS / IROS | 6–8 页 | 中 | 备选，社区更接受平台类贡献 |

判断：**RA-L 主稿 + ICRA 支撑稿**。理由：贡献是"可行域 + 检测形态 + 不可分离性"，
不是新算法；RA-L 对"把工程约束算清楚"的接受度高于 T-RO。

## 22.7 审稿风险（按被拒概率排序）

| # | 审稿人会说 | 现在的证据 | 补救 |
| --- | --- | --- | --- |
| 1 | "没有飞行实验，全是仿真与计算" | 无 | D1–D3 地面实测；先在支撑稿限定 claim |
| 2 | "σ=2%/3% 从哪来？" | 假设值，14.2 标注 | D2 实测 σ；给出整机振动谱 |
| 3 | "69% 零空间占比只对理想几何成立" | 20.3 证明 ≤2 mm 时误差 <0.02% | 补一次真实装配测量 |
| 4 | "和 Oishi/MARS 比，增量在哪？" | 17.1、22.3 | 明确"单旋翼+绑缚+内力不可分离"三点差异 |
| 5 | "150 ms 预算是谁定的？" | 14.6 给出闭环依据 | 补控制环带宽敏感性分析 |
| 6 | "D3 的 CV<10% 不可达" | 20.6 显示均匀装夹 57.4% | 把 D3 改成分级判据（先降装夹误差） |

## 22.8 投稿前检查清单

按顺序执行，任一步失败即停：

```bash
python experiments/check_claims.py          # 主张 ↔ 源章节 ↔ 骨架 数字一致
python experiments/check_related_table.py   # 表 1 引用编号与六列结构
python experiments/check_intro.py           # 24 章主张与引用编号
python experiments/check_submission.py      # 25 章 Highlights 字数/占位符/声明
python experiments/validate_runs.py         # runs/ 字段完整（无数据时退出 0）
python experiments/d2_detection_budget_sim.py   # 重跑 19 章数字（固定种子）
python experiments/internal_force_identifiability_sim.py  # 重跑 20 章数字
```

判据：

1. `check_claims.py` 退出 0，且新增主张必须同时进 JSON 与本表；
2. 14 章参数表里所有"假设/待实测"要么已回填、要么明确写进 Limitations；
3. 图 3/4/5 由脚本直接出图，不手工抄数；
4. D1–D3 的 JSON 与 meta 在 `runs/` 下可复算，`validate_runs.py` 退出 0；
5. 摘要里每个数字都能在本表找到编号。

## 22.9 本章结论与下一步

1. 骨架已完整，**唯一空缺是 Section 8（实测）**——这正好对应第 15/21 章的 D1–D3。
2. 主张从 15 条压到 12 条以内更稳：C3/C4 可合并为"两个年龄"，C7/C8 合并为
   "频率-σ 权衡"，C11/C12 合并为"预紧与热漂移"。
3. 下一步两条路：硬件到位 → 按 15/21 章做 D1–D3 并回填；硬件未到 → 用 [25](25_submission_package.md)
   的材料包先组装支撑稿（cover letter、Highlights、声明已写成模板）。

**本章不产生新数字**；`experiments/paper_claims.json` 与本节表格是同一事实的两种表示，
由 `experiments/check_claims.py` 强制同步。

