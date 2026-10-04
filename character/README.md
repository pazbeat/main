# Knight character — 3D model

Procedural 3D model of the medieval knight from `reference/` (front / back / side sheet).

| File | What |
|---|---|
| `knight.glb` | Final model, glTF binary with embedded textures (Y-up, metres, ~1.80 m tall) |
| `knight.blend` | Blender 4.2 scene with live modifiers (subsurf/solidify) |
| `build_knight.py` | Builds everything from code (`python3 build_knight.py --render`) |
| `make_textures.py` | Generates textures in `textures/` (leather, quilted gambeson, chainmail, steel, shield with eagle) |
| `renders/` | Preview renders: front, back, side, three-quarter, head (`ai_*.png`: the AI model) |
| `ai/knight_ai.glb` | AI image-to-3D model (TRELLIS.2), cleaned up: 1.80 m, 150k tris, 2048² JPEG PBR textures |
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
scales to 1.80 m with the soles on the origin and front along +Z, decimates to 150k triangles,
downsizes textures to 2048², and repaints the crown and back of the head (unseen in `front.png`,
so the generator left them grey and half-metallic) with the photo's dark-brown hair. It also writes
`viewer/knight_ai.gltf.json` for the turntable.

    pip install gradio_client bpy==4.2.0 pillow numpy
    HF_TOKEN=hf_... python3 ai/generate.py && python3 ai/finalize.py
