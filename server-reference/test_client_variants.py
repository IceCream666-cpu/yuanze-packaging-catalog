"""Confirmed customer variants preserve per-spec identity and approval checks."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from admin_store import AdminStore
from client_catalog import ClientCatalog
from test_admin_store import credentials


SOURCE_IDS = ('YZ-S01-R0012', 'YZ-S01-R0013')
CODES = ('YZ-BC-000009', 'YZ-BC-000010')
SAFE_FIELDS = {'id', 'productCode', 'name', 'capacity', 'capacityMl', 'category',
               'bottleType', 'materials', 'uses', 'referenceUses', 'sections', 'specifications', 'images'}


class ClientVariantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture_number = 0
        self.store, self.client = self.make_client()

    def record(self, record_id, capacity, image, material='PET'):
        return {'id': record_id, 'kind': 'package', 'name': 'PRIVATE-DESIGN',
                'category': '瓶', 'bottleType': '圆瓶', 'capacityMl': capacity,
                'materials': [material, 'PRIVATE-MATERIAL'], 'uses': ['洗手液'],
                'productCode': 'PRIVATE-CONTENT-CODE', 'model': 'PRIVATE-MODEL',
                'description': 'PRIVATE-DESCRIPTION', 'supplierRaw': 'PRIVATE-SUPPLIER',
                'unitPrice': 9.99, 'quoteRaw': 'PRIVATE-QUOTE',
                'source': {'workbook': 'PRIVATE-SOURCE.pdf', 'page': 1},
                'productDetails': [{'label': '口径', 'value': f'{24 if capacity == 250 else 28} mm'},
                                   {'label': '高度', 'value': 'PRIVATE-DIMENSION'},
                                   {'label': '价格', 'value': '9.99元'}],
                'images': [{'path': image, 'role': 'product', 'clientVisible': True},
                           {'path': 'media/private.png', 'role': 'product', 'clientVisible': False}]}

    def make_client(self, member_ids=SOURCE_IDS, extras=None, reverse=False):
        self.fixture_number += 1
        root = Path(self.temp.name) / str(self.fixture_number)
        state, private = root / 'state', root / 'private'
        state.mkdir(parents=True)
        (state / 'admin-bootstrap.json').write_text(json.dumps(credentials('admin')))
        (private / 'media').mkdir(parents=True)
        for filename, color in [('250.png', 'red'), ('500.png', 'blue'), ('private.png', 'black')]:
            Image.new('RGB', (12, 18), color).save(private / 'media' / filename)
        # Seed eight hidden packages so the two member mappings receive their
        # real immutable codes; initial raw content codes deliberately disagree.
        records = [{'id': f'HIDDEN-{index}', 'kind': 'package', 'name': 'PRIVATE-HIDDEN', 'images': []}
                   for index in range(8)]
        members = [self.record(member_ids[0], 250, 'media/250.png'),
                   self.record(member_ids[1], 500, 'media/500.png', 'PP')]
        records.extend(reversed(members) if reverse else members)
        records.extend(deepcopy(extras or []))
        store = AdminStore(state, private, {}, {'meta': {}, 'records': records})
        return store, ClientCatalog(store, state, private)

    def edit(self, source_id, changes=None, action='save'):
        record = self.store.read_admin('records', id=source_id)
        return self.store.mutate('records', action,
                                 {'id': source_id, 'version': record['version'], 'record': changes or {}}, 'admin')

    def test_one_card_preserves_safe_nonrecursive_per_spec_records_and_images(self):
        result = self.client.catalog()
        self.assertEqual((result['total'], result['pages']), (1, 1))
        item = result['items'][0]
        self.assertEqual(set(item), SAFE_FIELDS | {'variants'})
        self.assertEqual(item['productCode'], CODES[0])
        self.assertEqual(item['id'], self.client.opaque('record', SOURCE_IDS[0]))
        variants = item['variants']
        self.assertEqual([variant['productCode'] for variant in variants], list(CODES))
        self.assertEqual([variant['capacityMl'] for variant in variants], [250, 500])
        self.assertEqual([variant['specifications'] for variant in variants],
                         [[{'label': '口径', 'value': '24 mm'}], [{'label': '口径', 'value': '28 mm'}]])
        self.assertNotEqual(variants[0]['id'], variants[1]['id'])
        self.assertNotEqual(variants[0]['images'], variants[1]['images'])
        for variant in variants:
            self.assertEqual(set(variant), SAFE_FIELDS)
            self.assertEqual(len(variant['images']), 1)
            self.assertEqual(set(variant['images'][0]), {'url'})
            self.assertRegex(variant['images'][0]['url'], r'^/client-media/[a-f0-9]{64}\.jpg$')
        self.assertEqual(result['facets']['capacities'], ['250 mL', '500 mL'])
        self.assertEqual(result['facets']['materials'], ['PET', 'PP'])
        for private in ('PRIVATE', 'YZ-S01', 'supplier', 'price', 'quote', 'source', '9.99'):
            self.assertNotIn(private, json.dumps(result))
        # Returned cards and children cannot corrupt the shared safe snapshot.
        variants[1]['capacity'] = 'PRIVATE-MUTATED'
        self.assertEqual(self.client.catalog()['items'][0]['variants'][1]['capacity'], '500 mL')

    def test_matching_member_is_representative_and_filters_apply_before_grouping(self):
        for arguments in ({'q': CODES[1].lower()}, {'q': '500 ml hand wash'},
                          {'filters': {'capacity': ['500 mL']}}, {'filters': {'material': ['PP']}}):
            with self.subTest(arguments=arguments):
                result = self.client.catalog(**arguments)
                self.assertEqual(result['total'], 1)
                self.assertEqual(result['items'][0]['productCode'], CODES[1])
                self.assertEqual(result['items'][0]['capacityMl'], 500)
                self.assertEqual([v['productCode'] for v in result['items'][0]['variants']], list(CODES))
        for arguments in ({'q': CODES[1], 'filters': {'capacity': ['250 mL']}},
                          {'q': '500 mL', 'filters': {'material': ['PET']}},
                          {'filters': {'use': ['面霜']}}):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.client.catalog(**arguments)['total'], 0)
        self.assertEqual(self.client.catalog(filters={'capacity': ['250 mL', '500 mL']})['total'], 1)

    def test_private_search_cannot_select_a_group_or_expand_a_sibling(self):
        for query in ('PRIVATE', 'PRIVATE-MODEL', 'PRIVATE-SOURCE', 'PRIVATE-CONTENT-CODE',
                      SOURCE_IDS[0], 'supplier', '9.99', 'quote', 'source'):
            with self.subTest(query=query):
                result = self.client.catalog(q=query)
                self.assertEqual((result['total'], result['items']), (0, []))
                self.assertEqual(result['facets']['capacities'], ['250 mL', '500 mL'])

    def test_revocation_removes_sibling_immediately_including_cached_media(self):
        grouped = self.client.catalog()['items'][0]
        sibling_url = grouped['variants'][1]['images'][0]['url']
        token = sibling_url.rsplit('/', 1)[1]
        self.assertIsNotNone(self.client.media(token))
        saved = self.store.read_admin('records', id=SOURCE_IDS[1])
        saved['images'][0]['clientVisible'] = False
        self.edit(SOURCE_IDS[1], {'images': saved['images']})
        remaining = self.client.catalog()
        self.assertEqual(remaining['total'], 1)
        self.assertEqual(remaining['items'][0]['productCode'], CODES[0])
        self.assertNotIn('variants', remaining['items'][0])
        self.assertEqual(remaining['facets']['capacities'], ['250 mL'])
        self.assertEqual(self.client.catalog(q=CODES[1])['total'], 0)
        self.assertIsNone(self.client.media(token))
        saved['images'][0]['clientVisible'] = True
        self.edit(SOURCE_IDS[1], {'images': saved['images']})
        self.assertEqual(len(self.client.catalog()['items'][0]['variants']), 2)

    def test_archive_of_first_member_leaves_only_approved_active_sibling(self):
        first = self.client.catalog()['items'][0]
        token = first['images'][0]['url'].rsplit('/', 1)[1]
        self.edit(SOURCE_IDS[0], action='archive')
        remaining = self.client.catalog()
        self.assertEqual(remaining['total'], 1)
        self.assertEqual(remaining['items'][0]['productCode'], CODES[1])
        self.assertNotIn('variants', remaining['items'][0])
        self.assertEqual(remaining['facets']['capacities'], ['500 mL'])
        self.assertEqual(self.client.catalog(q=CODES[0])['total'], 0)
        self.assertIsNone(self.client.media(token))
        self.edit(SOURCE_IDS[0], action='unarchive')
        self.assertEqual(len(self.client.catalog()['items'][0]['variants']), 2)

    def test_lookalikes_and_content_code_spoofs_cannot_join_confirmed_pair(self):
        extras = [self.record(f'UNKNOWN-{index}', capacity, 'media/250.png')
                  for index, capacity in enumerate((250, 500))]
        for index, record in enumerate(extras):
            record['productCode'] = CODES[index]
            record['source']['id'] = SOURCE_IDS[index]
        store, client = self.make_client(extras=extras)
        result = client.catalog()
        self.assertEqual(result['total'], 3)
        grouped = [item for item in result['items'] if 'variants' in item]
        self.assertEqual(len(grouped), 1)
        self.assertEqual([variant['productCode'] for variant in grouped[0]['variants']], list(CODES))
        self.assertEqual(sum('variants' not in item for item in result['items']), 2)
        # Codes alone are insufficient when they belong to unknown source IDs.
        _, unknown_client = self.make_client(member_ids=('UNKNOWN-250', 'UNKNOWN-500'))
        result = unknown_client.catalog()
        self.assertEqual(result['total'], 2)
        self.assertEqual([item['productCode'] for item in result['items']], list(CODES))
        self.assertTrue(all('variants' not in item for item in result['items']))
        # Known IDs with the wrong authoritative code mappings also fail closed.
        _, wrong_mapping_client = self.make_client(reverse=True)
        result = wrong_mapping_client.catalog()
        self.assertEqual(result['total'], 2)
        self.assertTrue(all('variants' not in item for item in result['items']))

    def test_grouping_before_paging_does_not_repeat_pair_across_page_boundary(self):
        extras = [self.record(f'BEFORE-{index:02}', 100, 'media/250.png') for index in range(23)]
        extras.append(self.record('ZZ-AFTER', 100, 'media/500.png'))
        _, client = self.make_client(extras=extras)
        first, second = client.catalog(page_size=24), client.catalog(page=2, page_size=24)
        self.assertEqual((first['total'], first['pages'], len(first['items'])), (25, 2, 24))
        self.assertEqual((second['total'], second['page'], len(second['items'])), (25, 2, 1))
        self.assertEqual(first['items'][-1]['productCode'], CODES[0])
        self.assertEqual(len(first['items'][-1]['variants']), 2)
        self.assertNotIn('variants', second['items'][0])
        self.assertEqual(client.catalog(page=999, page_size=24)['items'], second['items'])
        combined = first['items'] + second['items']
        self.assertEqual(len({item['id'] for item in combined}), 25)

    def test_card_total_does_not_mutate_approved_record_count(self):
        extras = [self.record(f'OTHER-{index:03}', 100, 'media/250.png') for index in range(612)]
        store, client = self.make_client(extras=extras)
        self.assertEqual(client.catalog()['total'], 613)
        with store.connection() as connection:
            raw_approved = connection.execute('''SELECT COUNT(*) FROM admin_records
                WHERE archived=0 AND EXISTS (SELECT 1 FROM json_each(content,'$.images') AS image
                WHERE json_extract(image.value,'$.clientVisible')=1
                  AND json_type(image.value,'$.clientVisible')='true')''').fetchone()[0]
        self.assertEqual(raw_approved, 614)
        self.assertEqual(store.read_admin('records', id=SOURCE_IDS[0])['productCode'], CODES[0])
        self.assertEqual(store.read_admin('records', id=SOURCE_IDS[1])['productCode'], CODES[1])

    def test_image_search_groups_pair_and_keeps_first_public_hit_representative(self):
        matches = [{'record_id': SOURCE_IDS[1], 'image_path': 'media/private.png', 'score': 1},
                   {'record_id': SOURCE_IDS[1], 'image_path': 'media/500.png', 'score': .9},
                   {'record_id': SOURCE_IDS[0], 'image_path': 'media/250.png', 'score': .8}]
        result = self.client.image_search_results(matches)
        self.assertEqual((result['total'], result['page'], result['pages']), (1, 1, 1))
        item = result['items'][0]
        self.assertEqual(item['productCode'], CODES[1])
        self.assertEqual(item['capacityMl'], 500)
        self.assertEqual([variant['productCode'] for variant in item['variants']], list(CODES))
        self.assertEqual(item['images'], item['variants'][1]['images'])
        self.assertEqual(result['facets']['capacities'], ['250 mL', '500 mL'])
        for variant in item['variants']:
            self.assertEqual(set(variant), SAFE_FIELDS)
            self.assertIsNotNone(self.client.media(variant['images'][0]['url'].rsplit('/', 1)[1]))
        for secret in ('PRIVATE', 'YZ-S01', 'source', 'supplier', 'score', 'image_path', '9.99'):
            self.assertNotIn(secret, json.dumps(result))

    def test_image_search_requires_public_hit_before_exposing_approved_sibling_choices(self):
        private_match = {'record_id': SOURCE_IDS[0], 'image_path': 'media/private.png'}
        result = self.client.image_search_results([private_match])
        self.assertEqual((result['total'], result['items']), (0, []))
        self.assertTrue(all(not values for values in result['facets'].values()))
        # Only the 500-mL member matched a public image. Its known, separately
        # approved 250-mL sibling is a size choice, not a private-image match.
        result = self.client.image_search_results([private_match,
                {'record_id': SOURCE_IDS[1], 'image_path': 'media/500.png'}])
        self.assertEqual(result['total'], 1)
        item = result['items'][0]
        self.assertEqual(item['productCode'], CODES[1])
        self.assertEqual(len(item['variants']), 2)
        self.assertEqual(item['variants'][0]['images'][0]['url'],
                         '/client-media/' + self.client.opaque('image', SOURCE_IDS[0], 'media/250.png') + '.jpg')

    def test_image_search_ignores_catalog_snapshot_when_sibling_is_revoked_or_archived(self):
        self.client.catalog()  # Intentionally warm a snapshot containing both.
        saved = self.store.read_admin('records', id=SOURCE_IDS[0])
        saved['images'][0]['clientVisible'] = False
        self.edit(SOURCE_IDS[0], {'images': saved['images']})
        matches = [{'record_id': SOURCE_IDS[0], 'image_path': 'media/250.png'},
                   {'record_id': SOURCE_IDS[1], 'image_path': 'media/500.png'}]
        result = self.client.image_search_results(matches)
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['productCode'], CODES[1])
        self.assertNotIn('variants', result['items'][0])
        self.assertEqual(result['facets']['capacities'], ['500 mL'])
        self.assertEqual(self.client.image_search_results(matches[:1])['total'], 0)
        saved['images'][0]['clientVisible'] = True
        self.edit(SOURCE_IDS[0], {'images': saved['images']})
        self.edit(SOURCE_IDS[1], action='archive')
        result = self.client.image_search_results(matches)
        self.assertEqual(result['items'][0]['productCode'], CODES[0])
        self.assertNotIn('variants', result['items'][0])
        self.assertEqual(result['facets']['capacities'], ['250 mL'])

    def test_image_search_spoofed_code_pair_does_not_group_unknown_source_ids(self):
        _, client = self.make_client(member_ids=('UNKNOWN-250', 'UNKNOWN-500'))
        result = client.image_search_results([
            {'record_id': 'UNKNOWN-250', 'image_path': 'media/250.png'},
            {'record_id': 'UNKNOWN-500', 'image_path': 'media/500.png'}])
        self.assertEqual(result['total'], 2)
        self.assertEqual([item['productCode'] for item in result['items']], list(CODES))
        self.assertTrue(all('variants' not in item for item in result['items']))

    def test_image_search_limits_series_cards_after_deduplication_and_preserves_rank(self):
        extras = [self.record(f'OTHER-{index:02}', index + 1, 'media/250.png') for index in range(49)]
        _, client = self.make_client(extras=extras)
        matches = [{'record_id': SOURCE_IDS[1], 'image_path': 'media/500.png'},
                   {'record_id': SOURCE_IDS[0], 'image_path': 'media/250.png'},
                   *({'record_id': record['id'], 'image_path': 'media/250.png'} for record in extras)]
        result = client.image_search_results(matches, limit=500)
        self.assertEqual(result['total'], 48)
        self.assertEqual([item['capacityMl'] for item in result['items']], [500, *range(1, 48)])
        self.assertEqual(sum('variants' in item for item in result['items']), 1)
        small = client.image_search_results(matches, limit=2)
        self.assertEqual(small['total'], 2)
        self.assertEqual([item['capacityMl'] for item in small['items']], [500, 1])


if __name__ == '__main__':
    unittest.main()
