"""Texture an untextured image-to-3D shape by projecting the front/back reference photos onto it.

  pip install trimesh fast_simplification scipy pillow "rembg[cpu]"
  python3 texture_shape.py shape.glb [out.glb]

The shape is assumed to be in the image-to-3D canonical frame (Y up, front view looking down -Z,
orthographic), which is what Hunyuan3D / TRELLIS output for a single front image. Each face takes
its colour from whichever photo it faces (front.png or back.png, z-buffer checked for occlusion);
the head's sides come from side.png. All three photos are packed into one 3072x1024 atlas. Output: Y-up, metres, 1.80 m tall,
feet at y=0.
"""
import os
import sys

import fast_simplification
import numpy as np
import trimesh
from PIL import Image
from rembg import new_session, remove
from scipy.spatial import cKDTree
from scipy.ndimage import binary_closing, binary_erosion, distance_transform_edt, maximum_filter

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_FACES = 250_000
HEIGHT = 1.80
ZRES = 384  # z-buffer resolution for occlusion tests
HEAD_FROM = 0.875  # fraction of the height where the head starts


def cutout(path, session):
    rgba = np.array(remove(Image.open(path).convert("RGB"), session=session))
    mask = rgba[..., 3] > 128
    rgb = np.array(Image.open(path).convert("RGB"))
    # bleed edge colours into the background so texture filtering never picks up the backdrop
    _, (iy, ix) = distance_transform_edt(~mask, return_indices=True)
    return rgb[iy, ix], mask


def fit(xy, mask):
    """Find pixel = (x * sx + ox, -y * sy + oy) that best overlays the projected mesh on the mask."""
    ys, xs = np.nonzero(mask)
    h, w = mask.shape
    k = 4  # score on a 4x downsampled mask
    small = mask[::k, ::k]
    sub = xy[:: max(1, len(xy) // 150_000)]

    def iou(p):
        sx, sy, ox, oy = p
        px = ((sub[:, 0] * sx + ox) / k).astype(int)
        py = ((-sub[:, 1] * sy + oy) / k).astype(int)
        ok = (px >= 0) & (px < w // k) & (py >= 0) & (py < h // k)
        sil = np.zeros_like(small)
        sil[py[ok], px[ok]] = True
        sil = binary_closing(sil, iterations=2)
        return (sil & small).sum() / (sil | small).sum()

    # start: heights match, feet on the mask's lowest row, bounding boxes centred
    s0 = (ys.max() - ys.min()) / np.ptp(sub[:, 1])
    best = [s0, s0, (xs.min() + xs.max()) / 2 - (sub[:, 0].max() + sub[:, 0].min()) / 2 * s0,
            ys.max() + sub[:, 1].min() * s0]
    score = iou(best)
    # coordinate descent, coarse to fine: x/y scale, then x/y offset
    for step_s, step_o in ((0.06, 40), (0.03, 16), (0.012, 6), (0.005, 2)):
        improved = True
        while improved:
            improved = False
            for i, step in ((0, step_s * s0), (1, step_s * s0), (2, step_o), (3, step_o)):
                for sign in (-1, 1):
                    cand = list(best)
                    cand[i] += sign * step
                    sc = iou(cand)
                    if sc > score:
                        best, score, improved = cand, sc, True
    return score, best


def project(pts, params, flip):
    sx, sy, ox, oy = params
    x = -pts[:, 0] if flip else pts[:, 0]
    return np.stack([x * sx + ox, -pts[:, 1] * sy + oy], 1)


def visible(verts, faces, pix, depth, shape):
    """Per-face visibility: face centroid depth vs. a splatted vertex z-buffer (bigger = nearer)."""
    h, w = shape
    k = w / ZRES
    q = np.clip((pix / k).astype(int), 0, ZRES - 1)
    zbuf = np.full((int(h / k), ZRES), -np.inf)
    np.maximum.at(zbuf, (np.clip(q[:, 1], 0, zbuf.shape[0] - 1), q[:, 0]), depth)
    zbuf = maximum_filter(zbuf, size=3)
    c = pix[faces].mean(1)
    cq = np.clip((c / k).astype(int), 0, ZRES - 1)
    near = zbuf[np.clip(cq[:, 1], 0, zbuf.shape[0] - 1), cq[:, 0]]
    tol = 0.025 * np.ptp(verts[:, 1])
    return depth[faces].mean(1) >= near - tol


def main(src, out):
    mesh = trimesh.load(src, force="mesh")
    # Hunyuan3D pads its output with duplicate and zero-area faces, which break the decimator
    mesh.update_faces(mesh.unique_faces() & mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    v, f = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32),
                                        target_reduction=max(0.0, 1 - TARGET_FACES / len(mesh.faces)))
    mesh = trimesh.Trimesh(v, f, process=True)
    print("faces", len(mesh.faces), "verts", len(mesh.vertices))

    session = new_session("isnet-general-use")
    views = {}
    for name, flip in (("front", False), ("back", True)):
        rgb, mask = cutout(os.path.join(HERE, f"{name}.png"), session)
        xy = mesh.vertices[:, :2] * ([-1, 1] if flip else [1, 1])
        iou, params = fit(xy, mask)
        print(f"{name}: silhouette IoU {iou:.3f}")
        pix = project(mesh.vertices, params, flip)
        depth = mesh.vertices[:, 2] * (-1 if flip else 1)
        vis = visible(mesh.vertices, mesh.faces, pix, depth, mask.shape)
        inner = binary_erosion(mask, iterations=2)
        c = np.clip(pix[mesh.faces].mean(1).astype(int), 0, mask.shape[0] - 1)
        vis &= inner[c[:, 1], c[:, 0]]
        views[name] = dict(rgb=rgb, pix=pix, vis=vis)

    nz = mesh.face_normals[:, 2]
    fv, bv = views["front"]["vis"], views["back"]["vis"]
    use_back = nz < 0
    use_back = np.where(use_back & ~bv & fv, False, use_back)
    use_back = np.where(~use_back & ~fv & bv, True, use_back)
    view = use_back.astype(int)  # 0 front, 1 back, 2 side
    print(f"faces from front {np.sum(view == 0)}, from back {np.sum(view == 1)}, "
          f"seen by neither {np.sum(~fv & ~bv)}")

    # faces neither photo sees (armpits, inside of the cloak, behind the shield) take the colour of
    # the nearest seen face instead of a stretched projection
    seen = fv | bv
    cent = mesh.triangles_center
    near = np.flatnonzero(seen)[cKDTree(cent[seen]).query(cent[~seen])[1]]
    view[~seen] = view[near]

    # the side photo's pose differs from the front one (no shield, sword sheathed), so it is only
    # used for the head, where front/back projection would smear the face across the temples
    y = mesh.vertices[:, 1]
    head_v = y > y.min() + HEAD_FROM * np.ptp(y)
    rgb, mask = cutout(os.path.join(HERE, "side.png"), session)
    ys = np.nonzero(mask.any(1))[0]
    head_mask = mask.copy()
    head_mask[ys.min() + int((1 - HEAD_FROM) * (ys.max() - ys.min())):] = False
    fits = [fit(mesh.vertices[head_v][:, [2, 1]] * [sgn, 1], head_mask) for sgn in (1, -1)]
    sgn = (1, -1)[int(fits[1][0] > fits[0][0])]
    print(f"side (head): silhouette IoU {max(fits[0][0], fits[1][0]):.3f}")
    zy = np.column_stack([mesh.vertices[:, 2] * sgn, mesh.vertices[:, 1], np.zeros(len(y))])
    views["side"] = dict(rgb=rgb, pix=project(zy, fits[int(sgn < 0)][1], False))
    side = (head_v[mesh.faces].all(1) & (np.abs(mesh.face_normals[:, 0]) > 0.85)
            & (np.abs(nz) < 0.4))
    view[side] = 2
    print(f"head faces from side {side.sum()}")

    # atlas: front | back | side; split vertices on the seams
    h, w = views["front"]["rgb"].shape[:2]
    names = ("front", "back", "side")
    atlas = np.concatenate([views[n]["rgb"] for n in names], 1)
    corner_pix = np.stack([views[n]["pix"][mesh.faces] for n in names])[view, np.arange(len(view))]
    fill = ~seen & ~side
    corner_pix[fill] = corner_pix[near[~side[~seen]]].mean(1, keepdims=True)
    rows = np.column_stack([mesh.faces.ravel(), np.repeat(view, 3), corner_pix.reshape(-1, 2)])
    uniq, inv = np.unique(rows, axis=0, return_inverse=True)
    vid, vview, pix = uniq[:, 0].astype(int), uniq[:, 1], uniq[:, 2:]
    uv = np.stack([(pix[:, 0] + vview * w) / (len(names) * w), 1 - pix[:, 1] / h], 1)

    verts = mesh.vertices[vid]
    head = verts[:, 1] > verts[:, 1].min() + HEAD_FROM * np.ptp(verts[:, 1])
    # centre on the head: sword and shield make the bounding box lopsided
    verts -= [verts[head, 0].mean(), verts[:, 1].min(), verts[head, 2].mean()]
    verts *= HEIGHT / verts[:, 1].max()
    material = trimesh.visual.material.PBRMaterial(
        name="Knight", baseColorTexture=Image.fromarray(atlas), metallicFactor=0.0, roughnessFactor=0.8)
    out_mesh = trimesh.Trimesh(verts, inv.reshape(-1, 3), process=False,
                               visual=trimesh.visual.TextureVisuals(uv=uv, material=material))
    out_mesh.export(out)
    print("->", out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    src = sys.argv[1]
    main(src, sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "hunyuan2_knight.glb"))
