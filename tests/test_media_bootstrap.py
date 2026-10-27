import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('media_bootstrap',Path(__file__).resolve().parents[1]/'scripts'/'bootstrap_media_tools.py')
bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def archive(self):
        output=io.BytesIO()
        with tarfile.open(fileobj=output,mode='w:xz') as tar:
            for name in ['build/bin/ffmpeg','build/bin/ffprobe','../../outside']:
                data=b'generated fixture';member=tarfile.TarInfo(name);member.size=len(data);tar.addfile(member,io.BytesIO(data))
        return output.getvalue()

    def test_checksum_verified_install_is_cached_and_confined(self):
        data=self.archive();config={'url':'https://fixture.invalid/archive','sha256':hashlib.sha256(data).hexdigest(),'max_bytes':10000}
        with tempfile.TemporaryDirectory() as temp, patch.object(bootstrap.urllib.request,'urlopen',return_value=io.BytesIO(data)) as download:
            root=Path(temp)/'tools';first=bootstrap.install(root,config)
            with patch.object(bootstrap.urllib.request,'urlopen',side_effect=AssertionError('must use cache')):
                second=bootstrap.install(root,config)
            self.assertFalse(first['cached']);self.assertTrue(second['cached'])
            self.assertEqual(download.call_count,1);self.assertFalse((Path(temp)/'outside').exists())
            self.assertTrue((root/'bin/ffprobe').is_file())

    def test_wrong_checksum_never_creates_a_verified_install(self):
        data=self.archive();config={'url':'https://fixture.invalid/archive','sha256':'0'*64,'max_bytes':10000}
        with tempfile.TemporaryDirectory() as temp, patch.object(bootstrap.urllib.request,'urlopen',return_value=io.BytesIO(data)):
            with self.assertRaisesRegex(ValueError,'checksum'):bootstrap.install(temp,config)
            self.assertFalse((Path(temp)/'verified.json').exists())


if __name__=='__main__':unittest.main()
