"""Generate the dappled-light band overlay for normanhilldyer.org.

A horizontal band of dappled light that thins to nothing above and
below, like light falling through a canopy. The tile repeats horizontally only (seamless in x,
never wrapped in y), and CSS positions the band over the bottom third of the
page. Pure stdlib - no imaging libraries required.
"""
import math, random, struct, zlib

W, H = 1400, 560
SEED = 20261208  # Tony's birthday, for a reproducible tile
BAND_Y = H * 0.5          # band sits mid-tile; CSS places it on the page
BAND_SIGMA = H * 0.135    # how tightly foam gathers at the break

buf = bytearray(W * H * 4)


def env(y):
    """Vertical density envelope: dense at the break, thinning outward."""
    core = math.exp(-0.5 * ((y - BAND_Y) / BAND_SIGMA) ** 2)
    # A faint wash beyond the band, faded to nothing at the tile edges so the
    # overlay dissolves into the background instead of cutting off.
    edge = min(1.0, y / (H * 0.10), (H - y) / (H * 0.10))
    return max(0.0, (0.05 + 0.95 * core) * max(0.0, edge))


def blend(x, y, a):
    """Source-over white. Wraps in x (seamless tiling), clips in y."""
    if a <= 0 or y < 0 or y >= H:
        return
    x %= W
    i = (y * W + x) * 4
    da = buf[i + 3] / 255.0
    sa = min(a, 1.0)
    out_a = sa + da * (1 - sa)
    if out_a <= 0:
        return
    for off in (0, 1, 2):
        dc = buf[i + off] / 255.0
        buf[i + off] = int(round((sa + dc * da * (1 - sa)) / out_a * 255))
    buf[i + 3] = int(round(out_a * 255))


def bubble(cx, cy, rad, fill_a, rim_a):
    lo, hi = int(math.floor(-rad - 2)), int(math.ceil(rad + 2))
    for dy in range(lo, hi + 1):
        for dx in range(lo, hi + 1):
            d = math.hypot(dx + 0.5, dy + 0.5)
            if d > rad + 1.5:
                continue
            cov = max(0.0, min(1.0, rad - d + 0.5))
            if cov <= 0:
                continue
            rim = max(0.0, 1.0 - abs(d - (rad - 0.6)) / max(0.9, rad * 0.42))
            blend(int(cx) + dx, int(cy) + dy,
                  fill_a * cov * (1.0 - 0.35 * rim) + rim_a * rim * cov)


def streak(y0, length, amp, thickness, alpha):
    """A soft horizontal wisp of foam, drawn as overlapping blurred discs."""
    x = rng.uniform(0, W)
    phase = rng.uniform(0, math.tau)
    steps = int(length / 2)
    for i in range(steps):
        t = i / steps
        # Taper the ends so wisps fade in and out rather than stopping flat.
        taper = math.sin(math.pi * t) ** 0.7
        px = x + t * length
        py = y0 + math.sin(phase + t * math.pi * 1.6) * amp
        bubble(px, py, thickness * rng.uniform(0.7, 1.25),
               fill_a=alpha * taper, rim_a=alpha * taper * 0.5)


rng = random.Random(SEED)


def sample_y():
    """Rejection-sample a y weighted by the density envelope."""
    while True:
        y = rng.uniform(0, H)
        if rng.random() < env(y):
            return y


# Clusters, stretched horizontally so foam reads as parallel to the shore.
for _ in range(46):
    ccx, ccy = rng.uniform(0, W), sample_y()
    sx, sy = rng.uniform(60, 150), rng.uniform(10, 26)
    for _ in range(rng.randint(28, 55)):
        by = ccy + rng.gauss(0, sy)
        if rng.random() > env(by) * 1.15:
            continue
        rad = rng.choice([0.9, 1.2, 1.5, 1.9, 2.4, 3.0, 3.8, 4.6]) * rng.uniform(0.85, 1.2)
        bubble(ccx + rng.gauss(0, sx), by, rad,
               fill_a=rng.uniform(0.07, 0.17), rim_a=rng.uniform(0.14, 0.30))

# Fine spray, thickest through the band.
for _ in range(4200):
    y = sample_y()
    bubble(rng.uniform(0, W), y, rng.uniform(0.6, 1.5),
           fill_a=rng.uniform(0.05, 0.13), rim_a=0.09)

# Wisps trailing along the break.
for _ in range(22):
    streak(BAND_Y + rng.gauss(0, BAND_SIGMA * 0.85),
           length=rng.uniform(220, 620), amp=rng.uniform(4, 14),
           thickness=rng.uniform(2.0, 5.0), alpha=rng.uniform(0.020, 0.052))

# A few larger, softer bubbles for depth near the core of the break.
for _ in range(40):
    y = BAND_Y + rng.gauss(0, BAND_SIGMA * 0.7)
    bubble(rng.uniform(0, W), y, rng.uniform(5.5, 9.0),
           fill_a=rng.uniform(0.02, 0.05), rim_a=rng.uniform(0.06, 0.13))

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

out = "/Users/jeffdyer/work/normanhilldyer/dapple.png"
with open(out, "wb") as f:
    f.write(png)
print(f"wrote {out}  {W}x{H}  {len(png):,} bytes")
