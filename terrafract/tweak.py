import argparse, json, yaml, os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from .heightmap_generators import generate_heightmap
from .biome_texture import (compute_slope, compute_wetness,
                             assign_biomes, biome_colormap)

PRESETS = {
    "Mountains": dict(algo="diamond-square", size=129, roughness=1.2),
    "Hills":     dict(algo="fbm", size=256, octaves=4, persistence=0.6, lacunarity=2.0, scale=80.0),
    "Islands":   dict(algo="diamond-square", size=129, roughness=0.8, voronoi_sites=20, ridge_height=0.8),
    "Fjords":    dict(algo="fbm", size=256, octaves=6, persistence=0.4, lacunarity=2.8, scale=40.0, hydro_iters=30),
}
PALETTES = ['terrain','viridis','plasma','cividis']

if __name__ == '__main__':
    p = argparse.ArgumentParser(prog='terrafract-tweak')
    group = p.add_mutually_exclusive_group()
    group.add_argument('--preset', choices=PRESETS, help='Quick presets')
    group.add_argument('--config', type=Path, help='YAML/JSON file with parameters')
    p.add_argument('--algo', choices=['diamond-square','fbm'], help='Override algorithm')
    p.add_argument('--size', type=int, help='Grid size')
    p.add_argument('--seed', type=int, default=42)
    # DS params
    p.add_argument('--roughness', type=float)
    # FBM params
    p.add_argument('--octaves', type=int)
    p.add_argument('--persistence', type=float)
    p.add_argument('--lacunarity', type=float)
    p.add_argument('--scale', type=float)
    # Erosion passes
    p.add_argument('--preset-pass', choices=['thermal','hydraulic','both'], default='both',
                   help='Which post-processing to apply')
    p.add_argument('--therm-iters', type=int, default=0)
    p.add_argument('--talus', type=float, default=0.01)
    p.add_argument('--hydro-iters', type=int, default=0)
    p.add_argument('--rain', type=float, default=0.01)
    # Output flags
    p.add_argument('--save-heightmap', action='store_true')
    p.add_argument('--save-biomes', action='store_true')
    p.add_argument('--save-spectrum', action='store_true')
    p.add_argument('--palette', choices=PALETTES, default='terrain')
    # Batch mode
    p.add_argument('--batch-seeds', type=int, nargs='+', help='Run multiple seeds')
    args = p.parse_args()

    # Load config if provided
    params = {}
    if args.config:
        raw = yaml.safe_load(args.config.read_text()) if args.config.suffix in ('.yml','.yaml') else json.loads(args.config.read_text())
        params.update(raw)
    if args.preset:
        params.update(PRESETS[args.preset])
    # override individual
    for k in ['algo','size','seed','roughness','octaves','persistence','lacunarity','scale']:
        v = getattr(args, k)
        if v is not None:
            params[k] = v
    # erosion passes
    if args.preset_pass in ('thermal','both') and args.therm_iters>0:
        params['thermal_iters'] = args.therm_iters; params['talus_angle']=args.talus
    if args.preset_pass in ('hydraulic','both') and args.hydro_iters>0:
        params['hydro_iters'] = args.hydro_iters; params['rain_amount']=args.rain

    seeds = args.batch_seeds if args.batch_seeds else [params.get('seed',42)]
    out_dir = Path('tweak_outputs'); out_dir.mkdir(exist_ok=True)

    for sd in seeds:
        params['seed'] = sd
        desc = f"{params['algo']}_s{sd}"
        print(f"Generating {desc}...")
        Z = generate_heightmap(**params)
        # Heightmap
        if args.save_heightmap:
            np.save(out_dir/f"{desc}_height.npy", Z)
        # Biomes
        if args.save_biomes:
            slope = compute_slope(Z); wet=compute_wetness(Z)
            bmap = assign_biomes(Z,slope,wet)
            img = biome_colormap(bmap)
            plt.imsave(out_dir/f"{desc}_biomes.png", img)
        # Spectrum
        if args.save_spectrum:
            from scipy.fftpack import fftshift,fft2
            F=fftshift(fft2(Z)); P=abs(F)**2
            freqs=np.arange(P.shape[0]//2)
            ps = [P.flatten()[...,]] # dummy
        # Always save rendered height.png
        plt.figure(); plt.imshow(Z,cmap=args.palette); plt.axis('off')
        plt.tight_layout(pad=0); plt.savefig(out_dir/f"{desc}_terrain.png",dpi=200)
    print(f"All outputs in {out_dir.resolve()}")
