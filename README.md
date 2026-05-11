# Agent Workbench

1. 代码仓库自动诊断与修复 Agent
2. 海洋鱼类 YOLO 改进论文/实验自动化 Agent
3. 多模态检测框复核 Agent
4. 论文投稿合规检查 Agent
5. RL 实验自动调参/复现实验 Agent

## start

```bash
cd agent_workbench_project
python -m pip install -e .
python -m agent_workbench.cli repo-guardian --workspace examples/demo_workspace
python -m agent_workbench.cli research-factory --workspace outputs/ocean_yolo
```

## model

```bash
export OPENAI_API_KEY="key"
export AGENT_MODEL="gpt-4.1-mini"
python -m agent_workbench.cli research-factory --workspace outputs/ocean_yolo
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="你的key"
$env:AGENT_MODEL="gpt-4.1-mini"
python -m agent_workbench.cli research-factory --workspace outputs/ocean_yolo
```

## test

```bash
python -m pytest -q
```

## 设计特点

- 多 Agent 角色拆分：Intake、Planner、Builder、Evaluator、Reviewer。
- 内置 SQLite 记忆：保存每次任务、模型输出、工具调用与检查点。
- 工具注册机制：文件扫描、文本读写、grep、pytest/AST 检查、安全命令执行。
- 可恢复执行：每个阶段都会写入 checkpoint。
- 可审计输出：自动生成 `AGENT_REPORT.md`、`IMPLEMENTATION_PLAN.md`、`ABALATION_MATRIX.csv` 等文件。
