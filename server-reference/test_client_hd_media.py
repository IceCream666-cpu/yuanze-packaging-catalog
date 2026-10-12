"""Native-resolution client derivatives and authenticated resumable downloads."""
import hashlib
import http.client
import io
import os
import unittest
from unittest.mock import patch
from PIL import Image, PngImagePlugin
import test_client_access as fixtures
from test_server import server


class ClientHDMedia(unittest.TestCase):
    setUp = fixtures.ClientAccess.setUp
    tearDown = fixtures.ClientAccess.tearDown
    req = fixtures.ClientAccess.req
    login = fixtures.ClientAccess.login
    catalog = fixtures.ClientAccess.catalog

    def get(self, path, headers=None, method='GET'):
        connection = http.client.HTTPConnection(self.host)
        connection.request(method, path, headers={'Cookie':self.cookie, **(headers or {})})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def hd_fixture(self):
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('supplier', 'PRIVATE-SUPPLIER-SECRET')
        source = server.PRIVATE/'media/supplier-secret.png'
        Image.new('RGB', (2100, 1700), '#164b47').save(source, pnginfo=metadata)
        self.login()
        return self.catalog()['items'][0]['images'][0]['url']

    def test_original_resolution_is_sanitized_and_distinct_from_default_and_thumbnail(self):
        url = self.hd_fixture()
        for suffix, expected in [('', (1600,1295)), ('?thumb=1', (512,414)),
                                 ('?size=original', (2100,1700)),
                                 ('?size=original&thumb=1', (2100,1700))]:
            status, headers, body = self.get(url+suffix)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Content-Type'], 'image/jpeg')
            with Image.open(io.BytesIO(body)) as image:
                self.assertEqual(image.size, expected)
                self.assertEqual(image.getexif(), {})
                self.assertNotIn('supplier', image.info)
                self.assertNotIn('PRIVATE', str(image.info))
        status, headers, body = self.get(url+'?size=original&download=YZ-BC-000001-1.jpg')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Disposition'], 'attachment; filename="YZ-BC-000001-1.jpg"')
        self.assertEqual(int(headers['Content-Length']), len(body))
        token = url.rsplit('/',1)[1]
        with patch('PIL.Image.open', side_effect=AssertionError('Cached HD must not be re-rendered')):
            self.assertIsNotNone(server.CLIENT_CATALOG.media(token, original=True))

    def test_original_preserves_exif_orientation_but_removes_exif_and_never_upscales(self):
        source = server.PRIVATE/'media/supplier-secret.png'
        orientation = Image.Exif(); orientation[274] = 6; orientation[270] = 'PRIVATE-SUPPLIER-SECRET'
        Image.new('RGB',(1800,1200),'white').save(source,format='JPEG',exif=orientation)
        self.login();url=self.catalog()['items'][0]['images'][0]['url']
        with Image.open(io.BytesIO(self.get(url+'?size=original')[2])) as image:
            self.assertEqual(image.size,(1200,1800));self.assertEqual(image.getexif(),{})
        Image.new('RGB',(100,150),'white').save(source)
        with Image.open(io.BytesIO(self.get(url+'?size=original')[2])) as image:
            self.assertEqual(image.size,(100,150))

    def test_authenticated_ranges_match_bytes_and_allow_resumption(self):
        url=self.hd_fixture();path=url+'?size=original&download=YZ-BC-000001-1.jpg'
        status,headers,full=self.get(path);self.assertEqual(status,200)
        self.assertEqual(headers['Accept-Ranges'],'bytes');etag=headers['ETag']
        for value,span in [('bytes=0-99',(0,100)),('bytes=100-',(100,len(full))),
                           ('bytes=-37',(len(full)-37,len(full))),
                           ('bytes=0-999999',(0,len(full)))]:
            status,h,body=self.get(path,{'Range':value,'If-Range':etag})
            start,end=span
            self.assertEqual(status,206);self.assertEqual(body,full[start:end])
            self.assertEqual(h['Content-Range'],f'bytes {start}-{end-1}/{len(full)}')
            self.assertEqual(int(h['Content-Length']),len(body));self.assertIn('attachment',h['Content-Disposition'])
        status,h,body=self.get(path,{'Range':'bytes=0-99','If-Range':'"old"'})
        self.assertEqual((status,body),(200,full));self.assertNotIn('Content-Range',h)
        status,h,body=self.get(path,{'Range':'bytes=0-99'},method='HEAD')
        self.assertEqual(status,200);self.assertEqual(body,b'');self.assertEqual(int(h['Content-Length']),len(full))
        for value in ['bytes=999999-', 'bytes=-0']:
            status,h,body=self.get(path,{'Range':value})
            self.assertEqual(status,416);self.assertEqual(body,b'')
            self.assertEqual(h['Content-Range'],f'bytes */{len(full)}')
        for value in ['bytes=7-2', 'bytes=0-1,3-4', 'bytes=bad', 'items=0-2', 'bytes=-', 'bytes='+('9'*100)+'-']:
            self.assertEqual(self.get(path,{'Range':value})[::2],(200,full))

    def test_current_approval_is_required_before_hd_head_range_or_conditional_hit(self):
        url=self.hd_fixture();path=url+'?size=original';etag=self.get(path)[1]['ETag']
        self.assertEqual(self.get(path,{'If-None-Match':etag})[::2],(304,b''))
        record=server.STORE.read_admin('records',id='INTERNAL-1')
        record['images'][0]['clientVisible']=False
        server.STORE.mutate('records','save',{'id':record['id'],'version':record['version'],'record':record},'admin')
        for suffix,headers,method in [('',{'If-None-Match':etag},'GET'),('',{'Range':'bytes=0-99'},'GET'),
                                      ('&download=test.jpg',{'Range':'bytes=0-99'},'GET'),('',{},'HEAD')]:
            self.assertEqual(self.get(path+suffix,headers,method)[0],404)
        for private in ['/media/supplier-secret.png?size=original','/uploads/private.jpg?size=original']:
            self.assertEqual(self.get(private,{'Range':'bytes=0-99'})[0],403)
        self.req('/api/logout',{});self.cookie=''
        self.assertEqual(self.get(path,{'Range':'bytes=0-99'})[0],401)

    def test_showroom_original_range_download_and_role_boundaries(self):
        self.login();path='/showroom/assets/posters/poster-009.webp?download=yuanze-poster-009.webp'
        status,headers,full=self.get(path);self.assertEqual(status,200)
        source=server.PUBLIC/'showroom/assets/posters/poster-009.webp'
        self.assertEqual(hashlib.sha256(full).digest(),hashlib.sha256(source.read_bytes()).digest())
        status,h,body=self.get(path,{'Range':'bytes=128-255'})
        self.assertEqual(status,206);self.assertEqual(body,full[128:256]);self.assertIn('attachment',h['Content-Disposition'])
        self.req('/api/logout',{});self.cookie='';self.assertEqual(self.get(path,{'Range':'bytes=0-99'})[0],401)
        self.login('employee');self.assertEqual(self.get(path,{'Range':'bytes=0-99'})[0],403)

    def test_atomic_source_replacement_invalidates_hd_and_old_if_range_even_with_same_size_and_mtime(self):
        url=self.hd_fixture();source=server.PRIVATE/'media/supplier-secret.png'
        Image.new('RGB',(100,150),'blue').save(source,compress_level=0)
        path=url+'?size=original';_,headers,first=self.get(path);before=source.stat()
        replacement=source.with_name('replacement.png')
        Image.new('RGB',(100,150),'red').save(replacement,compress_level=0)
        os.utime(replacement,ns=(before.st_atime_ns,before.st_mtime_ns))
        self.assertEqual(replacement.stat().st_size,before.st_size)
        replacement.replace(source)
        status,latest,second=self.get(path,{'Range':'bytes=0-99','If-Range':headers['ETag']})
        self.assertEqual(status,200);self.assertNotEqual(first,second)
        self.assertNotEqual(headers['ETag'],latest['ETag']);self.assertNotIn('Content-Range',latest)

    def test_archived_product_rejects_warmed_hd_head_and_range(self):
        url=self.hd_fixture();path=url+'?size=original';self.assertEqual(self.get(path)[0],200)
        record=server.STORE.read_admin('records',id='INTERNAL-1')
        server.STORE.mutate('records','archive',{'id':record['id'],'version':record['version']},'admin')
        self.assertEqual(self.get(path,{'Range':'bytes=0-99'})[0],404)
        self.assertEqual(self.get(path,method='HEAD')[0],404)


if __name__=='__main__':
    unittest.main()
