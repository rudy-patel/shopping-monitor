"""Guard scheduled job workflow YAML (T6.3)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

SCRAPE_CRON_UTC = "0 8 * * *"
DIGEST_CRON_UTC = "0 14 * * *"


def _load_workflow(filename: str) -> dict:
    path = REPO_ROOT / ".github" / "workflows" / filename
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{filename} must parse to a mapping"
    return data


def _workflow_triggers(workflow: dict) -> dict:
    """GitHub Actions uses `on:`; PyYAML may parse unquoted `on` as boolean True."""
    triggers = workflow.get("on")
    if triggers is None:
        triggers = workflow.get(True)
    assert isinstance(triggers, dict), "workflow triggers must be a mapping"
    return triggers


def _cron_expressions(workflow: dict) -> list[str]:
    on_block = _workflow_triggers(workflow)
    schedule = on_block.get("schedule", [])
    assert isinstance(schedule, list), "schedule must be a list"
    crons: list[str] = []
    for entry in schedule:
        if isinstance(entry, dict) and "cron" in entry:
            crons.append(str(entry["cron"]))
    return crons


@pytest.mark.parametrize(
    ("filename", "job_id", "worker_script", "expected_cron"),
    [
        ("scrape.yml", "scrape", "scrape_all.py", SCRAPE_CRON_UTC),
        ("digest.yml", "digest", "send_digests.py", DIGEST_CRON_UTC),
    ],
)
def test_scheduled_workflow_cron_dispatch_and_worker_env(
    filename: str,
    job_id: str,
    worker_script: str,
    expected_cron: str,
):
    workflow = _load_workflow(filename)
    on_block = _workflow_triggers(workflow)
    assert "workflow_dispatch" in on_block

    crons = _cron_expressions(workflow)
    assert crons == [expected_cron]

    job = workflow["jobs"][job_id]
    script_step = next(
        step for step in job["steps"] if step.get("run", "").endswith(worker_script)
    )
    assert script_step["env"]["BACKEND_BASE_URL"] == "${{ secrets.BACKEND_BASE_URL }}"
    assert script_step["env"]["WORKER_TOKEN"] == "${{ secrets.WORKER_TOKEN }}"
