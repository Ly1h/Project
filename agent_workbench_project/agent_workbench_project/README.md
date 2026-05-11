# Agent Workbench

一个可直接运行的多 Agent 工作台原型，适合扩展成：

1. 代码仓库自动诊断与修复 Agent
2. 海洋鱼类 YOLO 改进论文/实验自动化 Agent
3. 多模态检测框复核 Agent
4. 论文投稿合规检查 Agent
5. RL 实验自动调参/复现实验 Agent

默认使用 `MockLLMProvider`，没有 API Key 也能跑通完整流程；配置 `OPENAI_API_KEY` 后，可替换为真实模型调用。

## 快速开始

```bash
cd agent_workbench_project
python -m pip install -e .
python -m agent_workbench.cli repo-guardian --workspace examples/demo_workspace --goal "检查这个仓库的测试、TODO和潜在工程问题"
python -m agent_workbench.cli research-factory --workspace outputs/ocean_yolo --goal "构建海洋鱼类YOLO改进论文的实验计划和消融矩阵"
```

## 使用真实模型

```bash
export OPENAI_API_KEY="你的key"
export AGENT_MODEL="gpt-4.1-mini"
python -m agent_workbench.cli research-factory --workspace outputs/ocean_yolo --goal "构建海洋鱼类YOLO改进论文的实验计划和消融矩阵"
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="你的key"
$env:AGENT_MODEL="gpt-4.1-mini"
python -m agent_workbench.cli research-factory --workspace outputs/ocean_yolo --goal "构建海洋鱼类YOLO改进论文的实验计划和消融矩阵"
```

## 运行测试

```bash
python -m pytest -q
```

## 设计特点

- 多 Agent 角色拆分：Intake、Planner、Builder、Evaluator、Reviewer。
- 内置 SQLite 记忆：保存每次任务、模型输出、工具调用与检查点。
- 工具注册机制：文件扫描、文本读写、grep、pytest/AST 检查、安全命令执行。
- 可恢复执行：每个阶段都会写入 checkpoint。
- 可审计输出：自动生成 `AGENT_REPORT.md`、`IMPLEMENTATION_PLAN.md`、`ABALATION_MATRIX.csv` 等文件。
- 支持无模型跑通，便于课堂展示、面试演示和后续替换为 LangGraph/CrewAI/OpenAI Agents SDK 等框架。
