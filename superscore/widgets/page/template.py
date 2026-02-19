"""
Templating helpers.  Widgets for creating and filling templates.

TODO:
- consider {{}} in CA requests, seems to bait out caproto errors?
- UI/UX: consider creating template alone, without base collection?
- (to confirm) re-create timestamps when filling a template
- Open new collection in builder page?
"""

import logging
from enum import Enum
from functools import partial
from typing import ClassVar, Dict, Set

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.model import Collection, Entry, Template
from superscore.templates import (TemplateMode, fill_template_collection,
                                  find_placeholders, safe_replace)
from superscore.widgets.core import DataWidget, Display, NameDescTagsWidget
from superscore.widgets.manip_helpers import insert_widget
from superscore.widgets.views import (LivePVHeader, LivePVTableView,
                                      NestableHeader, NestableTableModel,
                                      NestableTableView, RootTreeView)

logger = logging.getLogger(__name__)


class FillColors(Enum):
    FILLED = (200, 255, 200)  # green
    PARTIAL = (255, 200, 100)  # orange
    MISSING = (255, 200, 200)  # red

    def to_qcolor(self, diag: bool = False) -> QtGui.QBrush:
        if diag:
            return QtGui.QBrush(QtGui.QColor(*self.value), QtCore.Qt.FDiagPattern)

        return QtGui.QBrush(QtGui.QColor(*self.value))

    def to_stylesheet(self):
        return f"background-color: rgb{self.value}"


class SubstitutionWidget(Display, QtWidgets.QWidget):
    filename = "substitution_widget.ui"

    pre_edit: QtWidgets.QLineEdit  # left
    post_edit: QtWidgets.QLineEdit  # right
    placeholder_label: QtWidgets.QLabel  # center
    arrow_label: QtWidgets.QLabel
    right_bracket: QtWidgets.QLabel
    left_bracket: QtWidgets.QLabel

    remove_button: QtWidgets.QToolButton

    changed: ClassVar[QtCore.Signal] = QtCore.Signal()

    def __init__(
        self,
        pre: str = "",
        post: str = "",
        mode: TemplateMode = TemplateMode.CREATE_PLACEHOLDERS,
        parent=None,
    ):
        """
        Sets up the widget depending on the mode

        If CREATE_PLACEHOLDERS:
        - pre -> left text edit
        - post -> right text edit

        If FILL_PLACEHOLDERS, there is only the fill-text edit to interact with:
        - pre -> center text label (not editable)
        - post -> right text edit
        """
        super().__init__(parent)
        self._mode = mode
        self._configure_mode()

        icon = self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarCloseButton)
        self.remove_button.setIcon(icon)
        self.placeholder_label.setText(pre + ":")
        self.pre_edit.setText(pre)
        self.post_edit.setText(post)

        self.pre_edit.textChanged.connect(self.changed.emit)
        self.post_edit.textChanged.connect(self.changed.emit)

    @property
    def mode(self):
        return self._mode

    def _configure_mode(self) -> None:
        if self.mode == TemplateMode.CREATE_PLACEHOLDERS:
            self.left_bracket.show()
            self.right_bracket.show()
            self.pre_edit.show()
            self.arrow_label.show()
            self.placeholder_label.hide()
            self.remove_button.show()
        elif self.mode == TemplateMode.FILL_PLACEHOLDERS:
            self.left_bracket.hide()
            self.right_bracket.hide()
            self.pre_edit.hide()
            self.arrow_label.hide()
            self.placeholder_label.show()
            self.remove_button.hide()


class HighlightProxyModel(QtCore.QIdentityProxyModel):
    """
    Responsible for highlighting placeholders and filling them if a substitution applies
    Placeholder is a preview collection that either
        - CREATE_PLACEHOLDERS: has no {{placeholders}} inserted
        - FILL_PLACEHOLDERS: has all relevant {{placeholders}} inserted,
                             but not filled
    """
    def __init__(
        self,
        placeholders: Dict[str, str],
        substitutions: Dict[str, str],
        mode: TemplateMode = TemplateMode.FILL_PLACEHOLDERS,
        parent=None
    ):
        super().__init__(parent)
        self.placeholders = placeholders
        self.substitutions = substitutions
        self.mode = mode

    def data(self, index: QtCore.QModelIndex, role: int):
        if role not in (QtCore.Qt.BackgroundRole, QtCore.Qt.DisplayRole,
                        QtCore.Qt.ToolTipRole):
            return

        # Get display data from source model
        source_model = self.sourceModel()
        val = source_model.data(index, QtCore.Qt.DisplayRole)
        if not isinstance(val, str):
            # TODO: does this actually ever trigger?
            return val

        if self.mode == TemplateMode.CREATE_PLACEHOLDERS:
            for replaced, placeholder in self.placeholders.items():
                if index.column() not in (
                    LivePVHeader.PV_NAME, NestableHeader.NAME,
                    NestableHeader.DESCRIPTION
                ):
                    break
                if replaced not in val:
                    continue
                val = safe_replace(val, replaced, f"{{{{{placeholder}}}}}")

            if role == QtCore.Qt.DisplayRole:
                return val
            elif role == QtCore.Qt.BackgroundRole and "{{" in val:
                return FillColors.PARTIAL.to_qcolor()

        elif self.mode == TemplateMode.FILL_PLACEHOLDERS:
            substitution_found = False
            for placeholder, substituted in self.substitutions.items():
                if index.column() not in (
                    LivePVHeader.PV_NAME, NestableHeader.NAME,
                    NestableHeader.DESCRIPTION
                ):
                    break
                if f"{{{{{placeholder}}}}}" not in val:
                    continue

                val = val.replace(f"{{{{{placeholder}}}}}", substituted)
                substitution_found = True

            # Check for unfilled placeholders
            if role == QtCore.Qt.DisplayRole:
                return val
            elif role == QtCore.Qt.BackgroundRole:
                if "{{" in val:
                    return FillColors.MISSING.to_qcolor()
                elif substitution_found:
                    return FillColors.FILLED.to_qcolor()
                # if no substitution performed and no placeholders, no color

        # Nestable coloring for non-string cells, for indicating
        # placeholders in nested collection
        if (isinstance(source_model, NestableTableModel)
                and role in (QtCore.Qt.BackgroundRole, QtCore.Qt.ToolTipRole)):
            entry = source_model.entries[index.row()]
            if self.mode == TemplateMode.CREATE_PLACEHOLDERS:
                filled_entry = fill_template_collection(
                    entry, self.placeholders, mode=TemplateMode.CREATE_PLACEHOLDERS
                )
                filled_entry_phs = find_placeholders(filled_entry)
                if filled_entry_phs:
                    if role == QtCore.Qt.BackgroundRole:
                        return FillColors.PARTIAL.to_qcolor(diag=True)
                    elif role == QtCore.Qt.ToolTipRole:
                        return f"Nested Placeholders: {filled_entry_phs}"

            if self.mode == TemplateMode.FILL_PLACEHOLDERS:
                orig_entry_phs = find_placeholders(entry)
                filled_entry = fill_template_collection(
                    entry, self.substitutions, mode=TemplateMode.FILL_PLACEHOLDERS
                )
                filled_entry_phs = find_placeholders(filled_entry)
                if filled_entry_phs:
                    if role == QtCore.Qt.BackgroundRole:
                        return FillColors.MISSING.to_qcolor(diag=True)
                    elif role == QtCore.Qt.ToolTipRole:
                        return f"Remaining Placeholders: {filled_entry_phs}"
                elif orig_entry_phs and (not filled_entry_phs):
                    return FillColors.FILLED.to_qcolor(diag=True)

        return super().data(index, role)


class HighlightNameDescTagsWidget(NameDescTagsWidget):
    def __init__(
        self,
        *args,
        placeholders: Dict[str, str],
        substitutions: Dict[str, str],
        mode: TemplateMode = TemplateMode.FILL_PLACEHOLDERS,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.placeholders = placeholders
        self.substitutions = substitutions
        self.mode = mode

        self.name_edit.setEnabled(False)
        self.desc_edit.setEnabled(False)
        self.tags_frame.setEnabled(False)

        self.configure_mode()

    def configure_mode(self):
        self.setup_highlighting(self.name_edit)
        self.setup_highlighting(self.desc_edit)

    def update_data(self, data: Entry) -> None:
        """
        Helper to update data after init.
        Overloading set_data attempts to access widgets before setupUi is called
        """
        self.set_data(data)
        self.init_name()
        self.init_desc()

    def update_saved_desc(self) -> None:
        """
        Avoid writing back to the bridge when replacing.  For some reason I
        can't disconnect the slot specifically, so we nuke the method here
        """
        pass

    def setup_highlighting(self, text_edit: QtWidgets.QLineEdit | QtWidgets.QPlainTextEdit):
        # make a copy of the string to not modify the original
        if isinstance(text_edit, QtWidgets.QLineEdit):
            val = str(self.data.title)
        elif isinstance(text_edit, QtWidgets.QPlainTextEdit):
            val = str(self.data.description)

        style_sheet = ""
        if self.mode == TemplateMode.CREATE_PLACEHOLDERS:
            for replaced, placeholder in self.placeholders.items():
                if replaced not in val:
                    continue
                val = safe_replace(val, replaced, f"{{{{{placeholder}}}}}")

            if any(f"{{{{{p}}}}}" in val for p in self.placeholders.values()):
                style_sheet = FillColors.PARTIAL.to_stylesheet()

        elif self.mode == TemplateMode.FILL_PLACEHOLDERS:
            # Fill in placeholders, remember if we actually do this
            sub_found = False
            for placeholder, substituted in self.substitutions.items():
                if f"{{{{{placeholder}}}}}" not in val:
                    continue

                val = val.replace(f"{{{{{placeholder}}}}}", substituted)
                sub_found = True

            if "{{" in val:
                style_sheet = FillColors.MISSING.to_stylesheet()
            elif ("{{" not in val) and sub_found:
                style_sheet = FillColors.FILLED.to_stylesheet()

        if isinstance(text_edit, QtWidgets.QLineEdit):
            text_edit.setText(val)
        elif isinstance(text_edit, QtWidgets.QPlainTextEdit):
            text_edit.setPlainText(val)

        text_edit.setStyleSheet(style_sheet)


class LegendBadge(QtWidgets.QLabel):
    def __init__(self, color, pattern, text):
        super().__init__(text)
        self.color = color
        self.pattern = pattern
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setMargin(5)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        brush = QtGui.QBrush(QtGui.QColor(*self.color), self.pattern)

        # Draw background pattern
        painter.fillRect(self.rect(), brush)

        # Call super to draw the actual label text on top
        super().paintEvent(event)


class LegendLabel(QtWidgets.QLabel):
    def __init__(self, brush, text):
        super().__init__(text)
        self.brush = brush
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setMargin(5)

    def paintEvent(self, a0):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self.brush)
        super().paintEvent(a0)


class TemplateLegendWidget(QtWidgets.QWidget):
    """simple template widget"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(LegendLabel(
            FillColors.FILLED.to_qcolor(), "Placeholder Fully Filled"),
            0, 0,
        )
        layout.addWidget(LegendLabel(
            FillColors.FILLED.to_qcolor(diag=True), "(in nested Collection)"),
            0, 1,
        )
        layout.addWidget(LegendLabel(
            FillColors.PARTIAL.to_qcolor(), "Placeholders Found"),
            1, 0,
        )
        layout.addWidget(LegendLabel(
            FillColors.PARTIAL.to_qcolor(diag=True), "(in nested Collection)"),
            1, 1,
        )
        layout.addWidget(LegendLabel(
            FillColors.MISSING.to_qcolor(), "Substitutions Missing"),
            2, 0,
        )
        layout.addWidget(LegendLabel(
            FillColors.MISSING.to_qcolor(diag=True), "(in nested Collection)"),
            2, 1,
        )
        self.setLayout(layout)


class TemplatePage(Display, DataWidget[Template]):
    """
    A dual purpose page, for creating templates from collections and also filling
    existing placeholders with desired information.

    Left panel ("Placeholder Insertions") is for replacing existing substrings with
    placeholder templates (e.g. {{placeholder_text}})
    - These widgets are "placeholder_*"

    Right panel ("Template Substitutions") is for replacing templates with
    new desired text
    - These widgets are "substitute_*"
    """
    filename = 'template_page.ui'

    meta_placeholder: QtWidgets.QWidget
    meta_widget: NameDescTagsWidget

    legend_placeholder: QtWidgets.QWidget
    legend: TemplateLegendWidget

    templated_meta_placeholder: QtWidgets.QWidget
    templated_meta_widget: HighlightNameDescTagsWidget

    substitute_panel: QtWidgets.QFrame
    substitute_container: QtWidgets.QWidget

    create_placeholders_panel: QtWidgets.QFrame
    placeholder_container: QtWidgets.QWidget

    tree_view: RootTreeView
    sub_pv_table_view: LivePVTableView
    sub_coll_table_view: NestableTableView

    create_coll_button: QtWidgets.QPushButton
    swap_mode_button: QtWidgets.QPushButton
    add_placeholder_button: QtWidgets.QPushButton
    save_button: QtWidgets.QPushButton

    placeholder_widgets: Set[SubstitutionWidget]
    substitution_widgets: Dict[str, SubstitutionWidget]
    preview_collection: Collection

    def __init__(
        self,
        *args,
        data: Template,
        editable: bool = False,
        mode: TemplateMode = TemplateMode.CREATE_PLACEHOLDERS,
        **kwargs
    ):
        super().__init__(*args, data=data, **kwargs)
        # For creating new placeholders
        self.placeholder_widgets: Set[SubstitutionWidget] = set()
        # For filling placeholders with values
        self.substitution_widgets: Dict[str, SubstitutionWidget] = {}
        self.preview_collection = fill_template_collection(
            self.data.template_collection, {}, new_uuids=True
        )
        self._mode = mode
        # Ensure template collection is filled
        if self.client:
            self.client.fill(self.data)

        self.setup_ui()
        self.update_preview()

    @property
    def mode(self) -> TemplateMode:
        return self._mode

    def swap_mode(self) -> None:
        self._mode = ~self._mode
        self._configure_mode()
        self.update_preview()

    def _configure_mode(self) -> None:
        """
        On mode switch:
        - create an appropriate preview collection for the case
        - show/hide right/left panel
        - if showing right panel
            - apply proposed placeholders to collection
            - collect placeholders
            - create substitution widgets
        """
        # refresh internal data and clear widgets, toggle proxy models
        if self.mode == TemplateMode.CREATE_PLACEHOLDERS:
            self.create_placeholders_panel.show()
            self.substitute_panel.hide()
            self.swap_mode_button.setText("Fill Placeholders >")
            self.preview_collection = fill_template_collection(
                self.data.template_collection, {}, new_uuids=False
            )
        else:
            self.create_placeholders_panel.hide()
            self.substitute_panel.show()
            self.swap_mode_button.setText("< Create Placeholders")
            # Fill preview and make new placeholders
            new_placeholders = self.get_placeholders()
            self.preview_collection = fill_template_collection(
                self.data.template_collection, new_placeholders,
                new_uuids=False, mode=TemplateMode.CREATE_PLACEHOLDERS,
            )

            # clear existing substitution widgets:
            for old_ph_widget in self.substitution_widgets.values():
                self.substitute_container.layout().removeWidget(old_ph_widget)
                old_ph_widget.hide()
                old_ph_widget.deleteLater()
            self.substitution_widgets.clear()

            for ph in sorted(new_placeholders.values(), reverse=True):
                sub_widget = SubstitutionWidget(
                    pre=ph, mode=TemplateMode.FILL_PLACEHOLDERS
                )
                sub_widget.changed.connect(self.update_preview)
                layout: QtWidgets.QVBoxLayout = self.substitute_container.layout()
                layout.insertWidget(0, sub_widget)
                self.substitution_widgets[ph] = sub_widget

        self.tree_view.set_data(self.preview_collection)
        self.sub_pv_table_view.set_data(self.preview_collection)
        self.sub_coll_table_view.set_data(self.preview_collection)
        self.templated_meta_widget.update_data(self.preview_collection)

    def setup_ui(self):
        self.meta_widget = NameDescTagsWidget(data=self.data, is_independent=False)
        insert_widget(self.meta_widget, self.meta_placeholder)

        self.legend_widget = TemplateLegendWidget()
        insert_widget(self.legend_widget, self.legend_placeholder)

        for orig_str, ph_str in self.data.placeholders.items():
            self.add_placeholder(orig_str, ph_str)

        # all views share preview Collection
        self.tree_view.client = self.client
        self.tree_view.set_data(self.preview_collection, is_independent=False)

        self.sub_pv_table_view.client = self.client
        self.sub_pv_table_view.set_data(self.preview_collection, is_independent=False)
        stored_headers = (LivePVHeader.STORED_VALUE,
                          LivePVHeader.STORED_STATUS,
                          LivePVHeader.STORED_SEVERITY,
                          LivePVHeader.REMOVE)
        for header in stored_headers:
            self.sub_pv_table_view.setColumnHidden(header, True)

        self.sub_coll_table_view.client = self.client
        self.sub_coll_table_view.set_data(self.preview_collection, is_independent=False)

        self._setup_proxies()

        self.add_placeholder_button.clicked.connect(partial(self.add_placeholder, "", ""))
        self.create_coll_button.clicked.connect(self.create_collection)
        self.swap_mode_button.clicked.connect(self.swap_mode)
        self.save_button.clicked.connect(self.save_template)

        self._configure_mode()

    def _setup_proxies(self):
        """Set up proxy models and highlighted metadata widget"""
        self.pv_proxy = HighlightProxyModel(
            self.get_placeholders(), self.get_substitutions(), parent=self, mode=self.mode
        )
        self.pv_proxy.setSourceModel(self.sub_pv_table_view.model())
        self.sub_pv_table_view.setModel(self.pv_proxy)

        # TODO: decide if we want to recurse through Collection templates
        self.coll_proxy = HighlightProxyModel(
            self.get_placeholders(), self.get_substitutions(), parent=self
        )
        self.coll_proxy.setSourceModel(self.sub_coll_table_view.model())
        self.sub_coll_table_view.setModel(self.coll_proxy)

        self.tree_proxy = HighlightProxyModel(
            self.get_placeholders(), self.get_substitutions(), parent=self
        )
        self.tree_proxy.setSourceModel(self.tree_view.model())
        self.tree_view.setModel(self.tree_proxy)

        self.templated_meta_widget = HighlightNameDescTagsWidget(
            data=self.preview_collection,
            is_independent=False,
            placeholders=self.get_placeholders(),
            substitutions=self.get_substitutions()
        )
        insert_widget(self.templated_meta_widget, self.templated_meta_placeholder)

    def add_placeholder(
        self,
        orig_str: str = "",
        placeholder_str: str = ""
    ) -> None:
        ph_widget = SubstitutionWidget(
            pre=orig_str,
            post=placeholder_str,
            mode=TemplateMode.CREATE_PLACEHOLDERS,
        )
        self.placeholder_widgets.add(ph_widget)
        self.placeholder_container.layout().insertWidget(0, ph_widget)

        def _remove_slot():
            self.placeholder_widgets.remove(ph_widget)
            self.placeholder_container.layout().removeWidget(ph_widget)
            ph_widget.hide()
            ph_widget.deleteLater()
            self.update_preview()

        ph_widget.remove_button.clicked.connect(_remove_slot)
        ph_widget.changed.connect(self.update_preview)

    def get_substitutions(self) -> dict[str, str]:
        return {placeholder: widget.post_edit.text()
                for placeholder, widget in self.substitution_widgets.items()
                if widget.post_edit.text()}

    @property
    def placeholder_strs(self) -> set[str]:
        return set(self.get_placeholders().keys())

    def get_placeholders(self) -> dict[str, str]:
        """Gather substring -> placeholder mapping"""
        return {widget.pre_edit.text(): widget.post_edit.text()
                for widget in self.placeholder_widgets
                if widget.pre_edit.text()}

    def update_preview(self):
        """Update the preview collection"""
        if self.preview_collection is None:
            return

        subs = self.get_substitutions()
        new_placeholders = self.get_placeholders()

        for proxy in [self.pv_proxy, self.coll_proxy,
                      self.tree_proxy, self.templated_meta_widget]:
            proxy.substitutions = subs
            proxy.placeholders = new_placeholders
            proxy.mode = self.mode

        # Trigger model refresh
        for view in [self.sub_pv_table_view, self.sub_coll_table_view, self.tree_view]:
            if view.model():
                view.model().layoutChanged.emit()

        self.templated_meta_widget.configure_mode()

    def save_template(self):
        """Create and save template"""
        if self.client is None:
            return

        self.data.placeholders = self.get_placeholders()
        self.client.save(self.data)

    def create_collection(self):
        """Finalize and save the filled collection"""
        subs = self.get_substitutions()
        filled = fill_template_collection(self.data.template_collection, subs, new_uuids=True)

        # Open in a new collection builder page for review before saving
        if self.open_page_slot:
            window = self.get_window()
            if window is not None:
                window.open_page(filled)
                logger.info("Created collection from template, opened for review.")

    def closeEvent(self, a0: QCloseEvent) -> None:
        logger.debug(f"Stopping polling threads for {type(self.data)}")
        self.sub_pv_table_view._model.stop_polling(wait_time=5000)
        return super().closeEvent(a0)
