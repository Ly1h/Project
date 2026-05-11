from __future__ import annotations

import csv
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .core import Agent, AgentState, MemoryStore
from .providers import build_provider
from .tools import build_default_registry


INTAKE_PROMPT = "You are an Intake Agent. Clarify task scope, constraints, risks and measurable success criteria."
PLANNER_PROMPT = "You are a Planner Agent. Produce milestones, dependencies, checkpoints and evaluation plan."
BUILDER_PROMPT = "You are a Builder Agent. Generate concrete artifacts and implementation steps."
EVALUATOR_PROMPT = "You are an Evaluator Agent. Run checks, define metrics, diagnose failures and summarize evidence."
REVIEWER_PROMPT = "You are a Reviewer Agent. Critique outputs for correctness, safety, reproducibility and missing work."


def _new_state(workspace: Path, goal: str) -> AgentState:
    workspace.mkdir(parents=True, exist_ok=True)
    return AgentState(run_id=str(uuid.uuid4()), workspace=workspace.resolve(), goal=goal)


@dataclass
class BaseWorkflow:
    workspace: Path
    goal: str

    def __post_init__(self) -> None:
        self.workspace = self.workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.memory = MemoryStore(self.workspace / ".agent_memory" / "memory.sqlite")
        self.tools = build_default_registry()
        self.provider = build_provider()
        self.agents = {
            "intake": Agent("IntakeAgent", INTAKE_PROMPT, self.provider, self.memory),
            "planner": Agent("PlannerAgent", PLANNER_PROMPT, self.provider, self.memory),
            "builder": Agent("BuilderAgent", BUILDER_PROMPT, self.provider, self.memory),
            "evaluator": Agent("EvaluatorAgent", EVALUATOR_PROMPT, self.provider, self.memory),
            "reviewer": Agent("ReviewerAgent", REVIEWER_PROMPT, self.provider, self.memory),
        }

    def _step(self, state: AgentState, phase: str) -> None:
        state.phase = phase
        self.memory.checkpoint(state)
        self.memory.log(state.run_id, phase, "phase.start", {"phase": phase})

    def run(self) -> AgentState:
        raise NotImplementedError


class RepoGuardianWorkflow(BaseWorkflow):
    """Multi-agent repo diagnosis workflow."""

    def run(self) -> AgentState:
        state = _new_state(self.workspace, self.goal)

        self._step(state, "intake")
        intake = self.agents["intake"].run(state, "将需求重写为可执行的工程检查任务，列出边界条件。")
        state.artifacts["intake"] = intake

        self._step(state, "scan")
        files = self.tools.call("list_files", workspace=str(self.workspace), pattern="*", limit=300)
        todos = self.tools.call("grep_text", workspace=str(self.workspace), regex=r"TODO|FIXME|HACK|XXX", limit=80)
        ast_result = self.tools.call("ast_check_python", workspace=str(self.workspace))
        pytest_result = self.tools.call("run_safe_command", workspace=str(self.workspace), command="python -m pytest -q", timeout=30)
        state.metrics.update({
            "file_count": files.metadata.get("count", 0),
            "todo_hits": todos.metadata.get("count", 0),
            "ast_ok": ast_result.ok,
            "pytest_ok": pytest_result.ok,
        })

        self._step(state, "plan")
        plan_instruction = (
            "基于以下扫描结果生成修复/重构计划：\n\n"
            f"Files:\n{files.output[:4000]}\n\n"
            f"TODO/FIXME:\n{todos.output[:4000]}\n\n"
            f"AST:\n{ast_result.output[:4000]}\n\n"
            f"Pytest:\n{pytest_result.output[:4000]}"
        )
        plan = self.agents["planner"].run(state, plan_instruction)
        state.artifacts["plan"] = plan

        self._step(state, "build_artifacts")
        report = f"""# Agent Repository Diagnosis Report

## Goal

{state.goal}

## Intake

{intake}

## Repository Scan

- File count: {state.metrics['file_count']}
- TODO/FIXME hits: {state.metrics['todo_hits']}
- AST check passed: {state.metrics['ast_ok']}
- Pytest passed: {state.metrics['pytest_ok']}

## TODO/FIXME Evidence

```text
{todos.output or 'No TODO/FIXME found.'}
```

## AST Check

```text
{ast_result.output}
```

## Test Output

```text
{pytest_result.output}
```

## Proposed Plan

{plan}
"""
        self.tools.call("write_text", workspace=str(self.workspace), path="AGENT_REPORT.md", content=report)
        state.artifacts["AGENT_REPORT.md"] = str(self.workspace / "AGENT_REPORT.md")

        self._step(state, "review")
        review = self.agents["reviewer"].run(state, "审查报告是否可执行、是否缺少测试证据、是否需要人工审批。")
        self.tools.call("write_text", workspace=str(self.workspace), path="IMPLEMENTATION_PLAN.md", content=plan + "\n\n" + review)
        state.artifacts["IMPLEMENTATION_PLAN.md"] = str(self.workspace / "IMPLEMENTATION_PLAN.md")
        state.artifacts["review"] = review
        self.memory.checkpoint(state)
        return state


class ResearchFactoryWorkflow(BaseWorkflow):
    """Generate heavy-workload research artifacts for a YOLO/multimodal/RL style project."""

    def run(self) -> AgentState:
        state = _new_state(self.workspace, self.goal)

        self._step(state, "intake")
        intake = self.agents["intake"].run(
            state,
            "提取研究问题、目标数据、基线、改进模块、消融实验、评估指标、论文产出。"
        )

        self._step(state, "plan")
        plan = self.agents["planner"].run(
            state,
            "设计一个工作量较大的AI科研/工程项目路线，必须包含数据、模型、训练、评估、论文写作、风险控制。"
        )

        self._step(state, "build_artifacts")
        ablations = [
            ["Experiment", "Backbone", "Neck/Head", "Data Aug", "Loss", "Metric", "Purpose"],
            ["E0-Baseline", "YOLOv8", "Default", "Default", "Default", "mAP50/F1/FPS", "原始基线"],
            ["E1-DyHead", "YOLOv8", "DyHead", "Default", "Default", "mAP50/F1/FPS", "验证动态检测头"],
            ["E2-LightConv", "YOLOv8", "DualConv", "Default", "Default", "Params/FLOPs/FPS", "验证轻量化"],
            ["E3-DataQA", "YOLOv8", "DyHead+DualConv", "Label-clean", "Default", "mAP50/F1", "验证数据质检收益"],
            ["E4-Full", "YOLOv8", "DyHead+DualConv", "Label-clean+Mosaic", "CIoU/Focal", "mAP50/F1/FPS", "完整模型"],
        ]
        ablation_path = self.workspace / "ABALATION_MATRIX.csv"
        with ablation_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(ablations)

        prompt_schema = {
            "project": "Ocean-YOLO-Agentic-Research-Factory",
            "agents": [
                {"name": "DataAuditor", "role": "检查标注缺失、类别不均衡、异常框和重复样本"},
                {"name": "ExperimentPlanner", "role": "生成训练矩阵、消融配置和资源排期"},
                {"name": "TrainRunner", "role": "调用训练脚本，记录日志、显存、速度和指标"},
                {"name": "MetricAnalyst", "role": "汇总Precision、Recall、mAP、FLOPs、FPS与误检漏检"},
                {"name": "PaperWriter", "role": "生成论文结构、图表说明和投稿检查清单"},
            ],
            "guardrails": [
                "所有训练配置写入版本化文件",
                "每个指标都必须绑定日志或评估脚本输出",
                "论文中不写无法复现实验的结论",
                "人工确认后才覆盖原始数据或模型权重"
            ],
        }
        self.tools.call(
            "write_text",
            workspace=str(self.workspace),
            path="PROMPT_SCHEMA.json",
            content=json.dumps(prompt_schema, ensure_ascii=False, indent=2),
        )

        paper_plan = f"""# Agentic Research Factory Plan

## Goal

{state.goal}

## Intake

{intake}

## Project Route

{plan}

## System Architecture

DataAuditor → ExperimentPlanner → TrainRunner → MetricAnalyst → PaperWriter → HumanReview

## Deliverables

1. 数据质检报告：类别分布、异常框、漏标风险、难例库。
2. 训练配置矩阵：baseline、单模块、双模块、完整模型。
3. 自动评估脚本：mAP50、Precision、Recall、F1、Params、FLOPs、FPS。
4. 论文材料：方法图、消融表、失败案例、投稿合规清单。
5. 复现实验包：config、logs、weights checksum、README。

## Human Review Points

- 是否允许重写标注文件。
- 是否允许覆盖模型权重。
- 是否将实验结果写入论文主表。
- 是否提交投稿版本。
"""
        self.tools.call("write_text", workspace=str(self.workspace), path="PAPER_PLAN.md", content=paper_plan)

        self._step(state, "evaluate")
        eval_text = self.agents["evaluator"].run(
            state,
            "给出该项目的评估方案，要求覆盖效果、效率、稳定性、人工节省量和论文可复现性。"
        )
        self.tools.call("write_text", workspace=str(self.workspace), path="EVALUATION_CHECKLIST.md", content=eval_text)

        self._step(state, "review")
        review = self.agents["reviewer"].run(state, "审查是否存在夸大成果、指标不可复现、缺少数据来源的问题。")
        self.tools.call("write_text", workspace=str(self.workspace), path="REVIEW.md", content=review)

        state.artifacts.update({
            "PAPER_PLAN.md": str(self.workspace / "PAPER_PLAN.md"),
            "ABALATION_MATRIX.csv": str(ablation_path),
            "PROMPT_SCHEMA.json": str(self.workspace / "PROMPT_SCHEMA.json"),
            "EVALUATION_CHECKLIST.md": str(self.workspace / "EVALUATION_CHECKLIST.md"),
            "REVIEW.md": str(self.workspace / "REVIEW.md"),
        })
        self.memory.checkpoint(state)
        return state
