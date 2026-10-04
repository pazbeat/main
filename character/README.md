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
| `ai/hunyuan2_knight.glb` | AI model: Hunyuan3D-2 body + separate high-detail head, photo-baked textures (Y-up, metres, 1.80 m, 324k tris, 2 × 2048² textures) |
| `ai/hunyuan2_shape.glb`, `ai/hunyuan2_head_shape.glb` | Raw untextured shapes from the Space: full figure from `front.png`, head from `front_head.png` |
| `ai/{front,side,back}_head.png` | Head crops of the reference photos, upscaled 4× with Real-ESRGAN |
| `ai/generate.py` | Image-to-3D via Hugging Face ZeroGPU Spaces: TRELLIS.2 → Hunyuan3D-2.1 → TRELLIS → Hunyuan3D-2, first success wins (`python3 ai/generate.py hunyuan2` runs one backend) |
| `ai/texture_shape.py` | UV-unwraps the shapes and bakes textures that blend the photos per texel (no seams); swaps the detailed head in at the neck |
| `ai/render_preview.py` | Preview renders in `ai/renders/`, same rig as `build_knight.py` (AgX, since the photo textures carry their own lighting) |

Why a separate head: in the full-body shape the face is ~5% of the height, so it comes out as a
smooth blob with a ~100 px texture. Image-to-3D on the upscaled head crop gives real brows, eye
sockets, nose and ears.

TRELLIS.2 and Hunyuan3D-2.1 need more GPU time than a free HF account gets (Hunyuan3D-2.1 needs HF PRO);
on the free tier the two 40 s Hunyuan3D-2 shape calls fit. The viewer (`viewer/index.html`, serve
`character/` over HTTP) switches between the procedural and the AI model. For the AI model it adds
a soft light from the camera and turns off shadow-mapping on the head: the photo texture already has
the face's own shading, and doubling it turns the eye sockets into a black band.

Limits of the AI model: the back comes from `back.png`, whose pose differs slightly from the front
image; surfaces no photo sees (under the arms, inside the cloak) get the nearest seen colour; the one
profile photo is mirrored onto the far side of the head, and a faint pale strip remains at the
temples where hair meets skin at a grazing angle.
