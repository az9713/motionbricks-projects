"""Exercise all public exhibits and verify that captured animation changes on screen.

Start a local static server in this repository, then run:
    python tools/test_exhibits.py --base http://127.0.0.1:8090
"""

import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ROUTES = [
    ("performance", "/projects/02-performance/"),
    ("styles", "/projects/03-style-atlas/"),
    ("targets", "/projects/04-target-lab/"),
    ("wind", "/wind-tunnel/"),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_data():
    for name, minimum_styles in [("story", 8), ("atlas", 15)]:
        d = json.loads((ROOT / f"shared/{name}.json").read_text(encoding="utf-8"))
        frames = d["frames"]
        assert d["schema"] == "motionbricks-capture-v1"
        assert len(d["joints"]) == 34
        assert len(frames) > 1000 and frames[-1]["t"] > 50
        assert len(set(f["style"] for f in frames)) >= minimum_styles
        assert all(b["t"] > a["t"] for a, b in zip(frames, frames[1:]))
        assert all(len(f["r"]) == 3 and len(f["q"]) == 136 for f in frames)
        assert all(math.isfinite(v) for f in frames for v in f["r"] + f["q"])
        assert all(.97 < sum(x * x for x in f["q"][j:j + 4]) < 1.03
                   for f in frames[::25] for j in range(0, 136, 4))
        assert len(d["targets"]) > 50
        assert len(d["acks"]) >= len(d["phases"])
        print(f"DATA {name}: {len(frames)} poses, {len(d['summary']['styles_observed'])} styles, {len(d['targets'])} target events", flush=True)
    c = json.loads((ROOT / "shared/counterfactual.json").read_text(encoding="utf-8"))
    assert c["schema"] == "motionbricks-counterfactual-v1" and len(c["variants"]) == 4
    assert all(v["frames"] == 40 and len(v["roots"]) == 120 and len(v["rotations"]) == 5440 for v in c["variants"])
    assert all(math.isfinite(x) for v in c["variants"] for x in v["roots"] + v["rotations"])
    baseline = c["variants"][0]["generated_last_root"]
    assert all(math.dist(baseline, v["generated_last_root"]) > .1 for v in c["variants"][1:])
    print("DATA counterfactual: four valid, distinct model outputs", flush=True)


def ready(page, url):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
    assert response.status == 200, (url, response.status)
    page.wait_for_function("document.documentElement.dataset.ready === 'true'", timeout=60000)
    assert page.locator("canvas").count() == 1
    assert page.locator(".error").count() == 0
    assert page.locator("#phase-labels button").count() >= 12
    assert page.locator("#stage canvas").bounding_box()["height"] >= 300
    assert not errors, (url, errors)
    return errors


def test_desktop(browser, base, name, route, output):
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    errors = ready(page, base + route)
    initial_play = page.locator("#play").text_content().strip()
    page.locator("#play").click()
    assert page.locator("#play").text_content().strip() != initial_play
    if page.locator("#play").text_content().strip() == "Pause":
        page.locator("#play").click()
    page.locator('#phase-labels button[data-phase="1"]').click()
    page.wait_for_timeout(350)
    before = digest(page.locator("#stage").screenshot())
    page.locator("#targets").uncheck()
    page.wait_for_timeout(180)
    no_target = digest(page.locator("#stage").screenshot())
    assert before != no_target, (name, "target ghost toggle did not change rendered pixels")
    page.locator("#targets").check()
    page.locator('#phase-labels button[data-phase="6"]').click()
    page.wait_for_timeout(350)
    after = digest(page.locator("#stage").screenshot())
    assert after != before, (name, "different motion phase rendered identically")
    page.locator("#scrub").evaluate("e => {e.value='750';e.dispatchEvent(new Event('input',{bubbles:true}))}")
    assert abs(int(page.locator("#scrub").input_value()) - 750) <= 1
    page.locator("#speed").click()
    assert page.locator("#speed").text_content().strip() == "0.5× speed"
    page.locator("#follow").uncheck()
    assert not page.locator("#follow").is_checked()
    page.locator("#replay").click()
    assert int(page.locator("#scrub").input_value()) < 80
    page.locator("#play").click()
    canvas = Image.open(BytesIO(page.locator("#stage canvas").screenshot())).convert("RGB")
    assert sum(1 for r, g, b in canvas.getdata() if g > 150 and b > 145 and r < 150) > 50, (name, "character disappeared after restart with follow off")
    still = int(page.locator("#scrub").input_value())
    page.wait_for_timeout(850)
    assert int(page.locator("#scrub").input_value()) == still
    page.locator("#play").click()
    page.wait_for_timeout(900)
    assert int(page.locator("#scrub").input_value()) > still
    if name == "styles":
        assert page.locator(".style-grid button").count() == 15
        for button in page.locator(".style-grid button").all():
            button.click()
            assert button.get_attribute("class") == "active"
            assert page.locator("#command").inner_text().strip()
        assert page.locator(".style-grid small").count() >= 30
    if name == "targets":
        assert page.locator("[data-variant]").count() == 4
        renders = []
        for i in range(4):
            page.locator(f'[data-variant="{i}"]').click()
            page.wait_for_timeout(150)
            renders.append(digest(page.locator("#stage").screenshot()))
            assert page.locator("#phase-labels button").count() == 1
        assert len(set(renders)) == 4, "counterfactual outputs rendered identically"
        assert "Large lateral" in page.locator("#variant-status").inner_text()
        page.locator("#return-story").click()
        assert page.locator("#phase-labels button").count() == 12
    assert not errors, (name, errors)
    page.locator("#play").click() if page.locator("#play").text_content().strip() == "Pause" else None
    page.screenshot(path=str(output / f"{name}-desktop.png"), full_page=True)
    print(f"UI {name}: playback, pause, scrub, phases, target toggle, speed, follow, restart, animation frames passed", flush=True)
    page.close()


def test_mobile(browser, base, name, route, output):
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1, reduced_motion="reduce")
    errors = ready(page, base + route)
    assert page.locator("#play").text_content().strip() == "Play", (name, "reduced-motion autoplay")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), (name, "horizontal overflow")
    page.locator('#phase-labels button[data-phase="3"]').click()
    page.wait_for_timeout(300)
    assert page.locator("#stage canvas").bounding_box()["width"] > 300
    assert not errors, (name, errors)
    page.screenshot(path=str(output / f"{name}-mobile.png"), full_page=True)
    print(f"MOBILE {name}: responsive layout, phase navigation, reduced motion passed", flush=True)
    page.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8090")
    args = parser.parse_args()
    output = ROOT / ".test-output"
    output.mkdir(exist_ok=True)
    validate_data()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for name, route in ROUTES:
            test_desktop(browser, args.base, name, route, output)
            test_mobile(browser, args.base, name, route, output)
        browser.close()
    print("All four exhibits and eight browser layouts passed.", flush=True)


if __name__ == "__main__":
    main()
