from pathlib import Path

from agent_workbench.workflows import RepoGuardianWorkflow, ResearchFactoryWorkflow


def test_repo_guardian(tmp_path: Path):
    (tmp_path / "app.py").write_text("def add(a,b):\n    # TODO: refine\n    return a+b\n", encoding="utf-8")
    (tmp_path / "test_app.py").write_text("from app import add\n\ndef test_add():\n    assert add(1,2)==3\n", encoding="utf-8")
    state = RepoGuardianWorkflow(tmp_path, "检查仓库").run()
    assert (tmp_path / "AGENT_REPORT.md").exists()
    assert state.metrics["file_count"] >= 2


def test_research_factory(tmp_path: Path):
    state = ResearchFactoryWorkflow(tmp_path, "海洋鱼类YOLO改进论文").run()
    assert (tmp_path / "PAPER_PLAN.md").exists()
    assert (tmp_path / "ABALATION_MATRIX.csv").exists()
    assert "PAPER_PLAN.md" in state.artifacts
