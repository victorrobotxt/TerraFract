"""terrafract tweak – friendly one‑liner terrain generator.

Usage  (non‑interactive):
  terrafract tweak --preset mountains -o mountains.png
  terrafract tweak --algo fbm --size 129 --view biomes -o custom.png

Or run with **no flags** for a chat‑style wizard.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import matplotlib.pyplot as plt

from terrafract.heightmap_generators import generate_heightmap
from terrafract.biome_texture import synthesize_biomes

# Built‑in presets – zero jargon.
PRESETS: dict[str, dict] = {
    "mountains": {"algo": "diamond-square", "roughness": 1.2},
    "hills":     {"algo": "fbm", "octaves": 4, "persistence": 0.6, "scale": 80},
    "islands":   {"algo": "diamond-square", "roughness": 0.8},
    "fjords":    {"algo": "fbm", "octaves": 6, "persistence": 0.4, "scale": 40},
}

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="terrafract tweak",
        description="Generate a terrain PNG (heightmap or biome overlay) in seconds.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--preset", choices=PRESETS, help="Use a ready‑made terrain recipe")
    p.add_argument("--algo", "--algorithm", choices=["diamond-square", "fbm"],
                   help="Generator (ignored if --preset is given)")

    p.add_argument("--size", type=int, default=257, help="Map edge length (N×N)")
    p.add_argument("--seed", type=int, default=0, help="Random seed")

    # Diamond‑Square only.
    p.add_argument("--roughness", type=float, default=1.0,
                   help="Diamond‑Square roughness")

    # FBM only.
    p.add_argument("--octaves", type=int, default=6)
    p.add_argument("--persistence", type=float, default=0.5)
    p.add_argument("--lacunarity", type=float, default=2.0)
    p.add_argument("--scale", type=float, default=50.0)

    p.add_argument("--view", choices=["height", "biomes"], default="height",
                   help="Render raw heightmap or biome‑colored map")
    p.add_argument("--output", "-o", type=Path, default=Path("terrain.png"),
                   help="Filename for the PNG")
    return p

def _interactive() -> tuple[dict, Path]:
    print("\n✨  Welcome to TerraFract quick‑tweak wizard ✨\n")
    for i, name in enumerate(PRESETS, 1):
        print(f" {i}. {name.capitalize()}")
    print(f" {len(PRESETS)+1}. Custom settings")
    choice = int(input("\nChoose a preset (number): ").strip())

    if 1 <= choice <= len(PRESETS):
        cfg = PRESETS[list(PRESETS)[choice-1]].copy()
    else:
        algo = input("Algorithm [diamond-square/fbm]: ").strip().lower() or "diamond-square"
        cfg = {"algo": algo}
        if algo == "diamond-square":
            cfg["roughness"] = float(input("Roughness [1.0]: ") or 1.0)
        else:
            cfg["octaves"]     = int(input("Octaves [6]: ") or 6)
            cfg["persistence"] = float(input("Persistence [0.5]: ") or 0.5)
            cfg["lacunarity"]  = float(input("Lacunarity [2.0]: ") or 2.0)
            cfg["scale"]       = float(input("Scale [50.0]: ") or 50.0)

    cfg["size"] = int(input("Size [257]: ") or 257)
    cfg["seed"] = int(input("Seed [0]: ") or 0)
    view        = input("View type [height/biomes] (h/b): ").strip().lower()
    cfg["view"] = "biomes" if view.startswith("b") else "height"
    out = Path(input("Output file [terrain.png]: ") or "terrain.png")
    return cfg, out

def _render(cfg: dict, out_path: Path) -> None:
    Z = generate_heightmap(
        algorithm=cfg["algo"],
        size=cfg["size"],
        seed=cfg["seed"],
        **{k:v for k,v in cfg.items() if k not in ("algo", "size", "seed", "view")},
    )

    if cfg.get("view") == "biomes":
        img, _ = synthesize_biomes(Z)
        plt.imsave(out_path, img)
    else:
        plt.imsave(out_path, Z, cmap="terrain")
    print(f"\n✅  Saved {out_path}\n")

# ---------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:  # no flags → interactive wizard
        cfg, out_path = _interactive()
    else:
        args = _build_parser().parse_args(argv)
        if args.preset:
            cfg = PRESETS[args.preset].copy()
        else:
            cfg = {"algo": args.algo or "diamond-square"}
            if cfg["algo"] == "diamond-square":
                cfg["roughness"] = args.roughness
            else:
                cfg.update(octaves=args.octaves,
                           persistence=args.persistence,
                           lacunarity=args.lacunarity,
                           scale=args.scale)
        cfg.update(size=args.size, seed=args.seed, view=args.view)
        out_path = args.output

    _render(cfg, out_path)

if __name__ == "__main__":  # pragma: no cover
    main()