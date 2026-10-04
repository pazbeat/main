"""Texture untextured image-to-3D shapes by projecting the reference photos onto them.

  pip install trimesh fast_simplification scipy shapely xatlas onnxruntime pillow matplotlib \
      mediapipe "rembg[cpu]"
  python3 texture_shape.py body_shape.glb [--head head_shape.glb] [out.glb]

Shapes are assumed to be in the image-to-3D canonical frame (Y up, front view looking down -Z,
orthographic), which is what Hunyuan3D / TRELLIS output for a single front image.

Each mesh is UV-unwrapped (xatlas) and gets one baked texture: every texel blends the photos that
see it (z-buffer occlusion test), weighted by how squarely it faces each camera, so there are no
seams between photos. Body: front.png + back.png; texels neither sees take the nearest seen colour.

Head (optional, recommended): in a full-body shape the face is a few percent of the height, so it
comes out as a smooth blob with a 100 px texture. make_head_crops() cuts the head out of the
front/side/back photos and upscales it 4x with Real-ESRGAN; image-to-3D on front_head.png gives a
detailed head, which is baked from the three crops, aligned to the body through front.png and
swapped in for the body's own head at the neck.

Output: Y-up, metres, 1.80 m tall, feet at y=0; meshes "Body" and "Head", one 2048x2048 texture each.
"""
import os
import sys
import urllib.request

import fast_simplification
import numpy as np
import scipy.sparse
import trimesh
from matplotlib.path import Path as MplPath
from PIL import Image
from rembg import new_session, remove
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import binary_closing, binary_erosion, distance_transform_edt, grey_closing
from scipy.spatial import Delaunay, cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
HEIGHT = 1.80
BODY_FACES = 250_000
HEAD_FACES = 120_000
BODY_TEX = 2048
HEAD_TEX = 2048
ESRGAN_URL = "https://huggingface.co/imgdesignart/realesrgan-x4-onnx/resolve/main/onnx/model.onnx"
FACE_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/"
                  "float16/1/face_landmarker.task")
_session = None


def rembg_session():
    global _session
    if _session is None:
        _session = new_session("isnet-general-use")
    return _session


def cutout(img):
    """RGB with background bled from the edge colours (no backdrop in texture filtering), mask."""
    img = img.convert("RGB")
    mask = np.array(remove(img, session=rembg_session()))[..., 3] > 128
    rgb = np.array(img)
    _, (iy, ix) = distance_transform_edt(~mask, return_indices=True)
    return rgb[iy, ix], mask


def load_mesh(path, faces):
    mesh = trimesh.load(path, force="mesh")
    # Hunyuan3D pads its output with duplicate and zero-area faces, which break the decimator
    mesh.update_faces(mesh.unique_faces() & mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    v, f = fast_simplification.simplify(mesh.vertices, mesh.faces,
                                        target_reduction=max(0.0, 1 - faces / len(mesh.faces)))
    return trimesh.Trimesh(v, f, process=True)


# ------------------------------------------------------------------ head crops (Real-ESRGAN x4)
def upscale4(img, tile=64, pad=8):
    import onnxruntime as ort
    model = os.path.join(os.path.expanduser("~/.cache"), "realesrgan-x4.onnx")
    if not os.path.exists(model):
        os.makedirs(os.path.dirname(model), exist_ok=True)
        urllib.request.urlretrieve(ESRGAN_URL, model)
    sess = ort.InferenceSession(model)
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    h, w, _ = a.shape
    out = np.zeros((h * 4, w * 4, 3), np.float32)
    ap = np.pad(a, ((pad, pad + tile), (pad, pad + tile), (0, 0)), mode="reflect")
    step = tile - 2 * pad
    for y in range(0, h, step):
        for x in range(0, w, step):
            t = sess.run(None, {"input.1": ap[y:y + tile, x:x + tile].transpose(2, 0, 1)[None]})[0]
            t = t[0].transpose(1, 2, 0)[4 * pad:4 * (tile - pad), 4 * pad:4 * (tile - pad)]
            hh, ww = min(4 * step, 4 * (h - y)), min(4 * step, 4 * (w - x))
            out[4 * y:4 * y + hh, 4 * x:4 * x + ww] = t[:hh, :ww]
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))


def head_box(mask):
    """Square box around the head: centred on the top 16% of the figure, 20% of its height."""
    ys = np.nonzero(mask.any(1))[0]
    top, h = ys.min(), ys.max() - ys.min()
    xs = np.nonzero(mask[top:top + int(0.16 * h)].any(0))[0]
    cx, side = (xs.min() + xs.max()) // 2, int(0.2 * h)
    y0 = max(0, top - 8)
    return cx - side // 2, y0, cx + side // 2, y0 + side


def make_head_crops():
    """Write {front,side,back}_head.png (4x upscaled head crops); return their boxes in the photos."""
    boxes = {}
    for name in ("front", "side", "back"):
        img = Image.open(os.path.join(HERE, f"{name}.png")).convert("RGB")
        boxes[name] = head_box(cutout(img)[1])
        out = os.path.join(HERE, f"{name}_head.png")
        if not os.path.exists(out):
            upscale4(img.crop(boxes[name])).save(out)
    return boxes


def collar_row(mask):
    """Row in a head crop where the mask widens fastest below the face: where the collar starts."""
    rows = np.nonzero(mask.any(1))[0]
    width = mask.sum(1).astype(float)
    lo, hi = rows.min() + int(0.55 * np.ptp(rows)), rows.min() + int(0.97 * np.ptp(rows))
    d = int(0.03 * np.ptp(rows))
    return lo + int(np.argmax(width[lo + d:hi + d] - width[lo:hi]))


def neck_height(mesh):
    """y of the neck: the deepest point of the front profile between collar and chin."""
    v = mesh.vertices
    band = np.abs(v[:, 0] - np.median(v[:, 0])) < 0.04 * np.ptp(v[:, 0])
    y0, h = v[:, 1].min(), np.ptp(v[:, 1])
    bins = np.linspace(y0 + 0.05 * h, y0 + 0.45 * h, 40)
    i = np.digitize(v[band, 1], bins)
    zmax = np.array([v[band][i == j, 2].max() if np.any(i == j) else np.inf
                     for j in range(1, len(bins))])
    j = int(np.argmin(zmax))
    return (bins[j] + bins[j + 1]) / 2


# ------------------------------------------------------------------ face fitting (MediaPipe landmarks)
# eyelid loops of the MediaPipe face mesh, corner to corner; irises are points 468-477
R_EYE = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
L_EYE = [362, 398, 384, 385, 386, 387, 388, 466, 263, 249, 390, 373, 374, 380, 381, 382]
# on a sculpt with closed eyes the eyelid and iris points are guesses; use the rest for the warp
ROBUST = np.array([i for i in range(468)
                   if i not in (set(R_EYE) | set(L_EYE)) - {33, 133, 362, 263}])


def face_landmarks(img):
    """478 MediaPipe face landmarks (pixel x, y, relative depth) or None."""
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    model = os.path.join(os.path.expanduser("~/.cache"), "face_landmarker.task")
    if not os.path.exists(model):
        os.makedirs(os.path.dirname(model), exist_ok=True)
        urllib.request.urlretrieve(FACE_MODEL_URL, model)
    lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model, delegate=BaseOptions.Delegate.CPU),
        num_faces=1))
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(img)))
    lm.close()
    if not r.face_landmarks:
        return None
    h, w = img.shape[:2]
    return np.array([[q.x * w, q.y * h, q.z * w] for q in r.face_landmarks[0]])


def clay(mesh, params, shape, samples=6_000_000):
    """Grey shaded front render of the mesh in a photo's pixel frame, plus which surface sample
    each pixel shows, so landmarks found on the render can be lifted back onto the mesh."""
    h, w = shape
    pts, fid = trimesh.sample.sample_surface(mesh, samples, seed=0)
    q = np.clip(to_pixels(uv_coords(pts, FRONT), params).astype(int), [0, 0], [w - 1, h - 1])
    order = np.argsort(pts[:, 2])
    idx = np.full((h, w), -1)
    idx[q[order, 1], q[order, 0]] = order  # nearest sample wins
    light = np.array([-0.3, 0.4, 1.0]) / np.linalg.norm([-0.3, 0.4, 1.0])
    ok = idx >= 0
    shade = np.zeros((h, w))
    shade[ok] = np.clip(mesh.face_normals[fid][idx[ok]] @ light, 0, 1) * 0.8 + 0.15
    img = (np.stack([grey_closing(shade, size=3)] * 3, -1) * 255).astype(np.uint8)
    img[~grey_closing(ok, size=3)] = 110
    return img, idx, pts


def fit_face(head, params, photo_lm, shape, passes=2):
    """Pull the sculpted features onto the photo's (the texture then lands on them), and open
    the eyes, which image-to-3D sculpts as closed slits under the photo's open ones."""
    sx, sy, ox, oy = params
    v = head.vertices
    allp = photo_lm[:468, :2]
    c = allp.mean(0)
    for it in range(passes + 1):
        img, idx, pts = clay(head, params, shape)
        g = face_landmarks(img)
        if g is None:
            print("face fit: no face found on the sculpt, left as is")
            return head
        err = np.linalg.norm(g[ROBUST, :2] - photo_lm[ROBUST, :2], axis=1)
        print(f"face fit pass {it}: landmark offset median {np.median(err):.1f} px, max {err.max():.1f}")
        if it == passes:
            break
        # surface point under each sculpt landmark
        h, w = shape
        G = []
        for x, y in np.clip(np.round(g[ROBUST, :2]).astype(int), [0, 0], [w - 1, h - 1]):
            win = idx[max(0, y - 3):y + 4, max(0, x - 3):x + 4]
            win = win[win >= 0]
            G.append(pts[win].mean(0) if len(win) else [np.nan] * 3)
        G = np.array(G)
        ok = np.isfinite(G[:, 0])
        d = np.zeros((ok.sum(), 3))
        d[:, 0] = (photo_lm[ROBUST, 0] - g[ROBUST, 0])[ok] / sx
        d[:, 1] = -(photo_lm[ROBUST, 1] - g[ROBUST, 1])[ok] / sy
        # zero displacement away from the face and on the back of the head
        vp = to_pixels(uv_coords(v, FRONT), params)
        hull = np.vstack([allp, g[:468, :2]])
        far = (Delaunay(c + (hull - c) * 1.35).find_simplex(vp) < 0) | (head.vertex_normals[:, 2] < -0.2)
        anchors = v[np.random.default_rng(0).choice(np.flatnonzero(far), 1500, replace=False)]
        rbf = RBFInterpolator(np.vstack([G[ok], anchors]), np.vstack([d, np.zeros((len(anchors), 3))]),
                              kernel="thin_plate_spline", smoothing=1e-2)
        disp = rbf(v)
        disp[far] = 0
        v = v + disp
        head = trimesh.Trimesh(v, head.faces, process=False)

    # image-to-3D leaves thin spikes hanging from the nostrils: relax the strip between the
    # alar bases (98/327) and the top of the upper lip (0) into a smooth membrane, its edges
    # (nose tip above, lip below, cheeks) held fixed
    vp = to_pixels(uv_coords(v, FRONT), params)
    alar = photo_lm[[98, 327], :2]
    aw = abs(alar[1, 0] - alar[0, 0])
    top = alar[:, 1].mean() - 0.05 * aw
    bottom = photo_lm[0, 1] - 0.1 * (photo_lm[0, 1] - photo_lm[2, 1])
    region = (vp[:, 0] > alar[:, 0].min() - 0.1 * aw) & (vp[:, 0] < alar[:, 0].max() + 0.1 * aw) \
        & (vp[:, 1] > top) & (vp[:, 1] < bottom) & (v[:, 2] > np.median(v[:, 2]))
    edges = head.edges_unique
    nbr = scipy.sparse.coo_matrix((np.ones(2 * len(edges)), (edges.ravel("F"), edges[:, ::-1].ravel("F"))),
                                  shape=(len(v), len(v))).tocsr()
    deg = np.asarray(nbr.sum(1)).ravel()
    for _ in range(150):
        v[region] = 0.5 * v[region] + 0.5 * (nbr @ v)[region] / deg[region, None]
    head = trimesh.Trimesh(v, head.faces, process=False)

    # open the eyes: finer triangles around them, then an eyeball inside each eyelid contour,
    # centred on the iris, its front a little behind the lid margin
    for _ in range(2):
        vp = to_pixels(uv_coords(head.vertices, FRONT), params)
        fc = vp[head.faces].mean(1)
        sel = np.zeros(len(head.faces), bool)
        for loop in (R_EYE, L_EYE):
            lo, hi = photo_lm[loop, :2].min(0), photo_lm[loop, :2].max(0)
            pad = (hi - lo) * 0.35
            sel |= np.all((fc > lo - pad) & (fc < hi + pad), 1) & (head.face_normals[:, 2] > 0)
        nv, nf = trimesh.remesh.subdivide(head.vertices, head.faces, face_index=np.flatnonzero(sel))
        head = trimesh.Trimesh(nv, nf, process=False)
    v = head.vertices.copy()
    vp = to_pixels(uv_coords(v, FRONT), params)
    front = head.vertex_normals[:, 2] > 0.2
    irises = photo_lm[[468, 473], :2]
    for loop in (R_EYE, L_EYE):
        cont = photo_lm[loop, :2]
        iris = irises[np.argmin(np.linalg.norm(irises - cont.mean(0), axis=1))]
        width = np.linalg.norm(cont[0] - cont[8]) / sx
        inside = MplPath(cont).contains_points(vp) & front
        ring = MplPath(cont.mean(0) + (cont - cont.mean(0)) * 1.25).contains_points(vp) & ~inside & front
        r = 0.55 * width
        z_front = np.median(v[ring, 2]) - 0.035 * width
        dx = v[inside, 0] - (iris[0] - ox) / sx
        dy = v[inside, 1] - (oy - iris[1]) / sy
        v[inside, 2] = z_front - r + np.sqrt(np.clip(r * r - dx * dx - dy * dy, 0, None))
    print("face fit: eyes opened")
    return trimesh.Trimesh(v, head.faces, process=False)


# ------------------------------------------------------------------ fitting and projection
def fit(xy, mask):
    """Find pixel = (u * sx + ox, -v * sy + oy) that best overlays the projected points on the mask."""
    ys, xs = np.nonzero(mask)
    h, w = mask.shape
    k = max(1, w // 256)  # score on a downsampled mask
    small = mask[::k, ::k]
    sub = xy[:: max(1, len(xy) // 150_000)]

    def iou(p):
        sx, sy, ox, oy = p
        px = ((sub[:, 0] * sx + ox) / k).astype(int)
        py = ((-sub[:, 1] * sy + oy) / k).astype(int)
        ok = (px >= 0) & (px < small.shape[1]) & (py >= 0) & (py < small.shape[0])
        sil = np.zeros_like(small)
        sil[py[ok], px[ok]] = True
        sil = binary_closing(sil, iterations=2)
        return (sil & small).sum() / (sil | small).sum()

    # start: heights match, bottoms on the mask's lowest row, bounding boxes centred
    s0 = (ys.max() - ys.min()) / np.ptp(sub[:, 1])
    best = [s0, s0, (xs.min() + xs.max()) / 2 - (sub[:, 0].max() + sub[:, 0].min()) / 2 * s0,
            ys.max() + sub[:, 1].min() * s0]
    score = iou(best)
    # coordinate descent, coarse to fine: u/v scale, then u/v offset
    for step_s, step_o in ((0.06, 0.04), (0.03, 0.016), (0.012, 0.006), (0.005, 0.002)):
        improved = True
        while improved:
            improved = False
            for i, step in ((0, step_s * s0), (1, step_s * s0), (2, step_o * w), (3, step_o * h)):
                for sign in (-1, 1):
                    cand = list(best)
                    cand[i] += sign * step
                    sc = iou(cand)
                    if sc > score:
                        best, score, improved = cand, sc, True
    return score, best


# camera axes: (image u = (sign, vertex column), depth toward the camera = (sign, column))
FRONT = ((1, 0), (1, 2))
BACK = ((-1, 0), (-1, 2))


def sides(su):
    """Both side cameras for a profile photo with u = su * z (they share its pixels)."""
    return [((su, 2), (-su, 0)), ((su, 2), (su, 0))]


def uv_coords(verts, axes):
    (su, cu), _ = axes
    return np.column_stack([su * verts[:, cu], verts[:, 1]])


def to_pixels(uv, params):
    sx, sy, ox, oy = params
    return np.column_stack([uv[:, 0] * sx + ox, -uv[:, 1] * sy + oy])


def rasterize(uv, faces, size):
    """Texels covered by each UV triangle: (texel x, texel y, face id, barycentrics)."""
    tri = uv[faces] * size
    tri[..., 1] = size - tri[..., 1]  # image rows grow downward
    lo = np.floor(tri.min(1)).astype(int)
    ext = np.ceil(tri.max(1)).astype(int) - lo + 1
    span = ext.max(1)
    out = []
    for b in (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096):
        sel = np.flatnonzero((span <= b) & (span > b // 2) if b > 2 else span <= b)
        if not len(sel):
            continue
        gy, gx = np.mgrid[0:b, 0:b]
        gx, gy = gx.ravel(), gy.ravel()
        for chunk in np.array_split(sel, max(1, len(sel) * b * b // 2_000_000 + 1)):
            px = lo[chunk, 0, None] + gx  # (T, b*b)
            py = lo[chunk, 1, None] + gy
            cx, cy = px + 0.5, py + 0.5
            a, bb, c = (tri[chunk, i] for i in range(3))
            d = (bb[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - bb[:, 0]) * (a[:, 1] - c[:, 1])
            d = np.where(np.abs(d) < 1e-12, 1e-12, d)[:, None]
            l0 = ((bb[:, 1, None] - c[:, 1, None]) * (cx - c[:, 0, None])
                  + (c[:, 0, None] - bb[:, 0, None]) * (cy - c[:, 1, None])) / d
            l1 = ((c[:, 1, None] - a[:, 1, None]) * (cx - c[:, 0, None])
                  + (a[:, 0, None] - c[:, 0, None]) * (cy - c[:, 1, None])) / d
            l2 = 1 - l0 - l1
            ok = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4) & (px >= 0) & (px < size) \
                & (py >= 0) & (py < size)
            t, k = np.nonzero(ok)
            out.append((px[t, k], py[t, k], chunk[t], np.column_stack([l0[t, k], l1[t, k], l2[t, k]])))
    px, py, fid, bary = (np.concatenate(x) for x in zip(*out))
    # a texel on a shared edge belongs to one face only
    _, first = np.unique(py * size + px, return_index=True)
    return px[first], py[first], fid[first], bary[first]


def zbuffer(mesh, pix, depth, res, samples=3_000_000):
    """Nearest depth per cell from a dense surface sample, in image pixels / k."""
    pts, fid = trimesh.sample.sample_surface(mesh, samples, seed=0)
    bary = trimesh.triangles.points_to_barycentric(mesh.triangles[fid], pts)
    p = np.einsum("ij,ijk->ik", bary, pix[mesh.faces[fid]])
    d = np.einsum("ij,ij->i", bary, depth[mesh.faces[fid]])
    q = np.clip(p.astype(int), 0, res - 1)
    z = np.full((res, res), -np.inf)
    np.maximum.at(z, (q[:, 1], q[:, 0]), d)
    return z


def bake(mesh, views, name, size, fill="nearest", power=4):
    """UV-unwrap the mesh and bake one texture that blends every photo per texel.

    views: dicts(name, img=RGB array, mask, params, axes=[camera axes], weight, cutoff, erode). Each
    texel takes sum(w * colour) / sum(w), w = weight * max(cos(angle) - cutoff, 0)^power, over the cameras that
    see it (z-buffer) inside the photo's mask; no seams between photos. Texels no camera sees get
    the nearest seen texel's colour ("nearest": cloak insides, armpits) or the colour from the
    photo they face most directly, occlusion ignored ("facing": eye sockets, nostrils).
    """
    import xatlas
    from scipy.ndimage import map_coordinates

    vmap, faces, uv = xatlas.parametrize(mesh.vertices, mesh.faces)
    px, py, fid, bary = rasterize(uv, faces, size)
    tri_v = mesh.vertices[vmap][faces[fid]]
    pos = np.einsum("ij,ijk->ik", bary, tri_v)
    nrm = np.einsum("ij,ijk->ik", bary, mesh.vertex_normals[vmap][faces[fid]])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    tol = 0.02 * np.ptp(mesh.vertices[:, 1])

    acc, wsum = np.zeros((len(px), 3)), np.zeros(len(px))
    best_w, best_c = np.full(len(px), -np.inf), np.zeros((len(px), 3))
    for v in views:
        img = v["img"].astype(np.float32)
        h, w = v["mask"].shape
        # skip the cut-out's edge, where the backdrop halo lives (wider on upscaled crops)
        inner = binary_erosion(v["mask"], iterations=v.get("erode", 2))
        res = 512
        k = max(h, w) / res
        for axes in v["axes"]:
            (sd, cd) = axes[1]
            vpix = to_pixels(uv_coords(mesh.vertices, axes), v["params"])
            z = zbuffer(mesh, vpix / k, sd * mesh.vertices[:, cd], res)
            p = to_pixels(uv_coords(pos, axes), v["params"])
            q = np.clip((p / k).astype(int), 0, res - 1)
            seen = sd * pos[:, cd] >= z[q[:, 1], q[:, 0]] - tol
            pi = np.clip(p.astype(int), [0, 0], [w - 1, h - 1])
            inside = (p[:, 0] >= 0) & (p[:, 0] < w) & (p[:, 1] >= 0) & (p[:, 1] < h) \
                & inner[pi[:, 1], pi[:, 0]]
            cosang = np.clip(sd * nrm[:, cd], 0, None)
            # grazing views stretch the photo across the surface: drop them below `cutoff`
            facing = np.clip(cosang - v.get("cutoff", 0.0), 0, None) * v.get("weight", 1.0) ** (1 / power)
            col = np.stack([map_coordinates(img[..., c], [p[:, 1] - 0.5, p[:, 0] - 0.5], order=1,
                                            mode="nearest") for c in range(3)], 1)
            wt = np.where(seen & inside, facing ** power, 0.0)
            acc += wt[:, None] * col
            wsum += wt
            fb = np.where(inside, cosang * v.get("weight", 1.0), -np.inf)
            better = fb > best_w
            best_w[better], best_c[better] = fb[better], col[better]
    ok = wsum > 1e-6
    colour = np.zeros((len(px), 3))
    colour[ok] = acc[ok] / wsum[ok, None]
    if fill == "facing":
        colour[~ok] = best_c[~ok]
    else:
        colour[~ok] = colour[ok][cKDTree(pos[ok]).query(pos[~ok])[1]]
    print(f"{name}: {len(faces)} faces, {len(px)} texels, unseen {np.mean(~ok):.0%}")

    tex = np.zeros((size, size, 3), np.float32)
    filled = np.zeros((size, size), bool)
    tex[py, px], filled[py, px] = colour, True
    _, (iy, ix) = distance_transform_edt(~filled, return_indices=True)  # gutter padding
    tex = np.clip(tex[iy, ix], 0, 255).astype(np.uint8)
    material = trimesh.visual.material.PBRMaterial(
        name=name, baseColorTexture=Image.fromarray(tex), metallicFactor=0.0, roughnessFactor=0.85)
    # smooth normals from the unsplit mesh, so shading stays continuous across UV seams
    return trimesh.Trimesh(mesh.vertices[vmap], faces, vertex_normals=mesh.vertex_normals[vmap],
                           process=False,
                           visual=trimesh.visual.TextureVisuals(uv=uv, material=material))


# ------------------------------------------------------------------ main
def main(body_path, out, head_path=None):
    body = load_mesh(body_path, BODY_FACES)
    print("body faces", len(body.faces))
    photos = {k: cutout(Image.open(os.path.join(HERE, f"{k}.png"))) for k in ("front", "back")}
    params = {}
    for k, axes in (("front", FRONT), ("back", BACK)):
        iou, params[k] = fit(uv_coords(body.vertices, axes), photos[k][1])
        print(f"body {k}: silhouette IoU {iou:.3f}")

    meshes = {}
    if head_path:
        boxes = make_head_crops()
        head = load_mesh(head_path, HEAD_FACES)
        crops = {k: cutout(Image.open(os.path.join(HERE, f"{k}_head.png"))) for k in boxes}
        neck = neck_height(head)
        above = head.vertices[:, 1] > neck
        # fit the crops in the head's own frame; side/back only above their collar line
        hparams, haxes = {}, {"front": [FRONT], "back": [BACK]}
        for k, cands in (("front", [FRONT]), ("back", [BACK]), ("side", [sides(1)[0], sides(-1)[0]])):
            m = crops[k][1].copy()
            pts = head.vertices
            if k != "front":
                m[collar_row(m):] = False
                pts = pts[above]
            fits = [fit(uv_coords(pts, a), m) for a in cands]
            j = int(np.argmax([f[0] for f in fits]))
            hparams[k] = fits[j][1]
            if k == "side":  # which way the profile faces decides the sign of u
                haxes["side"] = sides(cands[j][0][0])
            print(f"head {k}: silhouette IoU {fits[j][0]:.3f}")

        photo_lm = face_landmarks(crops["front"][0])
        if photo_lm is not None:
            head = fit_face(head, hparams["front"], photo_lm, crops["front"][1].shape)
            # the neck from the photo: a little below the chin (152), a third of the way to the
            # nose tip's distance; the profile search lands in the collar on a broad bust
            _, fsy, _, foy = hparams["front"]
            chin, tip = (foy - photo_lm[[152, 1], 1]) / fsy
            neck = chin - 0.3 * (tip - chin)

        # keep the head down to just below the neck (a clean planar cut), so it tucks into the
        # body's collar instead of bringing its own badly textured piece of cloak
        cut = neck - 0.015 * np.ptp(head.vertices[:, 1])
        head = head.slice_plane([0, cut, 0], [0, 1, 0])
        above = head.vertices[:, 1] > neck
        textured = bake(head, [
            dict(name="front", img=crops["front"][0], mask=crops["front"][1], params=hparams["front"],
                 axes=haxes["front"], cutoff=0.25, erode=6),
            # one profile photo for both sides (mirrored on the far side). Its head is turned a
            # little differently from the front photo, so around the eyes it lines up worse; with
            # the grazing cutoff the front photo still wins there, the profile on the temples/ears.
            # Its higher cutoff keeps it off the cheeks, where it has scars the front photo hasn't
            dict(name="side", img=crops["side"][0], mask=crops["side"][1], params=hparams["side"],
                 axes=haxes["side"], weight=0.6, cutoff=0.45, erode=6),
            dict(name="back", img=crops["back"][0], mask=crops["back"][1], params=hparams["back"],
                 axes=haxes["back"], cutoff=0.25, erode=6),
        ], "Head", HEAD_TEX, fill="facing", power=2)

        # head frame -> front.png pixels (the crop is 4x) -> body frame; depth scaled alike
        hs = hparams["front"]
        bx0, by0 = boxes["front"][:2]
        sx, sy, ox, oy = params["front"]
        kx, ky = hs[0] / 4 / sx, hs[1] / 4 / sy

        def to_body(v):
            v = v.copy()
            v[:, 0] = (v[:, 0] * hs[0] / 4 + hs[2] / 4 + bx0 - ox) / sx
            v[:, 1] = (v[:, 1] * hs[1] / 4 - hs[3] / 4 - by0 + oy) / sy
            v[:, 2] *= (kx + ky) / 2
            return v

        hv = to_body(head.vertices)
        neck_y = to_body(np.array([[0.0, neck, 0.0]]))[0, 1]
        cx, half = hv[above, 0].mean(), np.ptp(hv[above, 0]) / 2
        hb = (body.vertices[:, 1] > neck_y) & (np.abs(body.vertices[:, 0] - cx) < half)
        dz = np.median(body.vertices[hb, 2]) - np.median(hv[above, 2])
        textured.vertices = to_body(textured.vertices) + [0, 0, dz]
        meshes["Head"] = textured

        # drop the body's own head
        body.update_faces(~hb[body.faces].all(1))
        body.remove_unreferenced_vertices()

    meshes["Body"] = bake(body, [
        dict(name=k, img=photos[k][0], mask=photos[k][1], params=params[k], axes=[a])
        for k, a in (("front", FRONT), ("back", BACK))], "Body", BODY_TEX)

    # centre on the head (sword and shield make the bounding box lopsided), feet at 0, 1.80 m
    allv = np.concatenate([m.vertices for m in meshes.values()])
    top = allv[:, 1] > allv[:, 1].min() + 0.875 * np.ptp(allv[:, 1])
    shift = np.array([allv[top, 0].mean(), allv[:, 1].min(), allv[top, 2].mean()])
    scale = HEIGHT / np.ptp(allv[:, 1])
    scene = trimesh.Scene()
    for name, m in meshes.items():
        normals = m.vertex_normals.copy()  # uniform scale + shift: normals unchanged
        m.vertices = (m.vertices - shift) * scale
        m.vertex_normals = normals
        scene.add_geometry(m, node_name=name, geom_name=name)
    # without NORMAL the glTF spec has viewers fall back to flat shading
    scene.export(out, include_normals=True)
    print("->", out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    args = sys.argv[1:]
    head = None
    if "--head" in args:
        i = args.index("--head")
        head = args[i + 1]
        del args[i:i + 2]
    main(args[0], args[1] if len(args) > 1 else os.path.join(HERE, "hunyuan2_knight.glb"), head)
