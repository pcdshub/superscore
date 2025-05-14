from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict, List, Union
from unittest.mock import MagicMock

import pytest
from qtpy.QtCore import QModelIndex, Qt
from qtpy.QtWidgets import (QApplication, QInputDialog, QMessageBox,
                            QPushButton, QWidget)

from superscore.widgets.configure_window import TagGroupsWindow, TagsDialog

# ---------------------------------------------------------------------------#
#                    ----------  stubs & fixtures  ----------                 #
# ---------------------------------------------------------------------------#


class _DummyBackend:
    """Minimal in-memory stand-in for the real backend."""

    def __init__(self) -> None:
        self._tags: Dict[int, List[Union[str, str, Dict[int, str]]]] = {}

    def get_tags(self) -> Dict[int, List[Union[str, str, Dict[int, str]]]]:
        return self._tags

    def set_tags(self, tags: Dict[int, List[Union[str, str, Dict[int, str]]]]) -> None:
        self._tags = tags


class _DummyClient:
    """Wrapper exposing the dummy backend via *backend* attribute."""

    def __init__(self) -> None:
        self.backend = _DummyBackend()


@pytest.fixture(scope="session")
def app() -> QApplication:
    """Provide a ``QApplication`` for the whole session."""
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def dummy_client() -> _DummyClient:
    """Return a fresh dummy client for each test."""
    return _DummyClient()


@pytest.fixture(autouse=True)
def always_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Replace ``PermissionManager`` with a stub that is **always** admin.

    Avoids signal wiring and logic branches unrelated to the unit tests.
    """
    from superscore.widgets import configure_window as cw

    pm = MagicMock()
    pm.is_admin.return_value = True
    pm.admin_status_changed.connect = MagicMock()
    monkeypatch.setattr(cw.PermissionManager, "get_instance", lambda: pm)


# ---------------------------------------------------------------------------#
#                        ----------  TagsDialog  ----------                   #
# ---------------------------------------------------------------------------#


def _dlg(
    *,
    parent: QWidget | None = None,
    tags: Dict[int, str] | None = None,
) -> TagsDialog:
    """Helper creating an **editable** ``TagsDialog``."""
    return TagsDialog(
        group_name="Group A",
        description="Desc",
        tags_dict=tags or {0: "one", 1: "two"},
        parent=parent,
        save_callback=None,
        is_admin=True,
        row_index=0,
    )


def test_tagsdialog_populate_tag_list(app: QApplication) -> None:
    """`populate_tag_list` should list every tag when no filter is set."""
    dlg = _dlg()
    dlg.populate_tag_list()
    assert dlg.tag_list.rowCount() == len(dlg.tags_dict)


def test_tagsdialog_filter_tags(app: QApplication) -> None:
    """`filter_tags` narrows the table to the matching rows."""
    dlg = _dlg()
    dlg.search_input.setText("on")
    dlg.filter_tags()
    assert dlg.tag_list.rowCount() == 1
    assert dlg.tag_list.item(0, 0).text() == "one"


def test_tagsdialog_add_new_tag(monkeypatch: pytest.MonkeyPatch, app: QApplication) -> None:
    """`add_new_tag` inserts a brand-new tag when the user confirms."""
    dlg = _dlg()

    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("three", True))
    dlg.add_new_tag()

    assert "three" in dlg.tags_dict.values()
    assert dlg.tag_list.rowCount() == 3


def test_tagsdialog_edit_tag(monkeypatch: pytest.MonkeyPatch, app: QApplication) -> None:
    """`edit_tag` renames a tag after confirmation."""
    dlg = _dlg()
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("uno", True))
    dlg.edit_tag(0, 0)
    assert dlg.tags_dict[0] == "uno"


def test_tagsdialog_remove_tag(monkeypatch: pytest.MonkeyPatch, app: QApplication) -> None:
    """`remove_tag` deletes the entry when the user clicks *Yes*."""
    dlg = _dlg()
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.Yes)
    dlg.remove_tag(0)
    assert 0 not in dlg.tags_dict
    assert dlg.tag_list.rowCount() == 1


def test_tagsdialog_save_changes(monkeypatch: pytest.MonkeyPatch, app: QApplication) -> None:
    """`save_changes` invokes callback when the name is unique."""

    class _Parent(QWidget):
        def group_name_exists(self, *_a, **_k) -> bool:  # noqa: D401
            return False

    parent = _Parent()
    called: Dict[str, bool] = {"ok": False}

    def _cb(name: str, _d: str, _t: Dict[int, str]) -> None:
        called["ok"] = True
        assert name == "Group B"

    dlg = _dlg(parent=parent)
    dlg.save_callback = _cb
    dlg.name_input.setText("Group B")

    monkeypatch.setattr(QMessageBox, "warning", lambda *_a, **_k: None)
    dlg.save_changes()

    assert called["ok"] is True


# ---------------------------------------------------------------------------#
#                     ----------  TagGroupsWindow ----------                  #
# ---------------------------------------------------------------------------#


@pytest.fixture()
def window(dummy_client: _DummyClient) -> TagGroupsWindow:
    """
    Create a ``TagGroupsWindow`` **and** add one starter group so that
    row-based logic has something to work with.
    """
    w = TagGroupsWindow(dummy_client)
    if w.table.rowCount() == 0:
        w.add_new_group()
    return w


def test_get_group_name_from_row(window: TagGroupsWindow) -> None:
    """Row-0 name should start with *New Group* by default."""
    assert window.get_group_name_from_row(0).startswith("New Group")


def test_get_description_from_row(window: TagGroupsWindow) -> None:
    """Default description for row-0 should match constructor value."""
    assert window.get_description_from_row(0) == "New group description"


def test_update_group_data(window: TagGroupsWindow) -> None:
    """The internal dict must reflect updated values."""
    window.update_group_data(0, "X", "Y", {0: "a"})
    assert window.groups_data[0][0:2] == ["X", "Y"]


def test_delete_row(monkeypatch: pytest.MonkeyPatch, window: TagGroupsWindow) -> None:
    """Row is removed when the user confirms the delete dialog."""
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.Yes)
    assert window.delete_row(0) is True
    assert window.table.rowCount() == 0


def test_add_new_group(window: TagGroupsWindow) -> None:
    """`add_new_group` appends a new row and reports its index."""
    idx = window.add_new_group()
    assert idx == 1
    assert window.table.rowCount() == 2


def test_group_name_exists(window: TagGroupsWindow) -> None:
    """Duplicate names (case-insensitive) must be detected."""
    name = window.get_group_name_from_row(0)
    assert window.group_name_exists(name) is True
    assert window.group_name_exists("totally-unique") is False


def test_toggle_edit_mode(window: TagGroupsWindow, qtbot) -> None:
    """First click should put the row into *editing* state."""
    window.table.setColumnCount(4)
    btn = QPushButton("Edit")
    window.table.setCellWidget(0, 3, btn)
    btn.clicked.connect(window.toggle_edit_mode)

    qtbot.mouseClick(btn, Qt.LeftButton)
    assert btn.property("editing") is True


def test_edit_next_cell(window: TagGroupsWindow) -> None:
    """After editing column-0, focus should move to column-2."""
    window.edit_next_cell(0, 0)
    assert window.table.currentColumn() == 2


def test_handle_cell_changed(window: TagGroupsWindow) -> None:
    """During edit mode the method delegates without crashing."""
    window.table.setColumnCount(4)
    btn = QPushButton("Edit")
    btn.setProperty("editing", True)
    window.table.setCellWidget(0, 3, btn)

    window.handle_cell_changed(0, 0)


def test_get_all_data(window: TagGroupsWindow) -> None:
    """Method returns the *identical* dict instance."""
    assert window.get_all_data() is window.groups_data


def test_save_and_load_data(tmp_path: Path, window: TagGroupsWindow) -> None:
    """Round-trip via JSON file preserves data."""
    file_ = tmp_path / "tags.json"
    original = copy.deepcopy(window.groups_data)

    assert window.save_data(str(file_))
    window.groups_data.clear()
    assert window.load_data(str(file_))
    assert window.groups_data == original


def test_rebuild_table_from_data(window: TagGroupsWindow) -> None:
    """Row count after rebuild must match the data dict size."""
    window.groups_data[1] = ["G2", "D2", {}]
    window.rebuild_table_from_data()
    assert window.table.rowCount() == 2


def test_print_all_data(capsys: pytest.CaptureFixture[str], window: TagGroupsWindow) -> None:
    """Method prints a summary and returns a string."""
    s = window.print_all_data()
    out = capsys.readouterr().out
    assert isinstance(s, str) and "TAG GROUPS DATA" in out


def test_handle_double_click(monkeypatch: pytest.MonkeyPatch, window: TagGroupsWindow) -> None:
    """Double-click creates a (patched) dialog and executes it modally."""
    made = {"done": False}

    class _FakeDialog:
        def __init__(self, *a, **kw) -> None:
            made["done"] = True

        def exec_(self) -> int:  # noqa: D401
            return 0

    monkeypatch.setattr("superscore.widgets.configure_window.TagsDialog", _FakeDialog)

    index: QModelIndex = window.table.model().index(0, 0)
    window.handle_double_click(index)

    assert made["done"]


def test_update_admin_status(window: TagGroupsWindow) -> None:
    """Button visibility toggles with admin status."""
    window.update_admin_status(False)
    assert window.new_group_button.parent() is None

    window.update_admin_status(True)
    assert window.new_group_button.parent() is not None
