#!/usr/bin/env python3
"""planter — a TUI task planner organized by features"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widgets import Button, Footer, Input, Label, ListItem, ListView, Static

PASTEL_GREEN = Theme(
    name="planter-green",
    primary="#4a8c5c",
    secondary="#6aab7a",
    accent="#3d7a50",
    background="#f2f8f3",
    surface="#e4f2e8",
    panel="#d3e9d9",
    boost="#c2dfc9",
    foreground="#1c3825",
    warning="#c97d2a",
    error="#b84040",
    success="#3a7d4e",
    dark=False,
    variables={
        "block-cursor-background":         "#8fcca0",
        "block-cursor-foreground":         "#1c3825",
        "block-cursor-text-style":         "none",
        "block-cursor-blurred-background": "#b8dfc4",
        "block-cursor-blurred-foreground": "#1c3825",
        "block-cursor-blurred-text-style": "none",
    },
)

DATA_FILE = Path.home() / ".planter" / "data.json"

STATUSES = ["todo", "in-progress", "done", "blocked"]

STATUS_COLOR = {
    "todo":        "dim",
    "in-progress": "yellow",
    "done":        "green",
    "blocked":     "red",
}

CATEGORIES = {
    "Note":    "cyan",
    "Status":  "yellow",
    "Blocker": "red",
    "Update":  "green",
}


# ── Data layer ────────────────────────────────────────────────────────────────

def _uid() -> str:
    return str(uuid.uuid4())[:8]


def load() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {"features": []}


def save(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))


def add_feature(data: dict, name: str) -> dict:
    f = {"id": _uid(), "name": name, "tasks": []}
    data["features"].append(f)
    return f


def add_task(data: dict, feature_id: str, title: str) -> dict:
    t = {
        "id": _uid(),
        "title": title,
        "status": "todo",
        "created_at": datetime.now().isoformat(),
        "notes": [],
    }
    for f in data["features"]:
        if f["id"] == feature_id:
            f["tasks"].append(t)
            break
    return t


def add_note(data: dict, task_id: str, body: str, category: str = "Note") -> None:
    note = {"body": body, "timestamp": datetime.now().isoformat(), "category": category}
    for f in data["features"]:
        for t in f["tasks"]:
            if t["id"] == task_id:
                t["notes"].append(note)
                return


def set_status(data: dict, task_id: str, status: str) -> None:
    for f in data["features"]:
        for t in f["tasks"]:
            if t["id"] == task_id:
                t["status"] = status
                return


def delete_task_by_id(data: dict, task_id: str) -> None:
    for f in data["features"]:
        f["tasks"] = [t for t in f["tasks"] if t["id"] != task_id]


def delete_feature_by_id(data: dict, feature_id: str) -> None:
    data["features"] = [f for f in data["features"] if f["id"] != feature_id]


def rename_feature(data: dict, feature_id: str, name: str) -> None:
    for f in data["features"]:
        if f["id"] == feature_id:
            f["name"] = name
            return


def rename_task(data: dict, task_id: str, title: str) -> None:
    for f in data["features"]:
        for t in f["tasks"]:
            if t["id"] == task_id:
                t["title"] = title
                return


# ── Modals ───────────────────────────────────────────────────────────────────

MODAL_CSS = """
.modal-box {
    width: 60;
    height: auto;
    border: thick $primary;
    background: $surface;
    padding: 1 2;
}
.modal-heading {
    text-align: center;
    margin-bottom: 1;
    text-style: bold;
}
.modal-buttons {
    align: center middle;
    margin-top: 1;
}
.modal-buttons Button { margin: 0 1; }
"""


class TextInputModal(ModalScreen):
    CSS = f"""
    TextInputModal {{ align: center middle; }}
    {MODAL_CSS}
    """
    BINDINGS = [Binding("escape", "dismiss_modal", "Cancel", show=False)]

    def __init__(self, heading: str, placeholder: str = "", initial: str = ""):
        super().__init__()
        self._heading = heading
        self._placeholder = placeholder
        self._initial = initial

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label(self._heading, classes="modal-heading")
            yield Input(value=self._initial, placeholder=self._placeholder)
            with Horizontal(classes="modal-buttons"):
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        inp = self.query_one(Input)
        inp.focus()
        inp.cursor_position = len(self._initial)

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            val = self.query_one(Input).value.strip()
            self.dismiss(val or None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        self.dismiss(val or None)


class StatusModal(ModalScreen):
    CSS = f"""
    StatusModal {{ align: center middle; }}
    .modal-box {{ width: 28; }}
    {MODAL_CSS}
    Button {{ width: 100%; margin-bottom: 1; }}
    """
    BINDINGS = [Binding("escape", "dismiss_modal", "Cancel", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label("Set Status", classes="modal-heading")
            for s in STATUSES:
                c = STATUS_COLOR.get(s, "white")
                yield Button(f"[{c}]{s}[/{c}]", id=f"s-{s}")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("s-"):
            self.dismiss(bid[2:])


class ConfirmModal(ModalScreen):
    CSS = f"""
    ConfirmModal {{ align: center middle; }}
    .modal-box {{ width: 50; }}
    {MODAL_CSS}
    """
    BINDINGS = [Binding("escape", "dismiss_modal", "Cancel", show=False)]

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label(self._message, classes="modal-heading")
            with Horizontal(classes="modal-buttons"):
                yield Button("Delete", variant="error", id="yes")
                yield Button("Cancel", id="cancel")

    def action_dismiss_modal(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)


class AddHistoryModal(ModalScreen):
    CSS = f"""
    AddHistoryModal {{ align: center middle; }}
    .modal-box {{ width: 70; }}
    {MODAL_CSS}
    .cat-label {{ margin-bottom: 0; }}
    .cat-row {{ height: 3; margin-bottom: 1; }}
    .cat-btn {{ min-width: 12; margin: 0 1 0 0; }}
    .cat-btn.active {{ background: $accent; color: $background; text-style: bold; }}
    """
    BINDINGS = [Binding("escape", "dismiss_modal", "Cancel", show=False)]

    def __init__(self, heading: str):
        super().__init__()
        self._heading = heading
        self._category = "Note"

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label(self._heading, classes="modal-heading")
            yield Label("Category:", classes="cat-label")
            with Horizontal(classes="cat-row"):
                for cat in CATEGORIES:
                    yield Button(cat, id=f"cat-{cat}", classes="cat-btn")
            yield Input(placeholder="Write your entry…")
            with Horizontal(classes="modal-buttons"):
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self._refresh_buttons()
        self.query_one(Input).focus()

    def _refresh_buttons(self) -> None:
        for cat in CATEGORIES:
            btn = self.query_one(f"#cat-{cat}", Button)
            if cat == self._category:
                btn.add_class("active")
            else:
                btn.remove_class("active")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("cat-"):
            self._category = bid[4:]
            self._refresh_buttons()
            event.stop()
            return
        if bid == "ok":
            val = self.query_one(Input).value.strip()
            self.dismiss((self._category, val) if val else None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        self.dismiss((self._category, val) if val else None)


# ── Main app ──────────────────────────────────────────────────────────────────

TCSS = """
Screen { layout: vertical; }

#main {
    layout: horizontal;
    height: 1fr;
}

#feature-panel {
    width: 22%;
    border: solid $primary;
    height: 100%;
}

#task-panel {
    width: 38%;
    border: solid $primary;
    height: 100%;
}

#note-panel {
    width: 40%;
    border: solid $primary;
    height: 100%;
}

.panel-title {
    background: $primary;
    color: $background;
    text-align: center;
    padding: 0 1;
    text-style: bold;
}

.panel-body { height: 1fr; }

ListView { height: 1fr; }

ListItem { padding: 0 1 1 1; }

ListItem.is-hovered { background: #ccdfd2; }
ListItem.--highlight.is-hovered { background: #a3d4b0; }

Footer { dock: bottom; }
"""


class _ListItem(ListItem):
    def on_enter(self) -> None:
        self.add_class("is-hovered")

    def on_leave(self) -> None:
        self.remove_class("is-hovered")


class PlanterApp(App):
    CSS = TCSS
    TITLE = "planter"

    BINDINGS = [
        Binding("f",       "add_feature",    "New Feature"),
        Binding("n",       "add_task",       "New Task"),
        Binding("s",       "set_status",     "Status"),
        Binding("a",       "add_note",       "Add Entry"),
        Binding("r",       "rename_task",    "Rename Task"),
        Binding("R",       "rename_feature", "Rename Feature", show=False),
        Binding("d",       "delete",         "Delete"),
        Binding("q",       "quit",           "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.data = load()
        self._feat_idx: int = 0
        self._task_idx: int = 0
        self._history_idx: int = 0
        self._rebuilding: bool = False

    # ── Layout ────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="feature-panel"):
                yield Static("  Features  ", classes="panel-title")
                yield ListView(id="feat-list", classes="panel-body")
            with Vertical(id="task-panel"):
                yield Static("  Tasks  ", classes="panel-title")
                yield ListView(id="task-list", classes="panel-body")
            with Vertical(id="note-panel"):
                yield Static("  History  ", classes="panel-title")
                yield ListView(id="history-list", classes="panel-body")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(PASTEL_GREEN)
        self.theme = "planter-green"
        self._rebuild_features()

    # ── Computed props ────────────────────────────────────────────────────

    @property
    def _sel_feature(self) -> Optional[dict]:
        fs = self.data["features"]
        return fs[self._feat_idx] if fs and 0 <= self._feat_idx < len(fs) else None

    @property
    def _sel_task(self) -> Optional[dict]:
        f = self._sel_feature
        if f and f["tasks"] and 0 <= self._task_idx < len(f["tasks"]):
            return f["tasks"][self._task_idx]
        return None

    # ── Rebuild helpers ───────────────────────────────────────────────────

    def _rebuild_features(self) -> None:
        self._rebuilding = True
        try:
            lv = self.query_one("#feat-list", ListView)
            lv.clear()
            for f in self.data["features"]:
                n = len(f["tasks"])
                lv.append(_ListItem(Label(f"  {f['name']}  ({n})")))
            if self.data["features"]:
                self._feat_idx = min(self._feat_idx, len(self.data["features"]) - 1)
                lv.index = self._feat_idx
        finally:
            self._rebuilding = False
        self._rebuild_tasks()

    def _rebuild_tasks(self) -> None:
        self._rebuilding = True
        try:
            lv = self.query_one("#task-list", ListView)
            lv.clear()
            f = self._sel_feature
            if f:
                for t in f["tasks"]:
                    c = STATUS_COLOR.get(t["status"], "white")
                    nn = len(t["notes"])
                    badge = f"  [dim]({nn} entries)[/dim]" if nn else ""
                    added = datetime.fromisoformat(t["created_at"]).strftime("%Y-%m-%d %H:%M")
                    lv.append(_ListItem(
                        Label(f"  [{c}]{t['status']:>11}[/{c}]  {t['title']}{badge}"),
                        Label(f"  [dim]added {added}[/dim]"),
                    ))
                if f["tasks"]:
                    self._task_idx = min(self._task_idx, len(f["tasks"]) - 1)
                    lv.index = self._task_idx
        finally:
            self._rebuilding = False
        self._rebuild_history()

    def _rebuild_history(self) -> None:
        self._rebuilding = True
        try:
            t = self._sel_task
            lv = self.query_one("#history-list", ListView)
            lv.clear()
            if not t or not t["notes"]:
                return
            for entry in reversed(t["notes"]):
                ts = datetime.fromisoformat(entry["timestamp"]).strftime("%Y-%m-%d  %H:%M")
                category = entry.get("category", "Note")
                color = CATEGORIES.get(category, "white")
                lv.append(_ListItem(
                    Label(f"  [{color}]\\[{category}][/{color}]  {entry['body']}"),
                    Label(f"  [dim]{ts}[/dim]"),
                ))
            if t["notes"]:
                self._history_idx = min(self._history_idx, len(t["notes"]) - 1)
                lv.index = self._history_idx
        finally:
            self._rebuilding = False

    # ── Events ────────────────────────────────────────────────────────────

    @on(ListView.Highlighted, "#feat-list")
    def _feat_highlighted(self, event: ListView.Highlighted) -> None:
        if self._rebuilding:
            return
        idx = event.list_view.index
        if idx is not None and idx != self._feat_idx:
            self._feat_idx = idx
            self._task_idx = 0
            self._history_idx = 0
            self._rebuild_tasks()

    @on(ListView.Highlighted, "#task-list")
    def _task_highlighted(self, event: ListView.Highlighted) -> None:
        if self._rebuilding:
            return
        idx = event.list_view.index
        if idx is not None and idx != self._task_idx:
            self._task_idx = idx
            self._history_idx = 0
            self._rebuild_history()

    @on(ListView.Highlighted, "#history-list")
    def _history_highlighted(self, event: ListView.Highlighted) -> None:
        if self._rebuilding:
            return
        idx = event.list_view.index
        if idx is not None:
            self._history_idx = idx

    # ── Actions ───────────────────────────────────────────────────────────

    def action_add_feature(self) -> None:
        def done(name: Optional[str]) -> None:
            if name:
                add_feature(self.data, name)
                save(self.data)
                self._feat_idx = len(self.data["features"]) - 1
                self._rebuild_features()
                self.call_later(self.query_one("#feat-list", ListView).focus)

        self.push_screen(TextInputModal("New Feature", "e.g. auth, backend, misc…"), done)

    def action_add_task(self) -> None:
        f = self._sel_feature
        if not f:
            self.notify("Create a feature first (press f).", severity="warning")
            return

        def done(title: Optional[str]) -> None:
            if title:
                add_task(self.data, f["id"], title)
                save(self.data)
                self._task_idx = len(f["tasks"]) - 1
                self._rebuild_tasks()

        self.push_screen(TextInputModal(f"New Task  [{f['name']}]", "Task title…"), done)

    def action_set_status(self) -> None:
        if not self._sel_task:
            self.notify("Select a task first.", severity="warning")
            return
        t = self._sel_task

        def done(status: Optional[str]) -> None:
            if status:
                old_status = t["status"]
                set_status(self.data, t["id"], status)
                add_note(self.data, t["id"], f"{old_status} → {status}", "Status")
                save(self.data)
                self._history_idx = 0
                self._rebuild_tasks()

        self.push_screen(StatusModal(), done)

    def action_add_note(self) -> None:
        if not self._sel_task:
            self.notify("Select a task first.", severity="warning")
            return
        t = self._sel_task

        def done(result) -> None:
            if result:
                category, body = result
                add_note(self.data, t["id"], body, category)
                save(self.data)
                self._rebuild_history()
                self.notify("Entry added.")

        self.push_screen(AddHistoryModal("Add History Entry"), done)

    def action_rename_task(self) -> None:
        t = self._sel_task
        if not t:
            self.notify("Select a task first.", severity="warning")
            return

        def done_task(title: Optional[str]) -> None:
            if title:
                rename_task(self.data, t["id"], title)
                save(self.data)
                self._rebuild_tasks()

        self.push_screen(TextInputModal("Rename Task", initial=t["title"]), done_task)

    def action_rename_feature(self) -> None:
        f = self._sel_feature
        if not f:
            self.notify("Select a feature first.", severity="warning")
            return

        def done_feat(name: Optional[str]) -> None:
            if name:
                rename_feature(self.data, f["id"], name)
                save(self.data)
                self._rebuild_features()

        self.push_screen(TextInputModal("Rename Feature", initial=f["name"]), done_feat)

    def action_delete(self) -> None:
        focused = self.focused
        if focused is self.query_one("#history-list", ListView):
            self._delete_entry()
        elif focused is self.query_one("#task-list", ListView):
            self._delete_task()
        else:
            self._delete_feature()

    def _delete_entry(self) -> None:
        t = self._sel_task
        if not t or not t["notes"]:
            self.notify("No history entries to delete.", severity="warning")
            return
        actual_idx = len(t["notes"]) - 1 - self._history_idx
        entry = t["notes"][actual_idx]

        def done(confirmed: Optional[bool]) -> None:
            if confirmed:
                t["notes"].pop(actual_idx)
                save(self.data)
                self._history_idx = max(0, self._history_idx - 1)
                self._rebuild_history()
                self._rebuild_tasks()
                self.notify("Entry deleted.")

        preview = entry["body"][:40] + ("…" if len(entry["body"]) > 40 else "")
        self.push_screen(ConfirmModal(f"Delete \"{preview}\"?"), done)

    def _delete_task(self) -> None:
        t = self._sel_task
        if not t:
            self.notify("Select a task first.", severity="warning")
            return

        def done(confirmed: Optional[bool]) -> None:
            if confirmed:
                delete_task_by_id(self.data, t["id"])
                save(self.data)
                self._task_idx = max(0, self._task_idx - 1)
                self._rebuild_tasks()
                self.notify(f"Deleted: {t['title']}")

        self.push_screen(ConfirmModal(f"Delete task \"{t['title']}\"?"), done)

    def _delete_feature(self) -> None:
        f = self._sel_feature
        if not f:
            self.notify("Select a feature first.", severity="warning")
            return

        def done(confirmed: Optional[bool]) -> None:
            if confirmed:
                delete_feature_by_id(self.data, f["id"])
                save(self.data)
                self._feat_idx = max(0, self._feat_idx - 1)
                self._rebuild_features()
                self.notify(f"Deleted feature: {f['name']}")

        self.push_screen(ConfirmModal(f"Delete feature \"{f['name']}\" and all its tasks?"), done)


if __name__ == "__main__":
    PlanterApp().run()
