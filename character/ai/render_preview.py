"""Preview renders of an AI-generated knight GLB (same camera/light rig as ../build_knight.py).

  pip install bpy==4.2.0 && python3 render_preview.py hunyuan2_knight.glb [outdir]
"""
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1]
outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "renders")
os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = int(os.environ.get("SAMPLES", 24))
scene.cycles.use_denoising = True
scene.render.resolution_x = 520
scene.render.resolution_y = 860
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.36, 0.37, 0.39, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.45
scene.view_settings.view_transform = "AgX"  # the photo textures carry their own lighting

bpy.ops.mesh.primitive_plane_add(size=6)
floor = bpy.data.materials.new("Floor")
floor.use_nodes = True
floor.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.055, 0.065, 1)
bpy.context.active_object.data.materials.append(floor)

for name, loc, energy, size in (("Key", (-2.0, -3.0, 3.2), 520, 2.5), ("Fill", (2.5, -2.5, 2.0), 200, 3),
                                ("Rim", (0.5, 3.0, 3.0), 380, 2)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    lo = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(lo)
    lo.location = loc
    lo.rotation_euler = (Vector((0, 0, 0.95)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

cam_d = bpy.data.cameras.new("Cam")
cam_d.lens = 85
cam = bpy.data.objects.new("Cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam
views = {"front": (0, -1), "back": (0, 1), "side": (-1, 0), "three_quarter": (-0.7, -0.75), "head": (-0.35, -1),
         "face": (0, -1)}
only = os.environ.get("VIEWS")
for vname, (dx, dy) in views.items():
    if only and vname not in only.split(","):
        continue
    close = vname in ("head", "face")
    target = Vector((0, 0, 1.62)) if close else Vector((0, 0, 0.92))
    dirv = Vector((dx, dy, 0.02 if close else 0.08)).normalized()
    cam.location = target + dirv * (1.6 if close else 6.4)
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(outdir, f"{vname}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", vname)
