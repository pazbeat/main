"""Realistic image-to-3D of the knight via Hugging Face Spaces (ZeroGPU).

  pip install gradio_client && python3 generate.py [backend ...]   # then: python3 finalize.py

Backends, best first; the first one that succeeds wins:
  trellis2   microsoft/TRELLIS.2        -> trellis2_knight.glb  (needs ~240 s GPU: valid HF_TOKEN)
  hunyuan21  tencent/Hunyuan3D-2.1      -> hunyuan21_knight.glb (needs 270 s GPU: HF PRO)
  trellis    trellis-community/TRELLIS  -> trellis_knight.glb   (120 s GPU: fits anonymous quota)
  hunyuan2   tencent/Hunyuan3D-2        -> hunyuan2_knight.glb  (90 s GPU: fits anonymous quota)

HF_TOKEN (Hugging Face Read token) is optional; without a valid one the Spaces run anonymously
with a small daily GPU quota, so only `trellis` and `hunyuan2` can complete.
"""
import json
import os
import shutil
import sys
import urllib.request

from gradio_client import Client, handle_file

HERE = os.path.dirname(os.path.abspath(__file__))
front = os.path.join(HERE, "front.png")


def valid_token():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN is not set, running anonymously")
        return None
    req = urllib.request.Request("https://huggingface.co/api/whoami-v2",
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("HF user:", json.load(r).get("name"))
        return token
    except Exception as e:
        print(f"HF_TOKEN rejected ({e}), running anonymously")
        return None


TOKEN = valid_token()


def save(src, name):
    out = os.path.join(HERE, name)
    shutil.copy(src, out)
    return out


def trellis2(res="1536"):
    c = Client("microsoft/TRELLIS.2", token=TOKEN, verbose=False)
    try:
        c.predict(api_name="/start_session")
    except Exception as e:  # older builds have no explicit session start
        print("start_session:", e)
    pre = c.predict(handle_file(front), api_name="/preprocess_image")
    path = pre["path"] if isinstance(pre, dict) else pre
    c.predict(handle_file(path), 42, res, api_name="/image_to_3d")
    glb = c.predict(400000, 4096, api_name="/extract_glb")
    glb = glb[0] if isinstance(glb, (list, tuple)) else glb
    return save(glb, "trellis2_knight.glb")


def hunyuan21():
    c = Client("tencent/Hunyuan3D-2.1", token=TOKEN, verbose=False)
    r = c.predict(handle_file(front), None, None, None, None, 30, 5.0, 1234, 384, True, 8000, False,
                  api_name="/generation_all")
    return save(r[1], "hunyuan21_knight.glb")


def trellis():
    c = Client("trellis-community/TRELLIS", token=TOKEN, verbose=False)
    c.predict(api_name="/start_session")
    pre = c.predict(handle_file(front), api_name="/preprocess_image")
    path = pre["path"] if isinstance(pre, dict) else pre
    # seed, ss cfg/steps, slat cfg/steps, multi-image algo (unused), mesh simplify, texture size
    r = c.predict(handle_file(path), [], 42, 7.5, 12, 3.0, 12, "stochastic", 0.9, 2048,
                  api_name="/generate_and_extract_glb")
    return save(r[1], "trellis_knight.glb")


def hunyuan2():
    c = Client("tencent/Hunyuan3D-2", token=TOKEN, verbose=False)
    r = c.predict(None, handle_file(front), None, None, None, None, 30, 5.0, 1234, 256, True, 8000,
                  False, api_name="/generation_all")
    return save(r[1], "hunyuan2_knight.glb")


BACKENDS = {"trellis2": trellis2, "hunyuan21": hunyuan21, "trellis": trellis, "hunyuan2": hunyuan2}

names = sys.argv[1:] or list(BACKENDS)
for name in names:
    try:
        print(f"{name}: {BACKENDS[name]()}")
        break
    except Exception as e:
        print(f"{name} failed: {e}")
else:
    sys.exit("no backend produced a model")
