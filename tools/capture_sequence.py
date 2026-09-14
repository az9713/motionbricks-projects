"""Capture a scripted, real G1 stream from an isolated local MotionBricks server.

The file contains sampled model poses, actual target events, and server acknowledgments.
No motion is fabricated or interpolated during capture. Browser playback may interpolate
between these 25 Hz samples. Use a separate demo port so an open browser keeps its session.
"""

import argparse
import asyncio
import json
import math
import time
import urllib.request
from pathlib import Path

import websockets


STORY = [
    ("Find the floor", "idle", (0, 0), (0, 1), 2),
    ("Walk forward", "walk", (0, 1), (0, 1), 6),
    ("Move quietly", "stealth_walk", (0, 1), (0, 1), 5),
    ("Injured walk", "injured_walk", (0, 1), (0, 1), 6),
    ("Turn 90° right", "injured_walk", (1, 0), (1, 0), 5),
    ("Side-step", "walk_right", (1, 0), (0, 1), 5),
    ("Zombie walk", "walk_zombie", (0, 1), (0, 1), 5),
    ("Happy dance", "walk_happy_dance", (0, 1), (0, 1), 5),
    ("Reverse course", "walk", (0, -1), (0, -1), 5),
    ("Get low", "hand_crawling", (0, 1), (0, 1), 5),
    ("Recover", "walk", (0, 1), (0, 1), 5),
    ("Stop", "idle", (0, 0), (0, 1), 5),
]
ATLAS = [(f"Style: {style.replace('_', ' ')}", style, (0, 0) if style == 'idle' else (0, 1), (0, 1), 3.5)
         for style in ('idle', 'walk', 'slow_walk', 'stealth_walk', 'walk_stealth', 'injured_walk',
                       'walk_zombie', 'walk_scared', 'walk_happy_dance', 'walk_boxing', 'walk_gun',
                       'walk_left', 'walk_right', 'hand_crawling', 'elbow_crawling')]
ATLAS.append(("Stop and recover", "idle", (0, 0), (0, 1), 4))


def get_meta(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/meta", timeout=15) as response:
        return json.load(response)


def compact(values):
    return [round(float(value), 5) for value in values]


async def capture(port, output):
    meta = get_meta(port)
    if len(meta["joints"]) != 34:
        raise RuntimeError("Expected the released 34-joint G1 model")
    phase_end = []
    total = 0
    for _, _, _, _, seconds in STORY:
        total += seconds
        phase_end.append(total)

    record = {
        "schema": "motionbricks-capture-v1",
        "source": "localai-org/motion-bricks.cpp@2727a456e0a99baf64476496cd58115fef717944",
        "backend": "CPU / Ubuntu WSL / RTX 3050 Laptop GPU unused",
        "fps_sampled": 25,
        "joints": meta["joints"],
        "phases": [], "frames": [], "targets": [], "acks": [],
    }
    last_tick = -1
    first_time = None
    last_sim_time = 0.0
    wall_start = time.perf_counter()
    async with websockets.connect(f"ws://127.0.0.1:{port}/api/stream/socket", max_size=2**20, ping_interval=15) as socket:
        hello = None
        while hello is None:
            packet = json.loads(await asyncio.wait_for(socket.recv(), 45))
            if packet.get("type") == "hello":
                hello = packet
        if not hello.get("owner"):
            raise RuntimeError("Another client owns this server; use an isolated port")
        seq = int(hello.get("last_seq", 0)) + 1
        await socket.send(json.dumps({"type": "resume", "seq": seq}))
        seq += 1
        phase_index = -1

        async def send_phase(index, t):
            nonlocal seq
            label, style, move, facing, duration = STORY[index]
            command = {"type": "control", "seq": seq, "style": style, "move": move, "facing": facing}
            await socket.send(json.dumps(command))
            record["phases"].append({"label": label, "style": style, "move": move, "facing": facing,
                                      "t": round(t, 3), "duration": duration, "seq": seq,
                                      "request_wall": round(time.perf_counter() - wall_start, 3)})
            print(f"{t:6.1f}s  {label} / {style}", flush=True)
            seq += 1

        while True:
            packet = json.loads(await asyncio.wait_for(socket.recv(), 120))
            kind = packet.get("type")
            if kind == "error":
                raise RuntimeError(str(packet))
            if kind == "frame":
                tick = int(packet["tick"])
                if tick <= last_tick:
                    continue
                last_tick = tick
                if first_time is None:
                    first_time = float(packet["time"])
                    phase_index = 0
                    await send_phase(0, 0)
                t = float(packet["time"]) - first_time
                last_sim_time = t
                while phase_index + 1 < len(STORY) and t >= phase_end[phase_index]:
                    phase_index += 1
                    await send_phase(phase_index, t)
                if tick % 2 == 0:
                    q = packet["rotations"]
                    if len(q) != 136 or len(packet["root"]) != 3:
                        raise RuntimeError("Invalid G1 pose shape")
                    if not all(math.isfinite(float(x)) for x in q + packet["root"]):
                        raise RuntimeError("Non-finite model pose")
                    record["frames"].append({"t": round(t, 3), "tick": tick,
                                             "r": compact(packet["root"]), "q": compact(q),
                                             "style": packet.get("style", ""),
                                             "revision": packet.get("revision", 0),
                                             "slow": packet.get("slow_ticks", 0)})
                if t >= total:
                    break
            elif kind == "targets":
                targets = packet.get("targets") or {}
                record["targets"].append({"t_wall": round(time.perf_counter() - wall_start, 3),
                                          "t": round(last_sim_time, 3),
                                          "revision": packet.get("revision", 0),
                                          "style": packet.get("style", ""),
                                          "roots": compact(targets.get("roots", [])),
                                          "rotations": compact(targets.get("rotations", []))})
            elif kind == "ack":
                record["acks"].append({"t_wall": round(time.perf_counter() - wall_start, 3),
                                       "t": round(last_sim_time, 3),
                                       "seq": packet.get("seq"), "state": packet.get("state"),
                                       "planner_ms": packet.get("planner_ms"),
                                       "at": packet.get("at"), "time": packet.get("time")})

    frames = record["frames"]
    if len(frames) < total * 12:
        raise RuntimeError(f"Only {len(frames)} sampled frames for {total}s of motion")
    expected_styles = {phase[1] for phase in STORY}
    observed_styles = {frame["style"] for frame in frames}
    if not expected_styles.issubset(observed_styles):
        raise RuntimeError(f"Style changes missing from stream: {expected_styles - observed_styles}")
    if any(b["t"] <= a["t"] for a, b in zip(frames, frames[1:])):
        raise RuntimeError("Non-monotonic recorded frame times")
    record["summary"] = {"sim_seconds": round(frames[-1]["t"], 2),
                         "wall_seconds": round(time.perf_counter() - wall_start, 2),
                         "sampled_frames": len(frames),
                         "styles_observed": sorted({frame["style"] for frame in frames}),
                         "target_events": len(record["targets"]),
                         "scheduled_plans": sum(a["state"] == "scheduled" for a in record["acks"])}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(record["summary"], indent=2), flush=True)
    print(f"Wrote {output} ({output.stat().st_size / 1e6:.2f} MB)", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--mode", choices=("story", "atlas"), default="story")
    parser.add_argument("--out", type=Path, default=Path("shared/story.json"))
    args = parser.parse_args()
    STORY = ATLAS if args.mode == "atlas" else STORY
    asyncio.run(capture(args.port, args.out))
