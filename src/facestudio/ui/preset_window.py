from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.presets.library import DescriptorPresetLibrary
from facestudio.ui.batch_window import BatchMainWindow
from facestudio.ui.pages.descriptor_presets import DescriptorPresetsPage
from facestudio.utils.config import AppConfig


class PresetMainWindow(BatchMainWindow):
    """Alpha 0.9 shell with Face Library, Batch Analysis and Descriptor Presets."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.descriptor_preset_store = DescriptorPresetLibrary(
            config_path.parent / "descriptor-presets.json",
            config_path.parent / "descriptor-comparison-history.json",
        )
        self.descriptor_presets = DescriptorPresetsPage(
            self.descriptor_preset_store,
            self.face_library_store,
        )

        page_index = self.stack.count()
        self.stack.addWidget(self.descriptor_presets)
        preset_button = QPushButton("Descriptor Presets")
        preset_button.setObjectName("NavButton")
        preset_button.setCheckable(True)
        preset_button.clicked.connect(
            lambda checked=False, index=page_index: self.navigate(index)
        )
        self.nav_buttons.append(preset_button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 3), preset_button)
        self.apply_theme(self.config.theme)
