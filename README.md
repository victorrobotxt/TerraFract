# TerraFract

**TerraFract** is a Python toolkit and standalone application for procedural terrain generation using fractal algorithms. It combines command-line utilities, a Qt-based GUI launcher, an interactive workbench, erosion timelapse tools, biome synthesis, and export capabilities to PNG, OBJ, and vector formats.

---

## Table of Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Quick Start](#quick-start)

   * [Command-Line Interface (CLI)](#command-line-interface-cli)
   * [Interactive Wizard](#interactive-wizard)
   * [GUI Launcher](#gui-launcher)
5. [Usage Examples](#usage-examples)

   * [Generate a Heightmap](#generate-a-heightmap)
   * [Generate and Render Biomes](#generate-and-render-biomes)
   * [Create an Erosion Timelapse](#create-an-erosion-timelapse)
   * [Reverse-Engineer a DEM](#reverse-engineer-a-dem)
6. [Python API](#python-api)
7. [Configuration Files](#configuration-files)
8. [Packaging the Standalone App](#packaging-the-standalone-app)
9. [Testing & CI](#testing--ci)
10. [Contributing](#contributing)
11. [License](#license)

---

## Features

* **Height-map Generators**

  * Diamond–Square
  * Fractal Brownian Motion (Perlin noise or Gaussian fallback)
  * Hybrid schemes via post-processing blend passes
* **Post-processing**

  * Thermal erosion (angle-of-repose model)
  * Hydraulic erosion (flow & sediment transport)
  * Voronoi-based cliff carving
* **Biome Texturing**

  * Classifies terrain into water, sand, grass, forest, rock, snow
  * Wetness and slope–driven coastal and forest variations
  * High-quality PBR-style color palettes
* **Interactive Workbench**

  * Real-time sliders for all generator parameters
  * 3D Matplotlib surface + live power-spectrum plot
  * Box-counting dimension estimator
  * Export to PNG + OBJ mesh
* **GUI Launcher**

  * **Quick** random map generator with thumbnail preview
  * **Workbench** full parameter playground
  * **Timelapse** erosion movie rendering
  * **Help** link to online docs
* **CLI Tools**

  * `terrafract tweak` – one-line heightmap/biome PNG export
  * `terrafract-timelapse` – batch erosion timelapse (MP4/GIF/frames)
* **Reverse Engineering**

  * Fit FBM parameters to real DEM via spectral regression
  * Synthesize matching fractal terrain
* **Stretch Goals**

  * River network extraction + Shapefile export
  * VR walkthrough stub (OpenXR)
  * Multiplayer WebSocket sandbox

---

## Requirements

* **Python 3.10+**
* **Core dependencies**:

  * `numpy`
  * `scipy`
  * `matplotlib`
  * `noise`
  * `numba`
* **Optional (GUI)**:

  * `PySide6`
* **Optional (analysis)**:

  * `pytest`, `pytest-cov`, `ruff`

---

## Installation

### From PyPI (soon)

```bash
pip install terrafract
```

### From Source

1. Clone the repo:

   ```bash
   git clone https://github.com/yourusername/terrafract.git
   cd terrafract
   ```
2. Install core dependencies:

   ```bash
   pip install numpy scipy matplotlib noise numba
   ```
3. (Optional) GUI & analysis extras:

   ```bash
   pip install .[gui,analysis]
   ```
4. Install the package:

   ```bash
   pip install -e .
   ```

---

## Quick Start

### Command-Line Interface (CLI)

#### `terrafract tweak`

Generate a terrain PNG in seconds:

```bash
# Heightmap only
terrafract tweak --preset mountains --view height -o mountains.png

# Biome-colored map
terrafract tweak --preset fjords --view biomes -o fjords_biomes.png

# Custom FBM
terrafract tweak --algo fbm --octaves 8 --persistence 0.4 \
    --lacunarity 2.5 --scale 60 --size 513 --seed 42 \
    --view biomes -o custom.png
```

Use `--help` to see all flags:

```bash
terrafract tweak --help
```

### Interactive Wizard

Run without flags:

```bash
terrafract tweak
```

Follow the prompts to pick a preset or custom parameters, then save your PNG.

### GUI Launcher

After installing `PySide6` and the package:

```bash
terrafract
```

You’ll see four cards:

1. **Quick** – random map with preset, seed, size, thumbnail preview
2. **Workbench** – full param playground (sliders, 3D+PS plots)
3. **Timelapse** – render erosion movie to MP4/GIF
4. **Help** – opens online docs

---

## Usage Examples

### Generate a Heightmap

```python
from terrafract.heightmap_generators import generate_heightmap
import matplotlib.pyplot as plt

# Diamond–Square, size=129, roughness=1.0
Z = generate_heightmap('diamond-square', size=129, seed=0, roughness=1.0)
plt.imshow(Z, cmap='terrain')
plt.axis('off')
plt.show()
```

### Generate and Render Biomes

```python
from terrafract.heightmap_generators import generate_heightmap
from terrafract.biome_texture import synthesize_biomes
import matplotlib.pyplot as plt

Z = generate_heightmap('fbm', size=257, octaves=5, persistence=0.6,
                       lacunarity=2.0, scale=50, seed=123)
img, biome_map = synthesize_biomes(Z)
plt.imshow(img)
plt.axis('off')
plt.show()
```

### Create an Erosion Timelapse

Using the CLI tool:

```bash
terrafract-timelapse \
  --input initial.npy \
  --steps 100 \
  --therm-iters 2 \
  --hydro-iters 3 \
  --fps 15 \
  --format mp4 \
  --output erosion.mp4
```

Or via Python:

```python
from terrafract.stretch_goals import create_erosion_timelapse
import numpy as np

Z0 = np.random.rand(256,256)
create_erosion_timelapse(Z0, steps=60, therm_iters=1, hydro_iters=1,
                         interval=100, output_path='timelapse.mp4')
```

### Reverse-Engineer a DEM

```python
import gdal
from terrafract.reverse_engineering import reverse_engineer_heightmap

dem = gdal.Open('SRTM_tile.tif')
Z_real = dem.GetRasterBand(1).ReadAsArray().astype(float)
params, Z_synth = reverse_engineer_heightmap(Z_real, seed=42)

print("Estimated FBM params:", params)
```

---

## Python API

All core functionality is exposed via Python:

* **`generate_heightmap(algorithm, size, seed, **params)`**
* **`synthesize_biomes(Z, **options)`** → `(rgb_image, biome_map)`
* **`thermal_erosion(Z, iterations, talus_angle)`**
* **`hydraulic_erosion(Z, iterations, rain_amount, solubility)`**
* **`voronoi_cliffs(Z, num_sites, ridge_height)`**
* **`radial_power_spectrum(Z)`**
* **`estimate_spectral_exponent(Z)`**
* **`reverse_engineer_heightmap(Z, **options)`**

Import these from their modules in the `terrafract` package.

---

## Configuration Files

The `tweak` script can load JSON or YAML configs:

```yaml
# terrain_config.yaml
algo: fbm
size: 257
octaves: 6
persistence: 0.5
lacunarity: 2.0
scale: 40
thermal_iters: 10
talus_angle: 0.02
hydro_iters: 20
rain_amount: 0.01
```

Run with:

```bash
terrafract tweak --config terrain_config.yaml --save-heightmap --save-biomes
```

---

## Packaging the Standalone App

A PyInstaller spec (`terrafract.spec`) is provided:

```bash
pip install pyinstaller
pyinstaller terrafract.spec
```

This produces:

* **One-file EXE** (`dist/TerraFract.exe`) on Windows
* **App folder** (`dist/TerraFract/TerraFract.exe` + assets)

You can customize the spec to add/remove hidden imports, data files, icons, and UPX compression.

---

## Testing & CI

Run the test suite:

```bash
pytest -q
```

Coverage:

```bash
pytest --cov=terrafract
```

Linting & formatting:

```bash
ruff .
black .
```

GitHub Actions workflows are configured for Python 3.10 and 3.11 on Windows & Linux.

---

## Contributing

1. Fork the repo & create a feature branch.
2. Write tests for new functionality.
3. Follow existing code style (see `pyproject.toml`).
4. Submit a pull request—CI will run tests & lint.

Please open issues for bugs or enhancement requests.

---

## License

This project is released under the [MIT License](LICENSE).
