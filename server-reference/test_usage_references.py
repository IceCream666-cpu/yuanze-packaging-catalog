import base64
import csv
import io
import json
import unittest
from copy import deepcopy

from admin_imports import parse_import
from admin_store import AdminError, ConflictError
from client_catalog import ClientCatalog, facet_values, matches_search, project_record
from catalog_pages import internal_csv
import test_admin_store as fixture
from usage_references import reference_uses, SPECIAL_TUBE_USES, STRUCTURE_RULES


class StructureReferenceTests(unittest.TestCase):
    def test_explicit_types_and_normalized_aliases(self):
        for aliases, family, expected in STRUCTURE_RULES:
            for alias in aliases:
                with self.subTest(alias=alias):
                    self.assertEqual(reference_uses({'bottleType': f' {alias.upper()} '}), list(expected))
        self.assertEqual(reference_uses({'bottleType': 'ＡＩＲＬＥＳＳ'}), ['精华液', '乳液', '面霜'])

    def test_category_fallback_requires_absent_type_and_consistent_family(self):
        self.assertEqual(reference_uses({'category': '软管'}), ['洁面', '护手霜', '身体乳'])
        self.assertEqual(reference_uses({'category': '罐'}), ['面霜', '身体霜'])
        self.assertEqual(reference_uses({'category': '滴管'}), [])
        self.assertEqual(reference_uses({'category': '滴管', 'bottleType': '滴管瓶'}), ['精华液', '精油'])
        self.assertEqual(reference_uses({'category': '待细分', 'bottleType': '精油滴管瓶'}), ['精华液', '精油'])
        self.assertEqual(reference_uses({'category': '待细分', 'bottleType': '软管'}), ['洁面', '护手霜', '身体乳'])
        self.assertEqual(reference_uses({'category': '待细分'}), [])
        self.assertEqual(reference_uses({'category': '瓶', 'bottleType': '滴管瓶'}), ['精华液', '精油'])
        for record in ({'category': '罐', 'bottleType': '喷雾瓶'},
                       {'category': '瓶', 'bottleType': '膏霜罐'},
                       {'category': '软管', 'bottleType': '未知'},
                       {'category': '罐', 'bottleType': '膏霜瓶'}):
            self.assertEqual(reference_uses(record), [])

    def test_accessories_sets_mixed_and_generic_shapes_fail_closed(self):
        for category in ('泵头', '泵头与喷头', '盖子', '盖与配件', '套装', '套系', '其他', '瓶罐包材', '膏霜瓶/罐'):
            self.assertEqual(reference_uses({'category': category, 'bottleType': '软管'}), [])
        for kind in ('source_page', 'process_rule', 'semi_finished', 'service', 'requirement', 'uncertain'):
            self.assertEqual(reference_uses({'kind': kind, 'bottleType': '软管', 'referenceUses': ['洁面']}), [])
        for bottle_type in ('乳液泵', '压泵瓶', '洗护瓶', '套装瓶', '双层套装瓶', '圆瓶', '方瓶', '广口瓶',
                            '膏霜瓶', '软管/瓶', '滴管', '防晒软管', '唇彩软管', '滚珠软管', '泵式软管'):
            self.assertEqual(reference_uses({'bottleType': bottle_type}), [])

    def test_source_prose_names_and_free_text_never_supply_structure(self):
        record = {'name': '软管 香水瓶 滴管瓶', 'description': '真空瓶', 'rawCells': {'瓶型': '乳液瓶'},
                  'provenance': {'bottleType': '膏霜罐'}, 'source': {'workbook': '喷雾瓶'},
                  'productDetails': [{'label': '瓶型', 'value': '泡沫瓶'}], 'images': [{'caption': '软管'}]}
        self.assertEqual(reference_uses(record), [])
        self.assertEqual(reference_uses({**record, 'bottleType': '软管 PRIVATE-VENDOR'}), [])

    def test_three_states_and_confirmed_usage_priority_without_mutation(self):
        record = {'bottleType': '软管', 'uses': ['洁面'], 'referenceUses': ['洁面', '面霜', '面霜']}
        original = deepcopy(record)
        self.assertEqual(reference_uses(record), ['面霜'])
        self.assertEqual(record, original)
        self.assertEqual(reference_uses({**record, 'referenceUses': []}), [])
        self.assertEqual(reference_uses({**record, 'referenceUses': None}), [])
        record.pop('referenceUses')
        self.assertEqual(reference_uses(record), ['护手霜', '身体乳'])

    def test_special_tube_uses_disable_generic_auto_from_product_evidence(self):
        for usage in SPECIAL_TUBE_USES:
            self.assertEqual(reference_uses({'bottleType': '软管', 'uses': [usage]}), [])
            self.assertEqual(reference_uses({'category': '软管', 'uses': [usage]}), [])
        self.assertEqual(reference_uses({'bottleType': '软管', 'uses': ['专用眼霜管待核对']}), [])
        self.assertEqual(reference_uses({'bottleType': '软管', 'uses': ['眼霜'], 'referenceUses': ['身体乳']}), ['身体乳'])

    def test_special_tube_guard_accepts_only_positive_product_scoped_sources(self):
        base = {'kind': 'package', 'bottleType': '软管', 'uses': []}
        for evidence in (
            {'name': 'ø19mm锌合金眼霜管'}, {'name': '圆形陶瓷头唇部护理管'},
            {'name': 'Tube for eye cream'},
            {'rawCells': {'用途': '眼霜'}},
            {'rawCells': {'original': {'产品用途': {'value': 'lip balm'}}}},
            {'productDetails': [{'label': '用途', 'value': '牙膏', 'sourceField': 'uses'}]},
            {'name': '不适用于眼霜，但可用于唇膏'},
        ):
            with self.subTest(evidence=evidence):
                self.assertEqual(reference_uses({**base, **evidence}), [])
        for evidence in (
            {'description': '眼霜'}, {'source': {'workbook': '眼霜图册.pdf'}},
            {'images': [{'caption': '眼霜'}]}, {'rawCells': {'A': '眼霜'}},
            {'rawCells': {'用途': {'value': '眼霜', 'scope': 'page'}}},
            {'productDetails': [{'label': '用途', 'value': '眼霜', 'sourceField': 'remarksRaw'}]},
            {'name': '图册整页 / 眼霜'}, {'name': '不适用于眼霜、唇膏'},
            {'name': 'not suitable for eye cream, lip balm'}, {'name': '眼霜（不适用）'},
        ):
            with self.subTest(evidence=evidence):
                self.assertEqual(reference_uses({**base, **evidence}), ['洁面', '护手霜', '身体乳'])
        # A human-maintained override still takes priority; names do not infer
        # a structure where no explicit tube category or bottle type exists.
        self.assertEqual(reference_uses({**base, 'name': '眼霜管', 'referenceUses': ['身体乳']}), ['身体乳'])
        self.assertEqual(reference_uses({'name': '洁面软管'}), [])

    def test_customer_canonical_whitelist_keeps_uses_and_regions_separate(self):
        record = {'category': '软管', 'uses': ['FACE CLEANSER'],
                  'referenceUses': ['洗面奶', 'hand cream', 'PRIVATE-CONTACT', '精华液 ￥2', 'BODY LOTION', 'HAND CREAM']}
        result = project_record(record, 'YZ-BC-000001')
        self.assertEqual(result['uses'], ['洁面'])
        self.assertEqual(result['referenceUses'], ['护手霜', '身体乳'])
        self.assertEqual(result['sections'], ['face'])
        self.assertEqual(facet_values(result, 'uses'), ['洁面', '护手霜', '身体乳'])
        for query in ('洁面', 'hand cream', 'body lotion'):
            self.assertTrue(matches_search(result, query), query)
        self.assertFalse(matches_search(result, 'PRIVATE'))
        self.assertNotIn('PRIVATE', json.dumps(result))
        automatic = project_record({'bottleType': '软管'}, 'YZ-BC-000001')
        self.assertEqual(automatic['uses'], [])
        self.assertEqual(automatic['referenceUses'], ['洁面', '护手霜', '身体乳'])
        self.assertEqual(automatic['sections'], [])

    def test_employee_csv_appends_display_uses_without_becoming_an_editable_import(self):
        rows = list(csv.reader(io.StringIO(internal_csv([{'name': '包材', 'uses': ['洁面'],
                                                        'referenceUses': ['护手霜', '身体乳']}]).decode('utf-8-sig'))))
        self.assertEqual(rows[0][-3:], ['来源', '资料用途', '参考用途（选型参考）'])
        self.assertEqual(rows[1][-2:], ['洁面', '护手霜 / 身体乳'])
        self.assertEqual(rows[0][:4], ['产品编号', '内部记录ID', '名称', '类型'])
        with self.assertRaises(ValueError):
            parse_import({'filename': 'report.csv', 'content': base64.b64encode(internal_csv([])).decode()})
        unsafe = list(csv.reader(io.StringIO(internal_csv([{'name': '包材', 'referenceUses': ['=SUM(A1)']}]).decode('utf-8-sig'))))
        self.assertEqual(unsafe[1][-1], "'=SUM(A1)")


class ReferenceUseAdminTests(unittest.TestCase):
    setUp = fixture.AdminStoreTests.setUp
    tearDown = fixture.AdminStoreTests.tearDown
    save = fixture.AdminStoreTests.save

    def change(self, patch):
        old = self.store.read_admin('records', 'ORIGINAL-1')
        return self.save('records', {'id': old['id'], 'version': old['version'], 'record': patch})

    def test_single_save_clear_reset_preserves_source_confirmed_uses_and_details(self):
        first = self.change({'category': '软管', 'uses': ['洁面'],
                             'productDetails': [{'label': '用途', 'value': '洁面'}, {'label': '口径', 'value': '24mm'}]})
        manual = self.change({'referenceUses': ['面霜', '面霜', ' 身体乳 ']})
        self.assertEqual(manual['referenceUses'], ['面霜', '身体乳'])
        for key in ('uses', 'productDetails', 'source', 'rawCells', 'productCode', 'images'):
            self.assertEqual(manual[key], first[key])
        self.assertEqual(self.change({'description': '另一个字段'})['referenceUses'], ['面霜', '身体乳'])
        self.assertEqual(self.change({'referenceUses': []})['referenceUses'], [])
        reset = self.change({'referenceUses': None})
        self.assertNotIn('referenceUses', reset)
        self.assertEqual(reference_uses(reset), ['护手霜', '身体乳'])
        self.assertEqual(reset['uses'], ['洁面'])
        audit = self.store.read_admin('audit')
        self.assertTrue(any(row['action'] == 'save' and row['entity_id'] == 'ORIGINAL-1' for row in audit))
        with self.assertRaises(AdminError):
            self.change({'uses': None})

    def test_bulk_reset_and_disabled_are_audited_with_atomic_conflicts(self):
        self.change({'category': '软管', 'referenceUses': ['面霜']})
        second = self.save('records', {'id': 'SECOND', 'version': 0, 'record': {'name': '另一款', 'category': '罐'}})
        records = [self.store.read_admin('records', rid) for rid in ('ORIGINAL-1', 'SECOND')]
        items = [{'id': row['id'], 'version': row['version']} for row in records]
        result = self.store.mutate('records', 'bulk', {'operation': 'save', 'items': items, 'patch': {'referenceUses': []}}, 'admin')
        self.assertTrue(all(row['referenceUses'] == [] for row in result['items']))
        reset_items = [{'id': row['id'], 'version': row['version']} for row in result['items']]
        reset = self.store.mutate('records', 'bulk', {'operation': 'save', 'items': reset_items, 'patch': {'referenceUses': None}}, 'admin')
        self.assertTrue(all('referenceUses' not in row for row in reset['items']))
        before = self.store.read_admin('records'); audit = self.store.read_admin('audit')
        with self.assertRaises(ConflictError):
            self.store.mutate('records', 'bulk', {'operation': 'save', 'items': reset_items, 'patch': {'referenceUses': ['眼霜']}}, 'admin')
        self.assertEqual(self.store.read_admin('records'), before)
        self.assertEqual(self.store.read_admin('audit'), audit)

    def test_invalid_reference_list_and_employee_write_are_rejected(self):
        before = self.store.read_admin('records', 'ORIGINAL-1')
        for value in ('面霜', {}, False, [None], [''], ['面霜'] * 101):
            with self.subTest(value=str(value)[:50]):
                with self.assertRaises(AdminError):
                    self.change({'referenceUses': value})
                self.assertEqual(self.store.read_admin('records', 'ORIGINAL-1'), before)
        with self.assertRaises(AdminError):
            self.save('records', {'id': before['id'], 'version': before['version'], 'record': {'referenceUses': ['面霜']}}, actor='yuanze')

    def test_import_preview_preserves_reset_intent_until_commit(self):
        old = self.change({'category': '软管', 'referenceUses': ['面霜']})
        content = f'记录编号,版本,名称,参考用途\nORIGINAL-1,{old["version"]},原始产品,自动\n'
        parsed = parse_import({'filename': 'uses.csv', 'content': base64.b64encode(content.encode()).decode()})
        self.assertIsNone(parsed['rows'][0]['referenceUses'])
        preview = self.store.bulk_preview(parsed['rows'])
        self.assertTrue(preview['valid'])
        self.assertIsNone(preview['rows'][0]['record']['referenceUses'])
        self.assertEqual(self.store.read_admin('records', 'ORIGINAL-1'), old)
        reset = self.store.bulk_save(preview['rows'], 'admin')['records'][0]
        self.assertNotIn('referenceUses', reset)
        self.assertEqual(reference_uses(reset), ['洁面', '护手霜', '身体乳'])

    def test_client_catalog_reference_filter_search_and_facets_do_not_infer_sections(self):
        old = self.store.read_admin('records', 'ORIGINAL-1')
        images = [{**old['images'][0], 'clientVisible': True}]
        self.change({'category': '软管', 'referenceUses': ['护手霜', 'PRIVATE-VENDOR'], 'images': images})
        catalog = ClientCatalog(self.store, self.state, self.private)
        result = catalog.catalog(filters={'use': ['护手霜']})
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['uses'], [])
        self.assertEqual(result['items'][0]['referenceUses'], ['护手霜'])
        self.assertEqual(result['facets']['uses'], ['护手霜'])
        self.assertEqual(result['facets']['sections'], [])
        self.assertEqual(catalog.catalog(q='hand cream')['total'], 1)
        self.assertEqual(catalog.catalog(q='PRIVATE')['total'], 0)
        self.assertEqual(catalog.catalog(filters={'section': ['body-head']})['total'], 0)


if __name__ == '__main__':
    unittest.main()
