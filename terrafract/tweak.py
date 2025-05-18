# tweak.py
import argparse
import matplotlib.pyplot as plt
from .heightmap_generators import generate_heightmap
from .biome_texture import synthesize_biomes

p = argparse.ArgumentParser()
p.add_argument("--algo", choices=["diamond-square","fbm"], default="diamond-square")
p.add_argument("--size", type=int, default=129)
p.add_argument("--seed", type=int, default=42)
# DS params
p.add_argument("--roughness", type=float, default=1.0)
# FBM params
p.add_argument("--octaves", type=int, default=6)
p.add_argument("--persistence", type=float, default=0.5)
p.add_argument("--lacunarity", type=float, default=2.0)
p.add_argument("--scale", type=float, default=50.0)
# Biome thresholds
p.add_argument("--water-thresh", type=float, default=0.2)
p.add_argument("--sand-thresh", type=float, default=0.3)
p.add_argument("--forest-thresh", type=float, default=0.8)
p.add_argument("--view", choices=["height","biomes"], default="height")
args = p.parse_args()

# Generate
common = dict(size=args.size, seed=args.seed)
if args.algo=="diamond-square":
    Z = generate_heightmap("diamond-square", **common, roughness=args.roughness)
else:
    Z = generate_heightmap("fbm", **common,
                           octaves=args.octaves, persistence=args.persistence,
                           lacunarity=args.lacunarity, scale=args.scale)

if args.view=="biomes":
    from biome_texture import compute_slope, compute_wetness, assign_biomes, biome_colormap
    s = compute_slope(Z)
    w = compute_wetness(Z)
    b = assign_biomes(Z, s, w,
                      water_thresh=args.water_thresh,
                      sand_thresh=args.sand_thresh,
                      grass_thresh=0.6,
                      forest_thresh=args.forest_thresh,
                      rock_thresh=0.9)
    img = biome_colormap(b)
    plt.imshow(img)
else:
    plt.imshow(Z, cmap="terrain")
plt.axis("off")
plt.show()
