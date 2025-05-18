# reverse_engineering.py

import numpy as np
from scipy import fftpack
from sklearn.linear_model import LinearRegression

from spectral import radial_power_spectrum

def estimate_spectral_exponent(Z, fit_range=None):
    freqs, power = radial_power_spectrum(Z)
    if fit_range is None:
        fit_range = (5, min(Z.shape)//3)
    fmin, fmax = fit_range
    mask = (freqs >= fmin) & (freqs <= fmax)
    log_f = np.log(freqs[mask])
    log_p = np.log(power[mask])
    model = LinearRegression()
    model.fit(log_f.reshape(-1,1), log_p)
    beta = model.coef_[0]
    return beta, model.intercept_

def translate_beta_to_H(beta):
    return (beta - 2) / 2

def fit_fbm_parameters(Z_real, scale=None, octaves=6):
    Z = Z_real.astype(float)
    Z -= Z.min(); Z /= Z.max()
    beta, _ = estimate_spectral_exponent(Z)
    H = np.clip((beta - 2)/2, 0.0, 1.0)
    return {
        'H': H,
        'persistence': 0.5,
        'lacunarity': 2.0,
        'octaves': octaves,
        'scale': scale if scale else max(Z.shape)/2
    }

def reverse_engineer_heightmap(Z_real, algorithm='fbm', seed=0):
    if algorithm.lower() != 'fbm':
        raise NotImplementedError("Only FBM reverse-engineering is implemented.")

    params = fit_fbm_parameters(Z_real)
    from heightmap_generators import FBMGenerator
    gen = FBMGenerator(seed=seed, size=Z_real.shape[0])
    Z_synth = gen.generate(
        octaves=params['octaves'],
        persistence=params['persistence'],
        lacunarity=params['lacunarity'],
        scale=params['scale']
    )
    return params, Z_synth

if __name__ == '__main__':
    import matplotlib.pyplot as plt

    dem = gdal.Open('path/to/SRTM_tile.tif')
    Z_real = dem.GetRasterBand(1).ReadAsArray().astype(float)

    params, Z_synth = reverse_engineer_heightmap(Z_real, seed=42)
    print("Estimated parameters:", params)

    fig, axes = plt.subplots(1,2, figsize=(10,5))
    axes[0].imshow(Z_real, cmap='terrain'); axes[0].set_title('Real DEM')
    axes[1].imshow(Z_synth, cmap='terrain'); axes[1].set_title('Synthesized fBm')
    plt.show()
