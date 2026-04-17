from __future__ import annotations

from datetime import datetime
import importlib
from pathlib import Path
import subprocess
import threading
from typing import Callable
import urllib.error
import urllib.request
import json

from tpms_utility.config import AppSettings, DltConnectionSettings
from tpms_utility.models import CycleRuntime, Stage
from tpms_utility.services.audio_service import AudioService
from tpms_utility.services.dlt_service import DltService
from tpms_utility.services.log_exporter import LogExporter
from tpms_utility.services.swut_service import SwutService


class CycleController:
    def __init__(
        self,
        stages: list[Stage],
        app_settings: AppSettings,
        dlt_settings: DltConnectionSettings,
        on_state_changed: Callable[[], None],
        on_log: Callable[[str], None],
        on_timer_changed: Callable[[int], None],
    ) -> None:
        self.stages = stages
        self.app_settings = app_settings
        self.dlt_settings = dlt_settings
        self.on_state_changed = on_state_changed
        self.on_log = on_log
        self.on_timer_changed = on_timer_changed

        self.current_index = 0
        self.runtime: CycleRuntime | None = None
        self.swut = SwutService(output_dir=Path("output"), mock_url=self.app_settings.swut_mock_url)
        self.dlt = DltService()
        self.audio = AudioService()
        self.exporter = LogExporter()

        self._timer_thread: threading.Thread | None = None
        self._timer_stop_event = threading.Event()
        self._state_lock = threading.Lock()
        self._fault_tokens_seen: set[str] = set()
        self._total_duration_seconds = self.app_settings.test_duration_seconds
        self._finished = False

    def resolve_stage_action(self, action_name: str | None) -> Callable[[CycleRuntime], None] | None:
        if action_name is None:
            return None

        action_map: dict[str, Callable[[CycleRuntime], None]] = {
            "init": self.action_init,
            "overwrite_wuids": self.action_overwrite_wuids,
            "enter_debug": self.action_enter_debug,
            "start_logging": self.action_start_logging,
            "clear_start_test": self.action_clear_start_test,
            "filter_export": self.action_filter_export,
        }
        try:
            return action_map[action_name]
        except KeyError as exc:
            known_actions = ", ".join(sorted(action_map))
            raise ValueError(f"Unknown stage action '{action_name}'. Known actions: {known_actions}") from exc

    @property
    def current_stage(self) -> Stage:
        return self.stages[self.current_index]

    @property
    def is_test_finished(self) -> bool:
        with self._state_lock:
            return self._finished

    def reset_cycle(self) -> None:
        self.current_index = 0
        self.runtime = None
        self._timer_stop_event.set()
        self.dlt.disconnect()
        with self._state_lock:
            self._fault_tokens_seen.clear()
            self._total_duration_seconds = self.app_settings.test_duration_seconds
            self._finished = False
        self.dlt.clear_payload_callbacks()
        self.on_timer_changed(0)
        self.on_state_changed()
        self.on_log("Cycle reset to stage 0")

    def advance_by_space(self) -> None:
        stage = self.current_stage
        stage_index = self.current_index
        self.on_log(f"Space pressed on stage {stage.stage_id}: {stage.name}")
        try:
            if stage.action:
                stage.action(self.runtime_context())
        except Exception:
            self.current_index = stage_index
            self.on_state_changed()
            self.on_log(
                f"Stage {stage.stage_id} halted. Press SPACE again to re-run stage {stage.stage_id} from start."
            )
            raise
        self.current_index += 1
        if self.current_index >= len(self.stages):
            self.current_index = 0
        self.on_state_changed()

    def runtime_context(self) -> CycleRuntime:
        if self.runtime is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_root = self.app_settings.output_root
            output_root.mkdir(parents=True, exist_ok=True)
            self.runtime = CycleRuntime(
                cycle_started_at=datetime.now(),
                run_timestamp=timestamp,
                temp_log_path=output_root / self.app_settings.temp_log_template.format(timestamp=timestamp),
                final_log_path=output_root / self.app_settings.final_log_template.format(timestamp=timestamp),
            )
        return self.runtime

    def action_init(self, _: CycleRuntime) -> None:
        self.on_log("Stage 0 init: ready for test cycle")

    def action_overwrite_wuids(self, _: CycleRuntime) -> None:
        commands = [
            "1D12 1003",
            "1D12 2717",
            "1D12 2705",
            "1D12 2E20EB20000001200000022000000320000004",
        ]
        results = self.swut.run_batch(commands)
        self._log_swut_test_results(results)
        failures = [result for result in results if not result.success]
        if failures:
            self.on_log("❌ Stage 1 halted: SWUT test failure detected; stage will not advance")
            raise RuntimeError(f"Stage 1 failed: {failures[0].command} -> {failures[0].details}")

    def action_enter_debug(self, _: CycleRuntime) -> None:
        self._restart_tawm_in_hpa()
        commands = ["1D12 2705", "1D12 3101DF04"]
        results = self.swut.run_batch(commands)
        self._log_swut_test_results(results)
        failures = [result for result in results if not result.success]
        if failures:
            self.on_log("❌ Stage 3 halted: SWUT test failure detected; stage will not advance")
            raise RuntimeError(f"Stage 3 failed: {failures[0].command} -> {failures[0].details}")

    def _log_swut_test_results(self, results: list) -> None:
        for result in results:
            mark = "✅" if result.success else "❌"
            verdict = "PASS" if result.success else "FAIL"
            self.on_log(f"{mark} SWUT test {verdict}: {result.command} -> {result.details}")

    def _restart_tawm_in_hpa(self) -> None:
        self.on_log("Restarting Tawm in HPA via SSH hop (SGA -> VCU)")

        if self.app_settings.ssh_mock_url:
            self._restart_tawm_via_mock()
            self.on_log("Tawm restart command completed via SSH mock endpoint")
            return

        if self.app_settings.sga_password or self.app_settings.vcu_password:
            self._restart_tawm_with_passwords()
            self.on_log("Tawm restart command completed and SSH session closed")
            return

        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={self.app_settings.ssh_timeout_seconds}",
            f"{self.app_settings.sga_user}@{self.app_settings.sga_host}",
            (
                "ssh -o BatchMode=yes "
                f"-o ConnectTimeout={self.app_settings.ssh_timeout_seconds} "
                f"{self.app_settings.vcu_user}@{self.app_settings.vcu_host} "
                f"'{self.app_settings.tawm_restart_command}'"
            ),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            detail = stderr or stdout or f"exit code {result.returncode}"
            raise RuntimeError(f"Stage 3 failed: Tawm restart over SSH failed: {detail}")
        self.on_log("Tawm restart command completed and SSH session closed")

    def _restart_tawm_via_mock(self) -> None:
        payload = {
            "sga_host": self.app_settings.sga_host,
            "vcu_host": self.app_settings.vcu_host,
            "vcu_user": self.app_settings.vcu_user,
            "command": self.app_settings.tawm_restart_command,
        }
        request = urllib.request.Request(
            url=f"{self.app_settings.ssh_mock_url.rstrip('/')}/restart",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.app_settings.ssh_timeout_seconds) as response:  # noqa: S310
                body = response.read().decode("utf-8", errors="ignore")
            parsed = json.loads(body) if body else {}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Stage 3 failed: Tawm restart mock request failed: {exc}") from exc

        if not bool(parsed.get("success", True)):
            detail = str(parsed.get("details", "mock restart failed"))
            raise RuntimeError(f"Stage 3 failed: Tawm restart over SSH failed: {detail}")

    def _restart_tawm_with_passwords(self) -> None:
        try:
            paramiko = importlib.import_module("paramiko")
        except ImportError as exc:
            raise RuntimeError(
                "Stage 3 failed: password-based SSH restart requires paramiko. "
                "Install dependencies from pyproject.toml."
            ) from exc

        sga = paramiko.SSHClient()
        sga.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        sga_kwargs: dict[str, object] = {
            "hostname": self.app_settings.sga_host,
            "username": self.app_settings.sga_user,
            "timeout": self.app_settings.ssh_timeout_seconds,
        }
        if self.app_settings.sga_password:
            sga_kwargs["password"] = self.app_settings.sga_password
            sga_kwargs["look_for_keys"] = False
            sga_kwargs["allow_agent"] = False

        try:
            sga.connect(**sga_kwargs)
            transport = sga.get_transport()
            if transport is None:
                raise RuntimeError("No SSH transport to SGA")

            jump = transport.open_channel(
                "direct-tcpip",
                (self.app_settings.vcu_host, 22),
                ("127.0.0.1", 0),
            )

            vcu = paramiko.SSHClient()
            vcu.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            vcu_kwargs: dict[str, object] = {
                "hostname": self.app_settings.vcu_host,
                "username": self.app_settings.vcu_user,
                "timeout": self.app_settings.ssh_timeout_seconds,
                "sock": jump,
            }
            if self.app_settings.vcu_password:
                vcu_kwargs["password"] = self.app_settings.vcu_password
                vcu_kwargs["look_for_keys"] = False
                vcu_kwargs["allow_agent"] = False

            try:
                vcu.connect(**vcu_kwargs)
                _, stdout, stderr = vcu.exec_command(self.app_settings.tawm_restart_command)
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    err = stderr.read().decode("utf-8", errors="ignore").strip()
                    out = stdout.read().decode("utf-8", errors="ignore").strip()
                    detail = err or out or f"exit code {exit_code}"
                    raise RuntimeError(f"Stage 3 failed: Tawm restart over SSH failed: {detail}")
            finally:
                vcu.close()
        finally:
            sga.close()

    def action_start_logging(self, runtime: CycleRuntime) -> None:
        self.dlt.disconnect()
        self.dlt.connect(self.dlt_settings)
        self.dlt.set_logging_profile(self.dlt_settings.logging_profile_id)
        self.dlt.start_logging(runtime.temp_log_path)
        self.on_log(
            "DLT logging started: "
            f"{self.dlt_settings.hostname}:{self.dlt_settings.port}, "
            f"tmp file {runtime.temp_log_path}"
        )

    def action_clear_start_test(self, runtime: CycleRuntime) -> None:
        self.dlt.clear_tmp_log()
        self.on_log(f"Temporary log cleared: {runtime.temp_log_path}")
        self.audio.beep_once()
        with self._state_lock:
            self._fault_tokens_seen.clear()
            self._total_duration_seconds = self.app_settings.test_duration_seconds
        self.dlt.clear_payload_callbacks()
        self.dlt.register_payload_callback(self._on_payload)
        self._start_timer(runtime)
        with self._state_lock:
            total_duration = self._total_duration_seconds
        self.on_log(f"Test timer started: {total_duration} seconds")

    def action_filter_export(self, runtime: CycleRuntime) -> None:
        with self._state_lock:
            finished = self._finished
        if not finished:
            raise RuntimeError("Cannot export yet. Stage 5 timer is still running.")
        tawm_dlt_path = runtime.final_log_path.parent / self.app_settings.tawm_export_template.format(
            timestamp=runtime.run_timestamp
        )
        tawm_lib_ascii_path = runtime.final_log_path.parent / self.app_settings.tawm_lib_export_template.format(
            timestamp=runtime.run_timestamp
        )
        self.exporter.export_filtered_dlt(runtime.final_log_path, tawm_dlt_path, app_id="Tawm")
        self.exporter.export_filtered_ascii(runtime.final_log_path, tawm_lib_ascii_path, app_id="Tawm", ctx_id="LIB")
        self.on_log(f"Exported DLT filter file: {tawm_dlt_path}")
        self.on_log(f"Exported ASCII filter file: {tawm_lib_ascii_path}")

    def _on_payload(self, payload: str) -> None:
        if self.app_settings.log_all_dlt_payloads:
            self.on_log(f"DLT payload: {payload}")

        matched_tokens = [token for token in self.app_settings.fault_tokens if token in payload]
        if not matched_tokens:
            return

        should_log_reduction = False
        with self._state_lock:
            for token in matched_tokens:
                if token not in self._fault_tokens_seen:
                    self._fault_tokens_seen.add(token)
                    self.on_log(f"DLT fault token matched: {token}")

            if len(self._fault_tokens_seen) == len(self.app_settings.fault_tokens):
                new_duration = min(
                    self._total_duration_seconds,
                    self.app_settings.shortened_duration_seconds,
                )
                should_log_reduction = new_duration != self._total_duration_seconds
                self._total_duration_seconds = new_duration
                current_duration = self._total_duration_seconds

        if should_log_reduction:
            self.on_log(
                "All four debounce fault payloads found. "
                f"Timer reduced to {current_duration} seconds."
            )

    def _start_timer(self, runtime: CycleRuntime) -> None:
        self._timer_stop_event.set()
        self._timer_stop_event = threading.Event()
        self._finished = False

        self._timer_thread = threading.Thread(
            target=self._run_timer,
            args=(runtime,),
            daemon=True,
        )
        self._timer_thread.start()

    def _run_timer(self, runtime: CycleRuntime) -> None:
        elapsed = 0
        while not self._timer_stop_event.is_set():
            with self._state_lock:
                total_duration = self._total_duration_seconds
            if elapsed >= total_duration:
                break
            remaining = max(total_duration - elapsed, 0)
            self.on_timer_changed(remaining)
            self._timer_stop_event.wait(timeout=1.0)
            elapsed += 1

        if self._timer_stop_event.is_set():
            return

        self.on_timer_changed(0)
        self.audio.beep_three_times()
        self.dlt.save_log_to(runtime.final_log_path)
        self.dlt.disconnect()
        with self._state_lock:
            self._finished = True
        self.on_log(f"Test completed. Final log saved: {runtime.final_log_path}")

    def stop(self) -> None:
        self._timer_stop_event.set()
        self.dlt.disconnect()
