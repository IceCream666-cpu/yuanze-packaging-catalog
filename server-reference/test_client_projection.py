"""Customer projection never copies editable prose or commercial values."""
import json
import unittest

from client_catalog import capacity_info, matches_search, project_record, safe_specifications


class ClientProjectionTests(unittest.TestCase):
    def project(self, record):
        return project_record(record, 'YZ-BC-000001')

    def test_exact_vocabulary_and_generic_name(self):
        record = {'name':'PRIVATE-VENDOR bottle ￥2', 'description':'PRIVATE-DESCRIPTION',
                  'category':' BOTTLE ', 'bottleType':' ＳＰＲＡＹ ',
                  'materials':['pet', 'PET', 'ＰＰ', 'PET ￥2', 'PET / PRIVATE-VENDOR'],
                  'uses':['TONER', '面霜', 'serum PRIVATE-CONTACT'], 'capacityMl':100,
                  'sections':['body-head PRIVATE-VENDOR'], 'model':'PRIVATE-MODEL',
                  'rawCells':{'用途':'PRIVATE-USE'}, 'source':{'workbook':'PRIVATE-FILE'}}
        result = self.project(record)
        self.assertEqual(result['name'], '喷雾瓶 · 100 mL')
        self.assertEqual(result['materials'], ['PET', 'PP'])
        self.assertEqual(result['uses'], ['爽肤水', '面霜'])
        self.assertEqual(result['sections'], ['face'])
        self.assertEqual(result['category'], '瓶类')
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn('￥2', json.dumps(result))
        for field, value in [('category','瓶 PRIVATE-VENDOR'), ('bottleType','喷雾瓶 ￥2'),
                             ('materials',['PP PRIVATE-CONTACT']), ('uses',['精华液 ￥2'])]:
            result = self.project({field:value})
            self.assertEqual(result[field], [] if field in {'materials','uses'} else '')
            self.assertEqual(result['name'], '包材')

    def test_details_require_trusted_labels_sources_and_complete_measurements(self):
        record = {'productDetails':[
            {'label':'口径', 'value':'24mm'},
            {'label':'瓶高（mm）', 'value':'120.5'},
            {'label':'高度', 'value':'12 cm', 'sourceField':'specificationRaw', 'evidence':'PRIVATE-VENDOR ￥2'},
            {'label':'重量', 'value':'10 克'},
            {'label':'满口容量', 'value':'0.2 L'},
            {'label':'直径', 'value':'40mm PRIVATE-VENDOR'},
            {'label':'长度', 'value':'50mm ￥2'},
            {'label':'宽度', 'value':'50mm', 'sourceField':'quoteRaw'},
            {'label':'厚度', 'value':'2mm', 'sourceField':'contactRaw'},
            {'label':'PRIVATE-LABEL', 'value':'1mm'},
            {'label':'价格', 'value':'9.99元'},
            {'label':'口径', 'value':'24mm'},
            {'label':'容量', 'value':'100 mL PRIVATE-CONTACT'},
            {'label':'净含量', 'value':'100 mL', 'sourceField':'quoteRaw'},
        ]}
        self.assertEqual(safe_specifications(record), [
            {'label':'口径','value':'24 mm'}, {'label':'瓶高','value':'120.5 mm'},
            {'label':'高度','value':'12 cm'}, {'label':'重量','value':'10 g'},
            {'label':'满口容量','value':'0.2 L'},
        ])
        self.assertEqual(capacity_info(record), ('', None))
        self.assertNotIn('PRIVATE', json.dumps(self.project(record)))
        self.assertNotIn('9.99', json.dumps(self.project(record)))

    def test_numeric_bounds_and_legacy_malformed_fields_fail_closed(self):
        for value in (None, True, float('nan'), float('inf'), -1, 0, 100001, '100ml PRIVATE'):
            self.assertEqual(capacity_info({'capacityMl':value}), ('', None))
        self.assertEqual(capacity_info({'productDetails':[{'label':'容量','value':'0.5 L'}]}), ('0.5 L',500))
        self.assertEqual(capacity_info({'productDetails':[{'label':'净含量','value':'50克'}]}), ('50 g',None))
        for value in ('-1 mm','NaN mm','10001 mm','1001 cm','0 mm','10元','9.99','24mm/PRIVATE','13812345678 mm'):
            self.assertEqual(safe_specifications({'productDetails':[{'label':'口径','value':value}]}), [])
        for details in (None, {}, 'PRIVATE', [None, 'PRIVATE', {'label':True,'value':False},
                        {'label':'口径','value':'24 mm','sourceField':{}},
                        {'label':'容量','value':'100 mL','sourceField':[]} ]):
            result=self.project({'productDetails':details,'materials':{},'uses':False})
            self.assertEqual(result['specifications'], [])
            self.assertEqual(result['materials'], [])
            self.assertEqual(result['uses'], [])

    def test_sections_require_explicit_safe_usage_and_private_prose_never_infers(self):
        record={'name':'面霜 身体乳', 'description':'面部 身体', 'uses':['精华液','乳液','防晒'],
                'source':{'用途':'面霜'}, 'rawCells':{'用途':'面霜'},
                'productDetails':[{'label':'用途','value':'面霜','sourceField':'supplierRaw'}]}
        self.assertEqual(self.project(record)['sections'], [])
        record['productDetails']=[{'label':'用途','value':'body lotion'}, {'label':'适用部位','value':'面部'}]
        result=self.project(record)
        self.assertEqual(result['sections'], ['face','body-head'])
        self.assertEqual(result['uses'], ['精华液','乳液','防晒','身体乳'])

    def test_mapping_is_authoritative_and_search_is_public_only(self):
        record={'productCode':'PRIVATE-CONTENT-CODE','name':'PRIVATE-NAME','category':'瓶',
                'materials':['PETG'],'uses':['精华液'], 'specificationRaw':'PRIVATE-SPEC',
                'unitPrice':9.99, 'supplierRaw':'PRIVATE-VENDOR'}
        result=self.project(record)
        self.assertEqual(result['productCode'], 'YZ-BC-000001')
        for query in ('bottle','SERUM','PETG','YZ-BC-000001','精华液'):
            self.assertTrue(matches_search(result,query), query)
        for query in ('PET','PRIVATE','9.99','VENDOR','PRIVATE-SPEC'):
            self.assertFalse(matches_search(result,query), query)
        self.assertEqual(project_record(record, 'PRIVATE-MAPPING')['productCode'], '')


if __name__ == '__main__':
    unittest.main()
