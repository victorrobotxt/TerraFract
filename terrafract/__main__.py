#!/usr/bin/env python3
import sys
import subprocess
import os
import tempfile
import webbrowser
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QMessageBox
from terrafract.fractal_workbench import FractalWorkbench
from terrafract.stretch_goals import create_erosion_timelapse
import numpy as np

from PySide6.QtCore import QThread, Signal

class TimelapseThread(QThread):
    """
    Runs create_erosion_timelapse in a worker thread so the GUI stays
    responsive.
    """
    finished = Signal(str)  # will emit the path of the saved video

    def __init__(self, Z_init, steps, therm_iters, hydro_iters, interval, output_path):
        super().__init__()
        self.Z_init = Z_init
        self.steps = steps
        self.therm_iters = therm_iters
        self.hydro_iters = hydro_iters
        self.interval = interval
        self.output_path = output_path

    def run(self):
        # This runs in the background!
        create_erosion_timelapse(
            self.Z_init,
            steps=self.steps,
            therm_iters=self.therm_iters,
            hydro_iters=self.hydro_iters,
            interval=self.interval,
            output_path=self.output_path
        )
        # Notify the main thread when done
        self.finished.emit(self.output_path)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TerraFract Launcher")
        self.workbenches = []  # keep Python refs so they're not GC'd

        layout = QVBoxLayout(self)

        open_btn = QPushButton("Open Workbench")
        open_btn.clicked.connect(self.open_workbench)
        layout.addWidget(open_btn)

        tweak_btn = QPushButton("Quick Tweak (CLI)")
        tweak_btn.clicked.connect(self.quick_tweak)
        layout.addWidget(tweak_btn)

        eros_btn = QPushButton("Erosion Time-lapse")
        eros_btn.clicked.connect(self.run_timelapse)
        layout.addWidget(eros_btn)

    def open_workbench(self):
        fb = FractalWorkbench(parent=self)
        self.workbenches.append(fb)
        fb.show()

    def quick_tweak(self):
        subprocess.Popen(
            [sys.executable, "-m", "terrafract.tweak"],
            creationflags=(
                subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
        )
        
    def run_timelapse(self):
        path = os.path.join(tempfile.gettempdir(), "timelapse.mp4")
        Z_init = np.random.rand(128, 128)

        # Create and start the worker thread
        self._timelapse_thread = TimelapseThread(
            Z_init,
            steps=60,
            therm_iters=1,
            hydro_iters=1,
            interval=100,
            output_path=path
        )
        self._timelapse_thread.finished.connect(self.on_timelapse_done)
        self._timelapse_thread.start()

        # Optionally give the user some feedback right away:
        QMessageBox.information(
            self,
            "Rendering…",
            "Your erosion timelapse is being generated in the background. "
            "I'll open it when it's ready 😊"
        )

    def on_timelapse_done(self, path):
        webbrowser.open(path)

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
