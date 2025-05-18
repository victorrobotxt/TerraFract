# spectral.py

import numpy as np
from scipy import fftpack

# Cache radial bin indices per shape to speed repeated calls
_radial_cache: dict[tuple[int,int], dict[int,np.ndarray]] = {}

def radial_power_spectrum(Z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute the radial (isotropic) power spectrum of a 2D array.

    Returns
    -------
    freqs : 1D array of radial frequencies (skipping zero)
    power : 1D array of averaged spectral power at each frequency
    """
    ny, nx = Z.shape
    key = (ny, nx)
    if key not in _radial_cache:
        cy, cx = ny // 2, nx // 2
        y, x = np.indices((ny, nx))
        r = np.hypot(x - cx, y - cy).astype(int)
        # map each radius to flat indices array
        tbin_idx = {ri: np.where(r.ravel() == ri)[0] for ri in np.unique(r)}
        _radial_cache[key] = tbin_idx
    else:
        tbin_idx = _radial_cache[key]

    # 2D FFT → shifted power
    F = fftpack.fftshift(fftpack.fft2(Z))
    P = np.abs(F)**2
    flatP = P.ravel()

    freqs = []
    power = []
    for ri, idxs in sorted(tbin_idx.items()):
        if ri == 0:  # skip the DC term
            continue
        freqs.append(ri)
        power.append(flatP[idxs].mean())

    return np.array(freqs), np.array(power)
