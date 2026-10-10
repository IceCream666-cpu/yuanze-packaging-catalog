import base64
import copy
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import admin_images
import image_search

try:
    import numpy as np
    from PIL import Image
except ImportError:
    np = Image = None


def upload(color="red", size=(60, 120)):
    output = io.BytesIO()
    image = Image.new("RGB", size, color)
    exif = Image.Exif()
    exif[270] = "private camera metadata"
    image.save(output, "JPEG", exif=exif)
    return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode()


class FakeEmbedder:
    dimension = 2
    calls = 0

    def pair(self, image):
        self.calls += 1
        vector = np.array([1, 0], dtype="float32")
        return vector.copy(), vector.copy()


@unittest.skipUnless(np is not None and Image is not None, "Optional image dependencies required")
class Uploads(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name)
        self.manager = admin_images.UploadManager(self.state)

    def tearDown(self):
        self.temp.cleanup()

    def test_registered_upload_is_resized_encoded_and_metadata_removed(self):
        result = self.manager.save(upload(size=(1800, 1800)))
        self.assertRegex(result["path"], r"^uploads/[a-f0-9]{32}\.jpg$")
        self.assertTrue(self.manager.is_registered(result["path"]))
        path = self.manager.resolve(result["path"])
        with Image.open(path) as image:
            self.assertEqual(image.size, (1600, 1600))
            self.assertEqual(image.format, "JPEG")
            self.assertFalse(image.getexif())
        reopened = admin_images.UploadManager(self.state)
        self.assertEqual(reopened.resolve(result["path"]), path)

    def test_fake_paths_unregistered_files_and_symlinks_rejected(self):
        path = "uploads/" + "a" * 32 + ".jpg"
        (self.state / path).write_bytes(b"unregistered")
        for value in (path, "../outside", "/tmp/a.jpg", "uploads/../../a.jpg", "uploads/a.png", None):
            self.assertIsNone(self.manager.resolve(value))
        result = self.manager.save(upload())
        target = self.manager.resolve(result["path"])
        target.unlink()
        target.symlink_to(self.state / path)
        self.assertIsNone(self.manager.resolve(result["path"]))

    def test_gate_precedes_body_read_and_invalid_upload_leaves_no_file(self):
        self.manager.gate.acquire()
        try:
            with self.assertRaises(image_search.SearchBusy):
                self.manager.save_request(lambda: self.fail("busy upload body read"))
        finally:
            self.manager.gate.release()
        with self.assertRaises(ValueError):
            self.manager.save("data:image/jpeg;base64,abcd")
        self.assertEqual(list((self.state / "uploads").iterdir()), [])
        self.assertTrue(self.manager.save(upload()))


@unittest.skipUnless(np is not None and Image is not None, "Optional image dependencies required")
class DynamicIndex(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.private, self.state = self.root / "private", self.root / "state"
        (self.private / "media").mkdir(parents=True)
        Image.new("RGB", (60, 120), "red").save(self.private / "media/base.jpg")
        model = self.private / "image-search/model"
        model.mkdir(parents=True)
        for name in ("model.onnx", "config.json", "preprocessor_config.json"):
            (model / name).write_text("fixture")
        self.base = image_search.ImageSearchService.__new__(image_search.ImageSearchService)
        self.base.available = True
        self.base.gate = threading.Lock()
        self.base.np = np
        self.base.embedder = FakeEmbedder()
        self.base.entries = [{"path": "media/base.jpg", "record_ids": ["base"],
                              "sha256": image_search.sha256(self.private / "media/base.jpg")}]
        self.base.gray = np.array([[1, 0]], dtype="float32")
        self.base.rgb = self.base.gray.copy()
        self.records = [{"id": "base", "kind": "package", "images": [{"path": "media/base.jpg", "role": "product"}]}]
        self.uploads = admin_images.UploadManager(self.state, self.base.gate)
        self.services = []
        self.service = self.new_service()
        self.wait_done()

    def new_service(self):
        service = admin_images.ManagedImageSearch(self.base, self.state, self.private,
            lambda: {"records": copy.deepcopy(self.records)}, self.uploads)
        self.services.append(service)
        return service

    def tearDown(self):
        for service in self.services:
            service.close()
        self.temp.cleanup()

    def wait_done(self, service=None):
        service = service or self.service
        deadline = time.monotonic() + 5
        while service.building and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(service.building, "background index did not finish")

    def add_uploaded_record(self):
        image = self.uploads.save(upload("blue"))
        self.records.append({"id": "new", "kind": "package", "images": [image]})
        self.service.refresh()
        self.wait_done()
        return image

    def add_media_batch(self, count, prefix="batch"):
        records = []
        for index in range(count):
            name = f"media/{prefix}-{index}.jpg"
            Image.new("RGB", (60, 120), (index, 30, 80)).save(self.private / name)
            records.append({"id": f"{prefix}-{index}", "kind": "source_page",
                            "images": [{"path": name, "role": "product"}]})
        self.records.extend(records)
        return records

    def test_catalogue_pages_and_unresolved_images_cannot_rank_as_products(self):
        path = "media/base.jpg"
        self.records = [
            {"id": "single", "kind": "package", "images": [{"path": path, "role": "product", "imageScope": "single_product"}]},
            {"id": "series", "kind": "package", "images": [{"path": path, "role": "product", "imageScope": "same_style_variants"}]},
            {"id": "grid", "kind": "package", "images": [{"path": path, "role": "product", "imageScope": "source_page"}]},
            {"id": "unclear", "kind": "package", "images": [{"path": path, "role": "product", "imageScope": "unresolved"}]},
            {"id": "old-grid", "kind": "package", "images": [{"path": path, "role": "product", "mapping": "pdf-page-preview"}]},
            {"id": "archive-page", "kind": "source_page", "images": [{"path": path, "role": "product", "imageScope": "source_page"}]},
        ]
        snapshot = self.service._snapshot()
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0]["record_ids"], ["archive-page", "series", "single"])

    def test_metadata_edits_and_shared_image_links_need_no_new_embeddings(self):
        self.records[0]["price"] = "changed"
        self.records.append({"id": "shared", "kind": "package", "images": copy.deepcopy(self.records[0]["images"])})
        self.service.refresh()
        self.wait_done()
        self.assertEqual(self.base.embedder.calls, 0)
        result = self.service.search_request(lambda: {"image": upload()})
        self.assertEqual({item["record_id"] for item in result["matches"]}, {"base", "shared"})
        self.assertEqual(result["indexed_images"], 1)
        self.assertEqual(result["indexed_records"], 2)

    def test_reviewed_bottle_and_jar_views_use_separate_vectors_and_survive_restart(self):
        path = self.private / 'media/series.jpg'
        with Image.new('RGB', (80, 120), 'red') as image:
            image.paste('blue', (40, 0, 80, 120))
            image.save(path)
        self.records.extend([{'id': rid, 'kind': 'package', 'images': []}
                             for rid in ['bottle', 'jar']])
        views = [dict(path='media/series.jpg', record_ids=['bottle'],
                      crop=(0., 0., .5, 1., 80, 120)),
                 dict(path='media/series.jpg', record_ids=['jar'],
                      crop=(.5, 0., .5, 1., 80, 120))]
        for view in views:
            view.update(review_native_path='media/series.jpg', review_sha256=image_search.sha256(path))

        def color_pair(image):
            r, _, b = image.getpixel((image.width//2, image.height//2))
            vector = np.array([1, 0] if r > b else [0, 1], dtype='float32')
            return vector.copy(), vector.copy()

        with patch.object(admin_images, 'reviewed_search_views', return_value=views), \
             patch.object(self.base.embedder, 'pair', side_effect=color_pair):
            self.service.refresh()
            self.wait_done()
            self.assertEqual(self.service.status()['indexed_images'], 3)
            red = self.service.search_request(lambda: {'image': upload('red')})
            blue = self.service.search_request(lambda: {'image': upload('blue')})
            self.assertLess([m['record_id'] for m in red['matches']].index('bottle'),
                            [m['record_id'] for m in red['matches']].index('jar'))
            self.assertEqual(blue['matches'][0]['record_id'], 'jar')
            self.service.close()
            restarted = self.new_service()
            self.wait_done(restarted)
            self.assertEqual(restarted.status()['pending_images'], 0)
            self.assertEqual(restarted.search_request(lambda: {'image': upload('blue')})['matches'][0]['record_id'], 'jar')
            # Removing a review link takes effect immediately, not after cache
            # deletion or another full model/index rebuild.
            with patch.object(admin_images, 'reviewed_search_views', return_value=views[:1]):
                self.assertNotIn('jar', {x['record_id'] for x in restarted.search_request(
                    lambda: {'image': upload('blue')})['matches']})

    def test_changed_review_native_hash_removes_crop_links_without_losing_ordinary_images(self):
        native = self.private / 'media/brochure-original.jp2'
        original = b'Native brochure encoding used only for audit hashing.'
        native.write_bytes(original)
        self.records.append({'id': 'reviewed', 'kind': 'package', 'images': []})
        views = [dict(path='media/base.jpg', record_ids=['reviewed'],
                      crop=(0., 0., .5, 1., 60, 120),
                      review_native_path='media/brochure-original.jp2',
                      review_sha256=image_search.sha256(native))]
        with patch.object(admin_images, 'reviewed_search_views', return_value=views):
            self.service.refresh()
            self.wait_done()
            calls = self.base.embedder.calls
            self.assertEqual(self.service.status()['indexed_images'], 2)
            self.assertEqual(self.service.status()['indexed_records'], 2)
            # Revoking the review evidence must invalidate its association even
            # while its previously computed crop vector remains cached.
            native.write_bytes(b'A different brochure photograph.')
            snapshot = self.service._snapshot()
            self.assertEqual([(item['path'], item['record_ids']) for item in snapshot],
                             [('media/base.jpg', ['base'])])
            self.assertEqual(self.service.status()['state'], 'ready')
            self.assertEqual(self.service.status()['indexed_images'], 1)
            result = self.service.search_request(lambda: {'image': upload()})
            self.assertEqual([item['record_id'] for item in result['matches']], ['base'])
            # Restoring the exact reviewed native bytes reuses the cached crop;
            # normal metadata/evidence checks never run another indexing job.
            after_query = self.base.embedder.calls
            self.assertGreater(after_query, calls)
            native.write_bytes(original)
            self.assertEqual(self.service.status()['indexed_images'], 2)
            self.assertEqual(self.base.embedder.calls, after_query)
            native.unlink()
            self.assertEqual(self.service.status()['indexed_images'], 1)

    def test_legacy_v1_dynamic_cache_restarts_without_embedding_or_rebuilding(self):
        self.add_uploaded_record()
        self.service.close()
        metadata_path = self.state / 'image-search/index.json'
        metadata = json.loads(metadata_path.read_text())
        self.assertTrue(metadata['entries'])
        self.assertTrue(all('crop' not in item for item in metadata['entries']))
        # v1 stores the same original-image vectors but predates crop identities.
        metadata['version'] = 1
        metadata_path.write_text(json.dumps(metadata))
        before_metadata = metadata_path.read_bytes()
        before_arrays = image_search.sha256(self.state / 'image-search/index.npz')
        calls = self.base.embedder.calls
        with patch.object(self.base.embedder, 'pair', side_effect=AssertionError('Unexpected v1 rebuild')) as pair:
            restarted = self.new_service()
            self.wait_done(restarted)
            pair.assert_not_called()
            status = restarted.status()
            self.assertEqual((status['state'], status['indexed_images'], status['indexed_records'],
                              status['pending_images'], status['failed_images']), ('ready', 2, 2, 0, 0))
        self.assertEqual(self.base.embedder.calls, calls)
        self.assertEqual(metadata_path.read_bytes(), before_metadata)
        self.assertEqual(image_search.sha256(self.state / 'image-search/index.npz'), before_arrays)
        self.assertEqual({item['record_id'] for item in restarted.search_request(
            lambda: {'image': upload()})['matches']}, {'base', 'new'})

    def test_client_allowed_links_are_read_after_inference_and_before_ranking(self):
        image = self.add_uploaded_record()
        events = []
        original_pair = self.base.embedder.pair
        def pair(query):
            events.append('inference')
            return original_pair(query)
        def allowed():
            self.assertIn('inference', events)
            return {('new', image['path'])}
        with patch.object(self.base.embedder, 'pair', side_effect=pair):
            result = self.service.search_request(lambda: {'image': upload()}, allowed_links=allowed)
        self.assertEqual([x['record_id'] for x in result['matches']], ['new'])
        self.assertEqual(self.service.search_request(lambda: {'image': upload()},
                                                    allowed_links=lambda: set())['matches'], [])

    def test_brochure_pages_cannot_consume_packaging_candidate_slots(self):
        self.records.extend([{'id': f'PAGE{i:03d}', 'kind': 'source_page',
                              'images': copy.deepcopy(self.records[0]['images'])}
                             for i in range(600)])
        all_results = self.service.search_request(lambda: {'image': upload()})
        self.assertEqual(len(all_results['matches']), image_search.MAX_SEARCH_RESULTS)
        package_results = self.service.search_request(lambda: {'image': upload()}, packages_only=True)
        self.assertEqual([item['record_id'] for item in package_results['matches']], ['base'])

    def test_archive_and_unlink_take_effect_without_reindex(self):
        self.records[0]["archived"] = True
        self.assertEqual(self.service.status()["indexed_records"], 0)
        with self.assertRaises(image_search.SearchUnavailable):
            self.service.search_request(lambda: self.fail("no active images"))
        self.records[0]["archived"] = False
        self.records[0]["images"] = []
        self.assertEqual(self.service.status()["indexed_images"], 0)

    def test_new_upload_joins_results_and_persistent_vectors_survive_restart(self):
        image = self.add_uploaded_record()
        self.assertEqual(self.base.embedder.calls, 1)
        self.assertEqual(self.service.status()["indexed_records"], 2)
        result = self.service.search_request(lambda: {"image": upload()})
        self.assertEqual({item["record_id"] for item in result["matches"]}, {"base", "new"})
        self.assertEqual(next(item["image_path"] for item in result["matches"] if item["record_id"] == "new"), image["path"])
        self.service.close()
        calls = self.base.embedder.calls
        restarted = self.new_service()
        self.wait_done(restarted)
        self.assertEqual(self.base.embedder.calls, calls)
        self.assertEqual(restarted.status()["indexed_images"], 2)

    def test_removed_record_during_build_cannot_be_reintroduced(self):
        image = self.uploads.save(upload("blue"))
        self.records.append({"id": "new", "kind": "package", "images": [image]})
        entered, resume = threading.Event(), threading.Event()
        original_pair = self.base.embedder.pair
        def slow_pair(image):
            entered.set()
            self.assertTrue(resume.wait(3))
            return original_pair(image)
        with patch.object(self.base.embedder, "pair", side_effect=slow_pair):
            self.service.refresh()
            self.assertTrue(entered.wait(3))
            self.records.pop()
            self.service.refresh()
            resume.set()
            self.wait_done()
        result = self.service.search_request(lambda: {"image": upload()})
        self.assertEqual([item["record_id"] for item in result["matches"]], ["base"])

    def test_archive_during_query_embedding_is_applied_before_results(self):
        self.records.append({"id": "shared", "kind": "package", "images": copy.deepcopy(self.records[0]["images"])})
        original_pair = self.base.embedder.pair
        def archive_while_query(image):
            self.records[0]["archived"] = True
            return original_pair(image)
        with patch.object(self.base.embedder, "pair", side_effect=archive_while_query):
            result = self.service.search_request(lambda: {"image": upload()})
        self.assertEqual([item["record_id"] for item in result["matches"]], ["shared"])

    def test_corrupt_saved_index_is_rebuilt_without_losing_original_results(self):
        self.add_uploaded_record()
        self.service.close()
        (self.state / "image-search/index.npz").write_bytes(b"invalid")
        calls = self.base.embedder.calls
        restarted = self.new_service()
        self.wait_done(restarted)
        self.assertEqual(self.base.embedder.calls, calls + 1)
        self.assertEqual(restarted.status()["indexed_images"], 2)

    def test_unregistered_and_unconfirmed_images_are_never_indexed(self):
        uploaded = self.uploads.save(upload())
        self.records.append({"id": "hidden", "kind": "package", "images": [
            {**uploaded, "uncertain": True}, {**uploaded, "role": "other"},
            {"path": "uploads/" + "a" * 32 + ".jpg", "role": "product"},
            {"path": "../outside.png", "role": "product"}]})
        self.records.append({"id": "service", "kind": "service", "images": [uploaded]})
        self.service.refresh()
        self.wait_done()
        self.assertEqual(self.base.embedder.calls, 0)
        self.assertEqual(self.service.status()["indexed_images"], 1)

    def test_pending_and_busy_are_truthful_and_do_not_read_query_body(self):
        uploaded = self.uploads.save(upload())
        self.records.append({"id": "new", "kind": "package", "images": [uploaded]})
        self.base.gate.acquire()
        try:
            self.service.refresh()
            status = self.service.status()
            self.assertTrue(status["building"])
            self.assertEqual(status["pending_images"], 1)
            self.assertEqual(status["indexed_images"], 1)
            with self.assertRaises(image_search.SearchBusy):
                self.service.search_request(lambda: self.fail("busy body read"))
        finally:
            self.base.gate.release()
        self.wait_done()
        self.assertEqual(self.service.status()["state"], "ready")

    def test_batch_scans_once_per_generation_and_checkpoints_without_model_gate(self):
        self.add_media_batch(12)
        save = self.service._save_cache
        checkpoints = []
        def checkpoint():
            self.assertFalse(self.base.gate.locked())
            checkpoints.append(self.base.embedder.calls)
            save()
        with patch.object(self.service, "_snapshot", wraps=self.service._snapshot) as snapshots, \
             patch.object(self.service, "_save_cache", side_effect=checkpoint), \
             patch.object(admin_images, "INDEX_CHECKPOINT_IMAGES", 4):
            self.service.refresh()
            self.wait_done()
            # One worker batch scan and request_reindex's public status scan.
            self.assertEqual(snapshots.call_count, 2)
        self.assertEqual(self.base.embedder.calls, 12)
        self.assertEqual(checkpoints, [4, 8, 12])
        metadata = json.loads((self.state / "image-search/index.json").read_text())
        self.assertEqual(len(metadata["entries"]), 12)
        self.assertEqual(self.service.status()["indexed_records"], 13)

    def test_new_generation_cancels_rest_of_old_queue_and_builds_new_queue(self):
        self.add_media_batch(3, "old")
        entered, resume = threading.Event(), threading.Event()
        original_pair = self.base.embedder.pair
        def first_slow(image):
            if not entered.is_set():
                entered.set()
                self.assertTrue(resume.wait(3))
            return original_pair(image)
        with patch.object(self.base.embedder, "pair", side_effect=first_slow):
            self.service.refresh()
            self.assertTrue(entered.wait(3))
            self.records[:] = self.records[:1]
            self.add_media_batch(1, "latest")
            self.service.refresh()
            resume.set()
            self.wait_done()
        self.assertEqual(self.base.embedder.calls, 2)
        result = self.service.search_request(lambda: {"image": upload()})
        self.assertEqual({item["record_id"] for item in result["matches"]}, {"base", "latest-0"})

    def test_close_preserves_partial_batch_and_does_not_process_remaining_queue(self):
        self.add_media_batch(4)
        original_pair = self.base.embedder.pair
        def close_after_first(image):
            # This models shutdown arriving during one image's inference.
            self.service.close()
            return original_pair(image)
        with patch.object(self.base.embedder, "pair", side_effect=close_after_first):
            self.service.refresh()
            self.wait_done()
        self.assertEqual(self.base.embedder.calls, 1)
        self.assertFalse(self.base.gate.locked())
        metadata = json.loads((self.state / "image-search/index.json").read_text())
        self.assertEqual(len(metadata["entries"]), 1)
        restarted = self.new_service()
        self.wait_done(restarted)
        self.assertEqual(self.base.embedder.calls, 4)
        self.assertEqual(restarted.status()["indexed_records"], 5)

    def test_source_replaced_during_embedding_rescans_without_wrong_hash_cache(self):
        record = self.add_media_batch(1)[0]
        path = self.private / record["images"][0]["path"]
        old_key = self.service._key(path, image_search.sha256(path))
        original_pair = self.base.embedder.pair
        def replace_once(image):
            if self.base.embedder.calls == 0:
                Image.new("RGB", (80, 120), "green").save(path)
            return original_pair(image)
        with patch.object(self.base.embedder, "pair", side_effect=replace_once):
            self.service.refresh()
            self.wait_done()
        self.assertEqual(self.base.embedder.calls, 2)
        self.assertNotIn(old_key, self.service.cache)
        self.assertIn(self.service._key(path, image_search.sha256(path)), self.service.cache)
        self.assertEqual(self.service.status()["pending_images"], 0)

    def test_gate_wait_does_not_rescan_batch_and_close_interrupts_wait(self):
        self.add_media_batch(2)
        self.base.gate.acquire()
        try:
            with patch.object(self.service, "_snapshot", wraps=self.service._snapshot) as snapshots:
                self.service.refresh()
                time.sleep(0.45)  # At least two bounded gate acquisition attempts.
                self.service.close(timeout=2)
                self.assertEqual(snapshots.call_count, 2)
                self.assertFalse(self.service.building)
                self.assertEqual(self.base.embedder.calls, 0)
        finally:
            self.base.gate.release()


if __name__ == "__main__":
    unittest.main()
