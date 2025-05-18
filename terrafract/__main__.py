#!/usr/bin/env python3
"""Graphical launcher for TerraFract – three large, self‑explaining tiles."""
from __future__ import annotations
import sys, os, tempfile, webbrowser
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QDialog, QFormLayout, QComboBox, QSpinBox, QLabel, QHBoxLayout,
    QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

from terrafract.heightmap_generators import generate_heightmap
from terrafract.fractal_workbench import FractalWorkbench
from terrafract.stretch_goals import create_erosion_timelapse

# ------------------------------- presets (shared with CLI)
PRESETS = {
    "Mountains": {"algorithm": "diamond-square", "roughness": 1.2},
    "Hills":     {"algorithm": "fbm", "octaves": 4, "persistence": 0.6, "scale": 80},
    "Islands":   {"algorithm": "diamond-square", "roughness": 0.8},
    "Fjords":    {"algorithm": "fbm", "octaves": 6, "persistence": 0.4, "scale": 40},
}

ICONS = {"Quick Terrain": "🗺️", "Workbench": "🧑‍💻", "Timelapse": "⏱️"}

# ------------------------------------------------------------------ threads
class _TimelapseThread(QThread):
    progress = Signal(int)   # 0‑100
    finished = Signal(str)

    def __init__(self, Z, steps, interval, out_path):
        super().__init__()
        self.Z, self.steps, self.interval, self.out = Z, steps, interval, out_path

    def run(self):
        create_erosion_timelapse(self.Z, steps=self.steps, interval=self.interval,
                                 therm_iters=1, hydro_iters=1, output_path=self.out)
        self.progress.emit(100)
        self.finished.emit(self.out)

# ------------------------------------------------------------------ dialogs
class _QuickTerrainDlg(QDialog):
    """Pick preset / seed / size –> PNG."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Terrain")
        f = QFormLayout(self)

        self.cb = QComboBox(); self.cb.addItems(PRESETS)
        f.addRow("Preset:", self.cb)
        self.seed = QSpinBox(); self.seed.setRange(0, 9999)
        f.addRow("Seed:", self.seed)
        self.size = QSpinBox(); self.size.setRange(33, 1025); self.size.setValue(257)
        f.addRow("Size:", self.size)

        self.path_lbl = QLabel("terrain.png")
        choose = QPushButton("Change…"); choose.clicked.connect(self._pick)
        hl = QHBoxLayout(); hl.addWidget(self.path_lbl); hl.addWidget(choose)
        f.addRow("Export:", hl)

        ok = QPushButton("Generate"); ok.clicked.connect(self.accept)
        f.addRow(ok)

    def _pick(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save PNG", "terrain.png", "PNG (*.png)")
        if p: self.path_lbl.setText(p)

    # helpers
    @property
    def params(self):
        p = PRESETS[self.cb.currentText()].copy()
        p.update(size=self.size.value(), seed=self.seed.value())
        return p
    @property
    def out_path(self):
        return self.path_lbl.text()

# ------------------------------------------------------------------ main win
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TerraFract")
        self.resize(520, 380)
        v = QVBoxLayout(self); v.setAlignment(Qt.AlignCenter)

        for label in ("Quick Terrain", "Workbench", "Timelapse"):
            btn = QPushButton(f"{ICONS[label]}  {label}")
            btn.setMinimumHeight(70)
            btn.clicked.connect(getattr(self, f"_on_{label.split()[0].lower()}"))
            v.addWidget(btn)

    # ---------- tile callbacks
    def _on_quick(self):  # Quick Terrain
        dlg = _QuickTerrainDlg(self)
        if dlg.exec() != QDialog.Accepted: return
        Z = generate_heightmap(**dlg.params)
        import matplotlib.pyplot as plt
        plt.imsave(dlg.out_path, Z, cmap="terrain")
        if QMessageBox.question(self, "Saved", f"Saved to {dlg.out_path}\nOpen it?",
                                 QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            webbrowser.open(dlg.out_path)

    def _on_workbench(self):
        self._wb = FractalWorkbench(); self._wb.show()  # keep ref

    def _on_timelapse(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save timelapse", "timelapse.mp4", "MP4 (*.mp4)")
        if not path: return
        Z = np.random.rand(128,128)
        self._thread = _TimelapseThread(Z, steps=60, interval=100, out_path=path)

        dlg = QDialog(self); dlg.setWindowTitle("Rendering timelapse…")
        l = QVBoxLayout(dlg)
        bar = QProgressBar(); bar.setRange(0,100); l.addWidget(bar)
        cancel = QPushButton("Cancel"); l.addWidget(cancel)
        cancel.clicked.connect(self._thread.terminate)
        self._thread.progress.connect(bar.setValue)
        self._thread.finished.connect(lambda p: (dlg.accept(), webbrowser.open(p)))
        self._thread.start(); dlg.exec()

# ------------------------------------------------------------------ bootstrap
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()