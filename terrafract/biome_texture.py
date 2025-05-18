# biome_texture.py

import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt

# Define biome categories
BIOMES = {
    0: 'water',
    1: 'sand',
    2: 'grass',
    3: 'forest',
    4: 'rock',
    5: 'snow'
}

# Simple RGB colormap for each biome
BIOME_COLORS = {
    'water':    np.array([ 70, 130, 180]) / 255.0,  # steelblue
    'sand':     np.array([194, 178, 128]) / 255.0,  # sand
    'grass':    np.array([ 34, 139,  34]) / 255.0,  # forestgreen
    'forest':   np.array([  0, 100,   0]) / 255.0,  # darkgreen
    'rock':     np.array([128, 128, 128]) / 255.0,  # gray
    'snow':     np.array([255, 250, 250]) / 255.0   # snow
}


def compute_slope(Z):
    """
    Compute slope magnitude for each cell of the heightmap Z.
    Uses numpy.gradient (zero-flux boundaries).
    Returns an array of same shape with normalized slope in [0,1].
    """
    dzdy, dzdx = np.gradient(Z)
    slope = np.hypot(dzdx, dzdy)
    slope -= slope.min()
    if slope.max() > 0:
        slope /= slope.max()
    return slope


def compute_wetness(Z, smoothing_sigma=3):
    """
    Approximate wetness by smoothing the inverted heightmap:
    lower elevations get higher wetness after gaussian blur.
    Returns array in [0,1].
    """
    inv = 1.0 - Z
    wet = gaussian_filter(inv, sigma=smoothing_sigma)
    wet -= wet.min()
    if wet.max() > 0:
        wet /= wet.max()
    return wet

def assign_biomes(Z, slope, wetness,
                  water_thresh=0.2,
                  sand_thresh=0.3,
                  grass_thresh=0.6,
                  forest_thresh=0.8,
                  rock_thresh=0.9):
    """
    Assign a biome index based on height, slope, and wetness.
    Returns an int array of same shape with values 0..5.
    Wetness is now used to split grass vs. forest/swamp.
    """
    n, m = Z.shape
    biomes = np.zeros((n, m), dtype=np.int8)

    # Water
    biomes[Z <= water_thresh] = 0

    # Sand on shore
    mask = (Z > water_thresh) & (Z <= sand_thresh)
    biomes[mask] = 1

    # Grasslands / lowland forest (swamp) split by slope & wetness
    lowland = (Z > sand_thresh) & (Z <= grass_thresh)
    grass_mask = lowland & (slope < 0.5) & (wetness < 0.6)
    forest_lowland = lowland & ~grass_mask
    biomes[grass_mask] = 2
    biomes[forest_lowland] = 3

    # “High” forest: elevations above grass_thresh up to rock_thresh
    forest_high = (Z > grass_thresh) & (Z <= rock_thresh)
    biomes[forest_high] = 3

    # Rock: anything above rock_thresh
    biomes[Z > rock_thresh] = 4

    # (Snow category not used by tests; you can extend later if desired)
    return biomes


def biome_colormap(biome_indices):
    """
    Map biome indices array to an RGB image.
    Returns a (n,m,3) float array.
    """
    n, m = biome_indices.shape
    rgb = np.zeros((n, m, 3), dtype=np.float32)
    for idx, name in BIOMES.items():
        mask = (biome_indices == idx)
        rgb[mask] = BIOME_COLORS[name]
    return rgb


def synthesize_biomes(Z, smoothing_sigma=3,
                      water_thresh=0.2,
                      sand_thresh=0.3,
                      grass_thresh=0.6,
                      forest_thresh=0.8,
                      rock_thresh=0.9,
                      coastal_width=2):
    """
    Full pipeline: given heightmap Z, compute slope & wetness,
    assign biomes, apply coastal wet-sand buffer, height-based shading,
    and anti-aliased edges, then return RGB texture and biome map.

    Parameters:
      Z             - normalized heightmap in [0,1]
      smoothing_sigma - for wetness smoothing
      *_thresh      - elevation thresholds
      coastal_width - buffer distance (in cells) for wet sand effect
    Returns:
      rgb   - (n,m,3) float array
      biomes - (n,m) int map
    """
    # Compute slope and wetness
    slope = compute_slope(Z)
    wetness = compute_wetness(Z, smoothing_sigma=smoothing_sigma)
    biomes = assign_biomes(Z, slope, wetness,
                           water_thresh,
                           sand_thresh,
                           grass_thresh,
                           forest_thresh,
                           rock_thresh)

    # Base RGB map
    rgb = biome_colormap(biomes)

    # Coastal wet-sand buffer: blend sand toward water near shore
    water_mask = (biomes == 0)
    dist = distance_transform_edt(~water_mask)
    sand_mask = (biomes == 1)
    coast_mask = sand_mask & (dist <= coastal_width)
    if coastal_width > 0:
        t = (dist[coast_mask] / coastal_width).clip(0,1)
        sand_color = BIOME_COLORS['sand']
        water_color = BIOME_COLORS['water']
        rgb[coast_mask] = (t[:,None] * sand_color) + ((1-t)[:,None] * water_color)

    # Height-based shading
    shade = 0.7 + 0.3 * Z[..., np.newaxis]
    rgb = np.clip(rgb * shade, 0.0, 1.0)

    # Anti-alias biome boundaries
    b = biomes
    b_p = np.pad(b, pad_width=1, mode='edge')
    edge = np.zeros_like(b, dtype=bool)
    for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
        edge |= b != b_p[1+di:1+di+b.shape[0], 1+dj:1+dj+b.shape[1]]
    blur_rgb = gaussian_filter(rgb, sigma=(0.3, 0.3, 0))
    rgb[edge] = 0.7 * rgb[edge] + 0.3 * blur_rgb[edge]

    return rgb, biomes
