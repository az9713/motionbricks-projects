"""Run real stateless G1 inference with identical source poses and changed targets.

Run in Ubuntu WSL after the Project 1 CPU build. Uses only Python stdlib ctypes.
The output is a small, browser-replayable educational dataset, not live inference.
"""

import ctypes as C
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = next((path for path in (ROOT / "motion-bricks.cpp", ROOT.parent / "motion-bricks.cpp") if path.exists()), ROOT / "motion-bricks.cpp")
LIB = C.CDLL(str(UPSTREAM / "build/wsl-cpu/libmotionbricks.so"))
MODEL = str(UPSTREAM / "generated/g1-f32").encode()
U64, U32, FP, PTR = C.c_uint64, C.c_uint32, C.c_float, C.c_void_p
ERR = C.create_string_buffer(1024)


def bind(name, *types):
    fn = getattr(LIB, name)
    fn.argtypes = types
    fn.restype = U32
    return fn


create_options = bind("mb_runtime_options_create", C.POINTER(PTR), C.c_void_p, U64)
set_device = bind("mb_runtime_options_set_device", PTR, U32, C.c_void_p, U64)
load_model = bind("mb_model_load", C.c_char_p, PTR, C.POINTER(PTR), C.c_void_p, U64)
create_request = bind("mb_inference_request_create", C.POINTER(PTR), C.c_void_p, U64)
set_boundary = bind("mb_inference_request_set_boundary_poses", PTR, PTR, U32, C.POINTER(FP), U64, C.POINTER(FP), U64, C.c_void_p, U64)
set_mask = bind("mb_inference_request_set_mask", PTR, U32, C.POINTER(U32), U64, C.c_void_p, U64)
set_seed = bind("mb_inference_request_set_seed", PTR, U64, C.c_void_p, U64)
infer = bind("mb_model_infer", PTR, PTR, C.POINTER(PTR), C.c_void_p, U64)
get_frames = bind("mb_motion_get_frame_count", PTR, C.POINTER(U64), C.c_void_p, U64)
get_roots = bind("mb_motion_get_root_translations", PTR, C.POINTER(C.POINTER(FP)), C.POINTER(U64), C.c_void_p, U64)
get_rotations = bind("mb_motion_get_local_rotations_xyzw", PTR, C.POINTER(C.POINTER(FP)), C.POINTER(U64), C.c_void_p, U64)
LIB.mb_motion_free.argtypes = [PTR]
LIB.mb_inference_request_free.argtypes = [PTR]
LIB.mb_model_free.argtypes = [PTR]
LIB.mb_runtime_options_free.argtypes = [PTR]


def checked(status, step):
    if status:
        raise RuntimeError(f"{step}: status {status}: {ERR.value.decode(errors='replace')}")


def yaw_from(q):
    x, y, z, w = q
    return math.atan2(2 * (w * y + x * z), 1 - 2 * (y * y + z * z))


def rotate_y(q, angle):
    x, y, z, w = q
    s, c = math.sin(angle / 2), math.cos(angle / 2)
    return [c * x + s * z, c * y + s * w, c * z - s * x, c * w - s * y]


def canonicalize(roots, rotations):
    origin_x, origin_z = roots[0], roots[2]
    yaw = yaw_from(rotations[:4])
    co, si = math.cos(yaw), math.sin(yaw)
    canon_roots, canon_q = [], list(rotations)
    for i in range(4):
        dx, z = roots[i * 3] - origin_x, roots[i * 3 + 2] - origin_z
        canon_roots += [co * dx - si * z, roots[i * 3 + 1], si * dx + co * z]
        offset = i * 136
        canon_q[offset:offset + 4] = rotate_y(rotations[offset:offset + 4], -yaw)
    return canon_roots, canon_q


def as_float_array(values):
    return (FP * len(values))(*values)


def run_variant(model, source_roots, source_q, dx, dz, seed):
    target_roots = list(source_roots)
    for i in range(4):
        target_roots[i * 3] += dx
        target_roots[i * 3 + 2] += dz
    request, motion = PTR(), PTR()
    try:
        checked(create_request(C.byref(request), ERR, len(ERR)), "create request")
        for half, roots in [(0, source_roots), (1, target_roots)]:
            checked(set_boundary(request, model, half, as_float_array(roots), 12,
                                 as_float_array(source_q), 544, ERR, len(ERR)), f"boundary {half}")
        duration_mask = (U32 * 11)(0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0)
        checked(set_mask(request, 3, duration_mask, 11, ERR, len(ERR)), "40-frame duration")
        checked(set_seed(request, seed, ERR, len(ERR)), "seed")
        checked(infer(model, request, C.byref(motion), ERR, len(ERR)), "inference")
        frames, roots_ptr, q_ptr, root_count, q_count = U64(), C.POINTER(FP)(), C.POINTER(FP)(), U64(), U64()
        checked(get_frames(motion, C.byref(frames), ERR, len(ERR)), "frame count")
        checked(get_roots(motion, C.byref(roots_ptr), C.byref(root_count), ERR, len(ERR)), "roots")
        checked(get_rotations(motion, C.byref(q_ptr), C.byref(q_count), ERR, len(ERR)), "rotations")
        if frames.value != 40 or root_count.value != 120 or q_count.value != 5440:
            raise RuntimeError("Unexpected inference output shape")
        roots = [round(roots_ptr[i], 5) for i in range(root_count.value)]
        rotations = [round(q_ptr[i], 5) for i in range(q_count.value)]
        if not all(math.isfinite(v) for v in roots + rotations):
            raise RuntimeError("Non-finite inferred motion")
        requested = target_roots[-3:]
        ending = roots[-3:]
        return {"dx": dx, "dz": dz, "requested_last_root": [round(x, 5) for x in requested],
                "generated_last_root": ending, "end_error_m": round(math.dist(requested, ending), 4),
                "roots": roots, "rotations": rotations, "frames": frames.value}
    finally:
        if motion:
            LIB.mb_motion_free(motion)
        if request:
            LIB.mb_inference_request_free(request)


def main():
    story = json.loads((ROOT / "shared/story.json").read_text(encoding="utf-8"))
    event = next(e for e in story["targets"] if e["style"] == "walk" and len(e["roots"]) == 12)
    source_roots, source_q = canonicalize(event["roots"], event["rotations"])
    options, model = PTR(), PTR()
    try:
        checked(create_options(C.byref(options), ERR, len(ERR)), "options")
        checked(set_device(options, 1, ERR, len(ERR)), "CPU backend")
        checked(load_model(MODEL, options, C.byref(model), ERR, len(ERR)), "load G1 model")
        variants = []
        for label, dx, dz in [("Forward baseline", 0.0, 0.65), ("Small lateral request", 0.15, 0.65),
                              ("Medium lateral request", 0.30, 0.65), ("Large lateral request", 0.55, 0.65)]:
            result = run_variant(model, source_roots, source_q, dx, dz, 7331)
            result["label"] = label
            variants.append(result)
            print(label, "end error", result["end_error_m"], "m", flush=True)
        output = {"schema": "motionbricks-counterfactual-v1", "source": story["source"],
                  "seed": 7331, "duration_frames": 40, "fps": 30,
                  "source_poses": {"roots": source_roots, "rotations": source_q},
                  "variants": variants,
                  "method": "Stateless mb_model_infer; same four source poses, same target rotations, same seed and 40-frame duration; only target root X changes. Both boundaries are canonicalized from one real controller target event."}
        path = ROOT / "shared/counterfactual.json"
        path.write_text(json.dumps(output, separators=(",", ":")), encoding="utf-8")
        print("Wrote", path, path.stat().st_size, "bytes", flush=True)
    finally:
        if model:
            LIB.mb_model_free(model)
        if options:
            LIB.mb_runtime_options_free(options)


if __name__ == "__main__":
    main()
