#!/usr/bin/env python3
"""Generate immutable shared experiment inputs without consulting RTL outcomes."""
import argparse
import hashlib
import json
from pathlib import Path

BASE = 0x80000000


def random_words(seed):
    state = seed
    while True:
        state ^= (state << 13) & 0xffffffff
        state ^= state >> 17
        state ^= (state << 5) & 0xffffffff
        state &= 0xffffffff
        yield state


def generate(out):
    out.mkdir(parents=True, exist_ok=False)
    image = {address: 0 for address in range(0x1000, 0x3000)}

    def word(address, value):
        for byte in range(4):
            image[address + byte] = (value >> (8 * byte)) & 255

    word(0x1000 + 512*4, (2 << 10) | 1)
    for page in range(128):
        word(0x2000 + page*4, ((0x200000 + ((73*page + 19) % 256)) << 10) | 0xdf)
    (out / "page_table.mem").write_text("".join(f"{a:09x} {v:02x}\n" for a, v in sorted(image.items())))
    traces = {}
    traces["sequential"] = [BASE + 64*i for i in range(8192)]
    traces["strided"] = [BASE + ((i*5) % 64)*4096 + ((i*64) % 4096) for i in range(8192)]
    for seed in [1, 7, 42]:
        rng = random_words(seed)
        traces[f"random_s{seed}"] = [BASE + (next(rng) & 63)*4096 + (next(rng) & 4095) for _ in range(8192)]
    for size in [2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 32]:
        traces[f"repeated_w{size}"] = [BASE + (i % size)*4096 + ((i*64) % 4096) for i in range(8192)]
    for name, addresses in traces.items():
        (out / (name + ".trace")).write_text("".join(f"{va:08x} 0\n" for va in addresses))
    manifest = {"schema": 1, "generator": "xorshift32-v1", "base": BASE, "length": 8192,
                "warmup": 1024, "root_ppn": 1, "memory_latency": 5, "clock_ns": 10,
                "seeds": [1, 7, 42], "traces": list(traces),
                "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir())}}
    (out / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    generate(parser.parse_args().out)
