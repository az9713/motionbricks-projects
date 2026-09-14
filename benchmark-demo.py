"""Measure a live local MotionBricks CPU planning request over WebSocket."""

import argparse
import asyncio
import json
import math
import time

import websockets


async def measure(url: str, seconds: float) -> None:
    async with websockets.connect(url, max_size=2**20) as socket:
        started = time.perf_counter()
        hello = None
        while hello is None:
            message = json.loads(await asyncio.wait_for(socket.recv(), 30))
            if message.get("type") == "hello":
                hello = message
        if not hello.get("owner"):
            raise RuntimeError("Another browser owns this demo. Use a separate port for the benchmark.")

        seq = int(hello.get("last_seq", 0)) + 1
        await socket.send(json.dumps({"type": "resume", "seq": seq}))
        seq += 1
        await socket.send(json.dumps({"type": "control", "seq": seq, "style": "walk", "move": [0, 1], "facing": [0, 1]}))
        requested = time.perf_counter()
        planner_ms = None
        scheduled_ms = None
        frames = []
        errors = []
        deadline = requested + seconds

        while time.perf_counter() < deadline:
            try:
                message = json.loads(await asyncio.wait_for(socket.recv(), deadline - time.perf_counter()))
            except asyncio.TimeoutError:
                break
            kind = message.get("type")
            if kind == "error":
                errors.append(message.get("error", "unknown error"))
            elif kind == "ack" and message.get("seq") == seq and message.get("state") == "scheduled":
                planner_ms = message.get("planner_ms")
                scheduled_ms = (time.perf_counter() - requested) * 1000
            elif kind == "frame":
                frames.append(message)

        if errors:
            raise RuntimeError("; ".join(errors))
        if planner_ms is None or not frames:
            raise RuntimeError("No completed motion plan and frames arrived during the measurement.")

        roots = [frame["root"] for frame in frames]
        displacement = math.dist(roots[0], roots[-1])
        tick_span = frames[-1]["tick"] - frames[0]["tick"]
        print(f"WebSocket connected in {requested - started:.2f} s")
        print(f"First requested walk plan: {planner_ms:.0f} ms inside planner; {scheduled_ms:.0f} ms to scheduled acknowledgement")
        print(f"Received {len(frames)} pose frames across {tick_span} server ticks in {seconds:.1f} s")
        print(f"Effective server progress: {tick_span / seconds:.1f} ticks/s (50 ticks/s is nominal)")
        print(f"Root displacement during sample: {displacement:.2f} m")
        print(f"Latest server slow-tick count: {frames[-1].get('slow_ticks', 0)}")
        print("Browser playback underruns must be checked in the viewer; they are not measured by this script.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--seconds", type=float, default=8)
    args = parser.parse_args()
    asyncio.run(measure(f"ws://127.0.0.1:{args.port}/api/stream/socket", args.seconds))


if __name__ == "__main__":
    main()
