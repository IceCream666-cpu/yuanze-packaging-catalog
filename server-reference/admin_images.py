"""Bounded administrator uploads and a live mapping over the private visual index.

The immutable shipped catalogue/index is never edited. Only administrator product
images are persisted; search query images remain in memory. One shared gate bounds
upload decoding, embedding queries and incremental index work on the small server.
"""
import io
from contextlib import contextmanager
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import threading
import time
import uuid
import zipfile
from search_views import reviewed_search_views, validated_crop

from image_search import (
    ALLOWED_ROLES, MAX_INDEX_BYTES, MAX_SOURCE_IMAGE_BYTES, MAX_SOURCE_PIXELS,
    SearchBusy, SearchUnavailable, UNAVAILABLE_MESSAGE,
    decode_image, decode_upload, model_manifest, rank_matches, sha256,
    query_pairs, MAX_SEARCH_RESULTS,
)

UPLOAD_NAME = re.compile(r"uploads/[0-9a-f]{32}\.jpg\Z")
INDEX_CHECKPOINT_IMAGES = 64


class UploadManager:
    def __init__(self, state, gate=None):
        self.state = Path(state).resolve()
        self.directory = self.state / "uploads"
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database = self.state / "admin_uploads.sqlite"
        self.gate = gate if gate is not None else threading.Lock()
        with self._connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS uploads (path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.database, timeout=10)
        try:
            db.execute("PRAGMA busy_timeout=10000")
            with db:
                yield db
        finally:
            db.close()

    def _safe_path(self, path):
        if not isinstance(path, str) or not UPLOAD_NAME.fullmatch(path):
            return None
        target = self.state / path
        # A generated filename may never become a symlink outside the upload root.
        if target.is_symlink() or not target.resolve().is_relative_to(self.directory.resolve()):
            return None
        return target

    def resolve(self, path):
        target = self._safe_path(path)
        if target is None or not target.is_file():
            return None
        with self._connection() as db:
            row = db.execute("SELECT 1 FROM uploads WHERE path=?", (path,)).fetchone()
        return target if row else None

    def is_registered(self, path):
        return self.resolve(path) is not None

    def save_request(self, read_body):
        if not self.gate.acquire(blocking=False):
            raise SearchBusy("正在处理图片，请稍后再上传")
        try:
            body = read_body()
            if not isinstance(body, dict) or set(body) != {"image"}:
                raise ValueError("请仅提交要上传的图片")
            return self._save(body["image"])
        finally:
            self.gate.release()

    def save(self, image):
        return self.save_request(lambda: {"image": image})

    def _save(self, value):
        image = decode_upload(value)
        try:
            from PIL import Image
            image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            # Fresh encoding strips EXIF, filenames and other supplied metadata.
            output = io.BytesIO()
            image.save(output, "JPEG", quality=90, optimize=True)
        finally:
            image.close()
        path = "uploads/" + uuid.uuid4().hex + ".jpg"
        target = self._safe_path(path)
        try:
            with target.open("xb") as stream:
                os.chmod(target, 0o600)
                stream.write(output.getvalue())
            with self._connection() as db:
                db.execute("INSERT INTO uploads(path,sha256) VALUES(?,?)", (path, sha256(target)))
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return {"path": path, "role": "product", "caption": "", "imageScope": "single_product"}


class ManagedImageSearch:
    """Reuse one model and image vectors while resolving current record links.

    Metadata edits and record archives only change links, never the model/vector
    cache. An older background job may add a reusable image vector, but cannot
    publish old catalogue links: every status/search reads the latest catalogue.
    """
    def __init__(self, base_service, state, private, catalog_provider, upload_manager=None):
        self.base = base_service
        self.gate = base_service.gate
        self.state = Path(state).resolve()
        self.private = Path(private).resolve()
        self.directory = self.state / "image-search"
        self.catalog_provider = catalog_provider
        self.uploads = upload_manager or UploadManager(state, self.gate)
        self.lock = threading.RLock()
        self.cache = {}
        self.base_keys = set()
        self.hash_cache = {}
        self.failures = {}
        self.worker = None
        self.building = False
        self.generation = 0
        self.failure_reason = ""
        self.closed = False
        self.model = None
        if self.base.available:
            self.np = self.base.np
            self.model = model_manifest(self.private / "image-search" / "model")
            for index, item in enumerate(self.base.entries):
                source = self._resolve(item["path"])
                if source is None:
                    continue
                digest = item.get("sha256") or sha256(source)
                key = self._key(source, digest)
                self.cache[key] = (self.base.gray[index], self.base.rgb[index])
                self.base_keys.add(key)
            self._load_cache()
            self.request_reindex()

    @staticmethod
    def _key(source, digest, crop=None):
        key = (str(source.resolve()), digest)
        return key + (tuple(crop),) if crop is not None else key

    def _resolve(self, name):
        if not isinstance(name, str):
            return None
        if name.startswith("uploads/"):
            return self.uploads.resolve(name)
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or not name.startswith("media/"):
            return None
        source = self.private / name
        if source.is_symlink() or not source.resolve().is_relative_to((self.private / "media").resolve()):
            return None
        return source.resolve() if source.is_file() else None

    def _hash(self, source):
        stat = source.stat()
        stamp = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        name = str(source)
        with self.lock:
            cached = self.hash_cache.get(name)
        if cached and cached[0] == stamp:
            return cached[1]
        value = sha256(source)
        with self.lock:
            self.hash_cache[name] = (stamp, value)
        return value

    def _snapshot(self):
        catalog = self.catalog_provider()
        records = catalog.get("records", []) if isinstance(catalog, dict) else catalog
        package_ids = {record.get('id') for record in records
                       if record.get('kind') == 'package' and not record.get('archived')}
        by_path = {}
        for record in records:
            if record.get("archived") or record.get("kind") not in ("package", "source_page"):
                continue
            rid = record.get("id")
            if not isinstance(rid, str) or not rid:
                continue
            for image in record.get("images", []):
                if image.get("missing") or image.get("uncertain") or image.get("role") not in ALLOWED_ROLES:
                    continue
                if record.get("kind") == "package" and (
                    image.get("imageScope") in {"source_page", "unresolved"}
                    or image.get("mapping") == "pdf-page-preview"
                ):
                    continue
                name = image.get("path")
                if not isinstance(name, str):
                    continue
                if name in by_path:
                    by_path[name]["record_ids"].add(rid)
                    continue
                source = self._resolve(name)
                if source is None:
                    continue
                try:
                    digest = self._hash(source)
                except OSError:
                    continue
                by_path[name] = {"path": name, "record_ids": {rid}, "sha256": digest,
                                 "source": source, "key": self._key(source, digest)}
        result = [{**item, "record_ids": sorted(item["record_ids"])}
                  for _, item in sorted(by_path.items())]
        # These code-owned reviews distinguish e.g. a bottle from a jar in the
        # same brochure photo. They do not approve any image for customers.
        for view in reviewed_search_views(self.private.parent / 'public', records):
            source = self._resolve(view['path'])
            native = self._resolve(view['review_native_path'])
            if source is None:
                continue
            try:
                digest = self._hash(source)
                expected_display = view.get('display_sha256')
                if expected_display is not None and digest != expected_display:
                    continue
                if native is None:
                    # Some brochures ship only their audited WebP derivative.
                    # An exact code-owned native/derivative hash pair is required;
                    # missing originals never permit guessed associations.
                    if expected_display is None:
                        continue
                elif self._hash(native) != view['review_sha256']:
                    continue
            except OSError:
                continue
            result.append({**view, 'source': source, 'sha256': digest,
                           'key': self._key(source, digest, view['crop'])})
        for item in result:
            item['package_record_ids'] = [rid for rid in item['record_ids'] if rid in package_ids]
        return result

    def _ready(self, snapshot):
        with self.lock:
            return [(item, self.cache[item["key"]]) for item in snapshot if item["key"] in self.cache]

    def status(self):
        if not self.base.available:
            return {"available": False, "state": "unavailable", "indexed_images": 0,
                    "indexed_records": 0, "pending_images": 0, "building": False,
                    "message": UNAVAILABLE_MESSAGE}
        snapshot = self._snapshot()
        ready = self._ready(snapshot)
        with self.lock:
            failed = sum(item["key"] in self.failures for item in snapshot)
            building = self.building
            failure_reason = self.failure_reason
        pending = len(snapshot) - len(ready)
        state = "building" if building else "error" if failed or failure_reason else "pending" if pending else "ready"
        result = {"available": bool(ready), "state": state, "indexed_images": len(ready),
                  "indexed_records": len({rid for item, _ in ready for rid in item["record_ids"]}),
                  "pending_images": pending, "failed_images": failed, "building": building,
                  "model": "DINOv2-small · 瓶型结构优先"}
        if pending:
            result["message"] = "新增图片正在加入检索；已完成的图片可正常检索。" if building else "部分图片尚未加入检索，可在管理后台重试。"
        elif failure_reason:
            result["message"] = "图片检索缓存未能保存，请重试建立索引；已完成的图片仍可检索。"
        elif not ready:
            result["message"] = "暂无可检索的包材图片，请先添加产品图片。"
        return result

    def search_request(self, read_body, allowed_links=None, packages_only=False):
        if not self.base.available or not self._ready(self._snapshot()):
            raise SearchUnavailable(UNAVAILABLE_MESSAGE)
        if not self.gate.acquire(blocking=False):
            raise SearchBusy("图片检索正在处理图片，请稍后重试")
        try:
            data = read_body()
            if not isinstance(data, dict) or set(data) != {"image"}:
                raise ValueError("请仅提交要检索的图片")
            image = decode_upload(data["image"])
            try:
                pairs = list(query_pairs(self.base.embedder, image))
            except Exception as error:
                raise SearchUnavailable("图片分析暂时未完成，请稍后重试") from error
            finally:
                image.close()
            # Read links after the slower image embedding, so an archive/unlink
            # during inference is effective before this request returns results.
            ready = self._ready(self._snapshot())
            if packages_only:
                ready = [({**item, 'record_ids': item['package_record_ids']}, pair)
                         for item, pair in ready if item['package_record_ids']]
            if not ready:
                return {"matches": [], "indexed_images": 0, "indexed_records": 0}
            entries = [{"path": item["path"], "record_ids": item["record_ids"]} for item, _ in ready]
            gray = self.np.stack([pair[0] for _, pair in ready])
            rgb = self.np.stack([pair[1] for _, pair in ready])
            links = allowed_links() if callable(allowed_links) else allowed_links
            matches = rank_matches(self.np, entries, gray, rgb, *pairs[0],
                                   extra_pairs=pairs[1:], allowed_links=links,
                                   limit=MAX_SEARCH_RESULTS)
            return {"matches": matches, "indexed_images": len(entries),
                    "indexed_records": len({rid for item in entries for rid in item["record_ids"]})}
        finally:
            self.gate.release()

    def refresh(self):
        return self.request_reindex()

    def request_reindex(self):
        if not self.base.available:
            return self.status()
        with self.lock:
            if self.closed:
                return self.status()
            self.generation += 1
            self.failures.clear()
            self.failure_reason = ""
            if not self.building:
                self.building = True
                self.worker = threading.Thread(target=self._build_pending, name="package-image-index", daemon=True)
                self.worker.start()
        return self.status()

    def close(self, timeout=10):
        with self.lock:
            self.closed = True
            worker = self.worker
        if worker and worker is not threading.current_thread():
            worker.join(timeout)

    def _build_pending(self):
        unsaved = 0
        try:
            while True:
                with self.lock:
                    generation = self.generation
                    if self.closed:
                        break
                # Read the catalogue once per generation, not once per image (or
                # while waiting for the model gate). A large import is one queue.
                snapshot = self._snapshot()
                with self.lock:
                    if generation != self.generation:
                        continue
                    pending = [item for item in snapshot if item["key"] not in self.cache and item["key"] not in self.failures]
                refresh_snapshot = False
                for item in pending:
                    # Waiting must not repeatedly scan thousands of records.
                    while True:
                        with self.lock:
                            interrupted = self.closed or generation != self.generation
                        if interrupted or self.gate.acquire(timeout=0.2):
                            break
                    if interrupted:
                        break
                    try:
                        # A refresh/close may arrive as acquire() succeeds.
                        with self.lock:
                            interrupted = self.closed or generation != self.generation
                        if interrupted:
                            break
                        if self._hash(item["source"]) != item["sha256"]:
                            refresh_snapshot = True
                            break
                        if item["source"].stat().st_size > MAX_SOURCE_IMAGE_BYTES:
                            raise ValueError("Source image exceeds size limit")
                        image = decode_image(item["source"].read_bytes(), max_bytes=MAX_SOURCE_IMAGE_BYTES,
                                             max_pixels=MAX_SOURCE_PIXELS)
                        try:
                            crop = item.get('crop')
                            if crop is None:
                                gray, rgb = self.base.embedder.pair(image)
                            else:
                                if image.size != tuple(crop[4:]):
                                    raise ValueError('Reviewed image dimensions changed')
                                width, height = image.size
                                box = (round(crop[0]*width), round(crop[1]*height),
                                       round((crop[0]+crop[2])*width), round((crop[1]+crop[3])*height))
                                if min(box[2]-box[0], box[3]-box[1]) < 16:
                                    raise ValueError('Reviewed product crop is too small')
                                with image.crop(box) as focused:
                                    gray, rgb = self.base.embedder.pair(focused)
                        finally:
                            image.close()
                        # Never cache a vector under a hash from a replaced file.
                        if self._hash(item["source"]) != item["sha256"]:
                            refresh_snapshot = True
                            break
                        for vector in (gray, rgb):
                            vector.flags.writeable = False
                        with self.lock:
                            self.cache[item["key"]] = (gray, rgb)
                        unsaved += 1
                    except Exception as error:
                        with self.lock:
                            if generation == self.generation:
                                self.failures[item["key"]] = type(error).__name__
                    finally:
                        # Checkpoints and the rest of the batch never hold this
                        # shared gate: interactive uploads/search get a turn.
                        self.gate.release()
                    if unsaved >= INDEX_CHECKPOINT_IMAGES:
                        self._save_cache()
                        unsaved = 0
                    time.sleep(0.025)
                with self.lock:
                    if self.closed:
                        break
                    if generation != self.generation or refresh_snapshot:
                        continue
                if unsaved:
                    self._save_cache()
                    unsaved = 0
                with self.lock:
                    # A mutation during the checkpoint must start another batch;
                    # idle publication is atomic with request_reindex's wakeup.
                    if self.closed:
                        break
                    if generation != self.generation:
                        continue
                    self.building = False
                    return
            # Graceful shutdown preserves already computed vectors, even if this
            # batch has fewer images than the periodic checkpoint interval.
            if unsaved:
                self._save_cache()
        except Exception as error:
            with self.lock:
                self.failure_reason = type(error).__name__ + ": " + str(error)
        finally:
            with self.lock:
                if self.worker is threading.current_thread():
                    self.building = False

    def _save_cache(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        entries, gray, rgb = [], [], []
        for key, pair in sorted(self.cache.items()):
            if key in self.base_keys:
                continue
            source = Path(key[0])
            if source.is_relative_to(self.state / "uploads"):
                name = "uploads/" + source.name
            elif source.is_relative_to(self.private / "media"):
                name = "media/" + str(source.relative_to(self.private / "media"))
            else:
                continue
            entry = {"path": name, "sha256": key[1]}
            if len(key) == 3:
                entry['crop'] = key[2]
            entries.append(entry)
            gray.append(pair[0])
            rgb.append(pair[1])
        dimension = self.base.embedder.dimension
        arrays_temp = self.directory / "index.npz.tmp"
        metadata_temp = self.directory / "index.json.tmp"
        with arrays_temp.open("wb") as stream:
            os.chmod(arrays_temp, 0o600)
            self.np.savez(stream, gray=self.np.stack(gray) if gray else self.np.empty((0, dimension), dtype="float32"),
                          rgb=self.np.stack(rgb) if rgb else self.np.empty((0, dimension), dtype="float32"))
        metadata = {"version": 2, "model": self.model, "dimension": dimension, "entries": entries,
                    "arrays_sha256": sha256(arrays_temp)}
        metadata_temp.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        os.chmod(metadata_temp, 0o600)
        os.replace(arrays_temp, self.directory / "index.npz")
        os.replace(metadata_temp, self.directory / "index.json")

    def _load_cache(self):
        metadata_file, array_file = self.directory / "index.json", self.directory / "index.npz"
        if not metadata_file.exists() or not array_file.exists():
            return
        try:
            if metadata_file.stat().st_size > 16 * 1024 * 1024 or array_file.stat().st_size > MAX_INDEX_BYTES:
                raise ValueError("Dynamic visual index is too large")
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            if metadata.get("version") not in (1, 2) or metadata.get("model") != self.model or metadata.get("arrays_sha256") != sha256(array_file):
                raise ValueError("Dynamic visual index version/checksum mismatch")
            entries, dimension = metadata["entries"], metadata["dimension"]
            if not isinstance(entries, list) or dimension != self.base.embedder.dimension:
                raise ValueError("Invalid dynamic index shape")
            with zipfile.ZipFile(array_file) as archive:
                if set(archive.namelist()) != {"gray.npy", "rgb.npy"} or sum(info.file_size for info in archive.infolist()) > MAX_INDEX_BYTES:
                    raise ValueError("Invalid dynamic index archive")
            with self.np.load(array_file, allow_pickle=False) as arrays:
                gray, rgb = arrays["gray"].copy(), arrays["rgb"].copy()
            for vectors in (gray, rgb):
                if vectors.shape != (len(entries), dimension) or vectors.dtype != self.np.float32 or not self.np.isfinite(vectors).all() or not self.np.allclose(self.np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
                    raise ValueError("Invalid dynamic index vectors")
                vectors.flags.writeable = False
            accepted = {}
            for index, item in enumerate(entries):
                crop = validated_crop(item.get('crop')) if 'crop' in item else None
                if 'crop' in item and (metadata['version'] != 2 or crop is None):
                    raise ValueError('Invalid cached product crop')
                source = self._resolve(item["path"])
                if source and self._hash(source) == item["sha256"]:
                    accepted[self._key(source, item["sha256"], crop)] = (gray[index], rgb[index])
            self.cache.update(accepted)
        except Exception:
            # Immutable vectors still work; corrupt/stale additions are rebuilt.
            return
