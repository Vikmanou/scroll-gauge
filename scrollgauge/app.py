import tkinter as tk
import webbrowser
from collections import Counter
from collections.abc import Callable
from tkinter import font, ttk

from . import extension, wsf

MIN_SPEED, MAX_SPEED = 0.05, 2.0
SAVE_DELAY_MS = 300
SWIPE_GAP_MS = 350
EXTENSION_URL = "https://extensions.gnome.org/extension/10008/touchpad-speed-control/"
DEMO_TEXT = (
    "Scrolling should feel calm and predictable.",
    "One swipe should move about the same distance in every app.",
    "Try a short swipe, then a long one.",
    "Slow swipes and quick flicks both count.",
    "Adjust the slider until this feels right.",
)


def speed_text(value: float) -> str:
    return f"{value:.2f}×"


class ScrollGauge(ttk.Frame):
    def __init__(self, root: tk.Tk):
        super().__init__(root, padding=16)
        self.apps = extension.installed_apps()
        self.schemas = extension.schema_dir()
        self.factors = extension.load_app_factors(self.schemas) if self.schemas else {}
        self.selected: str | None = None
        self._pending: dict[str, tuple[str, Callable[[], None]]] = {}
        self._swipe_timer: str | None = None
        self._swipe_start = 1
        self._settled_top = 1

        try:
            current = wsf.read().vertical
            self.wsf_error = None
        except wsf.WsfError as err:
            current, self.wsf_error = 1.0, str(err)
        if self.schemas:
            current = extension.load_global_factor(self.schemas)

        self.global_speed = tk.DoubleVar(value=current)
        self.app_speed = tk.DoubleVar(value=current)

        self.columnconfigure(0, weight=1, uniform="col")
        self.columnconfigure(1, weight=1, uniform="col")
        self.rowconfigure(1, weight=1)
        self._build_global().grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        self._build_per_app().grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        self._build_demo().grid(row=1, column=1, sticky="nsew")
        self._preview(current, "Global")

    def _build_global(self) -> ttk.Frame:
        frame = ttk.Frame(self)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Global speed", style="Heading.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        scale = ttk.Scale(frame, from_=MIN_SPEED, to=MAX_SPEED, variable=self.global_speed, command=self._on_global)
        scale.grid(row=0, column=1, sticky="ew")
        self.global_label = ttk.Label(frame, text=speed_text(self.global_speed.get()), width=6, anchor="e")
        self.global_label.grid(row=0, column=2, padx=(12, 0))
        hint = self.wsf_error or "Used by every app that has no speed of its own."
        ttk.Label(frame, text=hint, style="Hint.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))
        if self.wsf_error:
            scale.state(["disabled"])
        return frame

    def _build_per_app(self) -> ttk.Frame:
        frame = ttk.Frame(self)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Per-app speeds", style="Heading.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

        if self.schemas is None:
            ttk.Label(frame, text="Needs the Touchpad Speed Control extension.", style="Hint.TLabel").grid(row=1, column=0, sticky="nw")
            link = ttk.Label(frame, text="Get it from extensions.gnome.org", style="Link.TLabel", cursor="hand2")
            link.grid(row=2, column=0, sticky="nw")
            link.bind("<Button-1>", lambda _: webbrowser.open(EXTENSION_URL))
            return frame

        self.tree = ttk.Treeview(frame, columns=("speed",), selectmode="browse", height=8)
        self.tree.heading("#0", text="App", anchor="w")
        self.tree.heading("speed", text="Speed", anchor="e")
        self.tree.column("speed", width=70, stretch=False, anchor="e")
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        for app_id in sorted((a for a in self.factors if a in self.apps), key=self.apps.get):
            self.tree.insert("", "end", iid=app_id, text=self.apps[app_id], values=(speed_text(self.factors[app_id]),))

        editor = ttk.Frame(frame)
        editor.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        editor.columnconfigure(0, weight=1)
        self.app_scale = ttk.Scale(editor, from_=MIN_SPEED, to=MAX_SPEED, variable=self.app_speed, command=self._on_app_speed)
        self.app_scale.grid(row=0, column=0, sticky="ew")
        self.app_label = ttk.Label(editor, text="", width=6, anchor="e")
        self.app_label.grid(row=0, column=1, padx=(12, 8))
        self.remove_button = ttk.Button(editor, text="Remove", command=self._remove)
        self.remove_button.grid(row=0, column=2)

        adder = ttk.Frame(frame)
        adder.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        adder.columnconfigure(0, weight=1)
        self.app_choice = ttk.Combobox(adder, state="readonly")
        self.app_choice.grid(row=0, column=0, sticky="ew")
        ttk.Button(adder, text="Add", command=self._add).grid(row=0, column=1, padx=(8, 0))
        self._refresh_choices()
        self._set_editor_enabled(False)

        if not extension.is_enabled():
            notice = ttk.Frame(frame)
            notice.grid(row=4, column=0, sticky="ew", pady=(8, 0))
            ttk.Label(notice, text="Touchpad Speed Control is turned off.", style="Hint.TLabel").pack(side="left")
            ttk.Button(notice, text="Turn on", command=lambda: (extension.enable(), notice.destroy())).pack(side="right")
        return frame

    def _build_demo(self) -> ttk.Frame:
        frame = ttk.Frame(self)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Try it", style="Heading.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.demo = tk.Text(frame, wrap="word", relief="flat", padx=12, pady=8, spacing1=4, spacing3=4, cursor="arrow")
        scrollbar = ttk.Scrollbar(frame, command=self.demo.yview)
        self.demo.configure(yscrollcommand=lambda first, last: (scrollbar.set(first, last), self._on_demo_scroll()))
        self.demo.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        for n in range(1, 401):
            self.demo.insert("end", f"{n:>3}   {DEMO_TEXT[n % len(DEMO_TEXT)]}\n")
        self.demo.configure(state="disabled")

        self.swipe_label = ttk.Label(frame, text="Swipe on the text with two fingers.", style="Hint.TLabel")
        self.swipe_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.preview_label = ttk.Label(frame, text="", style="Hint.TLabel")
        self.preview_label.grid(row=3, column=0, columnspan=2, sticky="w")
        return frame

    def _on_global(self, _=None) -> None:
        value = round(self.global_speed.get(), 2)
        self.global_label.configure(text=speed_text(value))
        self._preview(value, "Global")
        if self.schemas:
            self._later("global", lambda: extension.save_global_factor(self.schemas, value))

    def _on_select(self, _=None) -> None:
        selection = self.tree.selection()
        self.selected = selection[0] if selection else None
        self._set_editor_enabled(self.selected is not None)
        if self.selected:
            value = self.factors[self.selected]
            self.app_speed.set(value)
            self.app_label.configure(text=speed_text(value))
            self._preview(value, self.apps[self.selected])

    def _on_app_speed(self, _=None) -> None:
        if not self.selected:
            return
        value = round(self.app_speed.get(), 2)
        self.factors[self.selected] = value
        self.tree.set(self.selected, "speed", speed_text(value))
        self.app_label.configure(text=speed_text(value))
        self._preview(value, self.apps[self.selected])
        self._save_factors()

    def _add(self) -> None:
        app_id = self._choices.get(self.app_choice.get())
        if not app_id:
            return
        self.factors[app_id] = round(self.global_speed.get(), 2)
        self.tree.insert("", "end", iid=app_id, text=self.apps[app_id], values=(speed_text(self.factors[app_id]),))
        self.tree.selection_set(app_id)
        self.tree.see(app_id)
        self._refresh_choices()
        self._save_factors()

    def _remove(self) -> None:
        if not self.selected:
            return
        del self.factors[self.selected]
        self.tree.delete(self.selected)
        self._refresh_choices()
        self._save_factors()
        self._on_global()

    def _refresh_choices(self) -> None:
        names = sorted((name, app_id) for app_id, name in self.apps.items() if app_id not in self.factors)
        counts = Counter(name for name, _ in names)
        self._choices = {name if counts[name] == 1 else f"{name} ({app_id})": app_id for name, app_id in names}
        self.app_choice.configure(values=list(self._choices))
        self.app_choice.set("Choose an app…")

    def _set_editor_enabled(self, enabled: bool) -> None:
        state = ["!disabled"] if enabled else ["disabled"]
        self.app_scale.state(state)
        self.remove_button.state(state)
        if not enabled:
            self.app_label.configure(text="")

    def _save_factors(self) -> None:
        factors = dict(self.factors)
        self._later("factors", lambda: extension.save_app_factors(self.schemas, factors))

    def _preview(self, value: float, source: str) -> None:
        self.preview_label.configure(text=f"Demo is using: {source}, {speed_text(value)}")
        if not self.wsf_error:
            self._later("wsf", lambda: wsf.write(wsf.Factors(value, value)))

    def _on_demo_scroll(self) -> None:
        if self._swipe_timer is None:
            self._swipe_start = self._settled_top
        else:
            self.after_cancel(self._swipe_timer)
        self._swipe_timer = self.after(SWIPE_GAP_MS, self._end_swipe)

    def _end_swipe(self) -> None:
        self._swipe_timer = None
        top = int(self.demo.index("@0,0").split(".")[0])
        moved = abs(top - self._swipe_start)
        self._settled_top = top
        if moved:
            self.swipe_label.configure(text=f"Last swipe moved {moved} line{'s' if moved != 1 else ''}.")

    def _later(self, key: str, action: Callable[[], None]) -> None:
        if key in self._pending:
            self.after_cancel(self._pending[key][0])
        after_id = self.after(SAVE_DELAY_MS, lambda: self._pending.pop(key)[1]())
        self._pending[key] = (after_id, action)

    def close(self) -> None:
        for after_id, action in self._pending.values():
            self.after_cancel(after_id)
            action()
        if not self.wsf_error:
            value = round(self.global_speed.get(), 2)
            wsf.write(wsf.Factors(value, value))
        self.master.destroy()


def _style(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    family = font.nametofont("TkDefaultFont").actual("family")
    style.configure("Heading.TLabel", font=(family, 12, "bold"))
    style.configure("Hint.TLabel", foreground="#666666")
    style.configure("Link.TLabel", foreground="#1c71d8")
    style.configure("Treeview", rowheight=26)


def main() -> None:
    root = tk.Tk(className="scrollgauge")
    root.title("Scroll Gauge")
    root.geometry("860x540")
    root.minsize(720, 440)
    _style(root)
    app = ScrollGauge(root)
    app.pack(fill="both", expand=True)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
