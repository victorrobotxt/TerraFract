# File: terrafract/fractal_workbench.py

import os
import random

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

        # Wire up dynamic behavior
        self.s_algo.currentTextChanged.connect(self._on_algo_changed)
        self.s_rough.valueChanged.connect(self._sync_simple_to_advanced)
        self.a_pers.valueChanged.connect(self._sync_advanced_to_simple)
        self.s_rough.valueChanged.connect(self._sync_simple_to_ds)
        self.a_ds_rough.valueChanged.connect(self._sync_ds_to_simple)

        # Apply default preset and enforce initial show/hide
        self.apply_preset("Mountains")
        self._on_algo_changed(self.s_algo.currentText())

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        vbox = QtWidgets.QVBoxLayout(central)

        # ── Preset + Random Seed bar ────────────────────────────
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

        # ── Tabs ─────────────────────────────────────────────────
        self.tabs = QtWidgets.QTabWidget()
        vbox.addWidget(self.tabs, 1)
        self._make_simple_tab()
        self._make_adv_tab()

        # ── Matplotlib canvas ────────────────────────────────────
        self.fig = Figure(figsize=(9, 6))
        self.ax3d = self.fig.add_subplot(121, projection='3d')
        self.ax_ps = self.fig.add_subplot(122)
        self.fig.subplots_adjust(wspace=0.35)
        self.canvas = FigureCanvas(self.fig)
        vbox.addWidget(self.canvas, 10)

        # ── Export button ────────────────────────────────────────
        exp_bar = QtWidgets.QHBoxLayout()
        exp_bar.addStretch()
        exp_btn = QtWidgets.QPushButton("Export PNG/OBJ…")
        exp_btn.clicked.connect(self.export_dialog)
        exp_bar.addWidget(exp_btn)
        vbox.addLayout(exp_bar)

        # Prevent the 3D plot from tilting up/down
        self._install_rotation_lock()

    def _make_simple_tab(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        self.simple_form = form

        # Algorithm selector
        self.s_algo = QtWidgets.QComboBox()
        self.s_algo.addItems(["diamond-square", "fbm"])
        self.s_algo.currentTextChanged.connect(lambda _: self._debounce.trigger(self.update))
        form.addRow("Algorithm:", self.s_algo)

        # Single slider (Roughness or Persistence)
        self.s_rough = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.s_rough.setRange(1, 100)
        self.s_rough.setValue(30)
        self.s_rough.valueChanged.connect(lambda _: self._debounce.trigger(self.update))
        form.addRow("Roughness:", self.s_rough)

        # Seed spinner
        self.s_seed = QtWidgets.QSpinBox()
        self.s_seed.setRange(0, 9999)
        self.s_seed.valueChanged.connect(lambda _: self._debounce.trigger(self.update))
        form.addRow("Seed:", self.s_seed)

        self.tabs.addTab(w, "Simple")

    def _make_adv_tab(self):
        w = QtWidgets.QScrollArea()
        w.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        w.setWidget(inner)
        form = QtWidgets.QFormLayout(inner)
        # Save handle for dynamic show/hide
        self.adv_form = form

        # Diamond–Square roughness
        self.a_ds_rough = QtWidgets.QDoubleSpinBox()
        self.a_ds_rough.setRange(0.1, 2.0)
        self.a_ds_rough.setSingleStep(0.1)
        self.a_ds_rough.setValue(1.0)
        self.a_ds_rough.valueChanged.connect(lambda _: self._debounce.trigger(self.update))
        form.addRow("DS roughness:", self.a_ds_rough)

        # FBM parameters
        self.a_oct = QtWidgets.QSpinBox()
        self.a_oct.setRange(1, 10)
        self.a_oct.setValue(6)
        self.a_oct.valueChanged.connect(lambda _: self._debounce.trigger(self.update))
        form.addRow("FBM octaves:", self.a_oct)

        self.a_pers = QtWidgets.QDoubleSpinBox()
        self.a_pers.setRange(0.0, 1.0)
        self.a_pers.setSingleStep(0.1)
        self.a_pers.setValue(0.5)
        self.a_pers.valueChanged.connect(lambda _: self._debounce.trigger(self.update))
        form.addRow("FBM persistence:", self.a_pers)

        self.a_lac = QtWidgets.QDoubleSpinBox()
        self.a_lac.setRange(1.0, 4.0)
        self.a_lac.setSingleStep(0.1)
        self.a_lac.setValue(2.0)
        self.a_lac.valueChanged.connect(lambda _: self._debounce.trigger(self.update))
        form.addRow("FBM lacunarity:", self.a_lac)

        self.tabs.addTab(w, "Advanced")

    def apply_preset(self, name: str):
        p = self.PRESETS[name]
        with QtCore.QSignalBlocker(self):
            self.s_algo.setCurrentText(p.get('algo', 'diamond-square'))
            self.s_seed.setValue(random.randint(0, 9999))
            self.a_ds_rough.setValue(p.get('roughness', 1.0))
            self.a_oct.setValue(p.get('octaves', 6))
            self.a_pers.setValue(p.get('persistence', 0.5))
            self.a_lac.setValue(p.get('lacunarity', 2.0))
        self.update()

    def random_seed(self):
        """Always immediately re-render with a new seed."""
        new_seed = random.randint(0, 9999)
        self.s_seed.setValue(new_seed)
        self.update()

    def _on_algo_changed(self, text: str):
        """Handle algorithm switch: relabel simple slider and show/hide advanced controls."""
        # Simple tab relabel
        lbl = self.simple_form.labelForField(self.s_rough)
        lbl.setText("Roughness:" if text == 'diamond-square' else "Persistence:")

        # Advanced tab show/hide
        ds_lbl = self.adv_form.labelForField(self.a_ds_rough)
        ds_wid = self.a_ds_rough
        oct_lbl = self.adv_form.labelForField(self.a_oct)
        oct_wid = self.a_oct
        pers_lbl = self.adv_form.labelForField(self.a_pers)
        pers_wid = self.a_pers
        lac_lbl = self.adv_form.labelForField(self.a_lac)
        lac_wid = self.a_lac

        if text == 'diamond-square':
            ds_lbl.show();    ds_wid.show()
            oct_lbl.hide();  oct_wid.hide()
            pers_lbl.hide(); pers_wid.hide()
            lac_lbl.hide();  lac_wid.hide()
        else:
            ds_lbl.hide();    ds_wid.hide()
            oct_lbl.show();  oct_wid.show()
            pers_lbl.show(); pers_wid.show()
            lac_lbl.show();  lac_wid.show()

        # Trigger a re-render
        self._debounce.trigger(self.update)

    def _sync_simple_to_advanced(self, slider_val: int):
        """Sync simple slider → advanced persistence (FBM only)."""
        if self.s_algo.currentText() != "fbm":
            return
        p = slider_val / self.s_rough.maximum()
        with QtCore.QSignalBlocker(self.a_pers):
            self.a_pers.setValue(p)

    def _sync_advanced_to_simple(self, pers_val: float):
        """Sync advanced persistence → simple slider (FBM only)."""
        if self.s_algo.currentText() != "fbm":
            return
        s = int(round(pers_val * self.s_rough.maximum()))
        s = max(self.s_rough.minimum(), min(s, self.s_rough.maximum()))
        with QtCore.QSignalBlocker(self.s_rough):
            self.s_rough.setValue(s)

    def _sync_simple_to_ds(self, slider_val: int):
        """Sync simple slider → advanced DS roughness (DS only)."""
        if self.s_algo.currentText() != "diamond-square":
            return
        r = slider_val / 50.0
        r = max(0.1, min(r, self.a_ds_rough.maximum()))
        with QtCore.QSignalBlocker(self.a_ds_rough):
            self.a_ds_rough.setValue(r)

    def _sync_ds_to_simple(self, ds_val: float):
        """Sync advanced DS roughness → simple slider (DS only)."""
        if self.s_algo.currentText() != "diamond-square":
            return
        s = int(round(ds_val * 50.0))
        s = max(self.s_rough.minimum(), min(s, self.s_rough.maximum()))
        with QtCore.QSignalBlocker(self.s_rough):
            self.s_rough.setValue(s)

    def _params(self) -> dict:
        algo = self.s_algo.currentText()
        seed = self.s_seed.value()

        if algo == 'diamond-square':
            rough = self.s_rough.value() / 50.0
            return dict(
                algorithm='diamond-square',
                size=129,
                seed=seed,
                roughness=max(0.1, rough)
            )

        # FBM: simple slider = persistence
        persistence = self.s_rough.value() / self.s_rough.maximum()
        return dict(
            algorithm='fbm',
            size=256,
            seed=seed,
            octaves=self.a_oct.value(),
            persistence=persistence,
            lacunarity=self.a_lac.value(),
            scale=60.0
        )

    def update(self):
        p = self._params()
        Z = generate_heightmap(**p)
        self._Z = Z

        # 3D surface
        X, Y = np.meshgrid(range(Z.shape[1]), range(Z.shape[0]))
        self.ax3d.clear()
        self.ax3d.plot_surface(X, Y, Z, cmap='terrain',
                               linewidth=0, antialiased=False)
        self.ax3d.set_axis_off()
        self.ax3d.set_title('Terrain')

        # Power spectrum
        self.ax_ps.clear()
        F = np.fft.fftshift(np.fft.fft2(Z))
        P = np.abs(F)**2
        cy, cx = [s // 2 for s in P.shape]
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

        QtWidgets.QMessageBox.information(
            self, 'Saved', f'Saved to:\n• {png}\n• {obj}'
        )

    def _install_rotation_lock(self) -> None:
        """Prevent the 3D plot from tilting up/down."""
        self._home_elev = self.ax3d.elev

        def _clamp_elev(*_):
            self.ax3d.view_init(elev=self._home_elev, azim=self.ax3d.azim)
            self.canvas.draw_idle()

        self.canvas.mpl_connect(
            "motion_notify_event",
            lambda e: _clamp_elev() if e.inaxes is self.ax3d else None
        )
        self.canvas.mpl_connect(
            "button_release_event",
            lambda e: _clamp_elev()
        )
