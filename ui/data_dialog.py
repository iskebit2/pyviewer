# ui/data_dialog.py

import numpy
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QDialogButtonBox,
)


class DataDialog(QDialog):

    def __init__(self, data: Any, title="Data", parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(300, 400)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Parameter", "Value"])

        self.tree.setColumnWidth(0, 160)
        self.tree.header().setStretchLastSection(True)

        self.tree.setAlternatingRowColors(True)

        self._build_tree(data)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        layout.addWidget(buttons)


    # ---------------------------------------------------------
    # PUBLIC
    # ---------------------------------------------------------

    def set_data(self, data):
        self.tree.clear()
        self._build_tree(data)


    # ---------------------------------------------------------
    # TREE BUILDER
    # ---------------------------------------------------------

    def _build_tree(self, data):

        root = self.tree.invisibleRootItem()

        self._add_value(
            root,
            "Data",
            data
        )

        self.tree.expandToDepth(1)


    # ---------------------------------------------------------
    # RECURSIVE WALKER
    # ---------------------------------------------------------

    def _add_value(self, parent, name, value):

        if is_dataclass(value):

            item = self._add_branch(parent, name)

            for field in fields(value):
                self._add_value(
                    item,
                    field.name,
                    getattr(value, field.name)
                )

        elif isinstance(value, dict):

            item = self._add_branch(parent, name)

            for key, val in value.items():
                self._add_value(item, key, val)

        elif isinstance(value, (list, tuple)):

            item = self._add_branch(parent, name)

            for i, val in enumerate(value):
                self._add_value(item, f"[{i}]", val)

        else:

            self._add_leaf(
                parent,
                name,
                self._format_value(value)
            )


    # ---------------------------------------------------------
    # TREE ITEMS
    # ---------------------------------------------------------

    @staticmethod
    def _add_branch(parent, name):

        item = QTreeWidgetItem(parent)

        item.setText(0, str(name))

        return item


    @staticmethod
    def _add_leaf(parent, name, value):

        item = QTreeWidgetItem(parent)

        item.setText(0, str(name))
        item.setText(1, str(value))

        return item


    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _is_numpy_array(value):

        try:
            import numpy as np

            return isinstance(value, np.ndarray)

        except ImportError:

            return False


    @staticmethod
    def _is_object(value):

        """
        Dataclass, dict, list vb. özel yapılar dışındaki
        normal Python nesnelerini yakalar.
        """

        if value is None:
            return False

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
                bytes,
                complex
            )
        ):
            return False

        return hasattr(value, "__dict__")


    @staticmethod
    def _format_value(value):

        if value is None:
            return "None"

        if isinstance(value, float):

            return f"{value:g}"

        if isinstance(value, bool):

            return "True" if value else "False"

        return str(value)


# =============================================================
# CONVENIENCE FUNCTION
# =============================================================

def show_data(data, title="Data", parent=None):

    dialog = DataDialog(
        data,
        title=title,
        parent=parent
    )

    dialog.exec()
