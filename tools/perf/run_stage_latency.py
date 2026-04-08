from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time

from tpms_utility.config import AppSettings, DltConnectionSettings
from tpms_utility.cycle_controller import CycleController
from tpms_utility.models import Stage
from tpms_utility.stages.default_cycle import build_default_cycle


def parse_stage_list(value: str) -> list[int]:
    if not value.strip():
        return [0, 1, 3, 4]
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def run_once(controller: CycleController, stage_map: dict[int, Stage], stage_ids: list[int]) -> dict[int, float]:
    runtime = controller.runtime_context()
    latencies: dict[int, float] = {}

    for stage_id in stage_ids:
        stage = stage_map[stage_id]
        if stage.action is None:
            continue

        start = time.perf_counter()
        stage.action(runtime)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        latencies[stage_id] = round(elapsed_ms, 3)

    return latencies


def summarize(records: list[dict[int, float]], stage_ids: list[int]) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}

    for stage_id in stage_ids:
        values = [entry[stage_id] for entry in records if stage_id in entry]
        if not values:
            continue
        summary[str(stage_id)] = {
            "count": float(len(values)),
            "min_ms": round(min(values), 3),
            "max_ms": round(max(values), 3),
            "avg_ms": round(sum(values) / len(values), 3),
        }

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run stage-level latency timing against configured endpoints.")
    parser.add_argument("--iterations", type=int, default=5, help="Number of repeated runs.")
    parser.add_argument(
        "--stages",
        type=str,
        default="0,1,3,4",
        help="Comma-separated stage IDs to execute in order.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output") / "perf" / "stage_latency.json",
        help="Output file path for metrics JSON.",
    )
    args = parser.parse_args()

    app_settings = AppSettings()
    dlt_settings = DltConnectionSettings()

    logs: list[str] = []
    controller = CycleController(
        stages=[],
        app_settings=app_settings,
        dlt_settings=dlt_settings,
        on_state_changed=lambda: None,
        on_log=lambda message: logs.append(message),
        on_timer_changed=lambda _: None,
    )

    stages = build_default_cycle(controller)
    stage_map = {stage.stage_id: stage for stage in stages}
    selected_stages = parse_stage_list(args.stages)

    for stage_id in selected_stages:
        if stage_id not in stage_map:
            raise ValueError(f"Unknown stage ID: {stage_id}")
        if stage_map[stage_id].action is None:
            raise ValueError(f"Stage {stage_id} has no executable action")

    records: list[dict[int, float]] = []

    try:
        for _ in range(args.iterations):
            controller.reset_cycle()
            records.append(run_once(controller, stage_map, selected_stages))
    finally:
        controller.stop()

    output = {
        "iterations": args.iterations,
        "stages": selected_stages,
        "app_settings": asdict(app_settings),
        "dlt_settings": asdict(dlt_settings),
        "records_ms": records,
        "summary_ms": summarize(records, selected_stages),
        "log_tail": logs[-30:],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=True, default=str), encoding="utf-8")
    print(f"Wrote stage latency report to {args.output}")


if __name__ == "__main__":
    main()
