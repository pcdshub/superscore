import json
import logging
from typing import Callable, Dict, Optional, Union

import qtawesome as qta
from qtpy.QtCore import QModelIndex, Qt
from qtpy.QtWidgets import (QAbstractItemView, QDialog, QFrame, QHBoxLayout,
                            QHeaderView, QInputDialog, QLabel, QLineEdit,
                            QMessageBox, QPushButton, QSizePolicy, QSpacerItem,
                            QTableWidget, QTableWidgetItem, QVBoxLayout,
                            QWidget)

from superscore.permission_manager import PermissionManager

logger = logging.getLogger(__name__)


class TagsDialog(QDialog):
    """
    Dialog for managing a tag group, including name, description and tags.

    This dialog has two modes:
    1. Admin mode: Full editing capabilities for name, description, and tags
    2. Read-only mode: Just viewing the group information without editing
    """

    def __init__(self,
                 group_name: str,
                 description: str,
                 tags_dict: Optional[Dict[int, str]] = None,
                 parent: Optional[QWidget] = None,
                 save_callback: Optional[Callable[[str, str, Dict[int, str]], None]] = None,
                 is_admin: bool = False,
                 row_index: Optional[int] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Tag Group")
        self.setMinimumSize(500, 600)
        self.original_group_name = group_name
        self.original_row = row_index
        self.tags_dict = tags_dict or {}
        self.save_callback = save_callback
        self.is_admin = is_admin

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        name_label: QLabel = QLabel("Title")
        layout.addWidget(name_label)

        if self.is_admin:
            self.name_input = QLineEdit(group_name)
        else:
            self.name_input = QLineEdit(group_name)
            self.name_input.setReadOnly(True)

        layout.addWidget(self.name_input)

        desc_label: QLabel = QLabel("Description")
        layout.addWidget(desc_label)

        if self.is_admin:
            self.desc_input = QLineEdit(description)
        else:
            self.desc_input = QLineEdit(description)
            self.desc_input.setReadOnly(True)

        layout.addWidget(self.desc_input)

        tags_label: QLabel = QLabel("Tags")
        layout.addWidget(tags_label)

        search_layout: QHBoxLayout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.textChanged.connect(self.filter_tags)
        search_layout.addWidget(self.search_input)

        if self.is_admin:
            add_button: QPushButton = QPushButton("+ Add New Tag")
            add_button.clicked.connect(self.add_new_tag)
            search_layout.addWidget(add_button)

        layout.addLayout(search_layout)

        self.tag_list = QTableWidget()

        if self.is_admin:
            self.tag_list.setColumnCount(3)
        else:
            self.tag_list.setColumnCount(1)

        self.tag_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        if self.is_admin:
            self.tag_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
            self.tag_list.setColumnWidth(1, 40)
            self.tag_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
            self.tag_list.setColumnWidth(2, 40)

        self.tag_list.horizontalHeader().setVisible(False)
        self.tag_list.verticalHeader().setVisible(False)
        self.tag_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tag_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tag_list.setShowGrid(False)
        self.tag_list.setFrameShape(QFrame.NoFrame)

        layout.addWidget(self.tag_list)

        self.populate_tag_list()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        if self.is_admin:
            save_button = QPushButton("Save")
            save_button.setFixedWidth(80)
            save_button.clicked.connect(self.save_changes)
            button_layout.addWidget(save_button)
        else:
            close_button = QPushButton("Close")
            close_button.setFixedWidth(80)
            close_button.clicked.connect(self.accept)
            button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def populate_tag_list(self) -> None:
        """
        Populate the tag list table with tags matching the current filter.
        """
        self.tag_list.setRowCount(0)

        filter_text = self.search_input.text().lower()

        for key, tag in self.tags_dict.items():
            if filter_text and filter_text not in tag.lower():
                continue

            row = self.tag_list.rowCount()
            self.tag_list.insertRow(row)

            item = QTableWidgetItem(tag)
            self.tag_list.setItem(row, 0, item)

            if self.is_admin:
                edit_button = QPushButton()
                edit_button.setIcon(qta.icon("msc.edit"))
                edit_button.setFlat(True)
                edit_button.clicked.connect(lambda _, k=key, r=row: self.edit_tag(k, r))
                edit_button.setProperty("tag_key", key)

                edit_widget = QWidget()
                edit_layout = QHBoxLayout(edit_widget)
                edit_layout.addWidget(edit_button)
                edit_layout.setAlignment(Qt.AlignCenter)
                edit_layout.setContentsMargins(0, 0, 0, 0)
                self.tag_list.setCellWidget(row, 1, edit_widget)

                delete_button = QPushButton()
                delete_button.setIcon(qta.icon("msc.trash"))
                delete_button.setFlat(True)
                delete_button.clicked.connect(lambda _, k=key: self.remove_tag(k))
                delete_button.setProperty("tag_key", key)

                delete_widget = QWidget()
                delete_layout = QHBoxLayout(delete_widget)
                delete_layout.addWidget(delete_button)
                delete_layout.setAlignment(Qt.AlignCenter)
                delete_layout.setContentsMargins(0, 0, 0, 0)
                self.tag_list.setCellWidget(row, 2, delete_widget)

    def filter_tags(self) -> None:
        """
        Filter the tag dict based on the search input.
        """
        self.populate_tag_list()

    def add_new_tag(self) -> None:
        """
        Add a new tag to the group.
        """
        tag, ok = QInputDialog.getText(self, "Add Tag", "Enter tag name:")
        if ok and tag:
            if tag in self.tags_dict.values():
                QMessageBox.warning(self, "Duplicate Tag",
                                    f"The tag '{tag}' already exists.")
            else:
                next_key = 0
                if self.tags_dict:
                    next_key = max(self.tags_dict.keys()) + 1

                self.tags_dict[next_key] = tag
                self.populate_tag_list()

    def edit_tag(self, key: int, row: int) -> None:
        """
        Edit a tag by its key.

        Parameters
        ----------
        key : int
            The dictionary key of the tag to edit
        row : int
            The row index in the table
        """
        current_tag = self.tags_dict[key]
        new_tag, ok = QInputDialog.getText(self, "Edit Tag", "Enter new tag name:", text=current_tag)
        if ok and new_tag and new_tag != current_tag:
            if new_tag in self.tags_dict.values():
                QMessageBox.warning(self, "Duplicate Tag",
                                    f"The tag '{new_tag}' already exists.")
            else:
                self.tags_dict[key] = new_tag
                self.populate_tag_list()

    def remove_tag(self, key: int) -> None:
        """
        Remove a tag from the group by its key.

        Parameters
        ----------
        key : int
            The dictionary key of the tag to remove
        """
        tag: str = self.tags_dict[key]
        confirm = QMessageBox.question(
            self,
            'Confirm Remove',
            f'Are you sure you want to remove the tag "{tag}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            del self.tags_dict[key]
            self.populate_tag_list()

    def save_changes(self) -> None:
        """
        Save all changes and close the dialog.
        """
        new_name: str = self.name_input.text()
        new_desc: str = self.desc_input.text()

        if not new_name:
            QMessageBox.warning(self, "Invalid Name", "Group name cannot be empty.")
            return

        parent = self.parent()

        if hasattr(parent, 'group_name_exists') and parent.group_name_exists(new_name, self.original_row):
            QMessageBox.warning(self, "Duplicate Name", f"A group with the name '{new_name}' already exists.")
            return

        if self.save_callback:
            self.save_callback(new_name, new_desc, self.tags_dict)

        self.accept()


class TagGroupsWindow(QWidget):
    """
    Main window for managing tag groups.

    This window allows users to create, edit, and delete tag groups, as well as
    manage the tags within each group.
    """

    def __init__(self, client) -> None:
        """
        Initialize the tag groups window.

        Sets up the UI and initializes the data structure for storing tag groups.
        """
        super().__init__()
        self.client = client

        self.permission_manager = PermissionManager.get_instance()
        self.permission_manager.admin_status_changed.connect(self.update_admin_status)

        self.setGeometry(100, 100, 800, 500)
        self.setWindowTitle("Tag Groups Manager")

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(600, 400)

        self.groups_data: dict[int, list[Union[str, str, dict[int, str]]]] = {}

        # self.setStyleSheet("background-color: #252525;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_frame = QFrame()
        main_frame.setFrameShape(QFrame.StyledPanel)
        frame_layout = QVBoxLayout(main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 4, 4, 4)

        title_label = QLabel("Tag Groups")
        # title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0e0e0; margin-bottom: 0px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        h_layout = QHBoxLayout()

        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        h_layout.addSpacerItem(spacer)

        self.new_group_button = QPushButton("+ New Group")
        self.new_group_button.setFixedWidth(100)
        self.new_group_button.clicked.connect(self.add_new_group)

        self.button_layout = h_layout

        if self.permission_manager.is_admin():
            h_layout.addWidget(self.new_group_button)

        main_layout.addLayout(h_layout)

        frame_layout.addWidget(header_widget)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        # self.table.setStyleSheet('QTableView::item {border-right: 1px solid #d6d9dc;}')

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self.handle_double_click)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.cellChanged.connect(self.handle_cell_changed)

        self.add_new_group()

        self.table.setColumnWidth(0, 100)  # Group name column
        self.table.setColumnWidth(1, 100)  # Tag count column
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Description column
        self.table.setColumnWidth(3, 80)  # Edit button column
        self.table.setColumnWidth(4, 80)  # Delete button column

        for i in range(self.table.rowCount()):
            self.table.setRowHeight(i, 50)

        frame_layout.addWidget(self.table)

        main_layout.addWidget(main_frame)

        '''
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
            }
            QTableWidget::item {
                padding: 5px;
            }
            alternate-background-color: #f0f0f0;
        """)
        '''

        self.table.setShowGrid(False)
        self.original_edit_triggers = QTableWidget.NoEditTriggers

        self.groups_data = self.client.backend.get_tags()
        self.rebuild_table_from_data()

    def get_group_name_from_row(self, row: int) -> str:
        """
        Get the group name from a specific row.

        Parameters
        ----------
        row : int
            The row index

        Returns
        -------
        str
            The group name displayed in that row
        """
        group_button = self.table.cellWidget(row, 0)
        return group_button.text() if group_button else f"New Group {row + 1}"

    def get_description_from_row(self, row: int) -> str:
        """
        Get the description from a specific row.

        Parameters
        ----------
        row : int
            The row index

        Returns
        -------
        str
            The description text in that row
        """
        desc_item = self.table.item(row, 2)
        return desc_item.text() if desc_item else "New group description"

    def update_group_data(self, row: int, name: str, description: str,
                          tags_dict: Optional[Dict[int, str]] = None) -> None:
        """
        Update the groups_data dictionary when group details change.

        Parameters
        ----------
        row : int
            The row index in the table
        name : str
            The name of the group
        description : str
            The updated description
        tags_dict : Dict[int, str], optional
            New dictionary of tags if provided, by default None
        """
        if tags_dict is not None:
            tag_dict = tags_dict
        elif row in self.groups_data:
            tag_dict = self.groups_data[row][2]
        else:
            tag_dict = {}

        self.groups_data[row] = [name, description, tag_dict]

    def delete_row(self, row: int) -> bool:
        """
        Delete a row from the table and its corresponding data.

        Parameters
        ----------
        row : int
            The row index to delete

        Returns
        -------
        bool
            True if the row was deleted, False otherwise
        """
        if row < 0 or row >= self.table.rowCount():
            logger.warning(f"Invalid row index: {row}")
            return False

        group_name = self.get_group_name_from_row(row)

        confirm = QMessageBox.question(
            self,
            'Confirm Delete',
            f'Are you sure you want to delete the group "{group_name}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            if row in self.groups_data:
                del self.groups_data[row]

            self.table.removeRow(row)

            return True

        return False

    def add_new_group(self) -> int:
        """
        Add a new group to the table and data structure.

        Returns
        -------
        int
            The row index of the newly added group
        """
        current_row = self.table.rowCount()

        base_name = "New Group"
        group_name = base_name
        counter = 1

        while self.group_name_exists(group_name):
            counter += 1
            group_name = f"{base_name} {counter}"

        self.table.insertRow(current_row)
        self.table.setRowHeight(current_row, 50)

        description = "New group description"

        self.groups_data[current_row] = [group_name, description, {}]

        group_button = QPushButton(group_name)
        '''
        group_button.setStyleSheet(
            "text-align: center; background-color: #f0f0f0; border-radius: 10px;")
        '''
        self.table.setCellWidget(current_row, 0, group_button)

        count_item = QTableWidgetItem("0 Tags")
        count_item.setFlags(count_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(current_row, 1, count_item)

        desc_item = QTableWidgetItem(description)
        desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(current_row, 2, desc_item)

        return current_row

    def group_name_exists(self, name: str, exclude_row: Optional[int] = None) -> bool:
        """
        Check if a group name already exists in the groups_data.

        Parameters
        ----------
        name : str
            The name to check
        exclude_row : Optional[int], default None
            Row to exclude from the check (useful when editing an existing group)

        Returns
        -------
        bool
            True if the name exists, False otherwise
        """
        for row, (group_name, _, _) in self.groups_data.items():
            if row != exclude_row and group_name.lower() == name.lower():
                return True
        return False

    def toggle_edit_mode(self) -> None:
        """
        Toggle the edit mode for a row.

        When entering edit mode, replaces the group name button with a line edit
        and makes the description editable. When exiting edit mode, saves the changes
        and restores the button.
        """
        button = self.sender()
        if not button:
            return

        current_row = -1
        for i in range(self.table.rowCount()):
            if self.table.cellWidget(i, 3) == button:
                current_row = i
                break

        if current_row < 0:
            return

        is_editing = button.property("editing")

        if not is_editing:
            self.table.setEditTriggers(QTableWidget.AllEditTriggers)

            group_button = self.table.cellWidget(current_row, 0)
            group_name = group_button.text() if group_button else "Group"

            button.setProperty("original_name", group_name)

            line_edit = QLineEdit(group_name)
            line_edit.setFrame(False)

            '''
            line_edit.setStyleSheet(
                "background-color: white; border: 1px solid #ccc; border-radius: 3px; padding: 3px;")
            '''
            self.table.setCellWidget(current_row, 0, line_edit)
            line_edit.selectAll()
            line_edit.setFocus()

            desc_item = self.table.item(current_row, 2)
            if desc_item:
                desc_item.setFlags(Qt.ItemIsEnabled |
                                   Qt.ItemIsEditable | Qt.ItemIsSelectable)

            button.setText("Save")
            button.setProperty("editing", True)

        else:
            line_edit = self.table.cellWidget(current_row, 0)
            new_name = ""

            if isinstance(line_edit, QLineEdit):
                new_name = line_edit.text()
            else:
                new_name = button.property("original_name") or "Group"

            if not new_name:
                new_name = "Group"

            if self.group_name_exists(new_name, current_row):
                QMessageBox.warning(self, "Duplicate Name",
                                    f"A group with the name '{new_name}' already exists.")
                return

            desc_item = self.table.item(current_row, 2)
            description = desc_item.text() if desc_item else "No description"

            self.update_group_data(current_row, new_name, description)

            self.table.removeCellWidget(current_row, 0)
            group_button = QPushButton(new_name)
            '''
            group_button.setStyleSheet(
                "text-align: center; background-color: #f0f0f0; border-radius: 10px;")
            '''
            self.table.setCellWidget(current_row, 0, group_button)

            if desc_item:
                desc_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            self.table.setEditTriggers(QTableWidget.NoEditTriggers)

            self.table.setSelectionBehavior(QTableWidget.SelectRows)

            button.setText("Edit")
            button.setProperty("editing", False)

    def edit_next_cell(self, row: int, column: int) -> None:
        """
        Move to the next editable cell after a cell has been edited.

        Parameters
        ----------
        row : int
            The current row
        column : int
            The current column
        """
        if column == 0:
            desc_item = self.table.item(row, 2)
            if desc_item:
                self.table.setCurrentCell(row, 2)
                self.table.editItem(desc_item)
        else:
            pass

    def handle_cell_changed(self, row: int, column: int) -> None:
        """
        Handle when a cell's content has changed.

        Moves to the next editable cell if in edit mode.

        Parameters
        ----------
        row : int
            The row of the changed cell
        column : int
            The column of the changed cell
        """
        edit_button = self.table.cellWidget(row, 3)
        if edit_button and edit_button.property("editing"):
            self.edit_next_cell(row, column)

    def get_all_data(self) -> Dict[int, list[Union[str, str, dict[int, str]]]]:
        """
        Return the entire groups data dictionary.

        Returns
        -------
        dict[int, list[str, str, dict[int, str]]]
            Dictionary with group names as keys and list of (tags set, description) as values
        """
        return self.groups_data

    def save_data(self, filename: str) -> bool:
        """
        Save the groups data to a file.

        Parameters
        ----------
        filename : str
            Path to the file where data should be saved

        Returns
        -------
        bool
            True if save was successful, False otherwise
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.groups_data, f, default=lambda o: list(o)
                          if isinstance(o, set) else o)
            return True
        except Exception as e:
            logger.debug(f"Error saving data: {e}")
            return False

    def load_data(self, filename: str) -> bool:
        """
        Load the groups data from a file.

        Parameters
        ----------
        filename : str
            Path to the file to load data from

        Returns
        -------
        bool
            True if load was successful, False otherwise
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            self.groups_data = {int(k): v for k, v in data.items()}

            self.rebuild_table_from_data()
            return True
        except Exception as e:
            logger.debug(f"Error loading data: {e}")
            return False

    def rebuild_table_from_data(self) -> None:
        """
        Rebuild the table based on the loaded data.

        Clears the current table and repopulates it with rows for each group
        in the groups_data dictionary.
        """
        self.table.setRowCount(0)

        for row, (group_name, description, tag_dict) in self.groups_data.items():
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            self.table.setRowHeight(row_idx, 50)

            group_button = QPushButton(group_name)
            '''
            group_button.setStyleSheet(
                "text-align: center; background-color: #f0f0f0; border-radius: 10px;")
            '''
            self.table.setCellWidget(row_idx, 0, group_button)

            tag_count: int = len(tag_dict)
            count_text: str = f"{tag_count} {'Tags' if tag_count != 1 else 'Tag'}"
            count_item = QTableWidgetItem(count_text)
            count_item.setFlags(count_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_idx, 1, count_item)

            desc_item = QTableWidgetItem(description)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_idx, 2, desc_item)

    def print_all_data(self) -> str:
        """
        Print all the group data in a readable format.

        Returns
        -------
        str
            String representation of the groups data dictionary
        """
        print("\n===== TAG GROUPS DATA =====")
        print(f"Total Groups: {len(self.groups_data)}")
        print("===========================")

        for row, (group_name, description, tag_dict) in self.groups_data.items():
            if isinstance(tag_dict, dict):
                tag_list = ", ".join(sorted(tag_dict.values())) if tag_dict else "No tags"
                tag_count = len(tag_dict)
            else:
                tag_list = str(tag_dict) if tag_dict else "No tags"
                tag_count = 0

            print(f"\nGROUP {row+1}: {group_name}")
            print(f"Description: {description}")
            print(f"Tags ({tag_count}): {tag_list}")
            print("---------------------------")

        print("\n")

        return str(self.groups_data)

    def handle_double_click(self, index: QModelIndex) -> None:
        """
        Handle double-click on a table row.

        Opens the tag dialog for the selected group, with editing capabilities
        only if the user is an admin.

        Parameters
        ----------
        index : QModelIndex
            The model index that was double-clicked
        """
        row = index.row()

        group_name = self.get_group_name_from_row(row)
        description = self.get_description_from_row(row)

        current_tags_dict = {}
        if row in self.groups_data and isinstance(self.groups_data[row][2], dict):
            current_tags_dict = self.groups_data[row][2]

        is_admin = self.permission_manager.is_admin()

        if is_admin:
            def save_group_data(new_name: str, new_desc: str, tags_dict: Dict[int, str]) -> None:
                self.update_group_data(row, new_name, new_desc, tags_dict)

                group_button = self.table.cellWidget(row, 0)
                if group_button:
                    group_button.setText(new_name)

                desc_item = self.table.item(row, 2)
                if desc_item:
                    desc_item.setText(new_desc)

                tag_count: int = len(tags_dict)
                count_text: str = f"{tag_count} {'Tags' if tag_count != 1 else 'Tag'}"
                count_item = self.table.item(row, 1)
                if count_item:
                    count_item.setText(count_text)

                self.client.backend.set_tags(self.groups_data)

            dialog: TagsDialog = TagsDialog(group_name, description, current_tags_dict if isinstance(current_tags_dict, dict) else None, self, save_group_data, is_admin=True, row_index=row)
        else:
            dialog: TagsDialog = TagsDialog(group_name, description, current_tags_dict if isinstance(current_tags_dict, dict) else None, self, is_admin=False, row_index=row)

        dialog.exec_()

    def update_admin_status(self, is_admin: bool) -> None:
        """
        Update the UI based on the current admin status.
        This method is called when admin status changes.

        Parameters
        ----------
        is_admin : bool
            Whether the current user is an admin
        """
        if is_admin:
            if not self.new_group_button.parent():
                self.button_layout.addWidget(self.new_group_button)
        else:
            if self.new_group_button.parent():
                self.button_layout.removeWidget(self.new_group_button)
                self.new_group_button.setParent(None)
