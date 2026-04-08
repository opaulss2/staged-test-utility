from __future__ import annotations

from pathlib import Path
import textwrap
import tkinter as tk
from tkinter import messagebox, ttk

from tpms_utility.config import DEFAULT_APP_SETTINGS, DEFAULT_DLT_SETTINGS
from tpms_utility.cycle_controller import CycleController
from tpms_utility.stages.default_cycle import build_default_cycle

_BORDER_SELECTED = "#F78923"  # orange  – current stage, ready to execute
_BORDER_UPCOMING = "#F7F323"  # yellow  – future stages
_BORDER_EXECUTED = "#91F723"  # green   – completed stages
_BORDER_WIDTH = 3
_WHEEL_SIZE = 220
_WHEEL_ARC_WIDTH = 18
_STAGE_FRAME_WIDTH = 860
_STAGE_FRAME_HEIGHT = 360
_DETAILS_FRAME_WIDTH = 360
_DETAILS_FRAME_HEIGHT = 360
_LOG_FRAME_HEIGHT = 380
_DETAILS_WRAP = 320
_LOG_MAX_LINES = 2000
_LOG_TRIM_EVERY = 100


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("TPMS Test Utility")
        self.root.geometry("1280x776")

        self._load_sun_valley_theme()

        self.status_var = tk.StringVar(value="Ready")
        self.timer_var = tk.StringVar(value="Remaining: 00:00")
        self.current_stage_var = tk.StringVar(value="Current stage: 0")
        self.timer_stage_var = tk.StringVar(value="Timed stage idle")

        self.log_text: tk.Text | None = None
        self.stage_buttons: dict[int, ttk.Button] = {}
        self.stage_frames: dict[int, tk.Frame] = {}
        self.timer_canvas: tk.Canvas | None = None
        self.timer_wheel_arc: int | None = None
        self.timer_wheel_angle = 0
        self.timer_wheel_job: str | None = None
        self.timer_running = False
        self.pending_timer_seconds: int | None = 0
        self._log_line_count = 0
        self._log_append_count = 0

        self.controller = CycleController(
            stages=[],
            app_settings=DEFAULT_APP_SETTINGS,
            dlt_settings=DEFAULT_DLT_SETTINGS,
            on_state_changed=self._refresh_stage_buttons,
            on_log=self._append_log,
            on_timer_changed=self._set_timer,
        )
        self.controller.stages = build_default_cycle(self.controller)

        self._build_layout()
        self._refresh_stage_buttons()
        self.root.after(0, self._run_startup_self_checks)
        self._process_pending_timer_update()

        self.root.bind("<space>", self._on_space)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_sun_valley_theme(self) -> None:
        theme_file = Path("vendor/sun-valley-ttk-theme/sv_ttk/sv.tcl")
        if not theme_file.exists():
            raise FileNotFoundError(
                "Sun Valley theme is required but missing at vendor/sun-valley-ttk-theme/sv_ttk/sv.tcl"
            )
        self.root.tk.call("source", str(theme_file))
        self.root.tk.call("ttk::style", "theme", "use", "sun-valley-dark")
        ttk.Style().configure("TButton", font=("TkDefaultFont", 10, "bold"))
        self.root.event_generate("<<ThemeChanged>>")

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=2)
        self.root.rowconfigure(0, weight=2)
        self.root.rowconfigure(1, weight=1)

        max_stage = max((stage.stage_id for stage in self.controller.stages), default=0)
        stage_frame = ttk.LabelFrame(
            self.root,
            text=f"Stages 0-{max_stage}",
            width=_STAGE_FRAME_WIDTH,
            height=_STAGE_FRAME_HEIGHT,
        )
        stage_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        stage_frame.grid_propagate(False)
        stage_frame.rowconfigure(0, weight=1)

        _btn_outer = 115 + 2 * _BORDER_WIDTH
        for idx in range(len(self.controller.stages)):
            stage_frame.columnconfigure(idx, weight=1, uniform="stage")
            stage = self.controller.stages[idx]
            label = self._format_stage_label(stage.stage_id, stage.name)
            border = tk.Frame(stage_frame, bg=_BORDER_UPCOMING, width=_btn_outer, height=_btn_outer)
            border.grid(row=0, column=idx, padx=8, pady=8)
            border.grid_propagate(False)
            border.rowconfigure(0, weight=1)
            border.columnconfigure(0, weight=1)
            button = ttk.Button(border, text=label, command=lambda i=idx: self._select_stage(i))
            button.grid(row=0, column=0, sticky="nsew", padx=_BORDER_WIDTH, pady=_BORDER_WIDTH)
            self.stage_frames[idx] = border
            self.stage_buttons[idx] = button

        details_frame = ttk.LabelFrame(
            self.root,
            text="Status",
            width=_DETAILS_FRAME_WIDTH,
            height=_DETAILS_FRAME_HEIGHT,
        )
        details_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        details_frame.grid_propagate(False)
        details_frame.columnconfigure(0, weight=1)

        lbl_stage = ttk.Label(details_frame, textvariable=self.current_stage_var, wraplength=_DETAILS_WRAP, justify="left")
        lbl_stage.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        lbl_status = ttk.Label(details_frame, textvariable=self.status_var, wraplength=_DETAILS_WRAP, justify="left")
        lbl_status.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        lbl_timer = ttk.Label(details_frame, textvariable=self.timer_var, wraplength=_DETAILS_WRAP, justify="left")
        lbl_timer.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        lbl_timer_stage = ttk.Label(details_frame, textvariable=self.timer_stage_var, wraplength=_DETAILS_WRAP, justify="left")
        lbl_timer_stage.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))

        self.timer_canvas = tk.Canvas(
            details_frame,
            width=_WHEEL_SIZE,
            height=_WHEEL_SIZE,
            highlightthickness=0,
            bd=0,
            background=self.root.cget("bg"),
        )
        self.timer_canvas.grid(row=4, column=0, pady=(0, 12))
        self.timer_canvas.grid_remove()
        inset = _WHEEL_ARC_WIDTH
        self.timer_canvas.create_oval(
            inset,
            inset,
            _WHEEL_SIZE - inset,
            _WHEEL_SIZE - inset,
            outline="#D9D9D9",
            width=6,
        )
        self.timer_wheel_arc = self.timer_canvas.create_arc(
            inset,
            inset,
            _WHEEL_SIZE - inset,
            _WHEEL_SIZE - inset,
            start=self.timer_wheel_angle,
            extent=90,
            style="arc",
            outline=_BORDER_SELECTED,
            width=_WHEEL_ARC_WIDTH,
        )

        instructions = (
            "Press SPACE to execute current stage and advance.\n"
            "Stage 2 is manual and only advances.\n"
            "Stage 6 will fail if stage 5 timer has not finished."
        )
        lbl_instructions = ttk.Label(details_frame, text=instructions, justify="left", wraplength=_DETAILS_WRAP)
        lbl_instructions.grid(row=5, column=0, sticky="nw", padx=8, pady=4)

        log_frame = ttk.LabelFrame(self.root, text="Execution log", height=_LOG_FRAME_HEIGHT)
        log_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 12))
        log_frame.grid_propagate(False)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=14, state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def _on_space(self, _: tk.Event) -> None:
        try:
            self.controller.advance_by_space()
            self.status_var.set("Stage executed")
        except Exception as exc:  # noqa: BLE001
            self.status_var.set("Execution failed")
            messagebox.showerror("Stage execution error", str(exc))

    def _run_startup_self_checks(self) -> None:
        if not self.controller.app_settings.enable_swut_startup_self_check:
            self._append_log("Startup SWUT self-check is disabled")
            return

        result = self.controller.swut.startup_self_check()
        if result.success:
            self._append_log(f"SWUT startup self-check: {result.details}")
            return

        self.status_var.set("SWUT self-check failed")
        self._append_log(f"SWUT startup self-check failed: {result.details}")

    def _select_stage(self, index: int) -> None:
        if index >= len(self.controller.stages):
            return
        self.controller.current_index = index
        self._refresh_stage_buttons()

    def _refresh_stage_buttons(self) -> None:
        stage = self.controller.current_stage
        self.current_stage_var.set(f"Current stage: {stage.stage_id} - {stage.name}")
        for index, button in self.stage_buttons.items():
            if index == self.controller.current_index:
                self.stage_frames[index].configure(bg=_BORDER_SELECTED)
                button.state(["pressed"])
            elif index < self.controller.current_index:
                self.stage_frames[index].configure(bg=_BORDER_EXECUTED)
                button.state(["!pressed"])
            else:
                self.stage_frames[index].configure(bg=_BORDER_UPCOMING)
                button.state(["!pressed"])

    def _append_log(self, message: str) -> None:
        if self.log_text is None:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self._log_append_count += 1
        self._log_line_count += message.count("\n") + 1
        if self._log_append_count % _LOG_TRIM_EVERY == 0 and self._log_line_count > _LOG_MAX_LINES:
            self._trim_log_lines()
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _trim_log_lines(self) -> None:
        if self.log_text is None:
            return

        trim_count = self._log_line_count - _LOG_MAX_LINES
        if trim_count <= 0:
            return

        self.log_text.delete("1.0", f"{trim_count + 1}.0")
        remaining_lines = int(self.log_text.index("end-1c").split(".")[0])
        self._log_line_count = max(remaining_lines, 0)

    @staticmethod
    def _format_stage_label(stage_id: int, stage_name: str) -> str:
        wrapped_name = textwrap.fill(stage_name, width=16)
        return f"Stage {stage_id}\n{wrapped_name}"

    def _set_timer(self, remaining_seconds: int) -> None:
        self.pending_timer_seconds = remaining_seconds

    def _process_pending_timer_update(self) -> None:
        if self.pending_timer_seconds is not None:
            self._apply_timer_update(self.pending_timer_seconds)
            self.pending_timer_seconds = None
        self.root.after(100, self._process_pending_timer_update)

    def _apply_timer_update(self, remaining_seconds: int) -> None:
        minutes, seconds = divmod(remaining_seconds, 60)
        self.timer_var.set(f"Remaining: {minutes:02d}:{seconds:02d}")
        if remaining_seconds > 0:
            self._show_timer_wheel()
        else:
            self._hide_timer_wheel()

    def _show_timer_wheel(self) -> None:
        if self.timer_canvas is None:
            return
        self.timer_stage_var.set("Timed stage running")
        self.timer_running = True
        self.timer_canvas.grid()
        if self.timer_wheel_job is None:
            self._animate_timer_wheel()

    def _hide_timer_wheel(self) -> None:
        self.timer_stage_var.set("Timed stage idle")
        self.timer_running = False
        if self.timer_canvas is not None:
            self.timer_canvas.grid_remove()
        if self.timer_wheel_job is not None:
            self.root.after_cancel(self.timer_wheel_job)
            self.timer_wheel_job = None

    def _animate_timer_wheel(self) -> None:
        if not self.timer_running or self.timer_canvas is None or self.timer_wheel_arc is None:
            self.timer_wheel_job = None
            return
        self.timer_wheel_angle = (self.timer_wheel_angle + 12) % 360
        self.timer_canvas.itemconfigure(self.timer_wheel_arc, start=self.timer_wheel_angle)
        self.timer_wheel_job = self.root.after(50, self._animate_timer_wheel)

    def _on_close(self) -> None:
        self._hide_timer_wheel()
        self.controller.stop()
        self.root.destroy()
