#!/usr/bin/env python3
"""Independently verify the portable portfolio against the approved release."""

import argparse
import base64
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image


LIMIT = 300_000_000
MODEL_PREFIX = "model-"
FORMAL_DEFAULT = Path(__file__).resolve().parents[2] / "rose-live"
SECRET_PATTERNS = {
    "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "GitHub token": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b",
    "AWS key": r"\bAKIA[0-9A-Z]{16}\b",
    "deployment password assignment": r"(?i)(?:SSH_PASSWORD|DEPLOY_PASSWORD|SERVER_PASSWORD)\s*[:=]\s*[\"'][^\"']+[\"']",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_glb(data):
    if len(data) < 20:
        raise ValueError("GLB is truncated")
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("Invalid GLB header or byte length")
    size, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A or 20 + size > len(data):
        raise ValueError("Invalid GLB JSON chunk")
    return json.loads(data[20:20 + size])


class PortfolioHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts = []
        self.styles = []
        self.references = []
        self.inline_styles = []
        self.csp = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "content-security-policy":
            self.csp.append(attrs.get("content", ""))
        for name in ("src", "href", "poster", "action", "data"):
            if attrs.get(name):
                self.references.append((f"{tag}.{name}", attrs[name]))
        if attrs.get("srcset"):
            # Portfolio previews should use src or JSON data, not a data-URI srcset.
            self.references.append((f"{tag}.srcset", attrs["srcset"]))
        if attrs.get("style"):
            self.inline_styles.append(attrs["style"])
        if tag in ("script", "style"):
            self.current = {"tag": tag, "attrs": attrs, "chunks": []}

    def handle_data(self, data):
        if self.current:
            self.current["chunks"].append(data)

    def handle_endtag(self, tag):
        if self.current and self.current["tag"] == tag:
            item = self.current
            item["text"] = "".join(item.pop("chunks"))
            (self.scripts if tag == "script" else self.styles).append(item)
            self.current = None


def all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from all_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from all_strings(item)


def image_from_data_url(url):
    header, encoded = url.split(",", 1)
    if not header.startswith("data:image/") or ";base64" not in header:
        raise ValueError("Expected a base64 image data URL")
    data = base64.b64decode(encoded, validate=True)
    if header.startswith("data:image/svg+xml"):
        root = ET.fromstring(data)
        if root.tag.split("}")[-1] != "svg":
            raise ValueError("SVG data has no svg root")
        for node in root.iter():
            if node.tag.split("}")[-1] in ("script", "foreignObject"):
                raise ValueError("SVG contains executable content")
            for key, value in node.attrib.items():
                if key.split("}")[-1] in ("href", "src") and not value.startswith(("#", "data:")):
                    raise ValueError("SVG references an external resource")
        return "SVG", root.get("viewBox")
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if image.width < 1 or image.height < 1:
            raise ValueError("Image has empty dimensions")
        return image.format, image.size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", type=Path)
    parser.add_argument("--formal", type=Path, default=FORMAL_DEFAULT)
    parser.add_argument("--zip", dest="archive", type=Path)
    parser.add_argument("--allow-file", action="append", default=[])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("Self-checks passed")
        return 0
    if not args.package:
        parser.error("package is required unless --self-test is used")

    package = args.package.resolve()
    formal = args.formal.resolve()
    failures, checks, warnings = [], [], []
    report = {"package": str(package), "formal": str(formal), "checks": checks,
              "failures": failures, "warnings": warnings, "statistics": {}}
    stats = report["statistics"]

    def check(ok, name, detail=None):
        (checks if ok else failures).append({"check": name, **({"detail": detail} if detail is not None else {})})
        return ok

    source = formal / "docs/client-motion-demo/src"
    public = formal / "server-reference/public"
    products = json.loads((source / "structure/collection-products.json").read_text())
    products.update({
        "poster-012": {"file": "beach-magic-packaging.glb", "parts": [{"node": n} for n in ("OuterCap", "InnerLid", "Jar", "LogoPrint")]},
        "poster-071": {"file": "liaose-pump.glb", "parts": [{"node": n} for n in ("PumpHead", "PumpStem", "Closure", "BottleAssembly", "LogoPrint")]},
    })
    posters = json.loads((source / "posters.json").read_text())
    paths = json.loads((source / "asset-paths.json").read_text())
    html_path = package / "打开作品.html"
    document = PortfolioHTML()
    document.feed(html_path.read_text(encoding="utf-8"))
    data_scripts = [s for s in document.scripts if s["attrs"].get("id") == "portfolio-data"]
    if not check(len(data_scripts) == 1, "One portfolio-data JSON block"):
        return finish(report, args.report)
    check(data_scripts[0]["attrs"].get("type") == "application/json", "Portfolio metadata uses inert JSON script")
    data = json.loads(data_scripts[0]["text"])
    expected_ids = set(products)
    check(len(expected_ids) == 26, "Formal source has 26 models")
    check(len(posters) == 61, "Formal source has 61 posters")
    check({p["id"] for p in data["posters"]} == {p["id"] for p in posters}
          and len(data["posters"]) == 61, "All 61 posters represented exactly once")
    check({p["id"] for p in data["featured"]} == expected_ids
          and len(data["featured"]) == 26, "All 26 featured models represented exactly once")
    check(data.get("sourceRelease") == "client1.40", "Approved source release recorded")
    stats["sourceRelease"] = data.get("sourceRelease")
    manifest = {m["id"]: m for m in data["models"]}
    check(set(manifest) == expected_ids and len(data["models"]) == 26, "26 model manifest entries")
    embedded = [s for s in document.scripts if s["attrs"].get("id", "").startswith(MODEL_PREFIX)]
    model_ids = [s["attrs"]["id"][len(MODEL_PREFIX):] for s in embedded]
    check(set(model_ids) == expected_ids and len(model_ids) == 26, "26 embedded GLBs exactly match formal IDs")
    model_bytes = 0
    for item in embedded:
        product_id = item["attrs"]["id"][len(MODEL_PREFIX):]
        try:
            if product_id not in products:
                raise ValueError("Unknown model ID")
            check(item["attrs"].get("type") == "application/octet-stream", f"{product_id}: inert binary script")
            raw = base64.b64decode(re.sub(r"\s+", "", item["text"]), validate=True)
            model_bytes += len(raw)
            product = products[product_id]
            approved = (public / "showroom/assets/packaging" / product["file"]).read_bytes()
            digest = sha256(raw)
            check(digest == sha256(approved), f"{product_id}: GLB equals formal SHA256")
            entry = manifest[product_id]
            check(entry["file"] == product["file"] and entry["bytes"] == len(raw)
                  and entry["sha256"] == digest, f"{product_id}: manifest bytes/file/SHA256")
            gltf = read_glb(raw)
            names = {n.get("name") for n in gltf.get("nodes", [])}
            missing = [p["node"] for p in product["parts"] if p["node"] not in names]
            check(not missing, f"{product_id}: all configured component nodes", missing or None)
            external = [r["uri"] for key in ("images", "buffers") for r in gltf.get(key, []) if "uri" in r]
            check(not external, f"{product_id}: GLB contains all textures and geometry")
        except Exception as exc:
            check(False, f"{product_id}: binary verification", str(exc))
    stats.update(models=len(embedded), model_bytes=model_bytes, posters=len(data["posters"]))

    allowed = {"打开作品.html", "先读我.txt", "第三方许可.txt", "作品清单.json", *args.allow_file}
    for poster in posters:
        relative = f"海报原图/{poster['id']}.webp"
        allowed.add(relative)
        original = package / relative
        approved = public / paths[poster["original"]].lstrip("/")
        check(original.is_file() and sha256(original.read_bytes()) == sha256(approved.read_bytes()),
              f"{poster['id']}: original poster equals formal SHA256")
    delivery_manifest = json.loads((package / "作品清单.json").read_text())
    html_bytes = html_path.read_bytes()
    check(delivery_manifest.get("htmlSha256") == sha256(html_bytes)
          and delivery_manifest.get("htmlBytes") == len(html_bytes), "Delivery manifest matches HTML bytes and SHA256")
    check(delivery_manifest.get("models") == data["models"], "Delivery and embedded model manifests agree")
    check(len(delivery_manifest.get("originals", [])) == 61, "Delivery manifest lists 61 originals")
    for entry in delivery_manifest.get("originals", []):
        location = (package / entry["destination"]).resolve()
        if check(location.is_relative_to(package) and location.is_file(), "Manifest original stays inside delivery"):
            raw = location.read_bytes()
            check(entry.get("bytes") == len(raw) and entry.get("sha256") == sha256(raw), "Original manifest hash: " + entry["destination"])

    strings = list(all_strings(data))
    data_urls = {s for s in strings if s.startswith("data:image/")}
    for _, value in document.references:
        if value.startswith("data:image/"):
            data_urls.add(value)
    for index, url in enumerate(sorted(data_urls, key=lambda s: (len(s), s[:80]))):
        try:
            image_from_data_url(url)
        except Exception as exc:
            check(False, f"Embedded image {index + 1} decodes", str(exc))
    check(bool(data_urls), "Embedded preview images found")
    stats["unique_embedded_images"] = len(data_urls)
    if not any(f["check"].startswith("Embedded image ") for f in failures):
        check(True, "Every embedded image data URL decodes", len(data_urls))

    def verify_reference(origin, url):
        url = url.strip()
        if url.startswith(("data:", "blob:", "#")):
            return
        if re.match(r"^(?:[a-zA-Z][\w+.-]*:|/|\\)", url):
            check(False, "No external or absolute resource entry", origin)
            return
        reference = url.split("?", 1)[0].split("#", 1)[0]
        path = (package / reference).resolve()
        check(path.is_relative_to(package) and path.is_file(), "Relative resource exists inside package", origin + ": " + reference)

    for poster in data["posters"]:
        check(all(poster.get(key, "").startswith("data:image/") for key in ("image", "smallImage", "thumb", "stripThumb")),
              poster["id"] + ": every preview is embedded")
        verify_reference(poster["id"] + " original", poster["original"])
    check(all(p.get("image", "").startswith("data:image/") for p in data["featured"]), "Every featured preview is embedded")
    check(data.get("logo", "").startswith("data:image/"), "Logo is embedded")
    check(len(document.csp) == 1, "One offline Content Security Policy")
    if document.csp:
        directives = {d.strip().split()[0]: d.strip().split()[1:] for d in document.csp[0].split(";") if d.strip()}
        check(directives.get("default-src") == ["'none'"] and directives.get("connect-src") == ["blob:"]
              and directives.get("script-src") == ["'unsafe-inline'"], "CSP blocks external scripts and network connections")
    for origin, value in document.references:
        verify_reference(origin, value)
    for item in document.styles + [{"text": s} for s in document.inline_styles]:
        for match in re.finditer(r"url\(\s*['\"]?([^)'\"]+)", item["text"]):
            verify_reference("CSS url", match.group(1))
        check(not re.search(r"@import\s", item["text"]), "No CSS imports")
    executable = "\n".join(s["text"] for s in document.scripts
                            if s["attrs"].get("type", "") not in ("application/octet-stream", "application/json"))
    # Only executable request forms count. Vendor attribution/license URLs are not requests.
    requests = re.findall(r"\b(?:fetch|import|importScripts|Worker)\s*\(\s*[\"'`]((?:https?:)?//[^\"'`]+|/[^\"'`]+)[\"'`]", executable)
    check(not requests, "No literal external/absolute JavaScript requests", len(requests))
    check(not any(s["attrs"].get("type") == "module" for s in document.scripts), "No module script entry requiring file-origin CORS")
    check(not re.search(r"\bimport\s*\(", executable), "No runtime dynamic imports")
    private_text = executable + "\n" + data_scripts[0]["text"]
    for name in ("先读我.txt", "作品清单.json"):
        private_text += "\n" + (package / name).read_text(encoding="utf-8")
    for label, pattern in SECRET_PATTERNS.items():
        check(not re.search(pattern, private_text), "No embedded " + label)
    check(not re.search(r"/Users/[^/\s]+/|/home/[^/\s]+/|[A-Z]:\\Users\\", private_text), "No embedded local user paths")

    actual = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()}
    check(actual == allowed, "Final files match explicit allowlist", {"unexpected": sorted(actual - allowed), "missing": sorted(allowed - actual)})
    check(not any(p.is_symlink() for p in package.rglob("*")), "No symlinks in delivery")
    raw_bytes = sum((package / p).stat().st_size for p in actual)
    stats["uncompressed_bytes"] = raw_bytes
    check(raw_bytes < LIMIT, "Unpacked delivery below 300000000 bytes", raw_bytes)
    if args.archive:
        archive = args.archive.resolve()
        stats["zip_bytes"] = archive.stat().st_size
        check(archive.stat().st_size < LIMIT, "ZIP below 300000000 bytes", archive.stat().st_size)
        with zipfile.ZipFile(archive) as z:
            check(z.testzip() is None, "ZIP CRC testzip succeeds")
            entries = [i for i in z.infolist() if not i.is_dir()]
            names = [i.filename for i in entries]
            check(len(names) == len(set(names)), "ZIP has no duplicate filenames")
            check(all(not PurePosixPath(n).is_absolute() and ".." not in PurePosixPath(n).parts for n in names), "ZIP paths cannot escape extraction directory")
            expected_zip = {package.name + "/" + p for p in actual}
            check(set(names) == expected_zip, "ZIP contains exactly the verified delivery files")
            unpacked = sum(i.file_size for i in entries)
            stats["zip_uncompressed_bytes"] = unpacked
            check(unpacked == raw_bytes and unpacked < LIMIT, "ZIP uncompressed bytes match and remain under limit", unpacked)
            for item in entries:
                relative = item.filename.removeprefix(package.name + "/")
                if relative in actual:
                    check(sha256(z.read(item)) == sha256((package / relative).read_bytes()), "ZIP file matches delivery: " + relative)
    else:
        warnings.append("ZIP not supplied; archive integrity and compressed size are not checked.")
    return finish(report, args.report)


def finish(report, destination):
    report["passed"] = not report["failures"]
    if destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "checks": len(report["checks"]),
                      "failures": report["failures"], "warnings": report["warnings"],
                      "statistics": report["statistics"]}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def self_test():
    payload = json.dumps({"asset": {"version": "2.0"}, "nodes": [{"name": "Body"}]}).encode()
    payload += b" " * (-len(payload) % 4)
    valid = struct.pack("<4sIII4s", b"glTF", 2, 20 + len(payload), len(payload), b"JSON") + payload
    assert read_glb(valid)["nodes"][0]["name"] == "Body"
    try:
        read_glb(valid[:-1])
        raise AssertionError("Truncated GLB was accepted")
    except ValueError:
        pass
    page = PortfolioHTML()
    page.feed('<script type="application/octet-stream" id="model-poster-012">YWJj</script><img src="data:image/png;base64,abc"><style>body{color:red}</style>')
    assert page.scripts[0]["text"] == "YWJj"
    assert page.references[0][0] == "img.src"
    assert page.styles[0]["text"] == "body{color:red}"
    buffer = io.BytesIO()
    Image.new("RGB", (2, 3), "white").save(buffer, "PNG")
    url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    assert image_from_data_url(url) == ("PNG", (2, 3))
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2 3"><path d="M0 0L2 3"/></svg>'
    assert image_from_data_url("data:image/svg+xml;base64," + base64.b64encode(svg).decode()) == ("SVG", "0 0 2 3")
    assert list(all_strings({"a": ["x", {"b": "y"}]})) == ["x", "y"]


if __name__ == "__main__":
    sys.exit(main())
