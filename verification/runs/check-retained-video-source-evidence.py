"""Verify retained source identities, screenshot bytes, dimensions and document references."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
from urllib.parse import parse_qs, urlparse


root = Path.cwd().resolve()
research = root / "research"
source = json.loads((research / "source-manifest.json").read_text(encoding="utf-8"))
screens = json.loads((research / "screenshot-manifest.json").read_text(encoding="utf-8"))
assert source["canonical_url"] == "https://www.youtube.com/watch?v=z97PnFIPoFg"
assert source["channel"] == "AI Pathways" and source["title"].startswith("Claude Tested 100,000 Price Action Strategies")
assert source["review_video"]["decoded_frame_count"] == 30_920
assert source["extraction"]["one_second_samples"] == 1_031
assert source["extraction"]["prompt_pages_read"] == list(range(2, 17))
assert any("Not manual inspection" in item for item in source["limitations"])
assert len(screens["screenshots"]) == 37 and screens["resolution"] == [3840, 2160]


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


verified = []
for representation in source["representations"]:
    path = (research / representation["path"]).resolve()
    assert path.is_relative_to(research) and sha(path) == representation["sha256"]
    assert path.stat().st_size == representation["size_bytes"]
    verified.append({"path": path.relative_to(root).as_posix(), "sha256": representation["sha256"]})

index = (research / "screenshots/README.md").read_text(encoding="utf-8")
seen = set()
for screenshot in screens["screenshots"]:
    path = (research / screenshot["path"]).resolve()
    assert path.is_relative_to(research / "screenshots")
    assert screenshot["id"] not in seen
    seen.add(screenshot["id"])
    assert sha(path) == screenshot["sha256"]
    with path.open("rb") as stream:
        header = stream.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24]) == (3840, 2160)
    assert path.name in index
    url = urlparse(screenshot["source_url"])
    parameters = parse_qs(url.query)
    assert url.netloc == "www.youtube.com" and parameters["v"] == ["z97PnFIPoFg"]
    timestamp = parameters["t"][0]
    seconds = float(timestamp.removesuffix("s"))
    requested = screenshot["source_seconds_requested"]
    assert 0 <= requested - seconds < 1
    assert abs(screenshot["source_frame_index_approx"] - 30 * requested) <= 1
    verified.append({"path": path.relative_to(root).as_posix(), "sha256": screenshot["sha256"]})

for document in ("PLAN.md", "VIDEO_REVIEW.md", "SCREENSHOT_FINDINGS.md", "research/screenshots/README.md"):
    path = root / document
    content = path.read_text(encoding="utf-8")
    if document == "SCREENSHOT_FINDINGS.md":
        assert "(VIDEO_REVIEW.md)" in content and "(research/screenshot-manifest.json)" in content
    else:
        assert "z97PnFIPoFg" in content
    for target in re.findall(r"\]\(([^)]+)\)", content):
        if target.startswith(("http://", "https://", "#")):
            continue
        local = (path.parent / target.split("#", 1)[0]).resolve()
        assert local.is_relative_to(root) and local.exists(), f"Missing local document link in {document}"
    verified.append({"path": document, "sha256": sha(path)})

output = {
    "scope": "Retained local provenance and link-target audit for SPEC-001-C01. External URL availability and source financial results are outside this check.",
    "video_title": source["title"], "source_url": source["canonical_url"],
    "verified_media_representations": len(source["representations"]),
    "verified_screenshots": len(screens["screenshots"]),
    "automatically_decoded_frames": 30_920, "visually_sampled_seconds": 1_031,
    "technical_prompt_pages": 15,
    "individual_visual_review_of_every_frame_claimed": False,
    "verified": verified,
}
out = Path(os.environ["PA_EVIDENCE_RUN_DIR"])
(out / "retained-video-source-evidence.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in output.items() if key != "verified"}), flush=True)
