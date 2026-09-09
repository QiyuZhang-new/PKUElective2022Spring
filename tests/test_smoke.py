import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from autoelective.captcha import Captcha, TTShituRecognizer


ROOT = Path(__file__).resolve().parents[1]


class CaptchaTests(unittest.TestCase):
    def test_captcha_result_object(self):
        captcha = Captcha("abcd")
        self.assertEqual(captcha.code, "abcd")
        self.assertEqual(repr(captcha), "Captcha('abcd')")

    def test_image_can_be_encoded(self):
        source = io.BytesIO()
        Image.new("RGB", (2, 2), "white").save(source, format="PNG")
        encoded = TTShituRecognizer.to_b64(source.getvalue())
        self.assertTrue(encoded)


class ConfigurationTests(unittest.TestCase):
    def test_valid_configuration_passes_offline_check(self):
        config_text = """\
[user]
student_id = test-user
password = local-test-only
dual_degree = false
identity = bzx

[client]
supply_cancel_page = 1
refresh_interval = 8
random_deviation = 0.2
iaaa_client_timeout = 30
elective_client_timeout = 60
elective_client_pool_size = 2
elective_client_max_life = 600
login_loop_interval = 2
print_mutex_rules = true
debug_print_request = false
debug_dump_request = false

[monitor]
host = 127.0.0.1
port = 7074

[notification]
disable_push = true
token = unused
verbosity = 1
minimum_interval = -1

[course:test]
name = 测试课程
class = 1
school = 测试学院
"""
        apikey_text = """{
  "username": "local-test-only",
  "password": "local-test-only",
  "RecognitionTypeid": "1003",
  "Timeout": "60"
}
"""

        with tempfile.TemporaryDirectory() as folder:
            config_path = Path(folder, "config.ini")
            apikey_path = Path(folder, "apikey.json")
            config_path.write_text(config_text, encoding="utf-8")
            apikey_path.write_text(apikey_text, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "main.py"),
                    "-c",
                    str(config_path),
                    "-a",
                    str(apikey_path),
                    "--check-config",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )

            import_result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "from autoelective.environ import Environ; "
                        "env = Environ(); "
                        "env.config_ini = r'%s'; "
                        "env.apikey_json = r'%s'; "
                        "import autoelective.loop, autoelective.monitor; "
                        "print('runtime imports OK')"
                    ) % (config_path, apikey_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )

            retry_result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    """
from autoelective.environ import Environ
env = Environ()
env.config_ini = r'%s'
env.apikey_json = r'%s'
import autoelective.loop as loop
from autoelective.captcha import Captcha

class Response:
    content = b'test'
    def json(self):
        return {'valid': '0'}

class Elective:
    def get_DrawServlet(self):
        return Response()
    def get_Validate(self, username, code):
        return Response()

class Recognizer:
    calls = 0
    def recognize(self, raw):
        self.calls += 1
        return Captcha('bad')

loop.RECOGNIZER_MAX_ATTEMPT = 4
loop.asyncRecognizer = Recognizer()
course = next(iter(loop.config.courses.values()))
result = loop._get_valid_captcha(Elective(), course)
assert result is None
assert loop.asyncRecognizer.calls == 4
assert course in loop.ignored
print('retry cap OK')
""" % (config_path, apikey_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Configuration OK: 1 course(s)", result.stdout)
        self.assertEqual(import_result.returncode, 0, import_result.stderr)
        self.assertIn("runtime imports OK", import_result.stdout)
        self.assertEqual(retry_result.returncode, 0, retry_result.stderr)
        self.assertIn("retry cap OK", retry_result.stdout)


if __name__ == "__main__":
    unittest.main()
