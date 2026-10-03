"""Realistic image-to-3D of the knight via Hugging Face Spaces.

Needs env var HF_TOKEN (free Hugging Face Read token).
  pip install gradio_client && python3 generate.py
Writes trellis2_knight.glb (TRELLIS.2, textured) and, if quota allows, hunyuan_knight.glb.
"""
import os
import shutil
import sys

from gradio_client import Client, handle_file

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("HF_TOKEN")
if not TOKEN:
    sys.exit("HF_TOKEN is not set")
front = os.path.join(HERE, "front.png")


def trellis2(res="1536"):
    c = Client("microsoft/TRELLIS.2", hf_token=TOKEN, verbose=False)
    try:
        c.predict(api_name="/start_session")
    except Exception as e:  # older builds have no explicit session start
        print("start_session:", e)
    pre = c.predict(handle_file(front), api_name="/preprocess_image")
    path = pre["path"] if isinstance(pre, dict) else pre
    c.predict(handle_file(path), 42, res, api_name="/image_to_3d")
    glb = c.predict(400000, 4096, api_name="/extract_glb")
    glb = glb[0] if isinstance(glb, (list, tuple)) else glb
    out = os.path.join(HERE, "trellis2_knight.glb")
    shutil.copy(glb, out)
    print("TRELLIS.2 ->", out)


def hunyuan():
    c = Client("tencent/Hunyuan3D-2.1", hf_token=TOKEN, verbose=False)
    r = c.predict(handle_file(front), None, None, None, None, 30, 5.0, 1234, 384, True, 8000, False,
                  api_name="/generation_all")
    out = os.path.join(HERE, "hunyuan_knight.glb")
    shutil.copy(r[1], out)
    print("Hunyuan3D-2.1 ->", out)


for name, fn in (("TRELLIS.2", trellis2), ("Hunyuan3D-2.1", hunyuan)):
    try:
        fn()
    except Exception as e:
        print(f"{name} failed: {e}")
