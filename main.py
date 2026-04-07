from __future__ import annotations

import tkinter as tk

from tpms_utility.ui.main_window import MainWindow


def main() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
