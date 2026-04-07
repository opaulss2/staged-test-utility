from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from tpms_utility.config import DEFAULT_APP_SETTINGS, DEFAULT_DLT_SETTINGS
from tpms_utility.cycle_controller import CycleController
from tpms_utility.stages.default_cycle import build_default_cycle


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("TPMS Test Utility")
        self.root.geometry("1180x720")

        self._load_sun_valley_theme()

        self.status_var = tk.StringVar(value="Ready")
        self.timer_var = tk.StringVar(value="Remaining: 00:00")
        self.current_stage_var = tk.StringVar(value="Current stage: 0")

        self.log_text = tk.Text(self.root, height=14, state="disabled")
        self.stage_buttons: dict[int, ttk.Button] = {}

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

        self.root.bind("<space>", self._on_space)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_sun_valley_theme(self) -> None:
        theme_file = Path("vendor/sun-valley-ttk-theme/sun-valley.tcl")
        if theme_file.exists():
            self.root.tk.call("source", str(theme_file))
            self.root.tk.call("set_theme", "light")

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=2)
        self.root.rowconfigure(0, weight=2)
        self.root.rowconfigure(1, weight=1)

        stage_frame = ttk.LabelFrame(self.root, text="Stages 0-9")
        stage_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        for idx in range(10):
            stage_frame.columnconfigure(idx % 5, weight=1)
            stage_frame.rowconfigure(idx // 5, weight=1)
            label = f"Stage {idx}\n(Not configured)"
            if idx < len(self.controller.stages):
                stage = self.controller.stages[idx]
                label = f"Stage {idx}\n{stage.name}"
            button = ttk.Button(stage_frame, text=label, command=lambda i=idx: self._select_stage(i))
            button.grid(row=idx // 5, column=idx % 5, sticky="nsew", padx=8, pady=8, ipadx=20, ipady=24)
            self.stage_buttons[idx] = button

        details_frame = ttk.LabelFrame(self.root, text="Status")
        details_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        details_frame.columnconfigure(0, weight=1)

        ttk.Label(details_frame, textvariable=self.current_stage_var).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        ttk.Label(details_frame, textvariable=self.status_var).grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(details_frame, textvariable=self.timer_var).grid(row=2, column=0, sticky="w", padx=8, pady=(4, 8))

        instructions = (
            "Press SPACE to execute current stage and advance.\n"
            "Stage 2 is manual and only advances.\n"
            "Stage 6 will fail if stage 5 timer has not finished."
        )
        ttk.Label(details_frame, text=instructions, justify="left", wraplength=300).grid(
            row=3, column=0, sticky="nw", padx=8, pady=4
        )

        log_frame = ttk.LabelFrame(self.root, text="Execution log")
        log_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 12))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text.grid(in_=log_frame, row=0, column=0, sticky="nsew", padx=8, pady=8)

    def _on_space(self, _: tk.Event) -> None:
        try:
            self.controller.advance_by_space()
            self.status_var.set("Stage executed")
        except Exception as exc:  # noqa: BLE001
            self.status_var.set("Execution failed")
            messagebox.showerror("Stage execution error", str(exc))

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
                button.state(["pressed"])
            else:
                button.state(["!pressed"])

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_timer(self, remaining_seconds: int) -> None:
        minutes, seconds = divmod(remaining_seconds, 60)
        self.timer_var.set(f"Remaining: {minutes:02d}:{seconds:02d}")

    def _on_close(self) -> None:
        self.controller.stop()
        self.root.destroy()
