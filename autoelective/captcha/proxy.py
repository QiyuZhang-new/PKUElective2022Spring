#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Filename : proxy
# @Date : 2022-09-05
# @Project: PKUElective2022Spring
# @AUTHOR : Totoro
import asyncio
from collections import Counter

import aiohttp

from .captcha import Captcha
from .online import APIConfig, TTShituRecognizer
from ..exceptions import OperationTimeoutError, RecognizerError

_RECOGNIZER_URL = "https://api.ttshitu.com/predict"

RECOGNITION_METHODS = [3, 1003, 7]
RECOGNITION_WEIGHT = {3: 0.4, 1003: 0.7, 7: 1.0}


class RecognitionProxy(object):
    def __init__(self):
        self._config = APIConfig()

    def msg_pack(self, raw, typeid):
        encoded = TTShituRecognizer.to_b64(raw)
        data = {
            "username": self._config.uname,
            "password": self._config.pwd,
            "image": encoded,
            "typeid": typeid
        }
        return data

    async def _recognize_all(self, trials):
        timeout = aiohttp.ClientTimeout(total=self._config.timeout)
        connector = aiohttp.TCPConnector(limit_per_host=len(trials), ttl_dns_cache=300)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async def post(content):
                try:
                    async with session.post(_RECOGNIZER_URL, json=content) as response:
                        response.raise_for_status()
                        return await response.json(), content['typeid']
                except asyncio.TimeoutError:
                    return None
                except (aiohttp.ClientError, ValueError):
                    return None

            return await asyncio.gather(*(post(trial) for trial in trials))

    def recognize(self, raw):
        base_msg = self.msg_pack(raw, self._config.typeid)
        trials = []
        for method in RECOGNITION_METHODS:
            temp = base_msg.copy()
            temp["typeid"] = method
            trials.append(temp)

        results = asyncio.run(self._recognize_all(trials))
        successful = []
        for item in results:
            if item is None:
                continue
            result, method = item
            if result.get('success') and isinstance(result.get('data'), dict):
                code = result['data'].get('result')
                if code:
                    successful.append((code, method))

        if not successful:
            if all(item is None for item in results):
                raise OperationTimeoutError(msg="All recognizer requests failed or timed out")
            raise RecognizerError(msg="The recognizer returned no usable result")

        scores = Counter()
        for code, method in successful:
            scores[code] += RECOGNITION_WEIGHT[method]
        code = max(scores, key=scores.get)
        return Captcha(code)


if __name__ == '__main__':
    with open("samples/test.png", "rb") as image_file:
        encoded_string = image_file.read()
    proxy = RecognitionProxy()
    proxy.recognize(encoded_string)
