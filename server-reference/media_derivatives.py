"""Small, metadata-free list images. Originals remain the download source."""
import hashlib
import os
from pathlib import Path
import secrets
import threading


class ThumbnailBusy(Exception):
    pass


class ThumbnailCache:
    def __init__(self, state):
        self.root = Path(state) / 'image-thumbnails'
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.gate = threading.BoundedSemaphore(2)

    def get(self, source):
        from PIL import Image, ImageOps, UnidentifiedImageError
        source = Path(source).resolve()
        stat = source.stat()
        key = hashlib.sha256(f'v1:512:78:{source}:{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()
        target = self.root / (key + '.jpg')
        if target.is_file():
            return target
        if not self.gate.acquire(timeout=10):
            raise ThumbnailBusy()
        temporary = target.with_suffix('.' + secrets.token_hex(6) + '.tmp')
        try:
            if target.is_file():
                return target
            with Image.open(source) as original:
                if not 0 < original.width * original.height <= 24_000_000:
                    return None
                original.draft('RGB', (512, 512))
                rendered = ImageOps.exif_transpose(original)
                rendered.thumbnail((512, 512))
                clean = Image.new('RGB', rendered.size, 'white')
                if 'A' in rendered.getbands():
                    clean.paste(rendered, mask=rendered.getchannel('A'))
                else:
                    clean.paste(rendered.convert('RGB'))
                clean.save(temporary, format='JPEG', quality=78, optimize=True)
                temporary.chmod(0o600)
                os.replace(temporary, target)
            return target
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            return None
        finally:
            temporary.unlink(missing_ok=True)
            self.gate.release()
