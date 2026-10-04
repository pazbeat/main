# Knight character — 3D model

Procedural 3D model of the medieval knight from `reference/` (front / back / side sheet).

| File | What |
|---|---|
| `knight.glb` | Final model, glTF binary with embedded textures (Y-up, metres, ~1.80 m tall) |
| `knight.blend` | Blender 4.2 scene with live modifiers (subsurf/solidify) |
| `build_knight.py` | Builds everything from code (`python3 build_knight.py --render`) |
| `make_textures.py` | Generates textures in `textures/` (leather, quilted gambeson, chainmail, steel, shield with eagle) |
| `renders/` | Preview renders: front, back, side, three-quarter, head (`ai_*.png`: the AI model) |
| `ai/knight_ai.glb` | AI image-to-3D model (TRELLIS.2) with the photo projected onto its front: 1.80 m, 237k tris, 4096² JPEG PBR textures |
| `viewer/` | three.js turntable, switches between the AI scan and the procedural model |

Contents: head with beard/hair, quilted gambeson with skirt, leather cuirass with three steel chest
lames and chest harness, 4-lame pauldrons, chainmail sleeves, leather bracers and gloves, double belt
with buckles, pouches and tassets, trousers, tall boots with three buckled straps, green cloak with
brown lining, brown mantle with ring brooch, leather backpack with buckled straps, longsword in the
right hand, scabbard on the left hip, wooden heater shield with steel rim and black eagle.

Rebuild: `pip install bpy==4.2.0 pillow && python3 make_textures.py && python3 build_knight.py --render`

## AI image-to-3D (`ai/`)

`ai/generate.py` turns `ai/front.png` into a textured GLB using Hugging Face ZeroGPU Spaces, trying
TRELLIS.2 → Hunyuan3D-2.1 → TRELLIS → Hunyuan3D-2 and stopping at the first one that succeeds
(`python3 ai/generate.py trellis` runs a single backend). TRELLIS.2 and Hunyuan3D-2.1 need a valid
`HF_TOKEN` (Hunyuan3D-2.1 needs HF PRO); TRELLIS and Hunyuan3D-2 fit the anonymous daily GPU quota.

Result (`python3 ai/generate.py` → TRELLIS.2 succeeded): `ai/trellis2_knight.glb` is the raw output
(395k tris, 4096² textures, 1 unit tall, 22 MB). `ai/finalize.py` turns it into `ai/knight_ai.glb`:

- scales to 1.80 m with the soles on the origin and the front along +Z;
- repaints the crown, back of the head and beard, which the generator leaves grey (and the hair
  half-metallic), with the photo's hair and beard colours;
- projects `ai/front.png` onto every texel that faces the camera and is not hidden. TRELLIS sees
  the whole knight at low resolution, so its face has blank eyes and its buckles and shield eagle are
  blurred; the projection gives them the photo's detail. A dense optical flow aligns the photo to the
  model (the head sits ~13 px off), only the photo's fine detail and hue are kept and the broad
  brightness comes from the model, so the front blends into the sides. `ai/front_mask.png` is the
  knight cut out of the photo (rembg);
- pads the texture islands and simplifies with gltfpack to 237k triangles (seam-aware; Blender's
  decimate cracked the face), with quantized geometry: 10.4 MB, 4096² JPEG textures.

It also writes `viewer/knight_ai.gltf.json` for the turntable.

    pip install gradio_client bpy==4.2.0 numpy scipy opencv-python-headless pillow   # + Node.js for gltfpack
    HF_TOKEN=hf_... python3 ai/generate.py && python3 ai/finalize.py
