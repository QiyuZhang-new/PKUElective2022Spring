import base64
from io import BytesIO
import json

import requests
from PIL import Image

from .captcha import Captcha
from .._internal import get_abs_path
from ..environ import Environ
from ..exceptions import OperationFailedError, OperationTimeoutError, RecognizerError


class APIConfig(object):
    _DEFAULT_CONFIG_PATH = '../apikey.json'

    def __init__(self, path=None):
        path = path or Environ().apikey_json or self._DEFAULT_CONFIG_PATH
        with open(get_abs_path(path), 'r', encoding='utf-8') as handle:
            self._apikey = json.load(handle)
        required = {'username', 'password', 'RecognitionTypeid', 'Timeout'}
        missing = required.difference(self._apikey)
        if missing:
            raise ValueError("apikey.json is missing: %s" % ", ".join(sorted(missing)))

    @property
    def uname(self):
        return self._apikey['username']

    @property
    def pwd(self):
        return self._apikey['password']

    @property
    def typeid(self):
        return int(self._apikey['RecognitionTypeid'])

    @property
    def timeout(self):
        return int(self._apikey['Timeout'])


class TTShituRecognizer(object):
    _RECOGNIZER_URL = "https://api.ttshitu.com/predict"

    def __init__(self):
        self._config = APIConfig()

    def recognize(self, raw):
        _typeid_ = self._config.typeid
        encode = TTShituRecognizer.to_b64(raw)
        data = {
            "username": self._config.uname,
            "password": self._config.pwd,
            "image": encode,
            "typeid": _typeid_
        }
        try:
            response = requests.post(
                TTShituRecognizer._RECOGNIZER_URL,
                json=data,
                timeout=self._config.timeout,
            )
            response.raise_for_status()
            result = response.json()
        except requests.Timeout:
            raise OperationTimeoutError(msg="Recognizer connection time out")
        except (requests.ConnectionError, requests.HTTPError, ValueError) as exc:
            raise OperationFailedError(msg="Unable to connect to the recognizer: %s" % exc)

        if result.get("success") and isinstance(result.get("data"), dict):
            return Captcha(result["data"]["result"])
        else:  # fail
            raise RecognizerError(msg="Recognizer ERROR: %s" % result.get("message", "unknown error"))

    @staticmethod
    def to_b64(raw):
        im = Image.open(BytesIO(raw))
        try:
            if im.is_animated:
                oim = im
                oim.seek(oim.n_frames - 1)
                im = Image.new('RGB', oim.size)
                im.paste(oim)
        except AttributeError:
            pass
        buffer = BytesIO()
        im.convert('RGB').save(buffer, format='JPEG')
        b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return b64
