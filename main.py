import os
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import api
import steam_core


def _resource_path(relative: str) -> str:
    """Resolves asset."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


class SteamAnchorApp(tk.Tk):
    REFRESH_COOLDOWN = 10  # seconds between successful fetches
    ERROR_COOLDOWN = 1     # seconds to wait after a failed fetch

    def __init__(self):
        super().__init__()
        self.title("Steam Anchor")
        self.resizable(False, False)
        self.iconbitmap(_resource_path(os.path.join("assets", "icon.ico")))

        self.versions_data: list[dict] = []
        self._steam_path: str | None = None
        self._last_refresh = 0.0

        self._build_ui()
        self._center_window()
        self._check_block_status()
        self._startup_load()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=24)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Select Steam version:").grid(
            row=0, column=0, columnspan=2, sticky=tk.W,
        )
        ttk.Label(
            frame, text="DD/MM/YYYY  |  notes",
            foreground="gray", font=("TkDefaultFont", 8),
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

        self.combo_var = tk.StringVar()
        self.combo = ttk.Combobox(
            frame, textvariable=self.combo_var, state="readonly", width=22,
        )
        self.combo.grid(row=2, column=0, sticky=tk.EW, padx=(0, 6))
        self.combo.bind("<ButtonPress-1>",
                        lambda _: self.after(10, self._widen_dropdown))

        self.btn_refresh = ttk.Button(
            frame, text="⟳", width=3, command=self.refresh_list)
        self.btn_refresh.grid(row=2, column=1, padx=(4, 0), sticky=tk.N)

        self.lbl_cooldown = ttk.Label(
            frame, text=" ", foreground="gray",
            font=("TkDefaultFont", 8), anchor=tk.CENTER,
        )
        self.lbl_cooldown.grid(row=3, column=1, pady=0)

        self.block_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, text="Block future updates", variable=self.block_var,
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(3, 0))

        self.btn_unblock = ttk.Button(
            frame, text="Unblock future updates", command=self._unblock_updates,
        )
        self.btn_unblock.grid(row=5, column=0, columnspan=2,
                              sticky=tk.W, pady=(6, 0))
        self.btn_unblock.grid_remove()

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=6, column=0, columnspan=2, sticky=tk.EW, pady=14,
        )

        self.lbl_status = ttk.Label(frame, text="Ready.", foreground="gray")
        self.lbl_status.grid(row=7, column=0, columnspan=2, sticky=tk.W)

        self.btn_apply = ttk.Button(
            frame, text="Apply Downgrade", command=self.start_downgrade,
        )
        self.btn_apply.grid(
            row=8, column=0, columnspan=2, sticky=tk.EW, pady=(10, 0), ipady=4,
        )

        frame.columnconfigure(0, weight=1)

    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _widen_dropdown(self):
        try:
            popdown = self.combo.tk.eval(
                f"ttk::combobox::PopdownWindow {self.combo._w}"
            )
            self.combo.tk.call(f"{popdown}.f.l", "configure", "-width", 55)
            geom = str(self.combo.tk.call("wm", "geometry", popdown))
            rest = geom.split("x", 1)[1]
            self.combo.tk.call("wm", "geometry", popdown, f"360x{rest}")
        except Exception:
            pass

    def _status(self, text: str, color: str = "gray"):
        self.lbl_status.config(text=text, foreground=color)

    def _format_version(self, version: dict) -> str:
        try:
            dt = datetime.strptime(version["date"], "%Y%m%d%H%M%S")
            date_str = dt.strftime("%d/%m/%Y")
        except ValueError:
            date_str = version["date"]

        note = version["notes"]
        if len(note) > 44:
            note = note[:44] + "…"
        return f"{date_str}  |  {note}"

    # -- Steam block status -------------------------------------------------

    def _check_block_status(self):
        """Shows the unblock button if steam.cfg is currently blocking updates."""
        try:
            self._steam_path, _ = steam_core.get_steam_paths()
            if steam_core.is_update_blocked(self._steam_path):
                self.btn_unblock.grid()
                self.block_var.set(True)
        except RuntimeError:
            pass  # Steam not installed, will surface during downgrade

    def _unblock_updates(self):
        if self._steam_path is None:
            return
        try:
            steam_core.remove_block_update(self._steam_path)
        except Exception as exc:
            messagebox.showerror(
                "Error", f"Could not remove steam.cfg:\n{exc}")
            return
        self.block_var.set(False)
        self.btn_unblock.grid_remove()
        self._status("Update block removed.", "green")

    # -- Version list -------------------------------------------------------

    def _startup_load(self):
        """Loads versions from cache on startup, falls back to network if absent."""
        cached = api.load_cache()
        if cached is not None:
            self.versions_data = sorted(
                cached, key=lambda v: v["date"], reverse=True)
            values = [self._format_version(v) for v in self.versions_data]
            self._on_fetch_ok(
                values, status="Loaded from cache.", cooldown=False)
        else:
            self.refresh_list()

    def refresh_list(self):
        """Fetches the version list from the network, respecting cooldown."""
        elapsed = time.monotonic() - self._last_refresh
        cooldown = self.REFRESH_COOLDOWN if self.versions_data else 0
        if elapsed < cooldown:
            return

        self._status("Fetching versions…")
        self.btn_refresh.state(["disabled"])
        self.btn_apply.state(["disabled"])
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            data = api.fetch_versions()
            self.versions_data = sorted(
                data, key=lambda v: v["date"], reverse=True)
            values = [self._format_version(v) for v in self.versions_data]
            self.after(0, self._on_fetch_ok, values)
        except Exception:
            try:
                data = api.fetch_fallback()
                self.versions_data = sorted(
                    data, key=lambda v: v["date"], reverse=True)
                values = [self._format_version(v) for v in self.versions_data]
                self.after(0, self._on_fetch_ok, values,
                           "Loaded from fallback.")
            except Exception:
                self._last_refresh = (
                    time.monotonic() - self.REFRESH_COOLDOWN + self.ERROR_COOLDOWN
                )
                self.after(0, self._on_fetch_err)

    def _on_fetch_ok(self, values, status="Version list updated.", cooldown=True):
        if cooldown:
            self._last_refresh = time.monotonic()
        self.combo["values"] = values
        if values:
            self.combo.current(0)
        self._status(status, "green")
        self.btn_refresh.state(["!disabled"])
        self.btn_apply.state(["!disabled"])
        if cooldown:
            self._start_cooldown(self.REFRESH_COOLDOWN)

    def _start_cooldown(self, seconds: int):
        self.btn_refresh.state(["disabled"])
        self._tick_cooldown(seconds)

    def _tick_cooldown(self, remaining: int):
        if remaining > 0:
            self.lbl_cooldown.config(text=f"{remaining}s")
            self.after(1000, self._tick_cooldown, remaining - 1)
        else:
            self.lbl_cooldown.config(text=" ")
            self.btn_refresh.state(["!disabled"])

    def _on_fetch_err(self):
        self._status("Failed to load version list. Click ⟳ to retry.", "red")
        self._start_cooldown(self.ERROR_COOLDOWN)

    # -- Downgrade ----------------------------------------------------------

    def start_downgrade(self):
        idx = self.combo.current()
        if idx < 0:
            messagebox.showwarning(
                "No Version Selected", "Please select a Steam version first.",
            )
            return

        version = self.versions_data[idx]

        raw_date = version["date"]
        fmt_date = f"{raw_date[6:8]}/{raw_date[4:6]}/{raw_date[:4]}" if len(
            raw_date) == 14 else raw_date

        if not messagebox.askyesno(
            "Confirm Downgrade",
            f"Downgrade to version from {fmt_date}?\n"
            "Steam will be closed during the process.",
        ):
            return

        self.btn_apply.state(["disabled"])
        self.btn_refresh.state(["disabled"])
        self._status("Running downgrade, please wait…")
        threading.Thread(
            target=self._do_downgrade,
            args=(version["date"], self.block_var.get()),
            daemon=True,
        ).start()

    def _do_downgrade(self, date: str, block: bool):
        try:
            steam_path, steam_exe = steam_core.get_steam_paths()
            self._steam_path = steam_path

            self.after(0, lambda: self._status("1/3  Closing Steam…"))
            steam_core.kill_steam_process()

            self.after(0, lambda: self._status("2/3  Downloading package…"))
            steam_core.execute_downgrade(steam_exe, date)

            if block:
                self.after(0, lambda: self._status(
                    "3/3  Applying update block…"))
                steam_core.apply_block_update(steam_path)
            else:
                self.after(0, lambda: self._status(
                    "3/3  Removing update block…"))
                steam_core.remove_block_update(steam_path)

            self.after(0, self._done_ok, block)
        except Exception as exc:
            self.after(0, lambda e=exc: self._done_err(str(e)))

    def _done_ok(self, block: bool):
        self._status("Downgrade completed!", "green")
        self.btn_apply.state(["!disabled"])
        self.btn_refresh.state(["!disabled"])

        if block:
            self.btn_unblock.grid()
        else:
            self.btn_unblock.grid_remove()

        messagebox.showinfo(
            "Success", "The process has finished.\nYou can now launch Steam.",
        )

    def _done_err(self, msg: str):
        self._status("An error occurred during the process.", "red")
        self.btn_apply.state(["!disabled"])
        self.btn_refresh.state(["!disabled"])
        messagebox.showerror("Downgrade Failed",
                             f"An error occurred:\n\n{msg}")


if __name__ == "__main__":
    SteamAnchorApp().mainloop()
