import base64
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import image_search as search
import test_http

try:
    import numpy as np
    from PIL import Image
except ImportError:
    np = Image = None


def png(color="white", size=(40, 80)):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, "PNG")
    return output.getvalue()


def upload(binary=None, mime="image/png"):
    return "data:" + mime + ";base64," + base64.b64encode(binary or png()).decode()


class FakeEmbedder:
    dimension = 2

    def __init__(self, *args):
        pass

    def pair(self, image):
        vector = np.asarray([1.0, 0.0], dtype="float32")
        return vector, vector


def ready_service():
    service = search.ImageSearchService.__new__(search.ImageSearchService)
    service.available = True
    service.gate = threading.Lock()
    service.np = np
    service.embedder = FakeEmbedder()
    service.entries = [{"path": "media/a.png", "record_ids": ["R1", "R2"]},
                       {"path": "media/b.png", "record_ids": ["R1", "R3"]}]
    service.gray = np.asarray([[1, 0], [0, 1]], dtype="float32")
    service.rgb = np.asarray([[1, 0], [0, 1]], dtype="float32")
    service.record_count = 3
    return service


@unittest.skipUnless(np is not None and Image is not None, "Optional image dependencies required")
class Images(unittest.TestCase):
    def test_upload_validates_contents_not_just_extension(self):
        with search.decode_upload(upload()) as image:
            self.assertEqual(image.size, (40, 80))
        for value in [upload(mime="image/jpeg"), "data:image/png;base64,%%%%", upload(b"not a picture"),
                      "https://external.example/image.png", upload(png(size=(4, 4)))]:
            with self.subTest(value=value[:45]), self.assertRaises(ValueError):
                search.decode_upload(value)

    def test_rejects_decompression_and_file_size_limits(self):
        # Small compressed data must still be rejected before full raster decoding.
        with patch.object(search, "MAX_PIXELS", 100), self.assertRaises(ValueError):
            search.decode_upload(upload())
        with patch.object(search, "MAX_IMAGE_BYTES", 3), self.assertRaises(ValueError):
            search.decode_image(png())
        # A tiny PNG can claim a very large raster. Inspect headers and reject it
        # before Pillow allocates the full image on the small production server.
        import struct
        import zlib
        binary = png()
        payload = struct.pack(">IIBBBBB", 5000, 4000, 8, 2, 0, 0, 0)
        ihdr = struct.pack(">I", len(payload)) + b"IHDR" + payload + struct.pack(">I", zlib.crc32(b"IHDR" + payload))
        pathological = binary[:8] + ihdr + binary[33:]
        with self.assertRaisesRegex(ValueError, "400 万"):
            search.decode_image(pathological)

    def test_grayscale_match_outweighs_color_and_shared_image_maps_all_rows(self):
        entries = [{"path": "media/shape.png", "record_ids": ["shape", "shared"]},
                   {"path": "media/color.png", "record_ids": ["color", "shared"]}]
        gray = np.asarray([[1, 0], [0, 1]], dtype="float32")
        rgb = np.asarray([[0, 1], [1, 0]], dtype="float32")
        query = np.asarray([1, 0], dtype="float32")
        result = search.rank_matches(np, entries, gray, rgb, query, query)
        self.assertEqual([item["record_id"] for item in result], ["shape", "shared", "color"])
        self.assertEqual(result[1]["image_path"], "media/shape.png")
        self.assertEqual(len(result), 3)  # shared row appears once, using its best image.

    def test_busy_and_unavailable_requests_do_not_read_upload(self):
        service = ready_service()
        service.gate.acquire()
        try:
            with self.assertRaises(search.SearchBusy):
                service.search_request(lambda: self.fail("busy requests must not read bodies"))
        finally:
            service.gate.release()
        service.available = False
        with self.assertRaises(search.SearchUnavailable):
            service.search_request(lambda: self.fail("unavailable requests must not read bodies"))

    def test_bad_query_does_not_poison_next_search(self):
        service = ready_service()
        with self.assertRaises(ValueError):
            service.search_request(lambda: {"image": "broken"})
        result = service.search_request(lambda: {"image": upload()})
        self.assertEqual(len(result["matches"]), 3)
        self.assertEqual(result["indexed_images"], 2)
        self.assertEqual(result["indexed_records"], 3)


@unittest.skipUnless(np is not None and Image is not None, "Optional image dependencies required")
class IndexIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.private = Path(self.temp.name)
        (self.private / "media").mkdir()
        for name in ("a.png", "b.png", "unconfirmed.png"):
            (self.private / "media" / name).write_bytes(png())
        self.records = [
            {"id": "R1", "kind": "package", "images": [
                {"path": "media/a.png", "role": "supplier"},
                {"path": "media/b.png", "role": "inquiry"},
                {"path": "../outside.png", "role": "supplier"}]},
            {"id": "R2", "kind": "package", "images": [
                {"path": "media/a.png", "role": "product"},
                {"path": "media/unconfirmed.png", "role": "supplier", "uncertain": True},
                {"path": "media/unconfirmed.png", "role": "other"}]},
            {"id": "service", "kind": "service", "images": [{"path": "media/a.png", "role": "product"}]}]
        self.catalog = self.private / "catalog.json"
        self.catalog.write_text(json.dumps({"records": self.records}))
        model = self.private / "image-search" / "model"
        model.mkdir(parents=True)
        for name in ("model.onnx", "config.json", "preprocessor_config.json"):
            (model / name).write_bytes(b"fixture")
        self.patch = patch.object(search, "Embedder", FakeEmbedder)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        # Inference is mocked above; index integrity still uses real NumPy/Pillow.
        dependencies = patch.object(search, "_dependencies", return_value=(np, Image, None, None))
        dependencies.start()
        self.addCleanup(dependencies.stop)

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_index_build_preserves_all_confirmed_mappings_only(self):
        result = search.build_index(self.private)
        self.assertEqual((result["indexed_images"], result["indexed_records"]), (2, 2))
        service = search.ImageSearchService(self.private)
        self.assertTrue(service.available, service.failure_reason)
        self.assertEqual(service.entries[0]["record_ids"], ["R1", "R2"])
        self.assertNotIn("service", str(service.entries))

    def test_changed_catalog_image_or_model_fails_closed(self):
        search.build_index(self.private)
        for path in [self.catalog, self.private / "media/a.png", self.private / "image-search/model/model.onnx"]:
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            service = search.ImageSearchService(self.private)
            self.assertFalse(service.available)
            self.assertEqual(service.status()["indexed_images"], 0)
            path.write_bytes(original)
        self.assertTrue(search.ImageSearchService(self.private).available)

    def test_corrupt_array_and_tampered_mapping_fail_closed(self):
        search.build_index(self.private)
        array = self.private / "image-search/index.npz"
        original = array.read_bytes()
        array.write_bytes(original[:-10])
        self.assertFalse(search.ImageSearchService(self.private).available)
        array.write_bytes(original)
        metadata_file = self.private / "image-search/index.json"
        metadata = json.loads(metadata_file.read_text())
        metadata["entries"][0]["record_ids"].append("unauthorized-row")
        metadata_file.write_text(json.dumps(metadata))
        self.assertFalse(search.ImageSearchService(self.private).available)

    def test_missing_optional_dependency_does_not_break_startup(self):
        with patch.object(search, "_dependencies", side_effect=ImportError("not installed")):
            service = search.ImageSearchService(self.private)
            self.assertFalse(service.available)
            self.assertIn("message", service.status())


@unittest.skipUnless(np is not None and Image is not None, "Optional image dependencies required")
class SearchHTTP(unittest.TestCase):
    req = test_http.HTTP.req
    login = test_http.HTTP.login

    def setUp(self):
        self.service = ready_service()
        self.mock = patch.object(test_http.server, "ImageSearchService", return_value=self.service)
        self.mock.start()
        self.addCleanup(self.mock.stop)
        # Exercise the HTTP contract without constructing a dynamic model worker.
        managed_mock = patch.object(test_http.server, "ManagedImageSearch", return_value=self.service)
        managed_mock.start()
        self.addCleanup(managed_mock.stop)
        test_http.HTTP.setUp(self)
        # These HTTP tests exercise the static search contract with a controlled
        # mapping. Dynamic catalogue reconciliation has its own test suite.
        managed = test_http.server.IMAGE_SEARCH
        if hasattr(managed, "close"):
            managed.close()
        test_http.server.IMAGE_SEARCH = self.service

    def tearDown(self):
        test_http.HTTP.tearDown(self)
        self.mock.stop()

    def test_auth_and_csrf_happen_before_upload_read(self):
        with patch.object(test_http.server.Handler, "body", side_effect=AssertionError("body read before auth")):
            self.assertEqual(self.req("/api/image-search", {"image": upload()})[0], 401)
        self.assertEqual(self.req("/api/image-search/status")[0], 401)
        self.login()
        with patch.object(test_http.server.Handler, "body", side_effect=AssertionError("body read before CSRF")):
            self.assertEqual(self.req("/api/image-search", {"image": upload()}, csrf=False)[0], 403)

    def test_search_returns_ranked_all_records_and_status(self):
        self.login()
        status = self.req("/api/image-search/status")[2]
        self.assertTrue(status["available"])
        code, _, data = self.req("/api/image-search", {"image": upload()})
        self.assertEqual(code, 200)
        self.assertEqual([row["record_id"] for row in data["matches"]], ["R1", "R2", "R3"])
        self.assertEqual(self.req("/api/image-search", {"image": "bad"})[0], 400)

    def test_busy_unavailable_and_origin_fail_with_clear_status(self):
        self.login()
        self.service.gate.acquire()
        try:
            code, headers, _ = self.req("/api/image-search", {"image": upload()})
            self.assertEqual(code, 429)
            self.assertEqual(headers["Retry-After"], "2")
        finally:
            self.service.gate.release()
        self.service.available = False
        self.assertEqual(self.req("/api/image-search", {"image": upload()})[0], 503)
        with patch.object(test_http.server.Handler, "valid_origin", return_value=False):
            self.assertEqual(self.req("/api/image-search", {"image": upload()})[0], 403)


if __name__ == "__main__":
    unittest.main()
