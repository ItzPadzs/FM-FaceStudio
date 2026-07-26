from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.pack_tools.service import PackTestInstallService, PackValidationReport


class PackTestInstallPage(QWidget):
    def __init__(self, service: PackTestInstallService) -> None:
        super().__init__()
        self.service = service
        root = QVBoxLayout(self)
        title = QLabel("Pack Test & Install")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        summary = QLabel(
            "Validate a FaceStudio graphics pack, preview every file operation, install it into a selected Football Manager graphics folder and verify the copied result."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        form_box = QGroupBox("Folders")
        form = QFormLayout(form_box)
        self.pack_path = QLineEdit()
        self.graphics_path = QLineEdit()
        form.addRow("Built pack", self._path_row(self.pack_path, self.choose_pack))
        form.addRow("Graphics folder", self._path_row(self.graphics_path, self.choose_graphics))
        root.addWidget(form_box)

        suggestions = QGroupBox("Common graphics locations")
        suggestions_layout = QVBoxLayout(suggestions)
        self.suggestion_list = QListWidget()
        for path in self.service.suggested_graphics_dirs():
            self.suggestion_list.addItem(str(path))
        self.suggestion_list.itemDoubleClicked.connect(
            lambda item: self.graphics_path.setText(item.text())
        )
        suggestions_layout.addWidget(self.suggestion_list)
        suggestions_layout.addWidget(QLabel("Double-click a suggestion to use it, or select the folder manually."))
        root.addWidget(suggestions)

        buttons = QHBoxLayout()
        validate = QPushButton("Validate pack")
        validate.clicked.connect(self.validate_pack)
        dry_run = QPushButton("Preview installation")
        dry_run.clicked.connect(self.preview_install)
        install = QPushButton("Install pack")
        install.clicked.connect(self.install_pack)
        verify = QPushButton("Verify installed copy")
        verify.clicked.connect(self.verify_install)
        for button in (validate, dry_run, install, verify):
            buttons.addWidget(button)
        root.addLayout(buttons)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        root.addWidget(self.output, 1)

    def _path_row(self, edit: QLineEdit, callback) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit, 1)
        button = QPushButton("Browse")
        button.clicked.connect(callback)
        layout.addWidget(button)
        return widget

    def choose_pack(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select the built FaceStudio pack")
        if selected:
            self.pack_path.setText(selected)

    def choose_graphics(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select or create the Football Manager graphics folder")
        if selected:
            self.graphics_path.setText(selected)

    def validate_pack(self) -> None:
        report = self.service.validate_pack(Path(self.pack_path.text()).expanduser())
        self._show_report("Pack validation", report)

    def preview_install(self) -> None:
        pack, graphics = self._paths()
        if pack is None or graphics is None:
            return
        actions = self.service.dry_run(pack, graphics)
        self.output.setPlainText("Installation preview\n\n" + "\n".join(f"• {item}" for item in actions))

    def install_pack(self) -> None:
        pack, graphics = self._paths()
        if pack is None or graphics is None:
            return
        answer = QMessageBox.question(
            self,
            "Install graphics pack",
            "FaceStudio will copy the selected pack into the chosen graphics folder. An existing folder with the same name will be backed up first. Continue?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.service.install(pack, graphics)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Installation failed", str(exc))
            return
        self.output.setPlainText(
            "Installation completed and verified.\n\n"
            f"Installed to: {result['target']}\n"
            f"Backup: {result['backup'] or 'Not required'}\n"
            f"Mappings: {result['mapping_count']}\n"
            f"Portraits: {result['image_count']}\n\n"
            "Launch Football Manager, clear the skin cache where applicable, and reload the skin."
        )

    def verify_install(self) -> None:
        pack, graphics = self._paths()
        if pack is None or graphics is None:
            return
        report = self.service.verify_installed(graphics / pack.name)
        self._show_report("Installed-copy verification", report)

    def _paths(self) -> tuple[Path | None, Path | None]:
        pack_text = self.pack_path.text().strip()
        graphics_text = self.graphics_path.text().strip()
        if not pack_text or not graphics_text:
            QMessageBox.warning(self, "Folders required", "Select both the built pack and Football Manager graphics folder.")
            return None, None
        return Path(pack_text).expanduser(), Path(graphics_text).expanduser()

    def _show_report(self, heading: str, report: PackValidationReport) -> None:
        lines = [
            heading,
            "",
            f"Result: {'PASS' if report.valid else 'FAIL'}",
            f"Mappings: {report.mapping_count}",
            f"PNG portraits: {report.image_count}",
        ]
        if report.issues:
            lines.extend(["", "Errors:", *(f"• {item}" for item in report.issues)])
        if report.warnings:
            lines.extend(["", "Warnings:", *(f"• {item}" for item in report.warnings)])
        if report.valid and not report.warnings:
            lines.extend(["", "No problems were found."])
        self.output.setPlainText("\n".join(lines))
