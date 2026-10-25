import textwrap
from collections.abc import Callable
from itertools import cycle, islice

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk, Pango

from . import __version__, extension, wsf

APP_ID = "io.github.vikmanou.ScrollGauge"
MIN_SPEED, MAX_SPEED, DEFAULT_SPEED = 0.05, 3.0, 1.0
SAVE_DELAY_MS = 300
SWIPE_GAP_MS = 350
EXTENSION_URL = "https://extensions.gnome.org/extension/10008/touchpad-speed-control/"
DEMO_LINES = 400
LOREM_IPSUM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris tristique viverra lobortis. Proin sem velit, "
    "hendrerit condimentum tortor sit amet, rutrum ornare ipsum. Pellentesque auctor et metus id condimentum. Morbi in "
    "facilisis metus, ac placerat purus. Nunc faucibus pulvinar est, vitae dictum nibh condimentum nec. Nulla et "
    "accumsan enim. Praesent ultrices malesuada velit, in sagittis odio suscipit a. Maecenas scelerisque quis tellus ut "
    "vulputate. Proin vel nisl blandit, convallis est vel, faucibus libero. Fusce ut porta mauris, at aliquam justo. "
    "Phasellus erat nulla, semper a hendrerit elementum, pharetra at ante. Proin laoreet lobortis ipsum ac euismod. "
    "Phasellus sit amet aliquet enim. Vestibulum sit amet urna nec purus efficitur consectetur quis at turpis. Morbi "
    "tristique turpis enim, et feugiat ex pellentesque id. Nulla eget varius neque. Pellentesque eu purus vel diam "
    "lacinia ultricies et id massa. Aliquam luctus libero sit amet pretium vehicula. Donec quis pharetra neque, eget "
    "laoreet erat. Mauris egestas ornare ante, in maximus velit lacinia laoreet. Suspendisse potenti. Quisque pretium "
    "enim sed consectetur eleifend. Suspendisse in ligula a lacus finibus hendrerit. Morbi tempus non leo vitae "
    "imperdiet. Sed dictum nibh ac mattis posuere."
)


def demo_text() -> str:
    lines = islice(cycle(textwrap.wrap(LOREM_IPSUM, width=44)), DEMO_LINES)
    return "\n".join(f"{n:>3}   {line}" for n, line in enumerate(lines, start=1))


def app_icon(info: Gio.AppInfo, size: int) -> Gtk.Image:
    icon = info.get_icon()
    if icon is None:
        return Gtk.Image(icon_name="application-x-executable", pixel_size=size)
    return Gtk.Image(gicon=icon, pixel_size=size)


class SpeedControl(Gtk.Box):
    def __init__(self, value: float, on_change: Callable[[float], None], button: Gtk.Button):
        super().__init__(spacing=8, valign=Gtk.Align.CENTER)
        self.adjustment = Gtk.Adjustment(
            value=value, lower=MIN_SPEED, upper=MAX_SPEED, step_increment=0.05, page_increment=0.25
        )
        scale = Gtk.Scale(adjustment=self.adjustment, draw_value=False, valign=Gtk.Align.CENTER)
        scale.set_size_request(200, -1)
        scale.add_mark(DEFAULT_SPEED, Gtk.PositionType.BOTTOM, None)
        spin = Gtk.SpinButton(
            adjustment=self.adjustment, digits=2, climb_rate=0.05, numeric=True, width_chars=4, valign=Gtk.Align.CENTER,
            tooltip_text="Type an exact speed, or step it with − and +",
        )
        button.add_css_class("flat")
        button.set_valign(Gtk.Align.CENTER)
        for child in (scale, spin, button):
            self.append(child)
        self.adjustment.connect("value-changed", lambda adj: on_change(round(adj.get_value(), 2)))

    @property
    def value(self) -> float:
        return round(self.adjustment.get_value(), 2)


class ScrollGaugeWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="Scroll Gauge", default_width=640, default_height=700)
        self.set_size_request(520, -1)
        self.schemas = extension.schema_dir()
        self.factors = extension.load_app_factors(self.schemas) if self.schemas else {}
        self.apps = {
            info.get_id().removesuffix(".desktop"): info
            for info in Gio.AppInfo.get_all()
            if info.should_show() and info.get_id() and info.get_id() != f"{APP_ID}.desktop"
        }
        self.app_rows: dict[str, Adw.ActionRow] = {}
        self.controls = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self._pending: dict[str, tuple[int, Callable[[], None]]] = {}
        self._unsaved: dict[str, float | None] = {}
        self._swipe_timeout = 0
        self._swipe_start = 0
        self._settled_line = 0
        self._last_swipe = "No swipe yet."
        self._demo_speed = ""

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Scroll Gauge", subtitle=f"v{__version__}"))
        view = Adw.ToolbarView()
        view.add_top_bar(header)
        self.set_content(view)
        if not wsf.is_active():
            view.add_top_bar(Adw.Banner(
                title="WSF isn't active in this session. Run “wsf enable”, then log out and back in.", revealed=True
            ))

        try:
            current = wsf.read().vertical
        except wsf.WsfError as err:
            view.set_content(Adw.StatusPage(icon_name="dialog-warning-symbolic", title="WSF Not Found", description=str(err)))
            return
        if self.schemas:
            if extension.is_customized("global-factor"):
                current = extension.load_global_factor(self.schemas)
            else:
                extension.save_global_factor(self.schemas, current)
            if not extension.is_customized("app-factors"):
                self.factors = extension.starter_app_factors(set(self.apps), current)
                extension.save_app_factors(self.schemas, self.factors)

        page = Adw.PreferencesPage()
        page.add(self._build_global(current))
        page.add(self._build_per_app())
        page.add(self._build_demo())
        view.set_content(page)
        self._show_demo_speed(current)
        self.connect("close-request", self._on_close)

    def _build_global(self, current: float) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="Global Speed", description="Used by every app without its own speed. 1.00 is the system default."
        )
        row = Adw.ActionRow(title="Touchpad scroll", title_lines=1, activatable=False)
        row.add_prefix(Gtk.Image.new_from_icon_name("input-touchpad-symbolic"))
        reset = Gtk.Button(icon_name="edit-undo-symbolic", tooltip_text=f"Reset to the system default ({DEFAULT_SPEED:.2f})")
        self.global_control = SpeedControl(current, self._on_global, reset)
        reset.connect("clicked", lambda _: self.global_control.adjustment.set_value(DEFAULT_SPEED))

        def update_reset(adjustment: Gtk.Adjustment) -> None:
            reset.set_sensitive(round(adjustment.get_value(), 2) != DEFAULT_SPEED)

        self.global_control.adjustment.connect("value-changed", update_reset)
        update_reset(self.global_control.adjustment)
        self.controls.add_widget(self.global_control)
        row.add_suffix(self.global_control)
        group.add(row)
        return group

    def _build_per_app(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Per-App Speeds")
        if self.schemas is None:
            group.set_description("Needs the Touchpad Speed Control extension.")
            row = Adw.ActionRow(
                title="Get Touchpad Speed Control", subtitle="extensions.gnome.org", activatable=True,
                tooltip_text="Open the extension's page in your browser",
            )
            row.add_suffix(Gtk.Image.new_from_icon_name("adw-external-link-symbolic"))
            row.connect("activated", lambda _: Gtk.UriLauncher.new(EXTENSION_URL).launch(self, None, None, None))
            group.add(row)
            return group

        group.set_description("Applied automatically. Try them out in the app itself.")
        group.set_header_suffix(self._build_add_button())
        self.per_app_group = group

        if not extension.is_enabled():
            off_row = Adw.ActionRow(title="Touchpad Speed Control is off", subtitle="Per-app speeds apply once it's on")
            turn_on = Gtk.Button(
                label="Turn On", valign=Gtk.Align.CENTER, tooltip_text="Turn on Touchpad Speed Control so per-app speeds apply"
            )
            turn_on.add_css_class("suggested-action")
            turn_on.connect("clicked", lambda _: (extension.enable(), group.remove(off_row)))
            off_row.add_suffix(turn_on)
            group.add(off_row)

        self.empty_row = Adw.ActionRow(title="No apps yet", subtitle="Use Add App to give an app its own speed")
        group.add(self.empty_row)
        for app_id in sorted((a for a in self.factors if a in self.apps), key=lambda a: self.apps[a].get_display_name()):
            self._add_app_row(app_id)
        self._update_empty_row()
        return group

    def _build_add_button(self) -> Gtk.MenuButton:
        self.search = Gtk.SearchEntry(placeholder_text="Search apps")
        self.app_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.app_list.add_css_class("navigation-sidebar")
        self.app_list.set_filter_func(self._matches_search)
        self.app_list.connect("row-activated", self._on_pick_app)
        self.search.connect("search-changed", lambda _: self.app_list.invalidate_filter())
        scroller = Gtk.ScrolledWindow(child=self.app_list, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_size_request(300, 340)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.append(self.search)
        box.append(scroller)
        self.popover = Gtk.Popover(child=box)
        self.popover.connect("show", lambda _: self.search.grab_focus())
        button = Gtk.MenuButton(
            popover=self.popover,
            valign=Gtk.Align.CENTER,
            child=Adw.ButtonContent(icon_name="list-add-symbolic", label="Add App"),
            tooltip_text="Give an app its own speed",
        )
        button.add_css_class("flat")
        self._refresh_app_list()
        return button

    def _build_demo(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="Try It", description="Swipe on the text with two fingers to feel the global speed."
        )
        buffer = Gtk.TextBuffer()
        buffer.set_text(demo_text())
        self.demo = Gtk.TextView(
            buffer=buffer, editable=False, cursor_visible=False, monospace=True,
            top_margin=12, bottom_margin=12, left_margin=16, right_margin=16, pixels_below_lines=8,
        )
        self.demo_scroller = Gtk.ScrolledWindow(child=self.demo, height_request=280)
        self.demo_scroller.get_vadjustment().connect("value-changed", self._on_demo_scroll)
        card = Gtk.Frame(child=self.demo_scroller)
        card.add_css_class("card")
        card.set_overflow(Gtk.Overflow.HIDDEN)

        self.demo_status = Gtk.Label(xalign=0, margin_top=12, wrap=True)
        self.demo_status.add_css_class("dim-label")
        group.add(card)
        group.add(self.demo_status)
        return group

    def _add_app_row(self, app_id: str) -> None:
        info = self.apps[app_id]
        row = Adw.ActionRow(title=info.get_display_name(), title_lines=1, activatable=False)
        row.add_prefix(app_icon(info, 32))
        remove = Gtk.Button(
            icon_name="user-trash-symbolic", tooltip_text=f"Remove {info.get_display_name()}; it will use the global speed"
        )
        control = SpeedControl(self.factors[app_id], lambda value: self._on_app_speed(app_id, value), remove)
        remove.connect("clicked", lambda _: self._remove_app(app_id))
        self.controls.add_widget(control)
        row.add_suffix(control)
        self.per_app_group.add(row)
        self.app_rows[app_id] = row

    def _refresh_app_list(self) -> None:
        self.app_list.remove_all()
        available = sorted(
            (info.get_display_name(), app_id) for app_id, info in self.apps.items() if app_id not in self.factors
        )
        for name, app_id in available:
            box = Gtk.Box(spacing=12, margin_top=4, margin_bottom=4)
            box.append(app_icon(self.apps[app_id], 24))
            box.append(Gtk.Label(label=name, xalign=0, ellipsize=Pango.EllipsizeMode.END))
            self.app_list.append(Gtk.ListBoxRow(child=box, name=app_id, tooltip_text=app_id))

    def _matches_search(self, row: Gtk.ListBoxRow) -> bool:
        query = self.search.get_text().strip().lower()
        app_id = row.get_name()
        return not query or query in self.apps[app_id].get_display_name().lower() or query in app_id.lower()

    def _update_empty_row(self) -> None:
        self.empty_row.set_visible(not self.app_rows)

    def _on_global(self, value: float) -> None:
        self._show_demo_speed(value)

        def save() -> None:
            if self.schemas:
                extension.save_global_factor(self.schemas, value)
            if not self._reapply_extension():
                wsf.write(wsf.Factors(value, value))

        self._later("global", save)

    def _on_app_speed(self, app_id: str, value: float) -> None:
        self.factors[app_id] = value
        self._save_app(app_id)

    def _on_pick_app(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        app_id = row.get_name()
        self.popover.popdown()
        self.search.set_text("")
        self.factors[app_id] = self.global_control.value
        self._add_app_row(app_id)
        self._refresh_app_list()
        self._update_empty_row()
        self._save_app(app_id)

    def _remove_app(self, app_id: str) -> None:
        del self.factors[app_id]
        self.per_app_group.remove(self.app_rows.pop(app_id))
        self._refresh_app_list()
        self._update_empty_row()
        self._save_app(app_id)

    def _save_app(self, app_id: str) -> None:
        self._unsaved[app_id] = self.factors.get(app_id)

        def save() -> None:
            changes, self._unsaved = self._unsaved, {}
            extension.update_app_factors(self.schemas, changes)
            self._reapply_extension()

        self._later("factors", save)

    def _reapply_extension(self) -> bool:
        if self.schemas is None or not extension.is_enabled():
            return False
        extension.reapply()
        return True

    def _show_demo_speed(self, value: float) -> None:
        self._demo_speed = f"Global speed {value:.2f}"
        self._update_demo_status()

    def _on_demo_scroll(self, _adjustment: Gtk.Adjustment) -> None:
        if self._swipe_timeout:
            GLib.source_remove(self._swipe_timeout)
        else:
            self._swipe_start = self._settled_line
        self._swipe_timeout = GLib.timeout_add(SWIPE_GAP_MS, self._end_swipe)

    def _end_swipe(self) -> bool:
        self._swipe_timeout = 0
        top = int(self.demo_scroller.get_vadjustment().get_value())
        line = self.demo.get_line_at_y(top)[0].get_line()
        moved = abs(line - self._swipe_start)
        self._settled_line = line
        if moved:
            self._last_swipe = f"Last swipe moved {moved} line{'s' if moved != 1 else ''}."
            self._update_demo_status()
        return GLib.SOURCE_REMOVE

    def _update_demo_status(self) -> None:
        self.demo_status.set_label(f"{self._last_swipe}  ·  {self._demo_speed}")

    def _later(self, key: str, action: Callable[[], None]) -> None:
        if key in self._pending:
            GLib.source_remove(self._pending[key][0])

        def run() -> bool:
            self._pending.pop(key)[1]()
            return GLib.SOURCE_REMOVE

        self._pending[key] = (GLib.timeout_add(SAVE_DELAY_MS, run), action)

    def _on_close(self, _window) -> bool:
        for source, action in self._pending.values():
            GLib.source_remove(source)
            action()
        self._pending.clear()
        return False


class ScrollGaugeApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self) -> None:
        window = self.props.active_window or ScrollGaugeWindow(self)
        window.present()


def main() -> int:
    return ScrollGaugeApp().run(None)
