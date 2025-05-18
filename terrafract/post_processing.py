# post_processing.py

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import Voronoi, cKDTree
from numba import njit, prange

@njit(parallel=True)
def _thermal_core(Z, iterations, talus_angle):
    """
    Core loop for thermal erosion, accelerated with Numba.
    Z: 2D float64 array
    iterations: number of passes
    talus_angle: slope threshold
    Returns: new heightmap array
    """
    n, m = Z.shape
    Z_out = Z.copy()
    for _ in range(iterations):
        delta = np.zeros_like(Z_out)
        for i in prange(1, n-1):
            for j in range(1, m-1):
                h = Z_out[i, j]
                # check 4 neighbors
                for di, dj in ((1,0), (-1,0), (0,1), (0,-1)):
                    h2 = Z_out[i+di, j+dj]
                    slope = h - h2
                    if slope > talus_angle:
                        tr = 0.5 * (slope - talus_angle)
                        delta[i, j]    -= tr
                        delta[i+di, j+dj] += tr
        Z_out += delta
    return Z_out


def thermal_erosion(Z, iterations=10, talus_angle=0.01):
    """
    Thermal erosion with Numba-accelerated core.
    Normalizes output back to [0,1].
    """
    Zn = Z.copy().astype(np.float64)
    Zn -= Zn.min()
    if Zn.max() > 0:
        Zn /= Zn.max()
    # run Numba core
    Zt = _thermal_core(Zn, iterations, talus_angle)
    # re-normalize
    Zt -= Zt.min()
    if Zt.max() > 0:
        Zt /= Zt.max()
    return Zt


@njit(parallel=True)
def _hydro_core(Z, water, sediment, iterations, rain_amount, solubility):
    """
    Core loop for hydraulic erosion, accelerated with Numba.
    Z: heightmap, water: water map, sediment: sediment map
    Returns: eroded heightmap
    """
    n, m = Z.shape
    Z_out = Z.copy()
    W = water.copy()
    S = sediment.copy()
    for _ in range(iterations):
        W += rain_amount
        for i in prange(1, n-1):
            for j in range(1, m-1):
                h = Z_out[i, j] + W[i, j]
                # find downslope neighbors
                total_drop = 0.0
                lows = []
                for di, dj in ((1,0), (-1,0), (0,1), (0,-1)):
                    ii, jj = i+di, j+dj
                    h2 = Z_out[ii, jj] + W[ii, jj]
                    drop = h - h2
                    if drop > 0.0:
                        total_drop += drop
                        lows.append((ii, jj, drop))
                if total_drop <= 0.0:
                    continue
                # distribute flow
                for ii, jj, drop in lows:
                    frac = drop / total_drop
                    flow = W[i, j] * frac
                    W[i, j]   -= flow
                    W[ii, jj] += flow
                    dsed = solubility * flow
                    Z_out[i, j]   -= dsed
                    S[ii, jj] += dsed
    return Z_out


def hydraulic_erosion(Z, iterations=50, rain_amount=0.01, solubility=0.1):
    """
    Hydraulic erosion with Numba-accelerated core.
    Normalizes output back to [0,1].
    """
    Zn = Z.copy().astype(np.float64)
    Zn -= Zn.min()
    if Zn.max() > 0:
        Zn /= Zn.max()
    # initialize water & sediment maps
    water = np.zeros_like(Zn)
    sediment = np.zeros_like(Zn)
    Zh = _hydro_core(Zn, water, sediment, iterations, rain_amount, solubility)
    Zh -= Zh.min()
    if Zh.max() > 0:
        Zh /= Zh.max()
    return Zh


def voronoi_cliffs(Z, num_sites=10, ridge_height=0.5):
    """
    Voronoi-based cliff formation (unchanged).
    """
    n, m = Z.shape
    pts = np.column_stack(
        (
            np.random.uniform(0, n, size=num_sites),
            np.random.uniform(0, m, size=num_sites)
        )
    )
    vor = Voronoi(pts)
    grid_pts = np.indices((n, m)).transpose(1, 2, 0).reshape(-1, 2)
    ridge_pts = vor.vertices
    tree = cKDTree(ridge_pts)
    dists, _ = tree.query(grid_pts)
    dist_map = dists.reshape(n, m)
    with np.errstate(divide='ignore'):
        influence = np.exp(-(dist_map**2) / (2 * (n/num_sites)**2))
    Z2 = Z + ridge_height * influence
    Z2 -= Z2.min()
    if Z2.max() > 0:
        Z2 /= Z2.max()
    return Z2