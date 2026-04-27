import base64
import tempfile
import os

from cnocr import CnOcr
from cnstd.ppocr.rapid_detector import Config


def _default_cnstd_root() -> str:
    if os.name == "nt":
        return os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "cnstd")
    return os.path.join(os.path.expanduser("~"), ".cnstd")


# cnstd 的 RapidDetector 默认 model_root_dir 为 None，必须手动补全，否则路径拼接报 TypeError
Config.DEFAULT_CFG["model_root_dir"] = os.getenv("CNSTD_ROOT", _default_cnstd_root())


class ImageOCRService:

    def __init__(self):
        os.environ.setdefault("HTTP_PROXY", "http://localhost:7897")
        os.environ.setdefault("HTTPS_PROXY", "http://localhost:7897")
        self.ocr = CnOcr()

    def ocr_from_file(self, image_path: str) -> str:
        """从文件路径识别图片文字，返回拼接后的纯文本。"""
        result = self.ocr.ocr(image_path)
        return self._extract_text(result)

    def ocr_from_base64(self, image_base64: str) -> str:
        """从 Base64 编码的图片识别文字，返回拼接后的纯文本。"""
        image_data = base64.b64decode(image_base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name
        try:
            return self.ocr_from_file(tmp_path)
        finally:
            os.unlink(tmp_path)

    def _extract_text(self, ocr_result: list) -> str:
        """将 CnOCR 的原始结果展平为纯文本，每行以换行符分隔。
        CnOCR 返回格式：[{"text": "...", "score": ...}, ...]
        """
        return "\n".join(item["text"].strip() for item in ocr_result
                         if item.get("text", "").strip())


if __name__ == "__main__":
    ocr_service = ImageOCRService()
    text = ocr_service.ocr_from_file("test.png")
    print(text)
