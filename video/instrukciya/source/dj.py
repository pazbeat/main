import json, sys, os, numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
REC = sys.argv[1]; PC = REC.endswith('pc')
n = len(os.listdir(f'{REC}/f'))
def load(i):
    im = Image.open(f'{REC}/f/{i:06d}.jpg').convert('L')
    return (np.asarray(im.resize((160, 90) if PC else (90, 160)), dtype=np.float32), np.asarray(im.resize((96, 54) if PC else (54, 96)), dtype=np.float32))
with ProcessPoolExecutor(4) as ex: A = list(ex.map(load, range(n), chunksize=64))
diffs = [0.0] + [float(np.abs(A[i][0] - A[i - 1][0]).mean()) for i in range(1, n)]
jumps = [[i, round(float(np.abs(A[i][1] - A[i - 1][1]).mean()), 1)] for i in range(1, n) if np.abs(A[i][1] - A[i - 1][1]).mean() > 25]
json.dump(diffs, open(f'{REC}/diffs.json', 'w')); json.dump(jumps, open(f'{REC}/jumps.json', 'w'))
print(REC, n, 'jumps', jumps)
