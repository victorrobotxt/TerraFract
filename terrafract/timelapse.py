import argparse, os
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
from .post_processing import thermal_erosion, hydraulic_erosion

def create_erosion_timelapse(
    Z_init, steps=100,
    therm_iters=1, hydro_iters=1,
    fps=10, overlay=False,
    fmt='mp4', output_path='timelapse.mp4'
):
    """
    Generates a time-lapse of erosion.
    fmt: 'mp4'|'gif'|'frames'
    """
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    fig, ax = plt.subplots()
    im = ax.imshow(Z_init, cmap='terrain', vmin=0, vmax=1)
    ax.axis('off')

    Z = Z_init.copy()
    records = []

    for i in tqdm(range(steps), desc="Erosion frames"):
        if therm_iters>0: Z = thermal_erosion(Z,iterations=therm_iters,talus_angle=0.01)
        if hydro_iters>0: Z = hydraulic_erosion(Z,iterations=hydro_iters,rain_amount=0.01)
        frame = Z.copy()
        if overlay:
            ax.text(0.02,0.95,f"Step {i+1}/{steps}",color='white',transform=ax.transAxes,fontsize=8)
        records.append(frame)

    def update(frame): im.set_data(frame); return [im]
    anim = FuncAnimation(fig, update, frames=records, blit=True)

    if fmt=='gif':
        writer = PillowWriter(fps=fps)
        anim.save(output_path, writer=writer)
    elif fmt=='frames':
        for idx,fr in enumerate(records):
            plt.imsave(f"{output_path}_frame{idx:03d}.png", fr, cmap='terrain')
    else:
        writer = FFMpegWriter(fps=fps)
        anim.save(output_path, writer=writer)
    plt.close(fig)
    print(f"Saved timelapse → {output_path}")

if __name__=='__main__':
    p = argparse.ArgumentParser(prog='terrafract-timelapse')
    p.add_argument('--input', type=str, help='.npy heightmap to erode', required=True)
    p.add_argument('--steps', type=int, default=100)
    p.add_argument('--therm-iters', type=int, default=1)
    p.add_argument('--hydro-iters', type=int, default=1)
    p.add_argument('--fps', type=int, default=10)
    p.add_argument('--overlay', action='store_true', help='Show step text')
    p.add_argument('--format', choices=['mp4','gif','frames'], default='mp4')
    p.add_argument('--output', type=str, default='timelapse.mp4')
    args = p.parse_args()
    Z0 = np.load(args.input)
    create_erosion_timelapse(
        Z0, steps=args.steps,
        therm_iters=args.therm_iters,
        hydro_iters=args.hydro_iters,
        fps=args.fps, overlay=args.overlay,
        fmt=args.format, output_path=args.output
    )
