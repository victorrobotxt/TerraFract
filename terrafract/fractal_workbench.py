import sys
import os
import random
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import Voronoi, cKDTree

# Optional Numba acceleration
try:
    from numba import njit, prange
    _USE_NUMBA = True
except ImportError:
    _USE_NUMBA = False
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    prange = range

from PySide6 import QtCore, QtWidgets
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

from .heightmap_generators import generate_heightmap
from .biome_texture import synthesize_biomes


class FractalWorkbench(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TerraFract Workbench")
        os.makedirs("exports", exist_ok=True)
        self.settings = QtCore.QSettings("TerraFract", "Workbench")
        self._init_ui()
        self.restore_settings()
        self.update_terrain()

    def _init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        # --- Generator Group ---
        self.gen_box = QtWidgets.QGroupBox("Generator Parameters")
        self.gen_box.setCheckable(True)
        self.gen_box.setChecked(True)
        gen_layout = QtWidgets.QFormLayout(self.gen_box)

        self.seedSpin = QtWidgets.QSpinBox()
        self.seedSpin.setRange(0, 9999)
        self.seedSpin.setValue(42)
        rand_btn = QtWidgets.QPushButton("🎲 Random Seed")
        rand_btn.clicked.connect(self.randomize_seed)
        seed_layout = QtWidgets.QHBoxLayout()
        seed_layout.addWidget(self.seedSpin)
        seed_layout.addWidget(rand_btn)
        gen_layout.addRow("Seed:", seed_layout)

        self.algorithm = QtWidgets.QComboBox()
        self.algorithm.addItems(["diamond-square", "fbm"])
        self.algorithm.currentTextChanged.connect(self.update_terrain)
        gen_layout.addRow("Algorithm:", self.algorithm)

        self.roughness = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.roughness.setRange(1, 100)
        self.roughness.setValue(10)
        self.roughness.valueChanged.connect(self.on_roughness_changed)
        self.roughness_label = QtWidgets.QLabel(f"{self.roughness.value()/10:.2f}")
        rough_layout = QtWidgets.QHBoxLayout()
        rough_layout.addWidget(self.roughness)
        rough_layout.addWidget(self.roughness_label)
        gen_layout.addRow("Roughness:", rough_layout)

        self.octaves = QtWidgets.QSpinBox()
        self.octaves.setRange(1, 10)
        self.octaves.setValue(6)
        self.octaves.valueChanged.connect(self.update_terrain)
        gen_layout.addRow("Octaves:", self.octaves)

        self.persistence = QtWidgets.QDoubleSpinBox()
        self.persistence.setRange(0.1, 1.0)
        self.persistence.setSingleStep(0.1)
        self.persistence.setValue(0.5)
        self.persistence.valueChanged.connect(self.update_terrain)
        gen_layout.addRow("Persistence:", self.persistence)

        self.lacunarity = QtWidgets.QDoubleSpinBox()
        self.lacunarity.setRange(1.0, 4.0)
        self.lacunarity.setSingleStep(0.1)
        self.lacunarity.setValue(2.0)
        self.lacunarity.valueChanged.connect(self.update_terrain)
        gen_layout.addRow("Lacunarity:", self.lacunarity)

        self.scale = QtWidgets.QDoubleSpinBox()
        self.scale.setRange(1.0, 100.0)
        self.scale.setSingleStep(1.0)
        self.scale.setValue(50.0)
        self.scale.valueChanged.connect(self.update_terrain)
        gen_layout.addRow("Scale:", self.scale)

        main_layout.addWidget(self.gen_box)

        # --- Post-processing Group ---
        post_box = QtWidgets.QGroupBox("Post-Processing")
        post_box.setCheckable(True)
        post_box.setChecked(False)
        post_layout = QtWidgets.QFormLayout(post_box)

        self.therm_chk = QtWidgets.QCheckBox("Thermal erosion")
        self.therm_chk.stateChanged.connect(self.update_terrain)
        self.therm_iters = QtWidgets.QSpinBox()
        self.therm_iters.setRange(0, 100)
        self.therm_iters.setValue(0)
        self.therm_iters.valueChanged.connect(self.update_terrain)
        post_layout.addRow(self.therm_chk, self.therm_iters)
        self.talus = QtWidgets.QDoubleSpinBox()
        self.talus.setRange(0.001, 0.1)
        self.talus.setSingleStep(0.001)
        self.talus.setValue(0.01)
        self.talus.valueChanged.connect(self.update_terrain)
        post_layout.addRow("Talus angle:", self.talus)

        self.hydro_chk = QtWidgets.QCheckBox("Hydraulic erosion")
        self.hydro_chk.stateChanged.connect(self.update_terrain)
        self.hydro_iters = QtWidgets.QSpinBox()
        self.hydro_iters.setRange(0, 200)
        self.hydro_iters.setValue(0)
        self.hydro_iters.valueChanged.connect(self.update_terrain)
        post_layout.addRow(self.hydro_chk, self.hydro_iters)
        self.rain = QtWidgets.QDoubleSpinBox()
        self.rain.setRange(0.001, 0.1)
        self.rain.setSingleStep(0.001)
        self.rain.setValue(0.01)
        self.rain.valueChanged.connect(self.update_terrain)
        post_layout.addRow("Rain amount:", self.rain)

        self.voro_chk = QtWidgets.QCheckBox("Voronoi cliffs")
        self.voro_chk.stateChanged.connect(self.update_terrain)
        self.voro_sites = QtWidgets.QSpinBox()
        self.voro_sites.setRange(0, 50)
        self.voro_sites.setValue(0)
        self.voro_sites.valueChanged.connect(self.update_terrain)
        post_layout.addRow(self.voro_chk, self.voro_sites)
        self.ridge = QtWidgets.QDoubleSpinBox()
        self.ridge.setRange(0.1, 2.0)
        self.ridge.setSingleStep(0.1)
        self.ridge.setValue(0.5)
        self.ridge.valueChanged.connect(self.update_terrain)
        post_layout.addRow("Ridge height:", self.ridge)

        main_layout.addWidget(post_box)

        # --- View & Export Group ---
        view_box = QtWidgets.QGroupBox("Viewer & Export")
        view_box.setCheckable(True)
        view_box.setChecked(True)
        view_layout = QtWidgets.QFormLayout(view_box)

        self.view_toggle = QtWidgets.QComboBox()
        self.view_toggle.addItems(["Height", "Biomes"])
        self.view_toggle.currentTextChanged.connect(self.update_terrain)
        view_layout.addRow("View:", self.view_toggle)

        self.dimension_label = QtWidgets.QLabel("Dimension: N/A")
        view_layout.addRow(self.dimension_label)

        # PNG/OBJ toggles
        self.png_toggle = QtWidgets.QCheckBox("Export PNG")
        self.png_toggle.setChecked(True)
        self.obj_toggle = QtWidgets.QCheckBox("Export OBJ")
        self.obj_toggle.setChecked(True)
        toolbar = self.addToolBar("Export Toggles")
        toolbar.addWidget(self.png_toggle)
        toolbar.addWidget(self.obj_toggle)

        self.export_btn = QtWidgets.QPushButton("Export…")
        self.export_btn.clicked.connect(self.export_dialog)
        view_layout.addRow(self.export_btn)

        main_layout.addWidget(view_box)

        # Matplotlib canvas
        self.fig = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.fig)
        main_layout.addWidget(self.canvas, 1)
        main_layout.setStretchFactor(self.canvas, 10)

        for box in (self.gen_box, post_box, view_box):
            box.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                              QtWidgets.QSizePolicy.Maximum)

        self.ax3d = None
        self.ax_ps = None

    def randomize_seed(self):
        self.seedSpin.setValue(random.randint(0, 9999))
        self.update_terrain()

    def on_roughness_changed(self, val):
        self.roughness_label.setText(f"{val/10:.2f}")
        self.update_terrain()

    def export_dialog(self):
        dlg = QtWidgets.QFileDialog(self, "Export Terrain", os.path.abspath("exports"))
        dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dlg.setNameFilters(["PNG Files (*.png)", "OBJ Files (*.obj)"])
        dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, False)

        if dlg.exec() == QtWidgets.QDialog.Accepted:
            out = dlg.selectedFiles()[0]
            base, ext = os.path.splitext(out)

            if self.png_toggle.isChecked():
                png_path = base + ".png"
                old = self.fig.get_size_inches()
                try:
                    self.fig.tight_layout(pad=0.3)
                    self.fig.set_size_inches(8, 6)
                    self.fig.savefig(png_path, dpi=300)
                finally:
                    self.fig.set_size_inches(old)

            if self.obj_toggle.isChecked():
                obj_path = base + ".obj"
                Z = self.current_Z
                h, w = Z.shape
                with open(obj_path, 'w') as f:
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

    def update_terrain(self):
        algo = self.algorithm.currentText()
        params = {}
        seed = self.seedSpin.value()

        if algo == 'diamond-square':
            params['roughness'] = self.roughness.value() / 10.0
            size = 129
        else:
            params.update({
                'octaves':     self.octaves.value(),
                'persistence': self.persistence.value(),
                'lacunarity':  self.lacunarity.value(),
                'scale':       self.scale.value()
            })
            size = 256

        if self.therm_chk.isChecked():
            params['thermal_iters'] = self.therm_iters.value()
            params['talus_angle']   = self.talus.value()
        if self.hydro_chk.isChecked():
            params['hydro_iters']  = self.hydro_iters.value()
            params['rain_amount']  = self.rain.value()
        if self.voro_chk.isChecked():
            params['voronoi_sites'] = self.voro_sites.value()
            params['ridge_height']  = self.ridge.value()

        Z = generate_heightmap(algo, size=size, seed=seed, **params)
        self.current_Z = Z

        # create or clear the subplots
        if self.ax3d is None or self.ax_ps is None:
            self.fig.clear()
            self.ax3d = self.fig.add_subplot(121, projection='3d')
            self.ax_ps = self.fig.add_subplot(122)
        else:
            self.ax3d.clear()
            self.ax_ps.clear()

        # adjust spacing every time we redraw
        self.fig.subplots_adjust(wspace=0.35)

        # render terrain
        view = self.view_toggle.currentText()
        img = synthesize_biomes(Z)[0] if view == 'Biomes' else Z

        X, Y = np.meshgrid(range(Z.shape[1]), range(Z.shape[0]))
        self.ax3d.plot_surface(
            X, Y, Z,
            facecolors=img if view=='Biomes' else None,
            cmap='terrain' if view=='Height' else None,
            linewidth=0, antialiased=False
        )
        self.ax3d.set_title('Terrain')
        if view == 'Biomes':
            self.ax3d.set_axis_off()

        # compute and plot power spectrum
        F = np.fft.fftshift(np.fft.fft2(Z))
        P = np.abs(F)**2
        cy, cx = P.shape[0]//2, P.shape[1]//2
        y, x = np.indices(P.shape)
        r = np.hypot(x-cx, y-cy).astype(int)
        tbin = np.bincount(r.ravel(), P.ravel())
        nr   = np.bincount(r.ravel())
        radial = tbin / np.maximum(nr, 1)

        freqs = np.arange(len(radial))
        self.ax_ps.loglog(freqs[1:], radial[1:]+1e-12)
        self.ax_ps.set_title('Power Spectrum')
        self.ax_ps.set_xlabel('Radial Frequency')
        self.ax_ps.set_ylabel('Power')

        # update dimension label
        dim = self.box_counting_dimension(Z)
        self.dimension_label.setText(f"Dimension: {dim:.3f}")

        self.canvas.draw()
        self.save_settings()

    def box_counting_dimension(self, Z, sizes=None):
        """
        Estimate the box-counting (Minkowski–Bouligand) fractal dimension.

        Works even when the map side-length is 2^k + 1 (129, 257, …) by
        trimming the extra row/col instead of insisting on exact divisibility.
        """
        mask = Z > Z.mean()
        n = Z.shape[0]

        # candidate box sizes: 2,4,8,… < n
        if sizes is None:
            max_pow = int(np.floor(np.log2(n)))
            sizes   = [2 ** i for i in range(1, max_pow)]

        counts, scales = [], []
        for s in sizes:
            grid_cnt = n // s
            if grid_cnt <= 1:
                continue
            sub = mask[:grid_cnt*s, :grid_cnt*s]
            blocks = sub.reshape(grid_cnt, s, grid_cnt, s)
            num_filled = blocks.any(axis=(1,3)).sum()
            if num_filled > 0:
                counts.append(num_filled)
                scales.append(s)

        if len(counts) < 2:
            return float('nan')

        logs     = np.log(counts)
        logs_inv = np.log(1/np.array(scales))
        slope, _ = np.polyfit(logs_inv, logs, 1)
        return slope

    def save_settings(self):
        self.settings.setValue("seed", self.seedSpin.value())
        self.settings.setValue("algorithm", self.algorithm.currentText())
        self.settings.setValue("roughness", self.roughness.value())
        self.settings.setValue("generator_expanded", self.gen_box.isChecked())

    def restore_settings(self):
        if self.settings.contains("seed"):
            self.seedSpin.setValue(int(self.settings.value("seed")))
        if self.settings.contains("algorithm"):
            self.algorithm.setCurrentText(self.settings.value("algorithm"))
        if self.settings.contains("roughness"):
            self.roughness.setValue(int(self.settings.value("roughness")))
        if self.settings.contains("generator_expanded"):
            self.gen_box.setChecked(self.settings.value("generator_expanded") == 'true')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = FractalWorkbench()
    w.show()
    sys.exit(app.exec())
