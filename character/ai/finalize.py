"""Clean up the raw image-to-3D output into a game/web-ready knight.

  pip install bpy==4.2.0 && python3 finalize.py [source.glb] [--tris 150000] [--tex 2048]

Takes trellis2_knight.glb (or the first raw *_knight.glb found), scales it to 1.80 m, stands it on
the origin facing +Z (glTF front), decimates it and downsizes the textures, then writes
  knight_ai.glb                    final model (WEBP textures)
  ../viewer/knight_ai.gltf.json    the same model as embedded glTF for the turntable viewer
"""
import argparse
import base64
import json
import os
import struct
import sys

import bpy
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = ["trellis2_knight.glb", "hunyuan21_knight.glb", "trellis_knight.glb", "hunyuan2_knight.glb"]
HEIGHT = 1.80

ap = argparse.ArgumentParser()
ap.add_argument("source", nargs="?")
ap.add_argument("--tris", type=int, default=150000)
ap.add_argument("--tex", type=int, default=2048)
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

# scale to 1.80 m, soles on z=0, centred between the feet (Blender Z-up; exported back to Y-up)
zs = [v.co.z for v in obj.data.vertices]
lo, hi = min(zs), max(zs)
s = HEIGHT / (hi - lo)
feet = [v.co for v in obj.data.vertices if v.co.z < lo + 0.06 * (hi - lo)]
cx = sum(c.x for c in feet) / len(feet)
cy = sum(c.y for c in feet) / len(feet)
for v in obj.data.vertices:
    v.co = (v.co - Vector((cx, cy, lo))) * s
obj.data.update()

tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
if tris > args.tris:
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = args.tris / tris
    bpy.ops.object.modifier_apply(modifier=mod.name)
obj.data.validate()
bpy.ops.object.shade_smooth()
print(f"triangles: {tris} -> {sum(len(p.vertices) - 2 for p in obj.data.polygons)}")

for img in bpy.data.images:
    if img.size[0] > args.tex:
        img.scale(args.tex, args.tex)


def fix_head():
    """The crown and back of the head are unseen in front.png, so the generator paints them grey
    and half-metallic. Repaint that hair with the photo's dark brown and make the head non-metal."""
    nodes = obj.active_material.node_tree.nodes
    imgs = [n.image for n in nodes if n.type == "TEX_IMAGE"]
    base = next(i for i in imgs if i.colorspace_settings.name == "sRGB")
    orm = next(i for i in imgs if i is not base)  # glTF metallicRoughness: G roughness, B metallic
    W, H = base.size
    co = np.array([v.co[:] for v in obj.data.vertices])
    uv = np.array([d.uv[:] for d in obj.data.uv_layers.active.data])
    head = co[co[:, 2] > HEIGHT - 0.12]
    hx, hy = head[:, 0].mean(), head[:, 1].mean()

    def raster(pred):
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        for p in obj.data.polygons:
            c = p.center
            if pred(c, p.normal) and np.hypot(c.x - hx, c.y - hy) < 0.13:
                pts = [(uv[i][0] * W, (1 - uv[i][1]) * H) for i in p.loop_indices]
                d.polygon(pts, fill=255, outline=255)
        m = m.filter(ImageFilter.MaxFilter(5))  # cover texels the sampler reads across UV seams
        return np.flipud(np.array(m) > 0)  # Blender pixel rows start at the bottom

    skull = raster(lambda c, n: c.z > HEIGHT - 0.25)
    crown = raster(lambda c, n: c.z > HEIGHT - 0.075)
    # back of the head, behind the ears (glTF +Z front is Blender -Y): no skin there to protect
    nape = raster(lambda c, n: c.z > HEIGHT - 0.15 and c.y > hy + 0.03)

    rgba = np.array(base.pixels[:], dtype=np.float32).reshape(H, W, 4)
    rgb = rgba[..., :3]
    skin = (rgb[..., 0] - rgb[..., 2] > 0.12) & (rgb[..., 0] > 0.35)
    sel = (crown & ~skin) | nape
    lum = rgb[sel].mean(1)
    shade = np.clip((lum / np.median(lum)) ** 0.5, 0.6, 1.4)[:, None]
    rgb[sel] = np.array([0.15, 0.115, 0.095]) * shade  # hair in front.png, slightly darker for albedo
    base.pixels.foreach_set(rgba.ravel())
    base.update()

    m = np.array(orm.pixels[:], dtype=np.float32).reshape(H, W, 4)
    m[skull, 2] = 0.0
    m[sel, 1] = np.maximum(m[sel, 1], 0.75)
    orm.pixels.foreach_set(m.ravel())
    orm.update()
    print(f"head fix: {sel.sum()} hair px repainted, {skull.sum()} px de-metalled")


fix_head()

out = os.path.join(HERE, "knight_ai.glb")
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True, export_apply=True,
                          export_image_format="WEBP", export_animations=False, export_extras=False)

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
