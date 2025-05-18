# heightmap_generators.py

import numpy as np
import warnings
from scipy.ndimage import gaussian_filter

from .post_processing import thermal_erosion, hydraulic_erosion, voronoi_cliffs


def _next_pow2_plus1(n: int) -> int:
    """Return the smallest 2^k + 1 ≥ n."""
    k = int(np.ceil(np.log2(n - 1)))
    return 2**k + 1


class HeightMapGenerator:
    """
    Base class for height map generators.
    Subclasses must implement generate() returning a 2D numpy array in [0,1].
    """
    def __init__(self, seed: int | None = None, size: int = 257):
        self.seed = seed
        self.size = size
        if seed is not None:
            np.random.seed(seed)

    def generate(self, **params) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement generate().")


class DiamondSquareGenerator(HeightMapGenerator):
    """
    Implements the diamond-square algorithm.
    params:
      - roughness: float, controls the variation amplitude
    """
    def generate(self, roughness: float = 1.0) -> np.ndarray:
        # ensure size = 2^n + 1
        if (self.size - 1) & (self.size - 2):
            new_size = _next_pow2_plus1(self.size)
            warnings.warn(f"Resizing grid from {self.size}→{new_size} for diamond-square")
            n = new_size
        else:
            n = self.size

        grid = np.zeros((n, n), dtype=np.float32)
        # initialize corners
        grid[0, 0] = np.random.rand()
        grid[0, -1] = np.random.rand()
        grid[-1, 0] = np.random.rand()
        grid[-1, -1] = np.random.rand()

        step_size = n - 1
        scale = roughness

        while step_size > 1:
            half = step_size // 2

            # Diamond step
            for x in range(0, n - 1, step_size):
                for y in range(0, n - 1, step_size):
                    avg = (
                        grid[x, y]
                        + grid[x + step_size, y]
                        + grid[x, y + step_size]
                        + grid[x + step_size, y + step_size]
                    ) * 0.25
                    grid[x + half, y + half] = avg + (np.random.rand() - 0.5) * scale

            # Square step
            for x in range(0, n, half):
                for y in range((x + half) % step_size, n, step_size):
                    vals = []
                    if x - half >= 0:
                        vals.append(grid[x - half, y])
                    if x + half < n:
                        vals.append(grid[x + half, y])
                    if y - half >= 0:
                        vals.append(grid[x, y - half])
                    if y + half < n:
                        vals.append(grid[x, y + half])
                    avg = np.mean(vals)
                    grid[x, y] = avg + (np.random.rand() - 0.5) * scale

            step_size = half
            scale *= 0.5  # fixed amplitude decay

        # normalize to [0,1]
        grid -= grid.min()
        grid /= grid.max()
        return grid


class FBMGenerator(HeightMapGenerator):
    """
    Fractal Brownian Motion using Perlin noise or fallback smooth noise.
    params:
      - octaves, persistence, lacunarity, scale
    """
    def __init__(self, seed: int | None = None, size: int = 256):
        super().__init__(seed, size)
        try:
            from noise import pnoise2
            self._noise_func = pnoise2
            self._use_perlin = True
        except ImportError:
            arr = np.random.rand(self.size, self.size).astype(np.float32)
            self._base_noise = gaussian_filter(arr, sigma=self.size / 8)
            self._use_perlin = False

    def generate(
        self,
        octaves: int = 6,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        scale: float = 50.0
    ) -> np.ndarray:
        shape = (self.size, self.size)
        heightmap = np.zeros(shape, dtype=np.float32)

        if not self._use_perlin:
            xv = np.linspace(0, self.size - 1, shape[1])
            yv = np.linspace(0, self.size - 1, shape[0])
            tmp = np.interp(xv[np.newaxis, :], np.arange(self.size), self._base_noise)
            heightmap = np.interp(yv[:, np.newaxis], np.arange(self.size), tmp)
        else:
            for i in range(shape[0]):
                for j in range(shape[1]):
                    x = i / scale
                    y = j / scale
                    amp, freq = 1.0, 1.0
                    val = 0.0
                    for _ in range(octaves):
                        val += amp * self._noise_func(x * freq, y * freq)
                        amp *= persistence
                        freq *= lacunarity
                    heightmap[i, j] = val

        # normalize to [0,1]
        heightmap -= heightmap.min()
        heightmap /= heightmap.max()
        return heightmap


def generate_heightmap(
    algorithm: str = 'diamond-square',
    size: int = 257,
    seed: int | None = None,
    **params
) -> np.ndarray:
    """
    Generate a heightmap using the specified algorithm, then apply optional post-processing.
    Supported post-processing keys in params:
      - thermal_iters, talus_angle
      - hydro_iters, rain_amount, solubility
      - voronoi_sites, ridge_height
    """
    post_keys = {
        'thermal_iters', 'talus_angle',
        'hydro_iters', 'rain_amount', 'solubility',
        'voronoi_sites', 'ridge_height'
    }
    post = {k: params.pop(k) for k in list(params) if k in post_keys}

    algo = algorithm.lower()
    if algo == 'diamond-square':
        gen = DiamondSquareGenerator(seed=seed, size=size)
    elif algo in ('fbm', 'fractal-brownian-motion'):
        gen = FBMGenerator(seed=seed, size=size)
    else:
        raise ValueError(f"Unknown algorithm '{algorithm}'")

    Z = gen.generate(**params)

    if post.get('thermal_iters'):
        Z = thermal_erosion(
            Z,
            iterations=post['thermal_iters'],
            talus_angle=post.get('talus_angle', 0.01)
        )
    if post.get('hydro_iters'):
        Z = hydraulic_erosion(
            Z,
            iterations=post['hydro_iters'],
            rain_amount=post.get('rain_amount', 0.01),
            solubility=post.get('solubility', 0.1)
        )
    if post.get('voronoi_sites'):
        Z = voronoi_cliffs(
            Z,
            num_sites=post['voronoi_sites'],
            ridge_height=post.get('ridge_height', 0.5)
        )

    return Z
