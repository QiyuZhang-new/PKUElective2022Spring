import os

from ..utils import xMD5


class Captcha(object):
    """A recognized captcha and, when available, its intermediate images."""

    __slots__ = ["_code", "_original", "_denoised", "_segments", "_spans"]

    def __init__(self, code, original=None, denoised=None, segments=None, spans=None):
        self._code = code
        self._original = original
        self._denoised = denoised
        self._segments = segments
        self._spans = spans

    @property
    def code(self):
        return self._code

    @property
    def original(self):
        return self._original

    @property
    def denoised(self):
        return self._denoised

    @property
    def segments(self):
        return self._segments

    @property
    def spans(self):
        return self._spans

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._code)

    def save(self, folder):
        """Save local-recognizer images; online results do not carry these images."""
        if self._original is None:
            return

        md5 = xMD5(self._original.tobytes())
        self._original.save(os.path.join(folder, "%s_original_%s.jpg" % (self._code, md5)))

        if self._denoised is not None:
            self._denoised.save(os.path.join(folder, "%s_denoised_%s.jpg" % (self._code, md5)))

        if self._segments is not None and self._spans is not None:
            for image, (start, end), char in zip(self._segments, self._spans, self._code):
                image.save(os.path.join(
                    folder,
                    "%s_%s_(%d,%d)_%s.jpg" % (self._code, char, start, end, md5),
                ))
