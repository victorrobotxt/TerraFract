#!/usr/bin/env python3
"""
Graphical launcher for TerraFract – four side-by-side cards.

New in this version
-------------------
• Timelapse card now opens a setup dialog where the user can
  – select preset / seed / size / steps,
  – preview the initial terrain, and
  – choose the output MP4 file,
  before the erosion movie is rendered.
"""
from __future__ import annotations

import io
import os
import sys
import webbrowser
import random

import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QFileDialog,
    QSizePolicy, QDialog, QProgressBar, QMessageBox,
)

from terrafract.heightmap_generators import generate_heightmap
from terrafract.fractal_workbench import FractalWorkbench
from terrafract.stretch_goals import create_erosion_timelapse

# ───────────────────────────── presets ──────────────────────────────
PRESETS = {
    "Mountains": {"algorithm": "diamond-square", "roughness": 1.2},
    "Hills":     {"algorithm": "fbm",            "octaves": 4, "persistence": 0.6, "scale": 80},
    "Islands":   {"algorithm": "diamond-square", "roughness": 0.8},
    "Fjords":    {"algorithm": "fbm",            "octaves": 6, "persistence": 0.4, "scale": 40},
}

ICONS = {
    "Quick":     "🗺️",
    "Workbench": "🧑‍💻",
    "Timelapse": "⏱️",
    "Help":      "❓",
}

DESCRIPTIONS = {
    "Quick":     "One-click random map",
    "Workbench": "Full param playground",
    "Timelapse": "See erosion in motion",
    "Help":      "Docs & source code",
}

# ───────────────────────── helper: MPL ➜ QPixmap ───────────────────
def _matplotlib_to_pixmap(fig) -> QPixmap:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    pix = QPixmap()
    pix.loadFromData(buf.getvalue())
    return pix

# ───────────────────── timelapse worker thread ──────────────────────
class _TimelapseThread(QThread):
    progress = Signal(int)   # 0–100
    finished = Signal(str)   # output path when done

    def __init__(self, Z, steps, interval_ms, out_path):
        super().__init__()
        self.Z = Z
        self.steps = steps
        self.interval = interval_ms
        self.out = out_path

    def run(self):
        create_erosion_timelapse(
            self.Z,
            steps=self.steps,
            interval=self.interval,
            therm_iters=1,
            hydro_iters=1,
            output_path=self.out
        )
        self.progress.emit(100)
        self.finished.emit(self.out)

# ───────────────────── quick-PNG generator dialog ───────────────────
class _QuickDlg(QDialog):
    """
    Pick preset / seed / size and save a single PNG (no erosion).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Terrain")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.cb = QComboBox()
        self.cb.addItems(PRESETS)
        self.cb.currentTextChanged.connect(self._refresh)
        layout.addRow("Preset:", self.cb)

        self.seed = QSpinBox()
        self.seed.setRange(0, 9999)
        self.seed.valueChanged.connect(self._refresh)
        layout.addRow("Seed:", self.seed)

        self.sz = QSpinBox()
        self.sz.setRange(33, 1025)
        self.sz.setValue(257)
        self.sz.valueChanged.connect(self._refresh)
        layout.addRow("Size:", self.sz)

        hl = QHBoxLayout()
        self.path_lbl = QLabel("terrain.png")
        self.path_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn = QPushButton("Change…")
        btn.clicked.connect(self._pick_path)
        hl.addWidget(self.path_lbl)
        hl.addWidget(btn)
        layout.addRow("Save to:", hl)

        self.thumb = QLabel(alignment=Qt.AlignCenter)
        self.thumb.setFixedSize(200, 200)
        layout.addRow(self.thumb)

        ok = QPushButton("Generate")
        ok.clicked.connect(self.accept)
        layout.addRow(ok)

        self._refresh()

    # ---------- helpers ----------
    def _pick_path(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save PNG", "terrain.png", "PNG (*.png)")
        if p:
            self.path_lbl.setText(p)

    def _refresh(self):
        """Update thumbnail preview."""
        p = self.params.copy()
        p["size"] = min(p["size"], 64)  # quick low-res preview
        fig = None
        try:
            Z = generate_heightmap(**p)
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(2, 2), dpi=100)
            ax.imshow(Z, cmap="terrain")
            ax.axis("off")
            pix = _matplotlib_to_pixmap(fig)
            self.thumb.setPixmap(
                pix.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        finally:
            if fig:
                import matplotlib.pyplot as plt
                plt.close(fig)

    # ---------- API ----------
    @property
    def params(self) -> dict:
        p = PRESETS[self.cb.currentText()].copy()
        p.update(seed=self.seed.value(), size=self.sz.value())
        return p

    @property
    def out_path(self) -> str:
        return self.path_lbl.text()

# ─────────────────── timelapse setup dialog (NEW) ────────────────────
class _TimelapseDlg(QDialog):
    """
    Pick preset / seed / size / steps, preview the terrain,
    and choose where the MP4 timelapse will be saved.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timelapse Setup")
        self.setMinimumWidth(420)

        layout = QFormLayout(self)

        # --- same controls as quick PNG ---
        self.cb = QComboBox()
        self.cb.addItems(PRESETS)
        self.cb.currentTextChanged.connect(self._refresh)
        layout.addRow("Preset:", self.cb)

        self.seed = QSpinBox()
        self.seed.setRange(0, 9999)
        self.seed.setValue(random.randint(0, 9999))
        self.seed.valueChanged.connect(self._refresh)
        layout.addRow("Seed:", self.seed)

        self.sz = QSpinBox()
        self.sz.setRange(64, 1025)
        self.sz.setValue(256)
        self.sz.valueChanged.connect(self._refresh)
        layout.addRow("Size:", self.sz)

        # --- timelapse-specific ---
        self.steps = QSpinBox()
        self.steps.setRange(10, 600)
        self.steps.setValue(60)
        layout.addRow("Steps:", self.steps)

        hl = QHBoxLayout()
        self.path_lbl = QLabel("timelapse.mp4")
        self.path_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn = QPushButton("Change…")
        btn.clicked.connect(self._pick_path)
        hl.addWidget(self.path_lbl)
        hl.addWidget(btn)
        layout.addRow("Save to:", hl)

        self.thumb = QLabel(alignment=Qt.AlignCenter)
        self.thumb.setFixedSize(200, 200)
        layout.addRow(self.thumb)

        ok = QPushButton("Start rendering")
        ok.clicked.connect(self.accept)
        layout.addRow(ok)

        self._refresh()

    # ---------- helpers ----------
    def _pick_path(self):
        p, _ = QFileDialog.getSaveFileName(
            self, "Save timelapse", "timelapse.mp4", "MP4 (*.mp4)"
        )
        if p:
            self.path_lbl.setText(p)

    def _refresh(self):
        """Update preview thumbnail."""
        p = self.params.copy()
        p["size"] = min(p["size"], 64)
        fig = None
        try:
            Z = generate_heightmap(**p)
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(2, 2), dpi=100)
            ax.imshow(Z, cmap="terrain")
            ax.axis("off")
            pix = _matplotlib_to_pixmap(fig)
            self.thumb.setPixmap(
                pix.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        finally:
            if fig:
                import matplotlib.pyplot as plt
                plt.close(fig)

    # ---------- API ----------
    @property
    def params(self) -> dict:
        p = PRESETS[self.cb.currentText()].copy()
        p.update(seed=self.seed.value(), size=self.sz.value())
        return p

    @property
    def out_path(self) -> str:
        return self.path_lbl.text()

    @property
    def steps_val(self) -> int:
        return self.steps.value()

# ───────────────────────────── main window ───────────────────────────
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TerraFract")
        self.resize(720, 240)

        layout = QHBoxLayout(self)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignCenter)

        for label in ("Quick", "Workbench", "Timelapse", "Help"):
            layout.addWidget(self._make_card(label))

    # ---------- card helper ----------
    def _make_card(self, label: str) -> QPushButton:
        btn = QPushButton()
        btn.setMinimumSize(160, 160)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            "  border:1px solid #444;"
            "  border-radius:8px;"
            "  background:#252525;"
            "}"
            "QPushButton:hover {"
            "  background:#333;"
            "}"
        )

        # inside layout
        box = QVBoxLayout(btn)
        box.setContentsMargins(12, 12, 12, 12)

        row = QHBoxLayout()
        ico = QLabel(ICONS[label]); ico.setStyleSheet("color:white;")
        title = QLabel(label); title.setStyleSheet("color:white;font-weight:bold;")
        row.addWidget(ico); row.addSpacing(6); row.addWidget(title); row.addStretch()
        box.addLayout(row)

        desc = QLabel(DESCRIPTIONS[label])
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#AAAAAA;")
        box.addWidget(desc, 1)

        btn.clicked.connect(getattr(self, f"_on_{label.lower()}"))
        return btn

    # ---------- card callbacks ----------
    def _on_quick(self):
        dlg = _QuickDlg(self)
        if dlg.exec() != QDialog.Accepted:
            return
        Z = generate_heightmap(**dlg.params)
        import matplotlib.pyplot as plt
        plt.imsave(dlg.out_path, Z, cmap="terrain")
        if QMessageBox.question(
            self, "Saved",
            f"Saved to {dlg.out_path}\nOpen it?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            webbrowser.open(dlg.out_path)

    def _on_workbench(self):
        self._wb = FractalWorkbench()
        self._wb.show()

    def _on_timelapse(self):
        setup = _TimelapseDlg(self)
        if setup.exec() != QDialog.Accepted:
            return

        # Generate the initial heightmap with the chosen parameters
        Z = generate_heightmap(**setup.params)

        # Worker thread for rendering
        self._thread = _TimelapseThread(
            Z,
            steps=setup.steps_val,
            interval_ms=100,
            out_path=setup.out_path,
        )

        # Progress dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Rendering timelapse…")
        v = QVBoxLayout(dlg)
        bar = QProgressBar(); bar.setRange(0, 100)
        v.addWidget(bar)
        cancel = QPushButton("Cancel"); v.addWidget(cancel)
        cancel.clicked.connect(self._thread.terminate)

        self._thread.progress.connect(bar.setValue)
        self._thread.finished.connect(lambda p: (dlg.accept(), webbrowser.open(p)))

        self._thread.start()
        dlg.exec()

    def _on_help(self):
        webbrowser.open("https://github.com/victorrobotxt/TerraFract")

# ────────────────────────────── bootstrap ───────────────────────────
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
