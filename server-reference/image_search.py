"""Private, CPU-only visual retrieval. Optional dependencies are loaded on demand.

Queries never leave this process and are never saved. Scores are weighted cosine
similarities, not probabilities and not measurements of material or capacity.
"""
import base64
import binascii
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import threading
import warnings
import zipfile

SCHEMA_VERSION = 1
ALLOWED_ROLES = {"supplier", "product", "inquiry"}
MAX_IMAGE_BYTES = 6 * 1024 * 1024
MAX_SOURCE_IMAGE_BYTES = 32 * 1024 * 1024
MAX_REQUEST_BYTES = ((MAX_IMAGE_BYTES + 2) // 3) * 4 + 1024
MAX_PIXELS = 4_000_000
MAX_SOURCE_PIXELS = 20_000_000
MAX_DIMENSION = 10_000
MAX_INDEX_BYTES = 256 * 1024 * 1024
SHAPE_WEIGHT = 0.8
PREPROCESS_VERSION = "letterbox-white-exif-rgb-and-gray-v1"
QUERY_VERSION = "whole-and-center-view-v1"
MAX_SEARCH_RESULTS = 120
UNAVAILABLE_MESSAGE = "图片检索索引暂不可用，请稍后重试；仍可使用文字和分类检索。"


class SearchUnavailable(Exception):
    pass


class SearchBusy(Exception):
    pass


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _dependencies():
    # The catalogue and login remain usable without the optional image stack.
    import numpy as np
    from PIL import Image, ImageOps
    import onnxruntime as ort
    ort.disable_telemetry_events()
    return np, Image, ImageOps, ort


def collect_images(private):
    """Return eligible source images once, preserving all confirmed row links."""
    private = Path(private).resolve()
    catalog_path = private / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    by_path = {}
    record_ids = set()
    for record in catalog.get("records", []):
        rid = record.get("id")
        if not isinstance(rid, str) or not rid or rid in record_ids:
            raise ValueError("目录记录编号缺失或重复")
        record_ids.add(rid)
        if record.get("kind") != "package":
            continue
        for image in record.get("images", []):
            if image.get("missing") or image.get("uncertain") or image.get("role") not in ALLOWED_ROLES:
                continue
            name = image.get("path", "")
            if not isinstance(name, str):
                continue
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts or not name.startswith("media/"):
                continue
            source = (private / name).resolve()
            if not source.is_relative_to((private / "media").resolve()) or not source.is_file():
                continue
            item = by_path.setdefault(name, {"path": name, "record_ids": set()})
            item["record_ids"].add(rid)
    manifest = []
    for name in sorted(by_path):
        item = by_path[name]
        manifest.append({"path": name, "record_ids": sorted(item["record_ids"]),
                         "sha256": sha256(private / name)})
    return {"catalog_sha256": sha256(catalog_path), "images": manifest}


def model_manifest(model_dir):
    model_dir = Path(model_dir)
    files = {name: sha256(model_dir / name) for name in
             ("model.onnx", "config.json", "preprocessor_config.json")}
    return {"files": files, "preprocess_version": PREPROCESS_VERSION,
            "shape_weight": SHAPE_WEIGHT}


def decode_image(data, expected_mime=None, max_bytes=None, max_pixels=None):
    """Validate bounded raster input before expensive pixel decoding."""
    from PIL import Image, ImageOps, UnidentifiedImageError
    if max_bytes is None:
        max_bytes = MAX_IMAGE_BYTES
    if max_pixels is None:
        max_pixels = MAX_PIXELS
    if not isinstance(data, bytes) or not data or len(data) > max_bytes:
        raise ValueError("图片不能为空，且不能超过 6 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                formats = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
                if original.format not in formats or (expected_mime and formats[original.format] != expected_mime):
                    raise ValueError("请上传真实的 JPG、PNG 或 WebP 图片")
                width, height = original.size
                if width < 16 or height < 16:
                    raise ValueError("图片太小，请上传至少 16 × 16 像素的图片")
                if width > MAX_DIMENSION or height > MAX_DIMENSION or width * height > max_pixels:
                    raise ValueError("图片像素过大，请压缩到 400 万像素以内后重试")
                if getattr(original, "n_frames", 1) != 1:
                    raise ValueError("请上传单张静态图片")
                original.load()
                corrected = ImageOps.exif_transpose(original)
                if corrected.mode in ("RGBA", "LA") or "transparency" in corrected.info:
                    rgba = corrected.convert("RGBA")
                    background = Image.new("RGBA", rgba.size, "white")
                    corrected = Image.alpha_composite(background, rgba)
                return corrected.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError("图片无法读取，请重新上传 JPG、PNG 或 WebP 图片") from error


def decode_upload(value):
    if not isinstance(value, str) or len(value) > MAX_REQUEST_BYTES:
        raise ValueError("图片提交格式错误或文件过大")
    match = re.fullmatch(r"data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/]*={0,2})", value)
    if not match:
        raise ValueError("请上传 JPG、PNG 或 WebP 图片")
    try:
        binary = base64.b64decode(match[2], validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("图片编码无效，请重新选择图片") from error
    return decode_image(binary, match[1])


class Embedder:
    def __init__(self, model_dir):
        self.np, self.Image, self.ImageOps, ort = _dependencies()
        model_dir = Path(model_dir)
        config = json.loads((model_dir / "config.json").read_text())
        processor = json.loads((model_dir / "preprocessor_config.json").read_text())
        self.dimension = int(config["hidden_size"])
        size = processor.get("crop_size", {"height": 224, "width": 224})
        if isinstance(size, int):
            size = {"height": size, "width": size}
        self.height, self.width = int(size["height"]), int(size["width"])
        if not 112 <= self.height <= 518 or not 112 <= self.width <= 518 or not 1 <= self.dimension <= 2048:
            raise ValueError("Unsupported visual model dimensions")
        self.mean = self.np.asarray(processor.get("image_mean", [0.485, 0.456, 0.406]), dtype="float32")[:, None, None]
        self.std = self.np.asarray(processor.get("image_std", [0.229, 0.224, 0.225]), dtype="float32")[:, None, None]
        if self.mean.shape != (3, 1, 1) or self.std.shape != (3, 1, 1) or (self.std <= 0).any():
            raise ValueError("Invalid preprocessing configuration")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.enable_cpu_mem_arena = False
        self.session = ort.InferenceSession(str(model_dir / "model.onnx"), sess_options=options,
                                            providers=["CPUExecutionProvider"])
        inputs = self.session.get_inputs()
        if len(inputs) != 1 or inputs[0].type != "tensor(float)":
            raise ValueError("Unexpected visual model inputs")
        self.input_name = inputs[0].name
        outputs = {output.name for output in self.session.get_outputs()}
        self.output_name = "pooler_output" if "pooler_output" in outputs else "last_hidden_state"
        if self.output_name not in outputs:
            raise ValueError("No DINOv2 CLS embedding output")

    def vector(self, image, grayscale):
        np = self.np
        if grayscale:
            image = self.ImageOps.grayscale(image).convert("RGB")
        # Whole-object letterboxing avoids cutting off tall bottles and pump heads.
        contained = self.ImageOps.contain(image, (self.width, self.height), self.Image.Resampling.BICUBIC)
        canvas = self.Image.new("RGB", (self.width, self.height), "white")
        canvas.paste(contained, ((self.width - contained.width) // 2, (self.height - contained.height) // 2))
        pixels = np.asarray(canvas, dtype="float32").transpose(2, 0, 1) / 255.0
        batch = np.ascontiguousarray(((pixels - self.mean) / self.std)[None], dtype="float32")
        output = self.session.run([self.output_name], {self.input_name: batch})[0]
        vector = output[0, 0, :] if self.output_name == "last_hidden_state" else output[0]
        if vector.shape != (self.dimension,) or not np.isfinite(vector).all():
            raise ValueError("Invalid model embedding")
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-12:
            raise ValueError("Empty model embedding")
        return (vector / norm).astype("float32")

    def pair(self, image):
        # Batch 1 and sequential views keep peak memory bounded on the small server.
        return self.vector(image, True), self.vector(image, False)


def query_pairs(embedder, image):
    """Bounded, sequential views reduce background/scale interference.

    Keep the full frame: a centre crop is only an additional hypothesis, never
    a detector or a replacement for a user-selected target. Index vectors stay
    compatible; query photos are neither persisted nor sent to another service.
    """
    yield embedder.pair(image)
    width, height = image.size
    for left, top, right, bottom in ((.2, .1, .8, .9),):
        box = (round(width * left), round(height * top),
               round(width * right), round(height * bottom))
        if min(box[2] - box[0], box[3] - box[1]) < 16:
            continue
        with image.crop(box) as view:
            yield embedder.pair(view)


def rank_matches(np, entries, gray_vectors, rgb_vectors, query_gray, query_rgb,
                 *, extra_pairs=(), allowed_links=None, limit=None):
    # Small catalogue: direct reductions avoid starting another BLAS thread pool.
    scores = SHAPE_WEIGHT * np.einsum("ij,j->i", gray_vectors, query_gray, optimize=False)
    scores += (1 - SHAPE_WEIGHT) * np.einsum("ij,j->i", rgb_vectors, query_rgb, optimize=False)
    for gray, rgb in extra_pairs:
        alternative = SHAPE_WEIGHT * np.einsum("ij,j->i", gray_vectors, gray, optimize=False)
        alternative += (1 - SHAPE_WEIGHT) * np.einsum("ij,j->i", rgb_vectors, rgb, optimize=False)
        scores = np.maximum(scores, alternative)
    if not np.isfinite(scores).all():
        raise SearchUnavailable("图片相似度计算未完成，请稍后重试")
    scores = np.clip(scores, -1, 1)
    matches = {}
    for item, score in zip(entries, scores.tolist()):
        for rid in item["record_ids"]:
            # Filter individual links BEFORE collapsing a record to its best
            # image. An internal best match must not suppress an approved one.
            if allowed_links is not None and (rid, item["path"]) not in allowed_links:
                continue
            result = {"record_id": rid, "image_path": item["path"], "score": round(float(score), 6)}
            if rid not in matches or result["score"] > matches[rid]["score"]:
                matches[rid] = result
    results = sorted(matches.values(), key=lambda item: (-item["score"], item["record_id"]))
    return results if limit is None else results[:max(0, min(MAX_SEARCH_RESULTS, limit))]


class ImageSearchService:
    def __init__(self, private):
        self.private = Path(private)
        self.directory = self.private / "image-search"
        self.gate = threading.Lock()
        self.available = False
        self.failure_reason = ""
        self.entries = []
        self.record_count = 0
        try:
            self._load()
            self.available = True
        except Exception as error:
            # A broken optional feature must not prevent catalogue/login startup.
            self.failure_reason = type(error).__name__ + ": " + str(error)

    def _load(self):
        np, _, _, _ = _dependencies()
        metadata_file = self.directory / "index.json"
        array_file = self.directory / "index.npz"
        if metadata_file.stat().st_size > 16 * 1024 * 1024 or array_file.stat().st_size > MAX_INDEX_BYTES:
            raise ValueError("Visual index is too large")
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        expected_source = collect_images(self.private)
        expected_model = model_manifest(self.directory / "model")
        if metadata.get("schema_version") != SCHEMA_VERSION or metadata.get("source") != expected_source or metadata.get("model") != expected_model:
            raise ValueError("Visual index is stale; rebuild required")
        if metadata.get("fingerprint") != canonical_hash({"source": expected_source, "model": expected_model}):
            raise ValueError("Visual index fingerprint mismatch")
        if metadata.get("arrays_sha256") != sha256(array_file):
            raise ValueError("Visual index data checksum mismatch")
        # Reject compressed archive bombs and Python object arrays before loading.
        with zipfile.ZipFile(array_file) as archive:
            if set(archive.namelist()) != {"gray.npy", "rgb.npy"} or sum(info.file_size for info in archive.infolist()) > MAX_INDEX_BYTES:
                raise ValueError("Invalid visual index archive")
        with np.load(array_file, allow_pickle=False) as arrays:
            gray, rgb = arrays["gray"].copy(), arrays["rgb"].copy()
        entries = metadata.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValueError("Visual index has no usable images")
        source_map = {item["path"]: item for item in expected_source["images"]}
        seen = set()
        for item in entries:
            if not isinstance(item, dict) or item != source_map.get(item.get("path")) or item["path"] in seen:
                raise ValueError("Invalid image-to-record mapping")
            seen.add(item["path"])
        dimension = int(metadata["dimension"])
        if dimension < 1 or dimension > 2048 or gray.shape != (len(entries), dimension) or rgb.shape != gray.shape:
            raise ValueError("Visual index dimensions do not match")
        for vectors in (gray, rgb):
            if vectors.dtype != np.float32 or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
                raise ValueError("Invalid normalized visual vectors")
            vectors.flags.writeable = False
        embedder = Embedder(self.directory / "model")
        if embedder.dimension != dimension:
            raise ValueError("Model and visual index dimensions differ")
        self.np, self.entries, self.gray, self.rgb, self.embedder = np, entries, gray, rgb, embedder
        self.record_count = len({rid for item in entries for rid in item["record_ids"]})

    def status(self):
        result = {"available": self.available, "indexed_images": len(self.entries),
                  "indexed_records": self.record_count, "model": "DINOv2-small · 瓶型结构优先"}
        if not self.available:
            result["message"] = UNAVAILABLE_MESSAGE
        return result

    def search_request(self, read_body, allowed_links=None, packages_only=False):
        if not self.available:
            raise SearchUnavailable(UNAVAILABLE_MESSAGE)
        # Acquire before reading/decompressing uploads, rather than queueing RAM-heavy requests.
        if not self.gate.acquire(blocking=False):
            raise SearchBusy("图片检索正在处理另一张图片，请稍后重试")
        try:
            data = read_body()
            if not isinstance(data, dict) or set(data) != {"image"}:
                raise ValueError("请仅提交要检索的图片")
            image = decode_upload(data["image"])
            try:
                pairs = list(query_pairs(self.embedder, image))
            except Exception as error:
                raise SearchUnavailable("图片分析暂时未完成，请稍后重试") from error
            finally:
                image.close()
            links = allowed_links() if callable(allowed_links) else allowed_links
            return {"matches": rank_matches(self.np, self.entries, self.gray, self.rgb, *pairs[0],
                                             extra_pairs=pairs[1:], allowed_links=links,
                                             limit=MAX_SEARCH_RESULTS),
                    "indexed_images": len(self.entries), "indexed_records": self.record_count}
        finally:
            self.gate.release()


def build_index(private, progress=None):
    """Build offline. Replacing either index file mid-deploy fails closed on restart."""
    np, _, _, _ = _dependencies()
    private = Path(private).resolve()
    directory = private / "image-search"
    directory.mkdir(parents=True, exist_ok=True)
    source = collect_images(private)
    model = model_manifest(directory / "model")
    embedder = Embedder(directory / "model")
    entries, gray, rgb, excluded = [], [], [], []
    for number, item in enumerate(source["images"], 1):
        try:
            path = private / item["path"]
            if path.stat().st_size > MAX_SOURCE_IMAGE_BYTES:
                raise ValueError("Source image exceeds size limit")
            image = decode_image(path.read_bytes(), max_bytes=MAX_SOURCE_IMAGE_BYTES, max_pixels=MAX_SOURCE_PIXELS)
            try:
                gv, rv = embedder.pair(image)
            finally:
                image.close()
            entries.append(item)
            gray.append(gv)
            rgb.append(rv)
        except ValueError as error:
            excluded.append({"path": item["path"], "reason": str(error)})
        if progress:
            progress(number, len(source["images"]), len(entries))
    if not entries:
        raise ValueError("No usable package images found")
    # Check sources have not changed while the long offline build was running.
    if source != collect_images(private) or model != model_manifest(directory / "model"):
        raise ValueError("Sources changed during index build; rerun the build")
    arrays_temp = directory / "index.npz.tmp"
    with arrays_temp.open("wb") as output:
        np.savez(output, gray=np.stack(gray), rgb=np.stack(rgb))
    metadata = {"schema_version": SCHEMA_VERSION, "source": source, "model": model,
                "fingerprint": canonical_hash({"source": source, "model": model}),
                "dimension": embedder.dimension, "entries": entries, "excluded": excluded,
                "arrays_sha256": sha256(arrays_temp)}
    metadata_temp = directory / "index.json.tmp"
    metadata_temp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(arrays_temp, directory / "index.npz")
    os.replace(metadata_temp, directory / "index.json")
    return {"indexed_images": len(entries), "indexed_records": len({rid for item in entries for rid in item["record_ids"]}),
            "excluded_images": len(excluded), "fingerprint": metadata["fingerprint"]}
