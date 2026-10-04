"""Clean up the raw image-to-3D output into a game/web-ready knight.

  pip install bpy==4.2.0 numpy scipy opencv-python-headless pillow   # plus Node.js for gltfpack
  python3 finalize.py [source.glb] [--ratio 0.6] [--tex 4096] [--no-project]

Takes trellis2_knight.glb (or the first raw *_knight.glb found) and
  1. scales it to 1.80 m, soles on the origin, front along +Z (glTF);
  2. repaints the crown and back of the head, which front.png never shows (the generator leaves
     them grey and half-metallic), with the photo's dark-brown hair;
  3. projects front.png onto every texel that faces the camera and is not hidden, so the face,
     eyes, buckles and shield get the photo's detail instead of the generator's blur. A dense
     optical flow aligns the photo to the model, and only the photo's fine detail is kept: the
     broad colour comes from the model, so the front blends into the sides;
  4. pads the texture islands so no seam samples the atlas background;
  5. simplifies with gltfpack (seam-aware, unlike Blender's decimate) and quantizes the mesh.
Writes
  knight_ai.glb                    final model (JPEG textures; WEBP needs a data: URI probe in three.js)
  ../viewer/knight_ai.gltf.json    the same model as embedded glTF for the turntable viewer
front_mask.png is the knight cut out of front.png (rembg, isnet-general-use).
"""
import argparse
import base64
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile

import bpy
import cv2
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = ["trellis2_knight.glb", "hunyuan21_knight.glb", "trellis_knight.glb", "hunyuan2_knight.glb"]
HEIGHT = 1.80
HAIR = np.array([0.15, 0.115, 0.095])  # hair in front.png, slightly darker for albedo
BEARD = np.array([0.392, 0.273, 0.212])  # beard in front.png (only its hue is used)

ap = argparse.ArgumentParser()
ap.add_argument("source", nargs="?")
ap.add_argument("--ratio", type=float, default=0.6, help="gltfpack simplification ratio")
ap.add_argument("--tex", type=int, default=4096, help="max texture size")
ap.add_argument("--no-project", action="store_true", help="skip projecting front.png")
args = ap.parse_args()

src = args.source or next((os.path.join(HERE, n) for n in RAW if os.path.exists(os.path.join(HERE, n))), None)
if not src:
    sys.exit("no raw model: run generate.py first")
print("source:", src)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
obj.name = obj.data.name = "Knight"
# drop the importer's parent empties and bake every transform into the mesh
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o is not obj:
        bpy.data.objects.remove(o)
me = obj.data

# scale to 1.80 m, soles on z=0, centred between the feet (Blender Z-up; exported back to Y-up)
co = np.zeros(len(me.vertices) * 3)
me.vertices.foreach_get("co", co)
co = co.reshape(-1, 3)
lo, hi = co[:, 2].min(), co[:, 2].max()
feet = co[co[:, 2] < lo + 0.06 * (hi - lo)]
co = (co - [feet[:, 0].mean(), feet[:, 1].mean(), lo]) * (HEIGHT / (hi - lo))
me.vertices.foreach_set("co", co.ravel())
me.update()
me.validate()
bpy.ops.object.shade_smooth()

nodes = obj.active_material.node_tree.nodes
base = next(n.image for n in nodes if n.type == "TEX_IMAGE" and n.image.colorspace_settings.name == "sRGB")
orm = next(n.image for n in nodes if n.type == "TEX_IMAGE" and n.image is not base)  # G rough, B metal
for img in (base, orm):
    if img.size[0] > args.tex:
        img.scale(args.tex, args.tex)
W, H = base.size
orm.scale(W, H)


def pixels(img):
    return np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)


def store(img, px):
    img.pixels.foreach_set(px.ravel())
    img.update()


def raster(tri, w, h):
    """Rasterise triangles tri (N,3,2) given in pixel units; pixel centres sit at +0.5.
    Returns the covered pixels' row, column, triangle index and barycentric weights."""
    lo = np.maximum(np.ceil(tri.min(1) - 0.5).astype(np.int64), 0)
    hi = np.minimum(np.floor(tri.max(1) - 0.5).astype(np.int64), [w - 1, h - 1])
    size = hi - lo + 1
    ok = (size > 0).all(1)
    ext = size.max(1)
    out, s = [], 4
    while True:  # triangles grouped by bounding-box size, each group checked on an s x s grid
        sel = np.where(ok & (ext <= s) & ((ext > s // 2) if s > 4 else True))[0]
        g = np.stack(np.meshgrid(np.arange(s), np.arange(s), indexing="xy"), -1).reshape(-1, 2)
        step = max(1, 4_000_000 // (s * s))
        for i in range(0, len(sel), step):
            ti = sel[i:i + step]
            px = lo[ti, None, :] + g[None]
            inb = (g[None, :, 0] < size[ti, None, 0]) & (g[None, :, 1] < size[ti, None, 1])
            a0 = tri[ti, 0][:, None]
            v0, v1, v2 = tri[ti, 1][:, None] - a0, tri[ti, 2][:, None] - a0, px + 0.5 - a0
            d = v0[..., 0] * v1[..., 1] - v1[..., 0] * v0[..., 1]
            d = np.where(np.abs(d) < 1e-12, np.nan, d)
            b = (v2[..., 0] * v1[..., 1] - v1[..., 0] * v2[..., 1]) / d
            c = (v0[..., 0] * v2[..., 1] - v2[..., 0] * v0[..., 1]) / d
            a = 1 - b - c
            r, k = np.nonzero(inb & (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6))
            out.append((px[r, k, 1], px[r, k, 0], ti[r], np.stack([a[r, k], b[r, k], c[r, k]], -1)))
        if s >= ext[ok].max():
            break
        s *= 2
    return [np.concatenate(z) for z in zip(*out)]


# texel table: every covered texel's 3D position and smooth normal
me.calc_loop_triangles()
n_tri = len(me.loop_triangles)
tri_loops = np.zeros(n_tri * 3, np.int64)
tri_verts = np.zeros(n_tri * 3, np.int64)
me.loop_triangles.foreach_get("loops", tri_loops)
me.loop_triangles.foreach_get("vertices", tri_verts)
tri_loops, tri_verts = tri_loops.reshape(-1, 3), tri_verts.reshape(-1, 3)
uv = np.zeros(len(me.loops) * 2)
me.uv_layers.active.data.foreach_get("uv", uv)
uv = uv.reshape(-1, 2)
vn = np.zeros(len(me.vertices) * 3)
me.vertices.foreach_get("normal", vn)
vn = vn.reshape(-1, 3)
ty, tx, tt, tb = raster(uv[tri_loops] * [W, H], W, H)  # Blender pixel rows run bottom-up, like v
ty, tx, tb = ty.astype(np.int32), tx.astype(np.int32), tb.astype(np.float32)
tpos = np.einsum("nk,nkc->nc", tb, co[tri_verts[tt]].astype(np.float32))
tnrm = np.einsum("nk,nkc->nc", tb, vn[tri_verts[tt]].astype(np.float32))
del tt, tb
tnrm /= np.linalg.norm(tnrm, axis=1, keepdims=True) + 1e-9
print(f"triangles {n_tri}, texture {W}x{H}, covered texels {len(ty)}")


def fix_head():
    """Repaint the unseen crown and back of the head with the photo's hair colour; make the head
    non-metallic (the generator gives the hair ~0.5 metalness)."""
    head = co[co[:, 2] > HEIGHT - 0.12]
    hx, hy = head[:, 0].mean(), head[:, 1].mean()
    near = np.hypot(tpos[:, 0] - hx, tpos[:, 1] - hy) < 0.13
    z = tpos[:, 2]
    skull = near & (z > HEIGHT - 0.25)
    crown = near & (z > HEIGHT - 0.075)
    nape = near & (z > HEIGHT - 0.15) & (tpos[:, 1] > hy + 0.03)  # behind the ears (front is -Y)

    px = pixels(base)
    rgb = px[ty, tx, :3]
    skin = (rgb[:, 0] - rgb[:, 2] > 0.12) & (rgb[:, 0] > 0.35)
    sel = (crown & ~skin) | nape
    lum = rgb[sel].mean(1)
    shade = np.clip((lum / np.median(lum)) ** 0.5, 0.6, 1.4)[:, None]
    px[ty[sel], tx[sel], :3] = HAIR * shade
    # the beard comes out grey: keep its brightness, give it the photo's brown
    beard = (np.hypot(tpos[:, 0] - hx, tpos[:, 1] - hy) < 0.11) & (z > HEIGHT - 0.28) & (z < HEIGHT - 0.19)
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    grey = beard & (rgb.max(1) - rgb.min(1) < 0.08) & (lum < 0.45)
    px[ty[grey], tx[grey], :3] = lum[grey, None] * (BEARD / (BEARD @ np.array([0.299, 0.587, 0.114])))
    store(base, px)

    m = pixels(orm)
    m[ty[skull], tx[skull], 2] = 0.0
    m[ty[sel], tx[sel], 1] = np.maximum(m[ty[sel], tx[sel], 1], 0.75)
    store(orm, m)
    print(f"head: {sel.sum()} hair and {grey.sum()} beard texels recoloured, {skull.sum()} de-metalled")


def render_albedo_front(path, size, a, bx, by):
    """Orthographic, unlit render of the base colour in the photo's pixel grid."""
    nt = obj.active_material.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image is base)
    surface = out.inputs["Surface"].links[0].from_socket
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 4
    sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.color_mode = "RGBA"
    cd = bpy.data.cameras.new("front")
    cd.type = "ORTHO"
    cd.ortho_scale = max(size) / a
    cam = bpy.data.objects.new("front", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = ((size[0] / 2 - bx) / a, -10, (by - size[1] / 2) / a)
    cam.rotation_euler = (np.pi / 2, 0, 0)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    nt.nodes.remove(em)
    nt.links.new(surface, out.inputs["Surface"])


def smooth_field(f, m, sig):
    out = np.zeros_like(f)
    den = cv2.GaussianBlur(m.astype(np.float32), (0, 0), sig) + 1e-6
    for c in range(f.shape[-1]):
        out[..., c] = cv2.GaussianBlur(np.where(m, f[..., c], 0).astype(np.float32), (0, 0), sig) / den
    return out


def project_photo():
    photo = cv2.cvtColor(cv2.imread(os.path.join(HERE, "front.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    pmask = cv2.imread(os.path.join(HERE, "front_mask.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    ph, pw = pmask.shape

    # photo pixel = (a*x + bx, by - a*z): match the knight's height and horizontal extent
    ys, xs = np.nonzero(pmask > 0.5)
    a = (ys.max() + 1 - ys.min()) / HEIGHT
    bx = (xs.min() + xs.max() + 1) / 2 - a * (co[:, 0].min() + co[:, 0].max()) / 2
    by = ys.max() + 1.0
    print(f"photo mapping: {a:.1f} px/m, origin ({bx:.1f}, {by:.1f})")

    with tempfile.TemporaryDirectory() as tmp:
        render_albedo_front(os.path.join(tmp, "front.png"), (pw, ph), a, bx, by)
        model = cv2.imread(os.path.join(tmp, "front.png"), cv2.IMREAD_UNCHANGED)
    mrgb = cv2.cvtColor(model[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    malpha = model[..., 3].astype(np.float32) / 255
    both = (malpha > 0.5) & (pmask > 0.5)

    # dense flow on local-contrast-normalised luminance: model pixel p shows photo pixel p + flow(p)
    def normalised(rgb):
        g = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        m = cv2.GaussianBlur(g, (0, 0), 8)
        s = np.sqrt(cv2.GaussianBlur((g - m) ** 2, (0, 0), 8)) + 4
        return np.clip((g - m) / s * 40 + 128, 0, 255).astype(np.uint8)
    raw = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM).calc(normalised(mrgb), normalised(photo), None)
    # trust the fine flow where the model texture has detail; featureless areas (the beard) get
    # the broad flow, otherwise they stretch whatever photo detail lies nearby
    g = cv2.cvtColor((mrgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    lstd = np.sqrt(np.maximum(cv2.GaussianBlur(g * g, (0, 0), 4) - cv2.GaussianBlur(g, (0, 0), 4) ** 2, 0))
    detail = cv2.GaussianBlur(np.clip((lstd - 6) / 8, 0, 1), (0, 0), 3)[..., None]
    flow = np.clip(detail * smooth_field(raw, both, 4) + (1 - detail) * smooth_field(raw, both, 20), -30, 30)

    # the photo has baked lighting: take its detail and hue, but the broad brightness of the model,
    # so the projected front blends into the sides
    luma = np.array([0.299, 0.587, 0.114], np.float32)
    lp_photo = smooth_field(photo @ luma[:, None], pmask > 0.5, 18)
    lp_model = smooth_field(mrgb @ luma[:, None], malpha > 0.5, 18)
    photo_c = np.clip(photo * np.clip(lp_model / (lp_photo + 1e-3), 0.3, 1.5), 0, 1)

    # what the camera sees: depth buffer at 2x the photo resolution (depth = Blender y)
    k = 2
    sp = np.stack([a * co[:, 0] + bx, by - a * co[:, 2]], -1) * k
    zy, zx, zt, zb = raster(sp[tri_verts], pw * k, ph * k)
    zbuf = np.full((ph * k, pw * k), np.inf)
    np.minimum.at(zbuf, (zy, zx), np.einsum("nk,nk->n", zb, co[tri_verts[zt], 1]))

    sx, sy = a * tpos[:, 0] + bx, by - a * tpos[:, 2]
    ix = np.clip(sx.astype(int), 0, pw - 1)
    iy = np.clip(sy.astype(int), 0, ph - 1)
    visible = tpos[:, 1] <= zbuf[np.clip((sy * k).astype(int), 0, ph * k - 1),
                                 np.clip((sx * k).astype(int), 0, pw * k - 1)] + 0.012
    facing = np.clip((-tnrm[:, 1] - 0.25) / 0.45, 0, 1)
    facing = facing * facing * (3 - 2 * facing)
    inside = cv2.GaussianBlur(cv2.erode(pmask, np.ones((7, 7))), (0, 0), 2)[iy, ix]
    w = facing * visible * inside
    # the face: also paint recesses the camera cannot see (the gap between the lips, eye corners),
    # otherwise the generator's pale texture shows through as an open mouth
    head = co[co[:, 2] > HEIGHT - 0.12]
    hx, hy = head[:, 0].mean(), head[:, 1].mean()
    front_of_head = (np.hypot(tpos[:, 0] - hx, tpos[:, 1] - hy) < 0.13) & (tpos[:, 1] < hy - 0.02)
    face = (front_of_head * np.clip((tpos[:, 2] - (HEIGHT - 0.29)) / 0.03, 0, 1)
            * np.clip((-tnrm[:, 1] + 0.3) / 0.5, 0, 1)  # not facing backwards
            * np.clip((0.75 - np.abs(tnrm[:, 0])) / 0.25, 0, 1))  # nor sideways (cheeks, temples)
    recess = face * (1 - visible)
    w = np.maximum(w, face * inside)[:, None]

    n = len(sx)
    cols = 4096
    rows = -(-n // cols)  # cv2.remap wants a 2D map smaller than 32k per side

    def grid(v):
        out = np.zeros(rows * cols, np.float32)
        out[:n] = v
        return out.reshape(rows, cols)
    col = cv2.remap(photo_c, grid(sx + flow[iy, ix, 0] - 0.5), grid(sy + flow[iy, ix, 1] - 0.5),
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).reshape(-1, 3)[:n]
    col *= (1 - 0.45 * recess)[:, None]  # hidden folds read as shadowed creases, not lit lips
    px = pixels(base)
    px[ty, tx, :3] = px[ty, tx, :3] * (1 - w) + col * w
    store(base, px)
    print(f"photo projected onto {(w[:, 0] > 0.5).sum()} texels")


def pad_islands():
    """Fill texels outside every UV island with the nearest island colour, so mip-mapping and the
    simplifier's small UV shifts never pull in the atlas background (dark cracks)."""
    covered = np.zeros((H, W), bool)
    covered[ty, tx] = True
    iy, ix = ndimage.distance_transform_edt(~covered, return_distances=False, return_indices=True)
    for img in (base, orm):
        px = pixels(img)
        store(img, px[iy, ix])


fix_head()
if not args.no_project:
    project_photo()
pad_islands()

out = os.path.join(HERE, "knight_ai.glb")
with tempfile.TemporaryDirectory() as tmp:
    full = os.path.join(tmp, "full.glb")
    bpy.ops.export_scene.gltf(filepath=full, export_format="GLB", export_yup=True, export_apply=True,
                              export_image_format="JPEG", export_jpeg_quality=90,
                              export_animations=False, export_extras=False)
    gltfpack = shutil.which("gltfpack") or None
    cmd = [gltfpack] if gltfpack else ["npx", "--yes", "gltfpack"]
    subprocess.run(cmd + ["-i", full, "-o", out, "-si", str(args.ratio)], check=True)

# GLB -> single-file glTF with the binary chunk as a data URI (what the viewer loads)
with open(out, "rb") as f:
    glb = f.read()
jlen = struct.unpack_from("<I", glb, 12)[0]
gltf = json.loads(glb[20:20 + jlen])
blen = struct.unpack_from("<I", glb, 20 + jlen)[0]
binary = glb[28 + jlen:28 + jlen + blen]
gltf["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(binary).decode()
view = os.path.join(HERE, "..", "viewer", "knight_ai.gltf.json")
with open(view, "w") as f:
    json.dump(gltf, f, separators=(",", ":"))
for p in (out, view):
    print(f"{os.path.relpath(p, HERE)}: {os.path.getsize(p) / 1e6:.1f} MB")
sys.stdout.flush()
os._exit(0)  # bpy as a module can segfault during interpreter teardown
