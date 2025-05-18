import numpy as np
import pytest

from terrafract import (
    compute_slope,
    compute_wetness,
    assign_biomes,
    biome_colormap,
    synthesize_biomes,
    generate_heightmap,
    thermal_erosion,
    hydraulic_erosion,
    voronoi_cliffs,
    reverse_engineer_heightmap,
    estimate_spectral_exponent,
    equalize_mean,
    radial_power_spectrum,
)

def test_compute_slope_constant():
    Z = np.ones((10, 10)) * 0.5
    s = compute_slope(Z)
    assert s.shape == Z.shape
    assert np.allclose(s, 0)


def test_compute_wetness_monotonic():
    # gradient from 0 to 1
    Z = np.linspace(0, 1, 100).reshape(10, 10)
    w = compute_wetness(Z, smoothing_sigma=1)
    assert w.shape == Z.shape
    # lower Z should have higher wetness
    assert w[0,0] > w[-1,-1]


def test_assign_biomes_and_colormap():
    Z = np.array([[0.1, 0.25, 0.5, 0.85, 0.95]])
    slope = np.zeros_like(Z)
    wet = np.zeros_like(Z)
    b = assign_biomes(Z, slope, wet)
    # expect water(0), sand(1), grass(2), forest(3), rock(4), snow(5)
    assert list(b.ravel()) == [0, 1, 2, 3, 4, 5][:len(b.ravel())]
    rgb = biome_colormap(b)
    assert rgb.shape == (1, 5, 3)


def test_synthesize_biomes_consistency():
    Z = np.random.rand(32,32)
    rgb, b = synthesize_biomes(Z)
    assert rgb.shape == (32,32,3)
    assert b.shape == (32,32)


def test_generate_heightmap_ds_and_fbm():
    Z1 = generate_heightmap('diamond-square', size=33, seed=0, roughness=0.5)
    assert Z1.shape == (33,33)
    assert Z1.min() >= 0 and Z1.max() <= 1
    Z2 = generate_heightmap('fbm', size=32, seed=0, octaves=3, persistence=0.5, lacunarity=2.0, scale=10)
    assert Z2.shape == (32,32)
    assert Z2.min() >= 0 and Z2.max() <= 1


@pytest.mark.slow
def test_post_processing_preserves_shape_and_norm():
    Z = np.random.rand(20,20)
    Zt = thermal_erosion(Z, iterations=5, talus_angle=0.01)
    Zh = hydraulic_erosion(Z, iterations=5, rain_amount=0.01)
    Zv = voronoi_cliffs(Z, num_sites=5, ridge_height=0.2)
    for Zp in (Zt, Zh, Zv):
        assert Zp.shape == Z.shape
        assert np.all(Zp >= 0) and np.all(Zp <= 1)


def test_reverse_engineering_fbm():
    # create a synthetic map
    np.random.seed(1)
    Z_real = generate_heightmap('fbm', size=64, seed=1, octaves=4, persistence=0.6, lacunarity=2.5, scale=20)
    params, Z_synth = reverse_engineer_heightmap(Z_real, algorithm='fbm', seed=1)
    assert 'H' in params
    assert Z_synth.shape == Z_real.shape


def test_estimate_spectral_exponent():
    Z = np.random.rand(64,64)
    beta, intercept = estimate_spectral_exponent(Z)
    assert isinstance(beta, float)


def test_comparative_study_helpers():
    Z = np.random.rand(50,50)
    Z_eq = equalize_mean(Z, target_mean=0.4)
    assert abs(Z_eq.mean() - 0.4) < 1e-2
    f, P = radial_power_spectrum(Z)
    assert len(f) == len(P)
    d = box_count_dim(Z)
    assert isinstance(d, float)


if __name__ == '__main__':
    pytest.main()
