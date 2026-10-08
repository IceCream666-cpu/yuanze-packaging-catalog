import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from admin_store import AdminStore, AdminError, ConflictError


PASSWORD = 'test-admin-pass-2026'


def credentials(username, password=PASSWORD):
    salt = 'ab' * 16
    return {'username': username, 'salt': salt, 'iterations': 100000,
            'hash': hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 100000).hex()}


class AdminStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name) / 'state'
        self.private = Path(self.temp.name) / 'private'
        self.state.mkdir()
        (self.private / 'media').mkdir(parents=True)
        (self.private / 'media/photo.jpg').write_bytes(b'fixture')
        self.base = {'meta': {'sourceFile': 'original.xlsx'}, 'records': [
            {'id': 'ORIGINAL-1', 'name': '原始产品', 'kind': 'package',
             'source': {'workbook': 'original.xlsx', 'sheet': '瓶', 'row': 4},
             'rawCells': {'A': 'original'}, 'supplierRaw': '原始供应商',
             'images': [{'path': 'media/photo.jpg', 'role': 'product', 'missing': False}]}
        ]}
        (self.state / 'admin-bootstrap.json').write_text(json.dumps(credentials('admin')))
        self.store = AdminStore(self.state, self.private, credentials('yuanze'), self.base)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, resource, data, action='save', actor='admin'):
        return self.store.mutate(resource, action, data, actor)

    def test_migration_accounts_and_no_reseed_or_secret_exports(self):
        self.assertEqual(self.store.authenticate('yuanze', PASSWORD)['role'], 'employee')
        self.assertEqual(self.store.authenticate('admin', PASSWORD)['role'], 'admin')
        self.assertIsNone(self.store.authenticate('missing', PASSWORD))
        self.assertIsNone(self.store.authenticate('admin', 'wrong'))
        self.save('records', {'id': 'ORIGINAL-1', 'version': 1, 'name': '已更新'})
        again = AdminStore(self.state, self.private, credentials('yuanze'), self.base)
        self.assertEqual(again.read_admin('records', 'ORIGINAL-1')['name'], '已更新')
        self.assertEqual(again.export()['originalRecords']['ORIGINAL-1']['name'], '原始产品')
        exported = json.dumps(again.export())
        for forbidden in ('"hash"', '"salt"', '"password"', PASSWORD):
            self.assertNotIn(forbidden, exported)

    def test_record_conflict_restore_and_original_provenance(self):
        self.save('records', {'id': 'ORIGINAL-1', 'version': 1, 'name': '改一版', 'materials': ['PET'], 'capacityMl': 50})
        with self.assertRaises(ConflictError):
            self.save('records', {'id': 'ORIGINAL-1', 'version': 1, 'name': '不能覆盖'})
        with self.assertRaises(AdminError):
            self.save('records', {'id': 'ORIGINAL-1', 'version': 2, 'source': {'workbook': '伪造'}})
        self.assertEqual(self.store.read_admin('records', 'ORIGINAL-1')['version'], 2)
        initial = next(r for r in self.store.read_admin('audit') if r['action'] == 'initial')
        restored = self.save('records', {'id': 'ORIGINAL-1', 'version': 2, 'revision': initial['id']}, 'restore')
        self.assertEqual(restored['version'], 3)
        self.assertEqual(restored['name'], '原始产品')
        # Restore is a full historical replacement, including removal of newer classification.
        self.assertNotIn('materials', restored)
        self.save('records', {'id': 'ORIGINAL-1', 'version': 3}, 'archive')
        self.assertEqual(self.store.catalog()['records'], [])
        self.save('records', {'id': 'ORIGINAL-1', 'version': 4}, 'unarchive')
        self.assertEqual(len(self.store.catalog()['records']), 1)

    def test_body_areas_are_optional_validated_deduplicated_and_preserved(self):
        original = self.store.read_admin('records', 'ORIGINAL-1')
        self.assertNotIn('bodyAreas', original)
        unchanged = self.save('records', {'id': original['id'], 'version': original['version'],
                                          'record': {'name': original['name']}})
        self.assertNotIn('bodyAreas', unchanged)
        tagged = self.save('records', {'id': original['id'], 'version': unchanged['version'],
                                      'record': {'bodyAreas': ['body', 'face', 'body']}})
        self.assertEqual(tagged['bodyAreas'], ['body', 'face'])
        self.assertEqual(tagged['productCode'], original['productCode'])
        excluded = {'bodyAreas', 'version', 'updated'}
        self.assertEqual({key: value for key, value in unchanged.items() if key not in excluded},
                         {key: value for key, value in tagged.items() if key not in excluded})
        edited = self.save('records', {'id': original['id'], 'version': tagged['version'],
                                      'record': {'name': '普通编辑保留护理部位'}})
        self.assertEqual(edited['bodyAreas'], ['body', 'face'])
        all_areas = self.save('records', {'id': original['id'], 'version': edited['version'],
                                         'record': {'bodyAreas': ['face', 'body', 'head']}})
        self.assertEqual(all_areas['bodyAreas'], ['face', 'body', 'head'])
        cleared = self.save('records', {'id': original['id'], 'version': all_areas['version'],
                                       'record': {'bodyAreas': []}})
        self.assertEqual(cleared['bodyAreas'], [])
        again = AdminStore(self.state, self.private, credentials('yuanze'), self.base)
        self.assertEqual(again.read_admin('records', original['id'])['bodyAreas'], [])

    def test_invalid_body_areas_reject_without_partial_write(self):
        original = self.store.read_admin('records', 'ORIGINAL-1')
        for value in (None, 'face', {'face': True}, ['Face'], ['body-head'], ['face '],
                      [True], [None], [{}], [['face']], ['face', 'body', 'head', 'face']):
            with self.subTest(value=value):
                with self.assertRaises(AdminError) as rejected:
                    self.save('records', {'id': original['id'], 'version': original['version'],
                                          'record': {'name': '无效写入', 'bodyAreas': value}})
                self.assertEqual(rejected.exception.status, 400)
                self.assertEqual(self.store.read_admin('records', original['id']), original)

    def test_body_areas_stay_out_of_client_projection(self):
        from client_catalog import project_record
        before = self.store.read_admin('records', 'ORIGINAL-1')
        after = self.save('records', {'id': before['id'], 'version': before['version'],
                                     'record': {'bodyAreas': ['face', 'head']}})
        self.assertEqual(project_record(after, after['productCode']),
                         project_record(before, before['productCode']))
        self.assertNotIn('bodyAreas', project_record(after, after['productCode']))

    def test_image_only_update_preserves_all_other_fields_and_checks_version(self):
        before = self.store.read_admin('records', 'ORIGINAL-1')
        images = [{**before['images'][0], 'caption': '原图保留'}]
        after = self.save('records', {'id': before['id'], 'version': before['version'], 'images': images}, 'images')
        excluded = {'images', 'version', 'updated'}
        self.assertEqual({k: v for k, v in before.items() if k not in excluded},
                         {k: v for k, v in after.items() if k not in excluded})
        self.assertEqual(after['version'], before['version'] + 1)
        self.assertEqual(after['images'][0]['caption'], '原图保留')
        with self.assertRaises(ConflictError):
            self.save('records', {'id': before['id'], 'version': before['version'], 'images': images}, 'images')
        with self.assertRaises(AdminError):
            self.save('records', {'id': before['id'], 'version': after['version'], 'images': images, 'quoteRaw': '改价'}, 'images')
        with self.assertRaises(AdminError):
            self.save('records', {'id': before['id'], 'version': after['version']}, 'images')
        self.assertEqual(self.store.read_admin('records', before['id']), after)

    def test_specification_override_tracks_explicit_field_changes_and_persists(self):
        record = self.store.read_admin('records', 'ORIGINAL-1')
        self.assertNotIn('specificationOverride', record)
        for changes in ({'name': '仅改名称'}, {'quoteRaw': '新报价'}, {'bodyAreas': ['body']},
                        {'specificationRaw': '', 'capacityMl': None}):
            record = self.save('records', {'id': record['id'], 'version': record['version'], 'record': changes})
            self.assertNotIn('specificationOverride', record)
        record = self.save('records', {'id': record['id'], 'version': record['version'],
                                      'record': {'capacityMl': 30}})
        self.assertEqual(record['specificationOverride'], {'label': '30 mL', 'sourceField': 'capacityMl'})
        record = self.save('records', {'id': record['id'], 'version': record['version'],
                                      'record': {'specificationRaw': '50-15g'}})
        self.assertEqual(record['specificationOverride'], {'label': '50-15g', 'sourceField': 'specificationRaw'})
        self.assertEqual(record['capacityMl'], 30)  # Original numeric evidence is retained.
        record = self.save('records', {'id': record['id'], 'version': record['version'],
                                      'record': {'capacityMl': 80.125}})
        self.assertEqual(record['specificationOverride'], {'label': '80.125 mL', 'sourceField': 'capacityMl'})
        unchanged = self.save('records', {'id': record['id'], 'version': record['version'], 'record': record})
        self.assertEqual(unchanged['specificationOverride'], record['specificationOverride'])
        after_image = self.save('records', {'id': record['id'], 'version': unchanged['version'],
                                           'images': unchanged['images']}, 'images')
        self.assertEqual(after_image['specificationOverride'], record['specificationOverride'])
        again = AdminStore(self.state, self.private, credentials('yuanze'), self.base)
        self.assertEqual(again.read_admin('records', record['id'])['specificationOverride'], record['specificationOverride'])
        from client_catalog import project_record
        self.assertNotIn('specificationOverride', project_record(after_image, after_image['productCode']))

    def test_specification_override_cannot_be_forged_and_is_absent_on_create(self):
        before = self.store.read_admin('records', 'ORIGINAL-1')
        forged = {'label': '999 mL', 'sourceField': 'capacityMl'}
        for changes in ({'specificationOverride': forged}, {'capacityMl': 50, 'specificationOverride': forged}):
            with self.assertRaises(AdminError):
                self.save('records', {'id': before['id'], 'version': before['version'], 'record': changes})
            self.assertEqual(self.store.read_admin('records', before['id']), before)
        with self.assertRaises(AdminError):
            self.save('records', {'version': 0, 'record': {'name': '伪造新产品', 'specificationOverride': forged}})
        created = self.save('records', {'version': 0, 'record': {'name': '新增产品', 'capacityMl': 50, 'specificationRaw': '50 mL'}})
        self.assertNotIn('specificationOverride', created)

    def test_specification_override_clear_and_restoring_history_do_not_reuse_stale_labels(self):
        record = self.save('records', {'id': 'ORIGINAL-1', 'version': 1,
                                      'record': {'capacityMl': 30, 'specificationRaw': '30 mL'}})
        initial = next(item for item in self.store.read_admin('audit') if item['action'] == 'initial')
        revised = next(item for item in self.store.read_admin('audit') if item['action'] == 'save')
        record = self.save('records', {'id': record['id'], 'version': record['version'], 'record': {'specificationRaw': ''}})
        self.assertEqual(record['specificationOverride'], {'label': '规格待补充', 'sourceField': 'specificationRaw'})
        self.assertEqual(record['capacityMl'], 30)
        record = self.save('records', {'id': record['id'], 'version': record['version'], 'record': {'capacityMl': None}})
        self.assertEqual(record['specificationOverride'], {'label': '规格待补充', 'sourceField': 'capacityMl'})
        restored = self.save('records', {'id': record['id'], 'version': record['version'], 'revision': revised['id']}, 'restore')
        self.assertEqual(restored['specificationOverride'], {'label': '30 mL', 'sourceField': 'specificationRaw'})
        restored = self.save('records', {'id': record['id'], 'version': restored['version'], 'revision': initial['id']}, 'restore')
        self.assertNotIn('specificationOverride', restored)
        self.assertNotIn('capacityMl', restored)

    def test_simultaneous_specification_fields_require_compatible_explicit_capacity(self):
        before = self.store.read_admin('records', 'ORIGINAL-1')
        for raw, capacity in (('80 mL', 30), ('30g', 30), ('50-15g', 50), ('30/50ml', 50),
                              ('30ml / 50ml', 30), ('容量待确认', 30), ('1L', 500)):
            with self.subTest(raw=raw, capacity=capacity):
                payload = {'id': before['id'], 'version': before['version'],
                           'record': {'specificationRaw': raw, 'capacityMl': capacity}}
                with self.assertRaises(AdminError):
                    self.save('records', payload)
                self.assertFalse(self.store.bulk_preview([payload])['valid'])
                self.assertEqual(self.store.read_admin('records', before['id']), before)
        record = self.save('records', {'id': before['id'], 'version': before['version'],
                                      'record': {'specificationRaw': '容量：８０ ｍＬ；口径24mm', 'capacityMl': 80}})
        self.assertEqual(record['specificationOverride']['sourceField'], 'specificationRaw')
        record = self.save('records', {'id': record['id'], 'version': record['version'],
                                      'record': {'specificationRaw': '1L', 'capacityMl': 1000}})
        self.assertEqual(record['specificationOverride']['label'], '1L')
        record = self.save('records', {'id': record['id'], 'version': record['version'],
                                      'record': {'specificationRaw': '50-15g', 'capacityMl': None}})
        self.assertEqual(record['specificationOverride']['label'], '50-15g')
        preview = self.store.bulk_preview([{'id': record['id'], 'version': record['version'],
                                          'record': {'specificationRaw': '60 mL', 'capacityMl': 60}}])
        self.assertTrue(preview['valid'], preview['errors'])
        saved = self.store.bulk_save(preview['rows'], 'admin')['records'][0]
        self.assertEqual(saved['specificationOverride'], {'label': '60 mL', 'sourceField': 'specificationRaw'})

    def test_uploaded_image_keeps_reference_scope_and_cannot_promote_original_page(self):
        path = 'uploads/' + 'a' * 32 + '.jpg'
        (self.state / 'uploads').mkdir(exist_ok=True)
        (self.state / path).write_bytes(b'fixture')
        self.store.register_upload(path, 'admin')
        for scope in ('single_product', 'same_style_variants', 'source_page', 'unresolved'):
            with self.store.connection() as c:
                image = self.store._images(c, [{'path': path, 'imageScope': scope}])[0]
            self.assertEqual(image['imageScope'], scope)
            self.assertFalse(image['clientVisible'])
        with self.store.connection() as c:
            with self.assertRaises(AdminError):
                self.store._images(c, [{'path': path, 'imageScope': 'not-a-scope'}])
            original = self.store._images(c, [{'path': 'media/photo.jpg', 'imageScope': 'single_product'}])[0]
            self.assertNotEqual(original.get('imageScope'), 'single_product')

    def test_atomic_bulk_preview_freezes_versions_and_create(self):
        preview = self.store.bulk_preview([
            {'id': 'ORIGINAL-1', 'version': 1, 'quoteRaw': '1.20'},
            {'name': '新瓶', 'capacityMl': 50, 'materials': ['玻璃']},
        ])
        self.assertTrue(preview['valid'])
        self.assertEqual(preview['updateCount'], 1)
        self.assertEqual(preview['createCount'], 1)
        self.assertEqual(preview['rows'][0]['version'], 1)
        self.save('records', {'id': 'ORIGINAL-1', 'version': 1, 'name': '其他人先改'})
        with self.assertRaises(ConflictError):
            self.store.bulk_save(list(reversed(preview['rows'])), 'admin')
        self.assertEqual(len(self.store.catalog()['records']), 1)
        preview = self.store.bulk_preview([{'id': 'ORIGINAL-1', 'version': 2, 'quoteRaw': '1.20'}, {'name': '新瓶'}])
        result = self.store.bulk_save(preview['rows'], 'admin')
        self.assertEqual(result['count'], 2)
        self.assertEqual(self.store.read_admin('records', 'ORIGINAL-1')['name'], '其他人先改')
        self.assertEqual(len(self.store.catalog()['records']), 2)
        invalid = self.store.bulk_preview([{'name': 'invalid', 'capacityMl': float('nan')}])
        self.assertFalse(invalid['valid'])

    def test_bulk_update_requires_the_exported_version(self):
        preview = self.store.bulk_preview([{'id': 'ORIGINAL-1', 'quoteRaw': '9.90'}])
        self.assertFalse(preview['valid'])
        self.assertEqual(preview['rows'], [])
        self.assertIn('版本', preview['errors'][0]['error'])
        self.assertEqual(self.store.read_admin('records', 'ORIGINAL-1')['version'], 1)
        # A new record still needs no version, and an update with the version
        # taken from the export is accepted.
        mixed = self.store.bulk_preview([
            {'name': '新增瓶', 'capacityMl': 30},
            {'id': 'ORIGINAL-1', 'version': 1, 'quoteRaw': '9.90'},
        ])
        self.assertTrue(mixed['valid'])
        self.assertEqual([r['version'] for r in mixed['rows']], [0, 1])
        self.assertEqual(self.store.bulk_save(mixed['rows'], 'admin')['count'], 2)
        self.assertEqual(self.store.read_admin('records', 'ORIGINAL-1')['version'], 2)

    def test_legacy_slash_record_id_remains_editable(self):
        with self.store.connection(True) as c:
            c.execute('INSERT INTO admin_records VALUES(?,?,?,?,?,?,?)',
                      ('验收/001', json.dumps({'name': '旧记录'}), json.dumps({'name': '旧记录'}), 1, 0, '2026-09-24', '2026-09-24'))
        result = self.save('records', {'id': '验收/001', 'version': 1, 'name': '可以继续维护'})
        self.assertEqual(result['id'], '验收/001')
        self.assertEqual(result['version'], 2)
        with self.assertRaises(AdminError):
            self.save('records', {'id': '新/记录', 'version': 0, 'name': '不能新建斜杠编号'})
        with self.assertRaises(AdminError):
            self.store.read_admin('records', '新/记录')
        preview = self.store.bulk_preview([{'id': '验收/001', 'version': 2, 'name': '批量更新旧编号'}])
        self.assertTrue(preview['valid'], preview['errors'])
        self.store.bulk_save(preview['rows'], 'admin')
        self.assertEqual(self.store.read_admin('records', '验收/001')['version'], 3)

    def test_account_security_last_admin_and_sessions_version(self):
        with self.assertRaises(AdminError):
            self.save('users', {'id': 'admin', 'version': 1, 'active': False})
        with self.assertRaises(AdminError):
            self.save('users', {'id': 'admin', 'version': 1, 'role': 'employee'})
        with self.assertRaises(AdminError) as denied:
            self.save('settings', {'version': 1, 'value': {'announcement': '不允许'}}, actor='yuanze')
        self.assertEqual(denied.exception.status, 403)
        self.save('users', {'id': 'second-admin', 'version': 0, 'role': 'admin', 'password': PASSWORD})
        disabled = self.save('users', {'id': 'admin', 'version': 1, 'active': False}, actor='second-admin')
        self.assertEqual(disabled['auth_version'], 2)
        self.assertIsNone(self.store.authenticate('admin', PASSWORD))
        previous = self.store.get_user('yuanze')
        result = self.save('users', {'id': 'yuanze', 'version': 1, 'password': 'replacement-pass-2026'}, actor='second-admin')
        self.assertEqual(result['auth_version'], previous['auth_version'] + 1)
        self.assertIsNone(self.store.authenticate('yuanze', PASSWORD))
        self.assertIsNotNone(self.store.authenticate('yuanze', 'replacement-pass-2026'))

    def test_only_trusted_and_registered_images_are_accepted(self):
        for path in ('../../auth.json', 'media/../secret.png', 'https://example.test/photo.jpg', 'uploads/' + 'a' * 32 + '.jpg'):
            with self.assertRaises(AdminError):
                self.save('records', {'id': 'ORIGINAL-1', 'version': 1, 'images': [{'path': path}]})
        path = 'uploads/' + 'a' * 32 + '.jpg'
        (self.state / 'uploads').mkdir()
        (self.state / path).write_bytes(b'validated upstream')
        uploaded = self.store.register_upload(path, 'admin')
        result = self.save('records', {'id': 'ORIGINAL-1', 'version': 1, 'images': [uploaded]})
        self.assertEqual(result['images'][0]['path'], path)

    def test_samples_and_plans_keep_history_and_legacy_columns(self):
        with self.store.connection() as c:
            c.execute('INSERT INTO plans VALUES(?,?,?,?,?,?)', ('PLAN-1', 'yuanze', '旧标题', '', '[{"name":"当时产品"}]', '2026-09-24'))
        result = self.save('plans', {'id': 'PLAN-1', 'version': 1, 'title': '新标题'})
        self.assertEqual(result['snapshot'][0]['name'], '当时产品')
        with self.assertRaises(AdminError):
            self.save('plans', {'id': 'PLAN-1', 'version': 2, 'snapshot': []})
        self.save('samples', {'id': 'SAMPLE-1', 'version': 0, 'record_id': 'ORIGINAL-1', 'location': 'A1', 'condition': '完好'})
        self.save('samples', {'id': 'SAMPLE-1', 'version': 1, 'status': 'lent', 'borrower': '小王', 'due': '2026-10-01'})
        with self.assertRaises(AdminError):
            self.save('samples', {'id': 'SAMPLE-1', 'version': 2, 'status': 'available'})
        self.save('samples', {'id': 'SAMPLE-1', 'version': 2, 'status': 'available', 'borrower': '', 'due': ''})
        self.save('samples', {'id': 'SAMPLE-1', 'version': 3}, 'archive')
        with self.store.connection() as c:
            self.assertEqual(len(c.execute('PRAGMA table_info(samples)').fetchall()), 8)
            self.assertEqual(len(c.execute('PRAGMA table_info(plans)').fetchall()), 6)
            self.assertEqual(c.execute('SELECT count(*) FROM movements').fetchone()[0], 4)
        self.assertTrue(self.store.read_admin('samples')[0]['archived'])

    def test_legacy_slash_identifier_remains_editable(self):
        with self.store.connection() as c:
            c.execute('INSERT INTO samples VALUES(?,?,?,?,?,?,?,?)',
                      ('验收/001', 'ORIGINAL-1', 'A1', 'available', '', '', '完好', '2026-09-24'))
        result = self.save('samples', {'id': '验收/001', 'version': 1, 'location': 'B2'})
        self.assertEqual(result['location'], 'B2')

    def test_legacy_multiple_image_roles_and_empty_quote_header(self):
        record = self.store.read_admin('records', 'ORIGINAL-1')
        record['quoteHeader'] = None
        record['images'] = [
            {'path': 'media/photo.jpg', 'role': 'inquiry'},
            {'path': 'media/photo.jpg', 'role': 'floating-reference'},
        ]
        result = self.save('records', {'id': 'ORIGINAL-1', 'version': 1, 'record': record})
        self.assertEqual(len(result['images']), 2)
        self.assertEqual(result['quoteHeader'], '')
        self.assertFalse(self.store.bulk_preview([{'record': []}])['valid'])
        with self.assertRaises(AdminError):
            self.store.bulk_save([{'record': []}], 'admin')

    def test_export_includes_complete_audit_and_no_credentials(self):
        with self.store.connection(True) as c:
            for index in range(1001):
                self.store._audit(c, 'records', 'ORIGINAL-1', 'fixture', 'admin', None, {'index': index})
        self.assertEqual(len(self.store.read_admin('audit')), 1000)
        self.assertEqual(len(self.store.export()['audit']), 1001)

    def test_settings_taxonomy_persist_and_validate(self):
        value = self.save('settings', {'version': 1, 'value': {'companyName': '源泽公司', 'processReference': '丝印仅供参考', 'showBusinessDemo': False}})
        self.assertEqual(value['version'], 2)
        with self.assertRaises(ConflictError):
            self.save('settings', {'version': 1, 'value': {'companyName': '覆盖'}})
        self.save('taxonomy', {'version': 1, 'value': {'materials': ['玻璃', '玻璃', 'PET']}})
        self.assertEqual(self.store.catalog()['taxonomy']['materials'], ['玻璃', 'PET'])
        self.assertEqual(self.store.catalog()['settings']['processReference'], '丝印仅供参考')


if __name__ == '__main__':
    unittest.main()
