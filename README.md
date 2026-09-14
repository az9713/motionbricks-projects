# MotionBricks projects

An independent, evidence-first collection of small projects for learning motion generation on a Windows laptop. This repository is the **home for the whole series**, not just the first G1 experiment. Project 1 is complete and documented; Projects 2–4 are proposed experiments, not published results.

**[Open the project site](https://az9713.github.io/motionbricks-projects/)** · **[Watch Project 1](https://az9713.github.io/motionbricks-projects/demo.html)** · **[Project 1 build and measurements](PROJECT-1.md)**

[![Watch the Project 1 G1 motion demonstration](https://az9713.github.io/motionbricks-projects/poster.jpg)](https://az9713.github.io/motionbricks-projects/demo.html)

The [compressed demonstration video](https://az9713.github.io/motionbricks-projects/demo.mp4) is a 134-second recording of the local browser viewer, hosted on GitHub Pages. The model itself runs locally; GitHub Pages hosts the explanations and recording.

## What MotionBricks is

[NVIDIA MotionBricks](https://nvlabs.github.io/motionbricks/) studies controllable character motion generation. This series uses the independent [localai-org/motion-bricks.cpp](https://github.com/localai-org/motion-bricks.cpp) C++/GGML implementation and its released Unitree G1 assets. In the G1 demo, movement direction, facing, and a motion style help construct four target poses. The model predicts a short continuation: root movement and rotations for 34 joints. A local server streams the result to a browser skeleton viewer.

```text
movement + facing + style
             ↓
     four target poses
             ↓
   C++ / GGML motion planner
             ↓
   root motion + 34 joints
             ↓
     local browser viewer
```

The rendered skeleton is a **generated motion reference**, not a simulated physical robot. A plausible walk in the viewer does not by itself establish balance, foot contact, game-ready latency, or reliable control of hardware.

## Project map

| Project | Status | Question | Main output |
| --- | --- | --- | --- |
| **1 · G1 motion lab** | **Complete** | Can the released model run on this laptop, and what does each browser control actually do? | Working local CPU demo, [control field guide](https://az9713.github.io/motionbricks-projects/MOTIONBRICKS-PROJECT1-CONTROL-FIELD-GUIDE.html), [development journey](https://az9713.github.io/motionbricks-projects/MOTIONBRICKS-PROJECT1-DEVELOPMENT-JOURNEY.html), [recording](https://az9713.github.io/motionbricks-projects/demo.html), and [detailed project notes](PROJECT-1.md). |
| **2 · Performance microscope** | Planned | Where does time go between an input and a visible pose? Can Vulkan improve the result within this laptop's 4 GB VRAM? | Repeatable latency traces, CPU/Vulkan comparison, peak VRAM, and a measured answer to “real time.” |
| **3 · Style atlas** | Planned | How much of a motion change comes from the `.mbstyle` target constraints versus the model's continuation? | Controlled comparisons of the 15 published styles, target windows, trajectories, and joint motion. |
| **4 · Target-pose lab** | Planned | What happens when we construct or alter G1 target poses directly, beyond the stock keyboard controls? | A small target authoring tool, controlled input/output experiments, and failure-case analysis. |

Projects 2–4 are an experimental roadmap. Their names, tools, and outputs may change when the first measurements reveal what is feasible. This repository will hold their code, data summaries, guides, and Pages links as they are completed. Each will receive its own project directory; the root README and site remain the series index.

## What Project 1 established

On a Windows 11 laptop with a Core i5-12450H, 32 GB RAM, and an RTX 3050 Laptop GPU (4 GB VRAM), the **CPU** build under Ubuntu WSL loaded the verified G1 distribution and its 15 styles. The local browser demo rendered movement and ran at `http://127.0.0.1:8080/`. The GPU was present but was **not used or benchmarked**.

An eight-second WebSocket probe received 168 poses over 162 server ticks and observed 2.81 m of root displacement. Its first requested planner call took 461 ms, while its scheduled acknowledgment arrived about 4.6 seconds later; that gap was not isolated. Effective server progress in that sample was about 20 ticks per wall-clock second, below the nominal 50 Hz stream rate. These observations establish a working local path, **not sustained real-time game performance**. The [development journey](https://az9713.github.io/motionbricks-projects/MOTIONBRICKS-PROJECT1-DEVELOPMENT-JOURNEY.html) gives the setup, failures, commands, and measurement limits.

The [control field guide](https://az9713.github.io/motionbricks-projects/MOTIONBRICKS-PROJECT1-CONTROL-FIELD-GUIDE.html) explains every right-panel knob, slider, button, and status readout. It distinguishes controls that affect the planner from target-window inspectors and viewer-only controls, then gives experiments that turn the demo into a learning instrument.

## Start Project 1 locally

Read [PROJECT-1.md](PROJECT-1.md) for the full reproduction steps. In brief: clone this repository, clone the [original C++ implementation](https://github.com/localai-org/motion-bricks.cpp) into a `motion-bricks.cpp` folder inside it, fetch the released G1 assets through the upstream SHA-256-verifying downloader, and build its CPU library and Go demo in Ubuntu WSL. On Windows, `Start-MotionBricks.cmd` starts the local demo; `Stop-MotionBricks.cmd` stops it. The detailed notes explain the exact checkout studied and how to interpret the benchmark.

## Sources and scope

The starting inspiration was Stefan 3D AI's YouTube video, [“Free and Local Real-Time AI Animation - NVIDIA MotionBricks.cpp”](https://www.youtube.com/watch?v=lj-xPo7ueGA). The research is [NVIDIA MotionBricks](https://nvlabs.github.io/motionbricks/). The port, demo, model downloader, and G1 assets come from the [original `motion-bricks.cpp` repository](https://github.com/localai-org/motion-bricks.cpp); Project 1 studied its commit [`2727a456`](https://github.com/localai-org/motion-bricks.cpp/tree/2727a456e0a99baf64476496cd58115fef717944). This series contributes independent Windows/WSL setup notes, measurements, learning guides, launch helpers, and a recording. It does not claim authorship of the research or port.

Weights, compiled binaries, local logs, the source transcript, and the upstream checkout are not redistributed here. Obtain the implementation and model from upstream under their own terms. Future projects will state their exact upstream versions and hardware so their evidence can be compared fairly.
