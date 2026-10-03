"""Procedural Blender (bpy) build of the medieval knight from reference/ref_*.png.

Run:  python3 build_knight.py [--render]
Outputs: knight.glb, knight.blend (and renders/*.png with --render)

Coordinates: metres, Z up, character faces -Y. Character's right = -X.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "textures")

# --------------------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
COLL = bpy.data.collections.new("Knight")
scene.collection.children.link(COLL)


# --------------------------------------------------------------------------- materials
_mats = {}


def mat(name, color=(0.5, 0.5, 0.5), tex=None, metal=0.0, rough=0.7, tex_scale=1.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if tex:
        nt = m.node_tree
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(os.path.join(TEX, tex), check_existing=True)
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
        if tex_scale != 1.0:
            mp = nt.nodes.new("ShaderNodeMapping")
            tc = nt.nodes.new("ShaderNodeTexCoord")
            mp.inputs["Scale"].default_value = (tex_scale, tex_scale, 1)
            nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
            nt.links.new(mp.outputs["Vector"], img.inputs["Vector"])
    if name in ("Hair",):
        bsdf.inputs["Specular IOR Level"].default_value = 0.15
    _mats[name] = m
    return m


M = dict(
    skin=mat("Skin", (0.55, 0.36, 0.27), "skin.png", rough=0.6),
    hair=mat("Hair", (0.022, 0.016, 0.012), rough=0.9),
    lip=mat("Lip", (0.36, 0.19, 0.15), rough=0.55),
    eye_w=mat("EyeWhite", (0.75, 0.72, 0.68), rough=0.2),
    iris=mat("Iris", (0.12, 0.08, 0.05), rough=0.1),
    leather=mat("Leather", (0.30, 0.17, 0.09), "leather_brown.png", rough=0.6),
    leather_d=mat("LeatherDark", (0.18, 0.10, 0.05), "leather_dark.png", rough=0.6),
    boot=mat("BootLeather", (0.26, 0.16, 0.10), "leather_boot.png", rough=0.7),
    steel=mat("Steel", (0.62, 0.63, 0.65), "steel.png", metal=1.0, rough=0.32),
    iron=mat("Iron", (0.30, 0.30, 0.31), metal=1.0, rough=0.45),
    mail=mat("Chainmail", (0.45, 0.45, 0.47), "chainmail.png", metal=0.9, rough=0.45, tex_scale=3.0),
    gamb=mat("Gambeson", (0.38, 0.35, 0.23), "gambeson.png", rough=0.9),
    trousers=mat("Trousers", (0.10, 0.16, 0.10), "trousers.png", rough=0.9),
    cloak_g=mat("CloakGreen", (0.08, 0.17, 0.10), "cloak_green.png", rough=0.95),
    cloak_b=mat("CloakBrown", (0.30, 0.18, 0.09), "cloak_brown.png", rough=0.95),
    wood=mat("ShieldFace", (0.5, 0.3, 0.15), "shield_face.png", rough=0.65),
    wood_back=mat("ShieldBack", (0.30, 0.18, 0.09), "leather_dark.png", rough=0.8),
    grip=mat("Grip", (0.20, 0.10, 0.05), "leather_dark.png", rough=0.7),
)


# --------------------------------------------------------------------------- geometry helpers
def to_obj(name, bm, material, smooth=True, subsurf=0, solidify=0.0, parent=None, mats=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    for mt in (mats or [material]):
        me.materials.append(mt)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if solidify:
        md = ob.modifiers.new("Solid", "SOLIDIFY")
        md.thickness = solidify
        md.offset = 0.0
        if mats and len(mats) > 1:
            md.material_offset = 1
    if subsurf:
        md = ob.modifiers.new("Sub", "SUBSURF")
        md.levels = subsurf
        md.render_levels = subsurf
    if parent:
        ob.parent = parent
    return ob


def surface(name, fn, nu, nv, material, closed_u=False, cap=False, uv_scale=(1, 1), **kw):
    """Parametric surface p = fn(u, v), u,v in [0,1]. Rows along v, columns along u."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    cols = nu if closed_u else nu + 1
    grid = []
    for j in range(nv + 1):
        row = []
        for i in range(cols):
            row.append(bm.verts.new(fn(i / nu, j / nv)))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % cols if closed_u else i + 1
            f = bm.faces.new((grid[j][i], grid[j][i2], grid[j + 1][i2], grid[j + 1][i]))
            uvs = [(i / nu, j / nv), ((i + 1) / nu, j / nv), ((i + 1) / nu, (j + 1) / nv), (i / nu, (j + 1) / nv)]
            for loop, uv in zip(f.loops, uvs):
                loop[uv_layer].uv = (uv[0] * uv_scale[0], uv[1] * uv_scale[1])
    if cap and closed_u:
        for j in (0, nv):
            ring = grid[j]
            if j == 0:
                ring = list(reversed(ring))
            center = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            for i in range(len(ring)):
                bm.faces.new((ring[i], ring[(i + 1) % len(ring)], center))
    bm.normal_update()
    return to_obj(name, bm, material, **kw)


def frame_along(points):
    """Tangent, side, normal frames along polyline (parallel transport)."""
    frames = []
    up = Vector((0, 0, 1))
    prev_side = None
    for k, p in enumerate(points):
        if k == 0:
            t = points[1] - points[0]
        elif k == len(points) - 1:
            t = points[-1] - points[-2]
        else:
            t = points[k + 1] - points[k - 1]
        t.normalize()
        if prev_side is None:
            ref = Vector((0, -1, 0)) if abs(t.dot(up)) > 0.9 else up
            side = t.cross(ref).normalized()
        else:
            side = (prev_side - t * prev_side.dot(t)).normalized()
        n = side.cross(t).normalized()
        frames.append((t, side, n))
        prev_side = side
    return frames


def tube(name, pts, radii, material, seg=16, cap=True, twist=0.0, **kw):
    """Loft an (optionally elliptical) tube through pts. radii: r or (r_side, r_normal)."""
    pts = [Vector(p) for p in pts]
    radii = [(r, r) if not isinstance(r, (tuple, list)) else r for r in radii]
    frames = frame_along(pts)

    # interpolate along the polyline for smoothness
    def fn(u, v):
        idx = v * (len(pts) - 1)
        k = min(int(idx), len(pts) - 2)
        f = idx - k
        p = pts[k].lerp(pts[k + 1], f)
        rs = radii[k][0] * (1 - f) + radii[k + 1][0] * f
        rn = radii[k][1] * (1 - f) + radii[k + 1][1] * f
        _, s0, n0 = frames[k]
        _, s1, n1 = frames[k + 1]
        s = s0.lerp(s1, f).normalized()
        n = n0.lerp(n1, f).normalized()
        a = 2 * math.pi * u + twist
        return p + s * (math.cos(a) * rs) + n * (math.sin(a) * rn)

    nv = max(2, (len(pts) - 1) * 4)
    return surface(name, fn, seg, nv, material, closed_u=True, cap=cap, **kw)


def ellipsoid(name, center, radii, material, seg=24, rings=16, rot=(0, 0, 0), deform=None, **kw):
    cx, cy, cz = center
    rx, ry, rz = radii
    R = Matrix.Rotation(rot[2], 3, "Z") @ Matrix.Rotation(rot[1], 3, "Y") @ Matrix.Rotation(rot[0], 3, "X")

    def fn(u, v):
        th = 2 * math.pi * u
        ph = math.pi * (v - 0.5)
        x, y, z = math.cos(ph) * math.cos(th), math.cos(ph) * math.sin(th), math.sin(ph)
        if deform:
            x, y, z = deform(x, y, z)
        p = R @ Vector((x * rx, y * ry, z * rz))
        return Vector((cx, cy, cz)) + p

    # pinch poles with tiny rings, fine for subsurf
    return surface(name, lambda u, v: fn(u, 0.001 + 0.998 * v), seg, rings, material, closed_u=True, cap=True, **kw)


def box(name, center, size, material, bevel=0.005, rot=(0, 0, 0), **kw):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    R = Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
    bmesh.ops.transform(bm, matrix=R, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect="EDGES", profile=0.5)
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:  # simple box projection
        n = f.normal
        for l in f.loops:
            c = l.vert.co
            if abs(n.x) > max(abs(n.y), abs(n.z)):
                l[uv].uv = (c.y * 4, c.z * 4)
            elif abs(n.y) > abs(n.z):
                l[uv].uv = (c.x * 4, c.z * 4)
            else:
                l[uv].uv = (c.x * 4, c.y * 4)
    return to_obj(name, bm, material, smooth=False, **kw)


def strap(name, pts, width, thick, material, normal_hint=None, **kw):
    """Flat belt/strap along a polyline. normal_hint: function p->outward normal."""
    pts = [Vector(p) for p in pts]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rows = []
    L = 0.0
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        nrm = normal_hint(p) if normal_hint else Vector((0, -1, 0))
        nrm = (nrm - t * nrm.dot(t)).normalized()
        side = t.cross(nrm).normalized()
        if k:
            L += (p - pts[k - 1]).length
        rows.append(([bm.verts.new(p + side * (width / 2) * s + nrm * thick * o)
                      for s, o in ((-1, 0), (1, 0), (1, 1), (-1, 1))], L))
    for k in range(len(rows) - 1):
        a, la = rows[k]
        b, lb = rows[k + 1]
        for i in range(4):
            f = bm.faces.new((a[i], a[(i + 1) % 4], b[(i + 1) % 4], b[i]))
            for l, (uu, vv) in zip(f.loops, ((i / 4, la), ((i + 1) / 4, la), ((i + 1) / 4, lb), (i / 4, lb))):
                l[uv].uv = (uu * width * 4, vv * 4)
    for ring in (rows[0][0], list(reversed(rows[-1][0]))):
        bm.faces.new(ring)
    bm.normal_update()
    return to_obj(name, bm, material, smooth=False, **kw)


def buckle(name, center, w, h, normal, material=None, up=Vector((0, 0, 1))):
    """Rectangular iron buckle frame facing `normal`."""
    normal = Vector(normal).normalized()
    side = up.cross(normal).normalized()
    upv = normal.cross(side).normalized()
    c = Vector(center)
    corners = [c + side * w / 2 * sx + upv * h / 2 * sy for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    corners.append(corners[0])
    pts = corners
    return tube(name, pts, [0.004] * len(pts), material or M["iron"], seg=6, cap=True)


def rivets(name, positions, r, material):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    for p in positions:
        res = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=r)
        bmesh.ops.translate(bm, vec=Vector(p), verts=res["verts"])
    return to_obj(name, bm, material)


# --------------------------------------------------------------------------- body proportions
H_HEAD_C = 1.672   # head centre
NECK_Z = 1.56
SH_Z = 1.455       # shoulder joint height
SH_X = 0.205
WAIST_Z = 1.04
HIP_Z = 0.93
KNEE_Z = 0.50
BOOT_TOP = 0.43

# ------------------------------------------------------------------ torso (gambeson body)
def torso_section(z):
    """(rx, ry, y_offset) of the torso ellipse at height z."""
    keys = [  # z, rx, ry, yoff
        (0.86, 0.175, 0.125, 0.0),
        (0.95, 0.170, 0.120, 0.0),
        (1.04, 0.158, 0.112, -0.005),
        (1.15, 0.168, 0.118, -0.012),
        (1.28, 0.180, 0.125, -0.012),
        (1.38, 0.190, 0.120, -0.005),
        (1.46, 0.170, 0.100, 0.005),
        (1.53, 0.080, 0.065, 0.012),
    ]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= z <= b[0]:
            f = (z - a[0]) / (b[0] - a[0])
            f = f * f * (3 - 2 * f)
            return tuple(a[i] + (b[i] - a[i]) * f for i in (1, 2, 3))
    k = keys[0] if z < keys[0][0] else keys[-1]
    return k[1], k[2], k[3]


def torso_pt(theta, z, grow=0.0):
    rx, ry, yo = torso_section(z)
    # squarer back/chest
    c, s = math.cos(theta), math.sin(theta)
    e = 0.75
    x = math.copysign(abs(c) ** e, c) * (rx + grow)
    y = math.copysign(abs(s) ** e, s) * (ry + grow) + yo
    return Vector((x, y, z))


Z0, Z1 = 0.86, 1.545
surface("Torso_Gambeson", lambda u, v: torso_pt(2 * math.pi * u, Z0 + (Z1 - Z0) * v),
        32, 18, M["gamb"], closed_u=True, cap=True, uv_scale=(4, 3), subsurf=1)

# gambeson skirt (flared, slight front split)
def skirt(u, v):
    th = 2 * math.pi * u
    z = 0.95 - v * 0.30
    rx, ry, yo = torso_section(0.93)
    flare = 1.0 + 0.32 * v
    c, s = math.cos(th), math.sin(th)
    x = c * rx * flare * 1.03
    y = s * ry * flare * 1.10 + yo + 0.005 * v
    wave = 1 + 0.025 * math.sin(th * 9) * v
    return Vector((x * wave, y * wave, z))


surface("Gambeson_Skirt", skirt, 40, 6, M["gamb"], closed_u=True, uv_scale=(5, 1.4),
        solidify=0.012, subsurf=1)

# ------------------------------------------------------------------ neck & head
tube("Neck", [(0, 0.012, 1.50), (0, 0.010, 1.57), (0, 0.004, 1.62)], [0.068, 0.064, 0.060], M["skin"], seg=16,
     subsurf=1)


def head_deform(x, y, z):
    # x side, y depth (front = -y), z up; unit sphere input
    # jaw taper
    if z < 0:
        k = 1 - 0.28 * (-z) ** 1.3
        x *= k
        y *= 1 - 0.10 * (-z)
    # flatten sides & back of skull slightly
    x *= 0.95
    # brow ridge / forehead
    if y < -0.5 and 0.05 < z < 0.35 and abs(x) < 0.7:
        y -= 0.05 * math.exp(-((z - 0.22) / 0.08) ** 2)
    # eye sockets
    for ex in (-0.36, 0.36):
        d2 = ((x - ex) / 0.18) ** 2 + ((z - 0.10) / 0.10) ** 2
        if y < 0:
            y += 0.06 * math.exp(-d2)
    # cheekbones
    for ex in (-0.6, 0.6):
        d2 = ((x - ex) / 0.2) ** 2 + ((z + 0.05) / 0.12) ** 2
        if y < 0:
            y -= 0.04 * math.exp(-d2)
            x += 0.04 * math.copysign(math.exp(-d2), ex)
    # chin
    if y < -0.3:
        y -= 0.06 * math.exp(-((x / 0.25) ** 2 + ((z + 0.85) / 0.15) ** 2))
    return x, y, z


HC = (0, -0.004, H_HEAD_C)
ellipsoid("Head", HC, (0.084, 0.100, 0.114), M["skin"], seg=32, rings=24, deform=head_deform, subsurf=1)

# nose
tube("Nose", [(0, -0.104, 1.695), (0, -0.112, 1.671), (0, -0.118, 1.647), (0, -0.108, 1.637)],
     [0.008, 0.012, 0.016, 0.012], M["skin"], seg=10, subsurf=1)
# ears
for sx in (-1, 1):
    ellipsoid(f"Ear_{'R' if sx < 0 else 'L'}", (sx * 0.080, 0.002, 1.677), (0.012, 0.022, 0.030), M["skin"],
              seg=12, rings=8, rot=(0, 0, sx * 0.3), subsurf=1)
# eyes
for sx in (-1, 1):
    ex = sx * 0.031
    ellipsoid(f"Eye_{sx}", (ex, -0.082, 1.685), (0.0125, 0.010, 0.0085), M["eye_w"], seg=12, rings=8)
    ellipsoid(f"Iris_{sx}", (ex, -0.0915, 1.685), (0.0055, 0.002, 0.0055), M["iris"], seg=10, rings=6)
    # eyebrows (heavy, slightly furrowed)
    tube(f"Brow_{sx}", [(sx * 0.012, -0.097, 1.699), (sx * 0.030, -0.098, 1.703), (sx * 0.050, -0.090, 1.701)],
         [(0.004, 0.0035)] * 3, M["hair"], seg=8)
    # upper eyelid
    tube(f"Lid_{sx}", [(ex - 0.013, -0.086, 1.689), (ex, -0.093, 1.693), (ex + 0.013, -0.086, 1.689)],
         [0.003] * 3, M["skin"], seg=8)

# lips
tube("Lips", [(-0.020, -0.096, 1.612), (0, -0.104, 1.614), (0.020, -0.096, 1.612)], [(0.004, 0.0035)] * 3,
     M["lip"], seg=8)


# beard: shell over lower face, short and dense
def beard_deform(x, y, z):
    x, y, z = head_deform(x, y, z)
    return x * 1.06, y * 1.07 - 0.01, z * 1.03


def beard_fn(u, v):
    th = math.pi * (0.92 + 1.16 * u)          # front half (y<0) plus a little round the jaw
    front = max(0.0, -math.sin(th))
    top = -0.10 - 0.58 * front ** 5
    ph = -1.50 + (top + 1.50) * v
    x, y, z = math.cos(ph) * math.cos(th), math.cos(ph) * math.sin(th), math.sin(ph)
    x, y, z = beard_deform(x, y, z)
    return Vector((HC[0] + x * 0.082, HC[1] + y * 0.098, HC[2] + z * 0.118))


surface("Beard", beard_fn, 20, 10, M["hair"], solidify=0.006, subsurf=1)
# moustache
tube("Moustache", [(-0.028, -0.090, 1.610), (-0.012, -0.103, 1.625), (0, -0.106, 1.627), (0.012, -0.103, 1.625),
                   (0.028, -0.090, 1.610)], [0.004, 0.006, 0.006, 0.006, 0.004], M["hair"], seg=8, subsurf=1)


# hair: short, messy, swept up front
def hair_fn(u, v):
    th = 2 * math.pi * u
    c, s_ = math.cos(th), math.sin(th)
    front, back = max(0.0, -s_), max(0.0, s_)
    low = 0.18 + 0.42 * front ** 2 - 0.55 * back ** 1.5        # hairline: high forehead, low nape
    ph = low + (math.pi / 2 - low) * v
    x, y, z = math.cos(ph) * c * 0.96, math.cos(ph) * s_, math.sin(ph)
    tuft = 1.03 + 0.035 * math.sin(th * 9 + v * 6) * v + 0.04 * v * front   # messy, a bit swept up front
    return Vector((HC[0] + x * 0.086 * tuft, HC[1] + y * 0.102 * tuft, HC[2] + 0.002 + z * 0.116 * tuft))


surface("Hair", hair_fn, 32, 8, M["hair"], closed_u=True, solidify=0.008, subsurf=1)
import random as _r
_r.seed(3)
for i in range(120):
    u, v = _r.random(), 0.10 + 0.90 * _r.random()
    base = hair_fn(u, v)
    nrm = (base - Vector(HC)).normalized()
    # comb direction: up/back from the forehead, down at the sides
    comb = Vector((0, 0.6, 0.4)) if base.y < 0 else Vector((0, 0.5, -0.6))
    comb = (comb - nrm * comb.dot(nrm)).normalized()
    L = 0.022 + 0.018 * _r.random()
    tip = base + comb * L + nrm * (0.001 + 0.004 * _r.random())
    tube(f"HairTuft_{i}", [base - nrm * 0.004, base.lerp(tip, 0.5) + nrm * 0.002, tip],
         [(0.009, 0.005), (0.007, 0.004), 0.0012], M["hair"], seg=6)

# ------------------------------------------------------------------ legs / trousers / boots
for sx, tag in ((-1, "R"), (1, "L")):
    hip = Vector((sx * 0.095, 0.0, HIP_Z))
    knee = Vector((sx * 0.13, -0.015, KNEE_Z))
    ankle = Vector((sx * 0.155, 0.005, 0.10))
    tube(f"Trouser_{tag}", [hip, hip.lerp(knee, 0.5) + Vector((0, -0.005, 0)), knee,
                            knee.lerp(ankle, 0.5)],
         [0.100, 0.090, 0.072, 0.062], M["trousers"], seg=16, subsurf=1, uv_scale=(2, 3))
    # boot shaft (tall, slightly loose), folded cuff
    shaft = [ankle + Vector((0, 0, -0.02)), ankle.lerp(knee, 0.25), ankle.lerp(knee, 0.62),
             ankle.lerp(knee, 0.82)]
    tube(f"Boot_Shaft_{tag}", shaft, [0.050, 0.056, 0.064, 0.068], M["boot"], seg=16, cap=False, subsurf=1,
         solidify=0.006, uv_scale=(2, 2))
    cz = ankle.lerp(knee, 0.82)
    tube(f"Boot_Cuff_{tag}", [cz + Vector((0, 0, -0.07)), cz + Vector((0, 0, -0.01)), cz + Vector((0, 0, 0.005))],
         [0.073, 0.076, 0.074], M["boot"], seg=16, cap=False, solidify=0.008, subsurf=1)
    # foot
    foot_c = Vector((sx * 0.165, -0.06, 0.045))
    ellipsoid(f"Boot_Foot_{tag}", foot_c, (0.052, 0.125, 0.050), M["boot"], seg=20, rings=12,
              rot=(0, 0, sx * -0.12),
              deform=lambda x, y, z: (x, y, max(z, -0.85)), subsurf=1)
    # sole and heel
    box(f"Sole_{tag}", (sx * 0.165, -0.045, 0.008), (0.086, 0.215, 0.016), M["leather_d"], bevel=0.006,
        rot=(0, 0, sx * -0.12))
    box(f"Heel_{tag}", (sx * 0.16, 0.035, 0.022), (0.075, 0.07, 0.03), M["leather_d"], bevel=0.005)
    # boot straps with buckles (3 per boot)
    for k, f in enumerate((0.0, 0.32, 0.58)):
        c = ankle.lerp(knee, f) + Vector((0, 0, 0.01 if k else 0.035))
        r = 0.054 + 0.012 * f + 0.004
        ring = [c + Vector((math.cos(a) * r * 1.02, math.sin(a) * r, 0)) for a in
                [2 * math.pi * i / 20 for i in range(21)]]
        strap(f"BootStrap_{tag}_{k}", ring, 0.022, 0.004, M["leather_d"],
              normal_hint=lambda p, c=c: (p - c).normalized())
        bpos = c + Vector((sx * r * 0.85, -r * 0.55, 0))
        buckle(f"BootBuckle_{tag}_{k}", bpos, 0.026, 0.028, (sx * 0.85, -0.55, 0))

# ------------------------------------------------------------------ arms
R_SH = Vector((-SH_X, 0.0, SH_Z))
R_EL = Vector((-0.285, 0.015, 1.18))
R_WR = Vector((-0.335, -0.035, 0.94))
L_SH = Vector((SH_X, 0.0, SH_Z))
L_EL = Vector((0.305, 0.045, 1.19))
L_WR = Vector((0.315, -0.150, 1.04))

for tag, sh, el, wr in (("R", R_SH, R_EL, R_WR), ("L", L_SH, L_EL, L_WR)):
    # gambeson sleeve
    tube(f"Sleeve_{tag}", [sh + Vector((0, 0, 0.01)), sh.lerp(el, 0.5), el, el.lerp(wr, 0.45)],
         [0.068, 0.058, 0.050, 0.046], M["gamb"], seg=16, subsurf=1, uv_scale=(2, 2))
    # mail sleeve band visible under pauldron
    tube(f"MailSleeve_{tag}", [sh.lerp(el, 0.25), sh.lerp(el, 0.62)], [0.064, 0.058], M["mail"], seg=16,
         cap=False, subsurf=1, solidify=0.004, uv_scale=(4, 2))
    # leather bracer (forearm)
    tube(f"Bracer_{tag}", [el.lerp(wr, 0.18), el.lerp(wr, 0.55), wr + (wr - el).normalized() * -0.005],
         [0.050, 0.046, 0.040], M["leather"], seg=16, cap=False, subsurf=1, solidify=0.006, uv_scale=(2, 2))
    d = (wr - el).normalized()
    for k, f in enumerate((0.30, 0.55, 0.80)):
        c = el.lerp(wr, f)
        tube(f"BracerStrap_{tag}_{k}", [c - d * 0.008, c + d * 0.008], [0.050 - 0.008 * f] * 2, M["leather_d"],
             seg=16, cap=False, solidify=0.004)
    # glove + fist
    hand_c = wr + d * 0.055
    tube(f"GloveCuff_{tag}", [wr - d * 0.03, wr + d * 0.01], [0.046, 0.044], M["leather_d"], seg=14,
         cap=False, solidify=0.005, subsurf=1)
    ellipsoid(f"Hand_{tag}", hand_c, (0.040, 0.050, 0.055), M["leather_d"], seg=16, rings=10,
              rot=(0, 0, 0), subsurf=1)

# right hand grips sword (fingers wrap forward), left hand grips shield handle: add thumbs
for tag, wr, el, sgn in (("R", R_WR, R_EL, -1), ("L", L_WR, L_EL, 1)):
    d = (wr - el).normalized()
    hc = wr + d * 0.055
    tube(f"Thumb_{tag}", [hc + Vector((0, -0.03, 0.02)), hc + Vector((0, -0.05, 0.0)),
                          hc + Vector((sgn * -0.01, -0.052, -0.02))], [0.013, 0.012, 0.010], M["leather_d"],
         seg=8, subsurf=1)
    # knuckle row
    tube(f"Knuckles_{tag}", [hc + Vector((sgn * 0.02, -0.035, 0.03)), hc + Vector((sgn * 0.035, -0.04, -0.01)),
                             hc + Vector((sgn * 0.03, -0.035, -0.045))], [0.018, 0.019, 0.016], M["leather_d"],
         seg=8, subsurf=1)

# ------------------------------------------------------------------ leather cuirass
def cuirass_pt(u, v, grow=0.018):
    th = 2 * math.pi * u
    z = 0.97 + (1.50 - 0.97) * v
    p = torso_pt(th, z, grow)
    # open at the very top of the arms, cut scoop at neck handled by z range
    return p


surface("Cuirass", cuirass_pt, 36, 12, M["leather"], closed_u=True, solidify=0.008, subsurf=1, uv_scale=(4, 2))

# steel chest plates (3 overlapping lames, curved)
for k, (zc, h, wfrac) in enumerate(((1.360, 0.072, 0.46), (1.292, 0.072, 0.50), (1.224, 0.068, 0.48))):
    def lame(u, v, zc=zc, h=h, wfrac=wfrac):
        th = math.pi * 1.5 + (u - 0.5) * math.pi * wfrac
        z = zc + h / 2 - v * h
        p = torso_pt(th, z, 0.030 + 0.004 * (1 - v))
        # pointed centre (tapul ridge)
        p.y -= 0.010 * math.exp(-((u - 0.5) / 0.12) ** 2)
        return p
    surface(f"ChestLame_{k}", lame, 18, 4, M["steel"], solidify=0.004, subsurf=1, smooth=True)
    rv = []
    for u in (0.08, 0.92):
        th = math.pi * 1.5 + (u - 0.5) * math.pi * wfrac
        p = torso_pt(th, zc, 0.036)
        rv.append(p)
    rivets(f"ChestRivets_{k}", rv, 0.006, M["iron"])

# rivets along cuirass edges (decorative)
rv = []
for i in range(14):
    th = math.pi * 1.5 + (i / 13 - 0.5) * math.pi * 0.9
    rv.append(torso_pt(th, 1.43, 0.028))
rivets("CuirassTopRivets", rv, 0.005, M["iron"])

# X-straps on upper chest (harness) + ring brooch
for sx in (-1, 1):
    pts = []
    for i in range(9):
        f = i / 8
        th = math.pi * 1.5 + sx * (0.55 - 0.55 * f) * math.pi * 0.5
        z = 1.47 - 0.28 * f
        p = torso_pt(th, z, 0.040)
        pts.append(p)
    strap(f"ChestStrap_{sx}", pts, 0.028, 0.004, M["leather_d"],
          normal_hint=lambda p: Vector((p.x, p.y + 0.01, 0)).normalized())

# side lacing straps of cuirass
for sx in (-1, 1):
    for k in range(3):
        z = 1.10 + k * 0.09
        p = torso_pt(math.pi if sx < 0 else 0.0, z, 0.026)
        buckle(f"SideBuckle_{sx}_{k}", p + Vector((0, -0.02, 0)), 0.02, 0.02, (sx, 0, 0))

# ------------------------------------------------------------------ belts, buckles, pouches, tassets
def belt_ring(z, grow, droop=0.0):
    pts = []
    for i in range(41):
        th = 2 * math.pi * i / 40
        zz = z - droop * max(0.0, -math.sin(th)) ** 2
        pts.append(torso_pt(th, zz, grow))
    return pts


strap("Belt_Main", belt_ring(1.035, 0.030), 0.050, 0.006, M["leather_d"],
      normal_hint=lambda p: Vector((p.x, p.y, 0)).normalized())
strap("Belt_Low", belt_ring(0.965, 0.040, droop=0.035), 0.040, 0.006, M["leather"],
      normal_hint=lambda p: Vector((p.x, p.y, 0)).normalized())
buckle("Belt_Buckle_Main", torso_pt(math.pi * 1.5, 1.035, 0.040), 0.058, 0.062, (0, -1, 0))
buckle("Belt_Buckle_Low", torso_pt(math.pi * 1.5 + 0.3, 0.935, 0.048), 0.046, 0.048, (0.25, -1, 0))
# hanging belt tongue
strap("Belt_Tongue", [torso_pt(math.pi * 1.5 + 0.05, 1.02, 0.044), torso_pt(math.pi * 1.5 + 0.05, 0.86, 0.046)],
      0.038, 0.005, M["leather_d"])

# leather tassets (front & side flaps over the skirt)
for k, (th0, w, L) in enumerate(((1.5, 0.30, 0.26), (1.18, 0.26, 0.22), (1.82, 0.26, 0.22),
                                 (0.95, 0.22, 0.18), (2.05, 0.22, 0.18))):
    def tasset(u, v, th0=th0, w=w, L=L):
        th = math.pi * th0 + (u - 0.5) * w
        z = 1.00 - v * L
        rx, ry, yo = torso_section(0.95)
        flare = 1.0 + 0.30 * v
        c, s = math.cos(th), math.sin(th)
        return Vector((c * (rx + 0.040) * flare, s * (ry + 0.045) * flare + yo, z))
    surface(f"Tasset_{k}", tasset, 6, 6, M["leather"], solidify=0.007, subsurf=1)

# pouches at both hips
for sx, th in ((-1, math.pi * 1.20), (1, math.pi * 1.80)):
    p = torso_pt(th, 0.97, 0.075)
    n = Vector((p.x, p.y, 0)).normalized()
    rot_z = math.atan2(n.y, n.x) + math.pi / 2
    box(f"Pouch_{sx}", p, (0.085, 0.045, 0.10), M["leather"], bevel=0.012, rot=(0, 0, rot_z), subsurf=1)
    box(f"PouchFlap_{sx}", p + n * 0.024 + Vector((0, 0, 0.025)), (0.088, 0.008, 0.06), M["leather_d"],
        bevel=0.004, rot=(0, 0, rot_z))

# ------------------------------------------------------------------ pauldrons (cap + 3 lames)
LAMES = [(0.45, 1.45, 2.1, 0.122), (0.15, 0.53, 1.75, 0.126), (-0.15, 0.23, 1.65, 0.128), (-0.45, -0.07, 1.55, 0.128)]
for sx, tag in ((-1, "R"), (1, "L")):
    c = Vector((sx * (SH_X + 0.035), 0.0, SH_Z - 0.045))
    az0 = 0.0 if sx > 0 else math.pi
    for k, (e0, e1, half, r) in enumerate(LAMES):
        def paul(u, v, e0=e0, e1=e1, half=half, r=r):
            az = az0 + (u - 0.5) * 2 * half * sx
            el = e1 - (e1 - e0) * v
            d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
            # slight flare at the lower edge of every lame
            rr = r * (1 + 0.06 * v)
            return c + Vector((d.x * rr, d.y * rr * 0.92, d.z * rr * 0.92))
        surface(f"Pauldron_{tag}_{k}", paul, 20, 4, M["steel"], solidify=0.004, subsurf=1)
        # rivets on the front/back ends of each lame
        el = (e0 + e1) / 2
        rv = []
        for az in (az0 - half * 0.85, az0 + half * 0.85, az0):
            d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
            rv.append(c + Vector((d.x * (r + 0.004), d.y * (r + 0.004) * 0.92, d.z * (r + 0.004) * 0.92)))
        rivets(f"PauldronRivets_{tag}_{k}", rv, 0.005, M["iron"])

# ------------------------------------------------------------------ cloak, mantle, hood, clasp
def cloak_fn(u, v, inner=0.0):
    # u: 0 (right front edge) .. 1 (left front edge) around the back; v: top..hem
    g = min(1.0, v * 3.0)
    a0 = math.pi * (0.24 - 0.21 * min(1.0, v / 0.45))   # wraps further forward lower down
    a = a0 + (math.pi - 2 * a0) * u
    z = 1.52 - v * 1.17
    rx = 0.215 + 0.11 * g ** 0.7 + 0.07 * v
    ry = 0.165 + 0.10 * max(0.0, (v - 0.3) / 0.7)
    x = -math.cos(a) * rx
    y = math.sin(a) * ry + 0.03
    # vertical folds, deeper towards the hem
    fold = (0.022 * math.sin(a * 13 + 0.6) + 0.012 * math.sin(a * 6 + 1.3)) * v ** 0.8
    x -= fold * math.cos(a)
    y += fold * math.sin(a)
    n = Vector((-math.cos(a), math.sin(a), 0))
    return Vector((x, y, z)) - n * inner


surface("Cloak_Outer", lambda u, v: cloak_fn(u, v), 44, 16, M["cloak_g"], solidify=0.004, subsurf=1,
        uv_scale=(3, 3))
surface("Cloak_Lining", lambda u, v: cloak_fn(u, v, inner=0.007), 44, 16, M["cloak_b"], solidify=0.003,
        subsurf=1, uv_scale=(3, 3))


# shoulder mantle (short cape over shoulders, brown in front)
def mantle(u, v):
    a = math.pi * (1.5 + 0.17) + u * math.pi * (2 - 0.34)   # leaves the chest open
    z = 1.565 - v * 0.13 - 0.04 * v * v
    r = 0.098 + v * 0.16
    x = math.cos(a) * r * 1.08
    y = math.sin(a) * r * 0.85 + 0.02
    sag = 0.025 * v * (1 + 0.4 * math.sin(a * 7))
    return Vector((x, y, z - sag))


surface("Mantle", mantle, 40, 5, M["cloak_b"], solidify=0.008, subsurf=1, uv_scale=(4, 1))


# hood folded down behind the neck
def hood(u, v):
    a = math.pi * (0.1 + 0.8 * u)
    r = 0.13 + 0.03 * math.sin(math.pi * v)
    z = 1.55 - 0.18 * v
    x = -math.cos(a) * r
    y = math.sin(a) * (r * 0.9 + 0.05 * v) + 0.02
    return Vector((x, y, z))


surface("Hood", hood, 20, 6, M["cloak_g"], solidify=0.01, subsurf=1)

# ring brooch at character's right collarbone
brooch_c = Vector((-0.105, -0.128, 1.455))
ring = [brooch_c + Vector((math.cos(a) * 0.022, -0.004, math.sin(a) * 0.022)) for a in
        [2 * math.pi * i / 24 for i in range(25)]]
tube("Brooch", ring, [0.0035] * len(ring), mat("Silver", (0.75, 0.74, 0.72), metal=1.0, rough=0.25), seg=8)
tube("BroochPin", [brooch_c + Vector((-0.03, -0.006, -0.01)), brooch_c + Vector((0.03, -0.006, 0.01))],
     [0.0022, 0.0022], _mats["Silver"], seg=6)

# ------------------------------------------------------------------ backpack
BP = Vector((0.0, 0.285, 1.265))
box("Backpack_Body", BP, (0.34, 0.13, 0.31), M["leather"], bevel=0.03, subsurf=1)
box("Backpack_Flap", BP + Vector((0, 0.068, 0.045)), (0.35, 0.012, 0.24), M["leather"], bevel=0.006)
box("Backpack_Top", BP + Vector((0, 0.0, 0.158)), (0.35, 0.14, 0.012), M["leather"], bevel=0.005)
for sx in (-1, 1):
    strap(f"Backpack_Strap_{sx}", [BP + Vector((sx * 0.08, 0.077, 0.165)), BP + Vector((sx * 0.08, 0.078, -0.07))],
          0.032, 0.005, M["leather_d"], normal_hint=lambda p: Vector((0, 1, 0)))
    buckle(f"Backpack_Buckle_{sx}", BP + Vector((sx * 0.08, 0.083, -0.045)), 0.036, 0.034, (0, 1, 0))
    box(f"Backpack_SidePocket_{sx}", BP + Vector((sx * 0.182, 0.01, -0.07)), (0.04, 0.09, 0.12), M["leather"],
        bevel=0.012)
# loop handle
tube("Backpack_Handle", [BP + Vector((-0.04, 0.0, 0.164)), BP + Vector((0, 0.0, 0.196)),
                         BP + Vector((0.04, 0.0, 0.164))], [0.007] * 3, M["leather_d"], seg=8)
# ------------------------------------------------------------------ sword (in right hand)
hand_r = R_WR + (R_WR - R_EL).normalized() * 0.055
blade_dir = Vector((-0.62, -0.18, -0.76)).normalized()
guard_c = hand_r + blade_dir * 0.065
tip = guard_c + blade_dir * 0.86
side = blade_dir.cross(Vector((0, -1, 0.15))).normalized()   # flat of blade faces viewer
flat_n = side.cross(blade_dir).normalized()


def blade(u, v):
    L = 0.86
    t = v
    w = 0.026 * (1 - t) + 0.020 * t
    if t > 0.85:
        w *= (1 - t) / 0.15
    a = 2 * math.pi * u
    # diamond cross section with fuller
    cs = math.cos(a)
    sn = math.sin(a)
    x = cs * w
    yy = sn * 0.0045 * (1 - abs(cs) ** 2 * 0.9)
    return guard_c + blade_dir * (L * t + 0.01) + side * x + flat_n * yy


surface("Sword_Blade", blade, 16, 20, M["steel"], closed_u=True)
# fuller (darker groove line on both faces)
for s in (-1, 1):
    tube(f"Sword_Fuller_{s}", [guard_c + blade_dir * 0.02 + flat_n * s * 0.004,
                               guard_c + blade_dir * 0.60 + flat_n * s * 0.004],
         [(0.004, 0.0008), (0.002, 0.0008)], M["iron"], seg=8)
# crossguard: slightly curved down toward blade, flared ends
gpts = [guard_c + side * (k * 0.11) + blade_dir * (0.018 * (k * k)) for k in (-1, -0.5, 0, 0.5, 1)]
tube("Sword_Guard", gpts, [0.012, 0.010, 0.013, 0.010, 0.012], M["steel"], seg=10, subsurf=1)
ellipsoid("Sword_GuardBlock", guard_c, (0.022, 0.016, 0.026), M["steel"], seg=12, rings=8)
# grip and pommel
grip_a = guard_c - blade_dir * 0.01
grip_b = guard_c - blade_dir * 0.185
tube("Sword_Grip", [grip_a, grip_a.lerp(grip_b, 0.5), grip_b], [0.0135, 0.015, 0.013], M["grip"], seg=12,
     subsurf=1)
ellipsoid("Sword_Pommel", grip_b - blade_dir * 0.022, (0.026, 0.026, 0.026), M["steel"], seg=16, rings=10,
          deform=lambda x, y, z: (x, y * 0.55, z))

# ------------------------------------------------------------------ scabbard at left hip
sc_top = torso_pt(math.pi * 1.92, 0.98, 0.07) + Vector((0.02, 0.0, 0))
sc_dir = Vector((0.18, 0.30, -0.93)).normalized()
sc_tip = sc_top + sc_dir * 0.84
tube("Scabbard", [sc_top, sc_top.lerp(sc_tip, 0.5), sc_tip - sc_dir * 0.03, sc_tip],
     [(0.024, 0.012), (0.022, 0.011), (0.017, 0.009), (0.006, 0.005)], M["leather"], seg=12, subsurf=1)
tube("Scabbard_Locket", [sc_top - sc_dir * 0.005, sc_top + sc_dir * 0.07], [(0.027, 0.015)] * 2, M["steel"],
     seg=12, subsurf=1)
tube("Scabbard_Chape", [sc_tip - sc_dir * 0.10, sc_tip - sc_dir * 0.01, sc_tip + sc_dir * 0.005],
     [(0.020, 0.011), (0.010, 0.007), (0.004, 0.004)], M["steel"], seg=12, subsurf=1)
for k in (0.12, 0.28):
    p = sc_top.lerp(sc_tip, k)
    tube(f"Scabbard_Band_{k}", [p - sc_dir * 0.01, p + sc_dir * 0.01], [(0.026, 0.014)] * 2, M["leather_d"], seg=12)
# hanger straps to the belt
strap("Scabbard_Hanger", [torso_pt(math.pi * 1.85, 1.03, 0.05), sc_top + sc_dir * 0.02],
      0.022, 0.004, M["leather_d"])
strap("Scabbard_Hanger2", [torso_pt(math.pi * 0.05, 1.03, 0.05), sc_top + sc_dir * 0.14], 0.022, 0.004,
      M["leather_d"])

# ------------------------------------------------------------------ heater shield on left arm
SH_W, SH_H = 0.54, 0.78
shield_c = Vector((0.335, -0.235, 0.83))


def shield_hw(v):
    # half width as a function of v (0 top .. 1 bottom point)
    if v < 0.40:
        return 0.5
    t = (v - 0.40) / 0.60
    return 0.5 * math.cos(t * math.pi / 2) ** 0.85


R_shield = (Matrix.Rotation(0.62, 3, "Z") @ Matrix.Rotation(-0.16, 3, "Y") @ Matrix.Rotation(0.05, 3, "X"))


def shield_local(x, z):
    """x,z in shield plane (metres, z up, top at +SH_H*0.45). Returns world point."""
    curv = 0.55  # cylindrical bend
    y = (x * x) * curv
    return shield_c + R_shield @ Vector((x, y, z))


def shield_face(u, v):
    top_bulge = 0.025 * (1 - (2 * u - 1) ** 2)
    hw = shield_hw(v)
    x = (2 * u - 1) * hw * SH_W
    z = SH_H * 0.45 + top_bulge - v * SH_H
    return shield_local(x, z)


def shield_uv_fix(ob):
    me = ob.data
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            u, v = uv[li].uv
            hw = shield_hw(v)
            uv[li].uv = (0.5 + (2 * u - 1) * hw, 1 - v * 0.95 - 0.02)


sh_ob = surface("Shield", shield_face, 24, 30, M["wood"], solidify=0.016,
                mats=[M["wood_back"], M["wood"]], smooth=True)
shield_uv_fix(sh_ob)
# steel rim along the outline
rim = []
for i in range(31):
    v = i / 30
    rim.append((shield_hw(v), v))
outline = [shield_face(0.5 + hw, v) for hw, v in rim] + \
          [shield_face(0.5 - hw, v) for hw, v in reversed(rim)]
outline.append(outline[0])
# push slightly forward so the rim wraps the edge
tube("Shield_Rim", outline, [(0.012, 0.014)] * len(outline), M["steel"], seg=8, cap=False)
# rim rivets
rv = [shield_face(0.5 + (hw - 0.03) * (1 if i % 2 else -1), min(v, 0.96)) for i, (hw, v) in enumerate(rim[::3])]
rivets("Shield_RimRivets", rv, 0.006, M["iron"])
# arm straps behind the shield (enarmes)
nrm_back = R_shield @ Vector((0, 1, 0))
for z in (0.10, -0.08):
    a = shield_local(-0.12, z) + nrm_back * 0.02
    b = shield_local(0.12, z) + nrm_back * 0.02
    strap(f"Shield_Enarme_{z}", [a, (a + b) / 2 + nrm_back * 0.05, b], 0.03, 0.005, M["leather_d"],
          normal_hint=lambda p: nrm_back)

# ------------------------------------------------------------------ finish: shade smooth, apply, export
for ob in COLL.objects:
    ob.select_set(True)

# root empty so engines can grab the whole character
root = bpy.data.objects.new("Knight", None)
COLL.objects.link(root)
for ob in COLL.objects:
    if ob is not root and ob.parent is None:
        ob.parent = root

glb = os.path.join(HERE, "knight.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True, export_yup=True,
                          export_image_format="JPEG", export_jpeg_quality=88)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "knight.blend"), compress=True)
print("EXPORTED", glb, os.path.getsize(glb) // 1024, "KB")

# --------------------------------------------------------------------------- optional preview renders
if "--render" in sys.argv:
    outdir = os.path.join(HERE, "renders")
    os.makedirs(outdir, exist_ok=True)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(os.environ.get("SAMPLES", 24))
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 520
    scene.render.resolution_y = 860
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("W")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.36, 0.37, 0.39, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.45
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    # floor
    bpy.ops.mesh.primitive_plane_add(size=6)
    fl = bpy.context.active_object
    fl.data.materials.append(mat("Floor", (0.05, 0.055, 0.065), rough=0.5))
    # lights: key, fill, rim
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
    views = {"front": (0, -1), "back": (0, 1), "side": (-1, 0), "three_quarter": (-0.7, -0.75)}
    only = os.environ.get("VIEWS")
    views["head"] = (-0.35, -1)
    for vname, (dx, dy) in views.items():
        if only and vname not in only.split(","):
            continue
        target = Vector((0, 0, 0.92)) if vname != "head" else Vector((0, -0.02, 1.66))
        dirv = Vector((dx, dy, 0.08 if vname != "head" else 0.02)).normalized()
        cam.location = target + dirv * (6.4 if vname != "head" else 1.6)
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(outdir, f"{vname}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", vname)
