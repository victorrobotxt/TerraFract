import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from .post_processing import thermal_erosion, hydraulic_erosion

# For river extraction and shapefile export
import shapely.geometry as geom
import geopandas as gpd

import matplotlib
matplotlib.use('Agg')


# For VR (stub)
try:
    import pyopenxr as xr
except ImportError:
    xr = None  # VR support requires pyopenxr

# For multiplayer sandbox
import asyncio
import websockets


def create_erosion_timelapse(Z_init, steps=100, therm_iters=1, hydro_iters=1, interval=100,
                             output_path='erosion_timelapse.mp4'):
    """
    Generate a time-lapse movie of terrain evolving under thermal and hydraulic erosion.

    Z_init: initial heightmap (2D numpy array)
    steps: number of frames (time steps)
    therm_iters/hydro_iters: erosion iterations per frame
    interval: ms between frames in the animation
    output_path: path to save the MP4 video
    """
    fig, ax = plt.subplots()
    im = ax.imshow(Z_init, cmap='terrain', vmin=0, vmax=1)
    plt.axis('off')

    Z = Z_init.copy()
    
    def update(frame):
        nonlocal Z
        if therm_iters > 0:
            Z = thermal_erosion(Z, iterations=therm_iters, talus_angle=0.01)
        if hydro_iters > 0:
            Z = hydraulic_erosion(Z, iterations=hydro_iters, rain_amount=0.01)
        im.set_data(Z)
        return [im]

    anim = animation.FuncAnimation(fig, update, frames=steps, interval=interval, blit=True)
    anim.save(output_path, dpi=200, fps=1000 // interval)
    plt.close(fig)
    print(f"Saved erosion time-lapse to {output_path}")


def generate_river_network(Z, threshold=100, smooth_factor=5):
    """
    Procedural river extraction via flow accumulation.

    Z: normalized heightmap in [0,1]
    threshold: min accumulation to form a river
    smooth_factor: degree of Bézier smoothing

    Returns a list of shapely LineString objects.
    """
    # Simple D8 flow directions
    ny, nx = Z.shape
    # Compute slope to neighbors
    acc = np.ones_like(Z)
    # Iteratively accumulate flow
    for i in range(ny):
        for j in range(nx):
            # find lowest neighbor
            min_h = Z[i,j]
            dir = None
            for di, dj in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                ii, jj = i+di, j+dj
                if 0 <= ii < ny and 0 <= jj < nx and Z[ii,jj] < min_h:
                    min_h = Z[ii,jj]
                    dir = (ii, jj)
            if dir:
                acc[dir] += acc[i,j]

    # Identify river pixels
    river_mask = acc > threshold
    # Extract connected river segments (simple approach: trace lines)
    rivers = []
    visited = np.zeros_like(river_mask)
    for i in range(ny):
        for j in range(nx):
            if river_mask[i,j] and not visited[i,j]:
                # Trace downstream
                coords = []
                ci, cj = i, j
                while True:
                    coords.append((cj, ci))
                    visited[ci, cj] = True
                    # find next
                    min_h = Z[ci,cj]
                    nxt = None
                    for di, dj in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                        ii, jj = ci+di, cj+dj
                        if 0 <= ii < ny and 0 <= jj < nx and Z[ii,jj] < min_h:
                            min_h = Z[ii,jj]
                            nxt = (ii, jj)
                    if nxt and river_mask[nxt]:
                        ci, cj = nxt
                        if visited[ci, cj]:
                            break
                    else:
                        break
                if len(coords) > 1:
                    rivers.append(geom.LineString(coords))
    # Smooth with Chaikin's corner cutting (approximate Bézier)
    def chaikin(coords):
        new = []
        for a,b in zip(coords[:-1], coords[1:]):
            new.append((0.75*a[0] + 0.25*b[0], 0.75*a[1] + 0.25*b[1]))
            new.append((0.25*a[0] + 0.75*b[0], 0.25*a[1] + 0.75*b[1]))
        return new
    smooth_rivers = []
    for line in rivers:
        coords = list(line.coords)
        for _ in range(smooth_factor):
            coords = chaikin(coords)
        smooth_rivers.append(geom.LineString(coords))

    return smooth_rivers


def export_rivers_shapefile(rivers, filename='rivers.shp'):
    """
    Export a list of shapely LineString objects as a Shapefile.
    """
    gdf = gpd.GeoDataFrame(geometry=rivers, crs="EPSG:4326")
    gdf.to_file(filename)
    print(f"Exported {len(rivers)} rivers to {filename}")


def run_vr_walkthrough(Z):
    """
    Stub for VR terrain walkthrough using OpenXR.
    Requires pyopenxr and a VR headset.
    """
    if xr is None:
        raise ImportError("pyopenxr not installed; install with pip install pyopenxr")
    # TODO: initialize XR instance, create swapchain, render heightmap mesh in VR
    print("Starting VR walkthrough (stub)...")


async def handle_terraforming(websocket, path, Z, bump_radius=5, bump_height=0.1):
    """
    WebSocket handler for multiplayer terraforming sandbox.
    Clients send JSON {x, y} to raise terrain.
    Broadcast updated heightmap to all clients.
    """
    import json
    clients = set()
    clients.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            x, y = data['x'], data['y']
            # apply Gaussian bump
            xx, yy = np.meshgrid(np.arange(Z.shape[1]), np.arange(Z.shape[0]))
            dist2 = (xx - x)**2 + (yy - y)**2
            bump = bump_height * np.exp(-dist2/(2*bump_radius**2))
            Z += bump
            Z = np.clip(Z, 0, 1)
            # broadcast new Z to clients
            payload = json.dumps({'heightmap': Z.tolist()})
            await asyncio.wait([c.send(payload) for c in clients])
    finally:
        clients.remove(websocket)


def start_multiplayer_sandbox(Z, host='localhost', port=8765):
    """
    Launch the multiplayer terraforming sandbox WebSocket server.
    """
    loop = asyncio.get_event_loop()
    server = websockets.serve(lambda ws, path: handle_terraforming(ws, path, Z), host, port)
    loop.run_until_complete(server)
    print(f"Multiplayer sandbox running on ws://{host}:{port}")
    loop.run_forever()