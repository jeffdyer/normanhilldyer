"""Generate a seamlessly tiling foliage texture.

Echoes the canopy in the photograph: overlapping leaf shapes in greens
sampled from the image itself. Pure stdlib - no imaging libraries required.
"""
import math, random, struct, zlib, sys

W, H = 900, 900
SEED = 20100927  # the date stamped on the photograph

buf = bytearray(W * H * 4)

# Greens measured off the photograph: canopy, lit midtone, backlit shade,
# plus a pale highlight for leaves catching the light.
PALETTE = [
    ((81, 126, 97),  0.26),   # #517e61 canopy
    ((86, 138, 99),  0.30),   # #568a63 lit green
    ((118, 171, 146), 0.24),  # #76ab92 backlit shade
    ((60, 96, 74),   0.12),   # deeper shadow
    ((198, 214, 196), 0.08),  # pale highlight
]


def pick_colour(rng):
    r = rng.random()
    acc = 0.0
    for rgb, wt in PALETTE:
        acc += wt
        if r <= acc:
            return rgb
    return PALETTE[0][0]


def blend(x, y, rgb, a):
    """Source-over, wrapping in both axes so the tile is seamless."""
    if a <= 0:
        return
    i = ((y % H) * W + (x % W)) * 4
    da = buf[i + 3] / 255.0
    sa = min(a, 1.0)
    out_a = sa + da * (1 - sa)
    if out_a <= 0:
        return
    for off in range(3):
        dc = buf[i + off] / 255.0
        sc = rgb[off] / 255.0
        buf[i + off] = int(round((sc * sa + dc * da * (1 - sa)) / out_a * 255))
    buf[i + 3] = int(round(out_a * 255))


def leaf(cx, cy, length, width, angle, rgb, alpha):
    """A pointed oval with a faint midrib - widest at the middle, tapering
    to a point at each end, which is what reads as 'leaf' at small sizes."""
    ca, sa_ = math.cos(angle), math.sin(angle)
    reach = int(length / 2 + width + 2)
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            u = dx * ca + dy * sa_          # across the leaf
            v = -dx * sa_ + dy * ca         # along the leaf axis
            t = (v + length / 2) / length
            if t < 0.0 or t > 1.0:
                continue
            half = (width / 2) * (math.sin(math.pi * t) ** 0.62)
            if half <= 0:
                continue
            cov = max(0.0, min(1.0, half - abs(u) + 0.5))
            if cov <= 0:
                continue
            a = alpha * cov
            # Midrib: a slightly deeper line down the centre.
            if abs(u) < 0.9 and half > 1.6:
                a *= 1.3
            blend(int(cx) + dx, int(cy) + dy, rgb, a)


rng = random.Random(SEED)

# Foliage is clumpy - leaves gather on branches rather than spreading evenly.
for _ in range(62):
    ccx, ccy = rng.uniform(0, W), rng.uniform(0, H)
    spread = rng.uniform(28, 68)
    drift = rng.uniform(0, math.tau)   # a loose prevailing direction per clump
    for _ in range(rng.randint(7, 16)):
        length = rng.uniform(11, 30)
        leaf(ccx + rng.gauss(0, spread), ccy + rng.gauss(0, spread * 0.8),
             length, length * rng.uniform(0.34, 0.52),
             drift + rng.gauss(0, 0.7), pick_colour(rng),
             rng.uniform(0.022, 0.055))

# A sparse scatter between the clumps so no area reads as empty.
for _ in range(310):
    length = rng.uniform(8, 22)
    leaf(rng.uniform(0, W), rng.uniform(0, H),
         length, length * rng.uniform(0.32, 0.5),
         rng.uniform(0, math.tau), pick_colour(rng),
         rng.uniform(0.016, 0.038))

# A few large, very faint leaves for depth.
for _ in range(34):
    length = rng.uniform(34, 52)
    leaf(rng.uniform(0, W), rng.uniform(0, H),
         length, length * rng.uniform(0.36, 0.5),
         rng.uniform(0, math.tau), pick_colour(rng),
         rng.uniform(0.009, 0.021))

raw = bytearray()
for y in range(H):
    raw.append(0)
    raw += buf[y * W * 4:(y + 1) * W * 4]


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
       + chunk(b"IEND", b""))

out = sys.argv[1] if len(sys.argv) > 1 else "leaves.png"
with open(out, "wb") as f:
    f.write(png)
print(f"wrote {out}  {W}x{H}  {len(png):,} bytes")
