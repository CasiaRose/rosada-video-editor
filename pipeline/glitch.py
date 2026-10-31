import numpy as np
PRI = np.array([61., 90., 128.]); COR = np.array([224., 122., 95.])
K = [1.0, 0.55, 0.25]
def apply(clean, prev, j, seed, coral):
    """brand-tinted glitch on the incoming side of a cut: frame j (0..2) after the cut."""
    k = K[j]; rng = np.random.default_rng(seed * 10 + j); H, W, _ = clean.shape
    out = clean.astype(np.float32).copy()
    s = int(round(6 * k)); 
    if s: out[..., 0] = np.roll(out[..., 0], s, 1)          # red-only split: red/cyan fringes, never magenta/purple
    for _ in range(int(4 + 6 * k)):
        h = int(rng.integers(18, 110)); y = int(rng.integers(40, H - 40 - h)); dx = int(rng.choice([-1, 1]) * rng.integers(18, 70) * k)
        out[y:y + h] = np.roll(out[y:y + h], dx, 1)
    tints = ((PRI, 0.16), (COR, 0.32)) if coral else ((PRI, 0.30), (COR, 0.22))
    for col, a in tints:
        for _ in range(2):
            h = int(rng.integers(40, 160)); y = int(rng.integers(60, 1440 - h)); A = a * k
            g = prev[y:y + h].astype(np.float32) * 0.45 + col * 0.55
            out[y:y + h] = out[y:y + h] * (1 - A) + g * A
    return np.clip(out, 0, 255).astype(np.uint8)
