# Knight character — 3D model

Procedural 3D model of the medieval knight from `reference/` (front / back / side sheet).

| File | What |
|---|---|
| `knight.glb` | Final model, glTF binary with embedded textures (Y-up, metres, ~1.80 m tall) |
| `knight.blend` | Blender 4.2 scene with live modifiers (subsurf/solidify) |
| `build_knight.py` | Builds everything from code (`python3 build_knight.py --render`) |
| `make_textures.py` | Generates textures in `textures/` (leather, quilted gambeson, chainmail, steel, shield with eagle) |
| `renders/` | Preview renders: front, back, side, three-quarter, head |

Contents: head with beard/hair, quilted gambeson with skirt, leather cuirass with three steel chest
lames and chest harness, 4-lame pauldrons, chainmail sleeves, leather bracers and gloves, double belt
with buckles, pouches and tassets, trousers, tall boots with three buckled straps, green cloak with
brown lining, brown mantle with ring brooch, leather backpack with buckled straps, longsword in the
right hand, scabbard on the left hip, wooden heater shield with steel rim and black eagle.

Rebuild: `pip install bpy==4.2.0 pillow && python3 make_textures.py && python3 build_knight.py --render`

## AI image-to-3D (`ai/`)

| File | What |
|---|---|
| `ai/hunyuan2_knight.glb` | AI model: Hunyuan3D-2 shape + photo-projected texture (Y-up, metres, 1.80 m, 250k tris, 3072×1024 atlas) |
| `ai/hunyuan2_shape.glb` | Raw untextured shape from the Space (input to `texture_shape.py`) |
| `ai/generate.py` | Image-to-3D via Hugging Face ZeroGPU Spaces: TRELLIS.2 → Hunyuan3D-2.1 → TRELLIS → Hunyuan3D-2, first success wins (`python3 ai/generate.py hunyuan2` runs one backend) |
| `ai/texture_shape.py` | Textures an untextured shape by projecting `front.png` / `back.png` (and `side.png` on the head) with occlusion checks |
| `ai/render_preview.py` | Preview renders in `ai/renders/`, same rig as `build_knight.py` |

TRELLIS.2 and Hunyuan3D-2.1 need more GPU time than a free HF account gets (Hunyuan3D-2.1 needs HF PRO);
on the free tier only the 40 s Hunyuan3D-2 shape call fits. The viewer (`viewer/index.html`, serve
`character/` over HTTP) switches between the procedural and the AI model.

Limits of the AI model: the back is projected from `back.png`, whose pose differs slightly from the
front image, and surfaces neither photo sees (under the arms, inside the cloak) get the nearest
seen colour, so expect soft patches there.
