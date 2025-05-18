# File: terrafract/fractal_workbench.py
# fractal_workbench.py – revamped UI/UX for TerraFract
# -------------------------------------------------------------
# Key improvements:
#   • Basic vs Advanced controls via QTabWidget
#   • One-click Presets (no fractal jargon)
#   • Tooltips & readable labels
#   • Debounced redraws (200 ms) for buttery sliders
#   • Fixed export spacing, bigger canvas, consistent font

import os
import random
import sys

import numpy as np
from PySide6 import QtCore, QtWidgets
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .heightmap_generators import generate_heightmap

class _Debounce(QtCore.QObject):
    """Call a slot once after inactivity (bundles rapid signals)."""

    def __init__(self, delay_ms=200, parent=None):
        super().__init__(parent)
        self._timer = QtCore.QTimer(self, singleShot=True, interval=delay_ms)
        self._timer.timeout.connect(self._emit)
        self._slot = None

    def trigger(self, slot):
        self._slot = slot
        self._timer.start()

    def _emit(self):
        if self._slot:
            self._slot()

class FractalWorkbench(QtWidgets.QMainWindow):
    """Simplified yet powerful terrain workbench."""

    PRESETS = {
        "Mountains": {"algo": "diamond-square", "roughness": 1.2},
        "Hills":     {"algo": "fbm",          "octaves": 4, "persistence": 0.6, "scale": 80.0},
        "Islands":   {"algo": "diamond-square", "roughness": 0.8, "voronoi_sites": 20, "ridge_height": 0.8},
        "Fjords":    {"algo": "fbm",           "octaves": 6, "persistence": 0.4, "scale": 40.0, "hydro_iters": 30},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TerraFract Workbench")
        self.resize(1024, 720)
        os.makedirs("exports", exist_ok=True)

        self._debounce = _Debounce(parent=self)
        self._build_ui()
        self.apply_preset("Mountains")

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        vbox = QtWidgets.QVBoxLayout(central)

        # Preset bar
        bar = QtWidgets.QHBoxLayout()
        bar.addWidget(QtWidgets.QLabel("Preset:"))
        self.preset = QtWidgets.QComboBox()
        self.preset.addItems(self.PRESETS)
        self.preset.currentTextChanged.connect(self.apply_preset)
        bar.addWidget(self.preset)
        rnd = QtWidgets.QPushButton("🔀 Random seed")
        rnd.clicked.connect(self.random_seed)
        bar.addWidget(rnd)
        bar.addStretch()
        vbox.addLayout(bar)

        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        vbox.addWidget(self.tabs, 0)
        self._make_simple_tab()
        self._make_adv_tab()

        # Canvas
        self.fig = Figure(figsize=(9, 6))
        self.ax3d = self.fig.add_subplot(121, projection='3d')
        self.ax_ps = self.fig.add_subplot(122)
        self.fig.subplots_adjust(wspace=0.35)
        self.canvas = FigureCanvas(self.fig)
        vbox.addWidget(self.canvas, 1)

        # Export
        exp_bar = QtWidgets.QHBoxLayout()
        exp_bar.addStretch()
        exp_btn = QtWidgets.QPushButton("Export PNG/OBJ…")
        exp_btn.clicked.connect(self.export_dialog)
        exp_bar.addWidget(exp_btn)
        vbox.addLayout(exp_bar)

    def _make_simple_tab(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)

        self.s_algo = QtWidgets.QComboBox()
        self.s_algo.addItems(["diamond-square", "fbm"])
        self.s_algo.setToolTip("Fractal generator")
        self.s_algo.currentTextChanged.connect(lambda: self._debounce.trigger(self.update))
        form.addRow("Algorithm:", self.s_algo)

        self.s_rough = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.s_rough.setRange(1, 100)
        self.s_rough.setValue(30)
        self.s_rough.setToolTip("Terrain roughness")
        self.s_rough.valueChanged.connect(lambda: self._debounce.trigger(self.update))
        form.addRow("Roughness:", self.s_rough)

        self.s_seed = QtWidgets.QSpinBox()
        self.s_seed.setRange(0, 9999)
        self.s_seed.valueChanged.connect(lambda: self._debounce.trigger(self.update))
        form.addRow("Seed:", self.s_seed)

        self.tabs.addTab(w, "Simple")

    def _make_adv_tab(self):
        w = QtWidgets.QScrollArea()
        w.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        w.setWidget(inner)
        form = QtWidgets.QFormLayout(inner)

        self.a_ds_rough = QtWidgets.QDoubleSpinBox()
        self.a_ds_rough.setRange(0.1, 2.0)
        self.a_ds_rough.setSingleStep(0.1)
        self.a_ds_rough.setValue(1.0)
        self.a_ds_rough.valueChanged.connect(lambda: self._debounce.trigger(self.update))
        form.addRow("DS roughness:", self.a_ds_rough)

        self.a_oct = QtWidgets.QSpinBox()
        self.a_oct.setRange(1, 10)
        self.a_oct.setValue(6)
        self.a_oct.valueChanged.connect(lambda: self._debounce.trigger(self.update))
        form.addRow("FBM octaves:", self.a_oct)

        self.a_pers = QtWidgets.QDoubleSpinBox()
        self.a_pers.setRange(0.1, 1.0)
        self.a_pers.setSingleStep(0.1)
        self.a_pers.setValue(0.5)
        self.a_pers.valueChanged.connect(lambda: self._debounce.trigger(self.update))
        form.addRow("FBM persistence:", self.a_pers)

        self.a_lac = QtWidgets.QDoubleSpinBox()
        self.a_lac.setRange(1.0, 4.0)
        self.a_lac.setSingleStep(0.1)
        self.a_lac.setValue(2.0)
        self.a_lac.valueChanged.connect(lambda: self._debounce.trigger(self.update))
        form.addRow("FBM lacunarity:", self.a_lac)

        self.tabs.addTab(w, "Advanced")

    def apply_preset(self, name: str):
        p = self.PRESETS[name]
        with QtCore.QSignalBlocker(self):
            self.s_algo.setCurrentText(p.get('algo', 'diamond-square'))
            if p.get('algo') == 'diamond-square':
                self.s_rough.setValue(int(p.get('roughness', 1.0) * 50))
            else:
                self.s_rough.setValue(int(p.get('persistence', 0.5) * 100))
            self.s_seed.setValue(random.randint(0, 9999))
            self.a_ds_rough.setValue(p.get('roughness', 1.0))
            self.a_oct.setValue(p.get('octaves', 6))
            self.a_pers.setValue(p.get('persistence', 0.5))
            self.a_lac.setValue(p.get('lacunarity', 2.0))
        self.update()

    def random_seed(self):
        self.s_seed.setValue(random.randint(0, 9999))

    def _params(self) -> dict:
        algo = self.s_algo.currentText()
        seed = self.s_seed.value()
        rough = self.s_rough.value() / 50
        if algo == 'diamond-square':
            return dict(algorithm='diamond-square', size=129, seed=seed, roughness=max(0.1, rough))
        else:
            octaves = max(1, int(3 + rough * 4))
            persistence = 0.3 + rough * 0.4
            return dict(
                algorithm='fbm',
                size=256,
                seed=seed,
                octaves=octaves,
                persistence=persistence,
                lacunarity=self.a_lac.value(),
                scale=60 / max(0.1, rough)
            )

    def update(self):
        p = self._params()
        Z = generate_heightmap(**p)
        self._Z = Z

        # 3D surface
        X, Y = np.meshgrid(range(Z.shape[1]), range(Z.shape[0]))
        self.ax3d.clear()
        self.ax3d.plot_surface(X, Y, Z, cmap='terrain', linewidth=0, antialiased=False)
        self.ax3d.set_axis_off()
        self.ax3d.set_title('Terrain')

        # Power spectrum
        self.ax_ps.clear()
        F = np.fft.fftshift(np.fft.fft2(Z))
        P = np.abs(F)**2
        cy, cx = [s//2 for s in P.shape]
        y, x = np.indices(P.shape)
        r = np.sqrt((x - cx)**2 + (y - cy)**2).astype(int)
        tbin = np.bincount(r.ravel(), P.ravel())
        nr   = np.bincount(r.ravel())
        radial = tbin / np.maximum(nr, 1)
        freqs  = np.arange(len(radial))
        self.ax_ps.loglog(freqs[1:], radial[1:])
        self.ax_ps.set_title('Power Spectrum')
        self.ax_ps.set_xlabel('Frequency')
        self.ax_ps.set_ylabel('Power')

        self.canvas.draw_idle()

    def export_dialog(self):
        dlg = QtWidgets.QFileDialog(self, 'Export', os.path.abspath('exports'))
        dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dlg.setNameFilters(['PNG image (*.png)', 'OBJ mesh (*.obj)'])
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        base, _ = os.path.splitext(dlg.selectedFiles()[0])
        png = base + '.png'
        obj = base + '.obj'

        self.fig.subplots_adjust(wspace=0.35)
        self.fig.savefig(png, dpi=300)

        Z = self._Z
        h, w = Z.shape
        with open(obj, 'w') as f:
            for i in range(h):
                for j in range(w):
                    f.write(f"v {j} {i} {Z[i,j]:.4f}\n")
            for i in range(h-1):
                for j in range(w-1):
                    v1 = i*w + j + 1
                    v2 = v1 + 1
                    v3 = v1 + w
                    v4 = v3 + 1
                    f.write(f"f {v1} {v2} {v4} {v3}\n")

        QtWidgets.QMessageBox.information(self, 'Saved', f'Saved to:\n• {png}\n• {obj}')

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = FractalWorkbench()
    w.show()
    sys.exit(app.exec())
