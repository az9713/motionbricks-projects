# MotionBricks Project 1: a local G1 motion lab

This is an independent, reproducible learning project built around the [original `motion-bricks.cpp` repository](https://github.com/localai-org/motion-bricks.cpp). It runs that repository's released Unitree G1 motion model on a Windows laptop through Ubuntu WSL, then uses the repository's browser demo to study what movement, facing, style, and target-pose controls actually do.

**[Project site](https://az9713.github.io/motionbricks-project1-g1-lab/)** · **[Control field guide](https://az9713.github.io/motionbricks-project1-g1-lab/MOTIONBRICKS-PROJECT1-CONTROL-FIELD-GUIDE.html)** · **[Development journey](https://az9713.github.io/motionbricks-project1-g1-lab/MOTIONBRICKS-PROJECT1-DEVELOPMENT-JOURNEY.html)** · **[Watch the demo](https://az9713.github.io/motionbricks-project1-g1-lab/demo.html)**

[![Watch the Project 1 G1 motion demonstration](https://az9713.github.io/motionbricks-project1-g1-lab/poster.jpg)](https://az9713.github.io/motionbricks-project1-g1-lab/demo.html)

The [compressed MP4](https://az9713.github.io/motionbricks-project1-g1-lab/demo.mp4) is hosted on GitHub Pages (134 seconds, 1600 × 724, H.264, silent, about 6.7 MB). The original local recording was about 120 MB. The recording shows the real local viewer, including several styles and the target-pose overlay; it is not a rendered marketing animation.

## Why this project exists

The starting point was Stefan 3D AI's YouTube video, [“Free and Local Real-Time AI Animation - NVIDIA MotionBricks.cpp”](https://www.youtube.com/watch?v=lj-xPo7ueGA). The video shows the promise of local motion generation and an Unreal integration, while also discussing response time and low-VRAM constraints. Rather than treating a compelling video as a performance guarantee, Project 1 asks a narrower question: **can the published G1 model really load, generate controllable motion, and stream it to a browser on this laptop—and what does each control tell us?**

The underlying research is [NVIDIA's MotionBricks project](https://nvlabs.github.io/motionbricks/). The C++/GGML port, G1 model packaging, demo, and model downloader are from [localai-org/motion-bricks.cpp](https://github.com/localai-org/motion-bricks.cpp), licensed there under Apache-2.0. This repository contributes the Windows/WSL setup record, local launch helpers, a small measurement script, educational guides, and the demo recording. It does **not** fork or claim authorship of the original research or port.

## What MotionBricks is, in this installation

MotionBricks generates a short continuation of character motion from recent pose context and control targets. In the released G1 path used here, the output includes root movement and local rotations for **34 joints**. The demo controller turns direction, facing, and a selected `.mbstyle` asset into a short window of **four target poses (T0–T3)**. The model plans motion against that window. The Go server advances the generated reference and streams timestamped poses; a Three.js viewer interpolates and draws a skeleton.

```text
W/A/S/D + facing + style
          ↓
  four placed G1 target poses
          ↓
     C++ / GGML planner
          ↓
  root path + 34 joint rotations
          ↓
 Go WebSocket stream → browser viewer
```

The mint skeleton is generated output. The warm ghost is a placed target constraint. The target slider and overlay help inspect that constraint window; **they do not change the model's prediction**. Camera orbit changes viewpoint and also changes the world direction implied by camera-relative W/A/S/D. The [field guide](https://az9713.github.io/motionbricks-project1-g1-lab/MOTIONBRICKS-PROJECT1-CONTROL-FIELD-GUIDE.html) explains every right-panel item and gives six controlled experiments.

## What Project 1 established

On the measured Windows 11 laptop (Core i5-12450H, 32 GB RAM, RTX 3050 Laptop GPU with 4 GB VRAM), the **CPU** path in Ubuntu 24.04 WSL loaded the SHA-256-verified model distribution, accepted 15 style assets, and served the browser demo at `http://127.0.0.1:8080/`. The G1 skeleton rendered, W produced forward walking, and the Windows start/stop launchers worked. The GPU was present but was **not used or benchmarked**.

One eight-second WebSocket probe received 168 pose messages over 162 server ticks with 2.81 m of root displacement. Its first requested planner call took 461 ms; the scheduled acknowledgment arrived after about 4.6 seconds, for reasons the probe did not isolate. The effective server progress in that sample was about 20 ticks per wall-clock second, below the nominal 50 Hz stream rate. A short later Chrome test showed no playback underruns, while an earlier test had some. These observations prove that local generation works; they **do not prove sustained real-time game performance**. The [development journey](https://az9713.github.io/motionbricks-project1-g1-lab/MOTIONBRICKS-PROJECT1-DEVELOPMENT-JOURNEY.html) records the build, failures, commands, and measurement boundaries.

This installation does not include live SONIC/MuJoCo physics, a skinned character, an Unreal connection, or a physical robot. GitHub Pages hosts the educational pages and video, **not the running neural model**. The interactive demo remains a local application.

## Reproduce the local demo

These steps are for a Windows machine with Ubuntu WSL, GCC/G++, CMake, Go, Python, Git, and enough disk space for the approximately 0.73 GB model distribution and build products. The tested build used CMake 3.31.5 and Go 1.26.3. Work in a folder on a Windows drive if you want the supplied double-click launchers to map the path into WSL. Linux commands below run inside Ubuntu unless stated otherwise.

1. Clone this educational repository, then clone the original implementation into its expected sibling folder. Pinning the upstream commit reproduces the version studied here:

   ```bash
   git clone https://github.com/az9713/motionbricks-project1-g1-lab.git
   cd motionbricks-project1-g1-lab
   git clone --recurse-submodules https://github.com/localai-org/motion-bricks.cpp.git motion-bricks.cpp
   git -C motion-bricks.cpp checkout 2727a456e0a99baf64476496cd58115fef717944
   git -C motion-bricks.cpp submodule update --init --recursive
   ```

2. Download the released G1 assets using the original repository's SHA-256-verifying downloader, then build its CPU library and command-line tool:

   ```bash
   cd motion-bricks.cpp
   python3 scripts/download_gguf_weights.py
   cmake -S . -B build/wsl-cpu -G "Unix Makefiles" \
     -DCMAKE_BUILD_TYPE=Release \
     -DMOTIONBRICKS_ENABLE_VULKAN=OFF \
     -DMOTIONBRICKS_DOWNLOAD_MODELS=OFF \
     -DMOTIONBRICKS_CPU_ALL_VARIANTS=OFF \
     -DMOTIONBRICKS_BUILD_TESTS=ON
   cmake --build build/wsl-cpu --target motionbricks_shared motionbricks-cli --parallel 4
   cd demo
   CGO_ENABLED=0 go build -o ../build/wsl-cpu/bin/motionbricks-demo .
   cd ../..
   ```

3. On Windows, double-click [`Start-MotionBricks.cmd`](Start-MotionBricks.cmd). It uses the `Ubuntu` WSL distro, waits for the health endpoint, and opens the local page. Double-click [`Stop-MotionBricks.cmd`](Stop-MotionBricks.cmd) when done. The helper scripts are [`run-demo.sh`](run-demo.sh), [`stop-demo.sh`](stop-demo.sh), and the paired PowerShell wrappers. If your WSL distro has a different name, change `-d Ubuntu` in the PowerShell wrappers. The output log is local at `.state/demo-8080.log`.

The original build encountered a broken `apt` dependency state in Ubuntu, so portable official CMake and Go archives were used locally instead of changing the system CUDA packages. Those archives are not redistributed here; the [journey](https://az9713.github.io/motionbricks-project1-g1-lab/MOTIONBRICKS-PROJECT1-DEVELOPMENT-JOURNEY.html#wsl) explains that decision. If your WSL distribution already has suitable CMake and Go, use them as in the commands above.

For an independent WebSocket timing sample, [`benchmark-demo.py`](benchmark-demo.py) uses Python's `websockets` package and expects a **separate** demo server on port 8081. The browser and a benchmark client cannot both own the same shared session. See the journey's measurement section before interpreting its numbers.

## Learn by changing one input at a time

| Experiment | Change | What to inspect |
| --- | --- | --- |
| Walk, stop, restart | W or the latched on-screen pad | Target ghost, root path, planner wait, playback buffer |
| Same command, two styles | `walk` versus `stealth_walk` or `walk_zombie` | Posture, step timing, target poses, actual displacement |
| Target-window inspection | T0–T3 slider and all-four overlay | The four adjacent constraints; the generated motion should not change because you moved the inspector |
| Camera-relative motion | Orbit the camera, then press W | The input coordinate transform before blaming the model for a turn |
| Continuity | Repeated turns and stops | Planner time, server ticks, viewer underruns, visible delay as separate measurements |

The [full control field guide](https://az9713.github.io/motionbricks-project1-g1-lab/MOTIONBRICKS-PROJECT1-CONTROL-FIELD-GUIDE.html) also covers Pause, Reset, Jump, Kimodo upload, disabled physics options, all 15 styles, and what every status readout means.

## What to build next

The next useful project is an instrumented latency study: timestamp the input, target construction, planner start/end, scheduled acknowledgment, streamed frame arrival, and browser presentation for the same scripted movement sequence. That will separate inference cost from scheduling and playback. A Vulkan comparison should then measure both latency **and peak VRAM** on this 4 GB GPU. Only after those baselines would an Unreal bridge and retargeted skinned character be meaningful to evaluate. Optional SONIC/MuJoCo physics is a separate experiment: kinematic plausibility in Project 1 is not evidence of balance or contact feasibility.

## Repository contents and publication boundary

- [`index.html`](index.html): public learning hub.
- [`MOTIONBRICKS-PROJECT1-CONTROL-FIELD-GUIDE.html`](MOTIONBRICKS-PROJECT1-CONTROL-FIELD-GUIDE.html): every right-panel control and six experiments.
- [`MOTIONBRICKS-PROJECT1-DEVELOPMENT-JOURNEY.html`](MOTIONBRICKS-PROJECT1-DEVELOPMENT-JOURNEY.html): the full installation and validation record.
- [`demo.html`](demo.html), [`demo.mp4`](demo.mp4), [`poster.jpg`](poster.jpg): recorded demonstration.
- Launch helpers and [`benchmark-demo.py`](benchmark-demo.py): local reproducibility aids.

Model weights, compiled binaries, tool archives, local logs, source transcript, and the upstream source checkout are intentionally **not** in this repository. Obtain the implementation and model through the [original repository](https://github.com/localai-org/motion-bricks.cpp) and its downloader, subject to its own licensing and model terms. This project's guides describe the pinned checkout `2727a456e0a99baf64476496cd58115fef717944`; future upstream revisions may behave differently.
