from __future__ import annotations

from typing import TYPE_CHECKING

from tpms_utility.models import CycleRuntime

if TYPE_CHECKING:
    from tpms_utility.cycle_controller import CycleController


class DltActions:
    def __init__(self, controller: CycleController) -> None:
        self.controller = controller

    def action_start_logging(self, runtime: CycleRuntime) -> None:
        self.controller.dlt.disconnect()
        self.controller.dlt.connect(self.controller.dlt_settings)
        self.controller.dlt.set_logging_profile(self.controller.dlt_settings.logging_profile_id)
        self.controller.dlt.start_logging(runtime.temp_log_path)
        self.controller.on_log(
            "DLT logging started: "
            f"{self.controller.dlt_settings.hostname}:{self.controller.dlt_settings.port}, "
            f"tmp file {runtime.temp_log_path}"
        )

    def action_clear_start_test(self, runtime: CycleRuntime) -> None:
        self.controller.dlt.clear_tmp_log()
        self.controller.on_log(f"Temporary log cleared: {runtime.temp_log_path}")
        self.controller.audio.beep_once()
        with self.controller._state_lock:
            self.controller._fault_tokens_seen.clear()
            self.controller._total_duration_seconds = self.controller.app_settings.test_duration_seconds
        self.controller.dlt.clear_payload_callbacks()
        self.controller.dlt.register_payload_callback(self.controller._on_payload)
        self.controller._start_timer(runtime)
        with self.controller._state_lock:
            total_duration = self.controller._total_duration_seconds
        self.controller.on_log(f"Test timer started: {total_duration} seconds")

    def action_filter_export(self, runtime: CycleRuntime) -> None:
        with self.controller._state_lock:
            finished = self.controller._finished
        if not finished:
            raise RuntimeError("Cannot export yet. Stage 5 timer is still running.")
        tawm_dlt_path = runtime.final_log_path.parent / self.controller.app_settings.tawm_export_template.format(
            timestamp=runtime.run_timestamp
        )
        tawm_lib_ascii_path = runtime.final_log_path.parent / self.controller.app_settings.tawm_lib_export_template.format(
            timestamp=runtime.run_timestamp
        )
        self.controller.exporter.export_filtered_dlt(runtime.final_log_path, tawm_dlt_path, app_id="Tawm")
        self.controller.exporter.export_filtered_ascii(
            runtime.final_log_path,
            tawm_lib_ascii_path,
            app_id="Tawm",
            ctx_id="LIB",
        )
        self.controller.on_log(f"Exported DLT filter file: {tawm_dlt_path}")
        self.controller.on_log(f"Exported ASCII filter file: {tawm_lib_ascii_path}")
