# TerraFract

**TerraFract** is a Python toolkit and interactive workbench for procedural terrain generation using fractal algorithms. It supports classic Diamond–Square, Fractal Brownian Motion (FBM), and hybrid schemes, along with post-processing (thermal and hydraulic erosion, Voronoi cliffs), biome synthesis, spectral analysis, and export tools.

---

## Features

* **Height-map Generators**: Diamond–Square (2ⁿ+1 grids with intuitive roughness decay), FBM (Perlin-noise based, with graceful fallback), and hybrid mixes.
* **Post-processing**: Thermal erosion (angle-of-repose), hydraulic erosion (flow and sediment transport), Voronoi-based cliff carving.
* **Biome Texturing**: Automatic classification by elevation, slope, and wetness into water, sand, grass, forest, rock, and snow; PBR-ready colormap.
* **Interactive Workbench**: Real-time GUI with parameter sliders, 3D Matplotlib surface or biome overlay, spectral (power-spectrum) plot, box-counting dimension estimate.
* **Comparative Study Notebook**: Jupyter notebook for elevation histograms, log-log spectral plots, and fractal-dimension comparisons across generators.
* **Reverse Engineering**: Fit FBM parameters (Hurst exponent H, persistence, lacunarity) to a real DEM, then synthesize a matching fractal surface.
* **Stretch Goals**: Erosion time-lapse animations, river network extraction + Shapefile export, basic VR stub, multiplayer terraforming sandbox, OBJ export.

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/terrafract.git
cd terrafract
pip install -r requirements.txt
````

Alternatively, install from PyPI (coming soon):

```bash
pip install terrafract
```

---

## Quickstart

### Command-Line Demo

```bash
# Generate and view a simple heightmap via CLI
python - << 'PY'
from heightmap_generators import generate_heightmap
import matplotlib.pyplot as plt
Z = generate_heightmap('diamond-square', size=129, seed=0, roughness=0.8)
plt.imshow(Z, cmap='terrain'); plt.axis('off'); plt.show()
PY
```

### GUI Workbench

Launch the interactive tool:

```bash
python fractal_workbench.py
```

![Workbench Slider Demo](docs/sliders.gif)

* Select presets (Default, Alpine, Desert, Archipelago) or fine-tune sliders.
* Toggle between height shading and biome overlay.
* View power-spectrum and fractal dimension in real time.
* Click **Save** to export `terrain.png` and `terrain.obj` into the `exports/` folder.

---

## Documentation

Full API reference, tutorials, and examples are available in the `docs/` directory (generate with MkDocs) or online at:

```
https://yourusername.github.io/terrafract/
```

Key docs:

* **Usage Guide**: `docs/usage.md`
* **API Reference**: `docs/api.md`
* **Tutorials**: `docs/tutorials/*.md`

---

## Testing & CI

Run the test suite:

```bash
pytest -q
```

Configure pre-commit hooks with [Black](https://black.readthedocs.io) and [Ruff](https://github.com/charliermarsh/ruff).

Continuous integration is set up via GitHub Actions for Python 3.10 and 3.11 on Windows and Linux.

---

## Contributing

Feel free to open issues and pull requests. Please follow the existing code style and add tests for new features.

---

## License

[MIT License](LICENSE)
