import base64
import tempfile
import os

import easyocr


class ImageOCRService:
    def __init__(self):
        # lang_list 支持中英混排；gpu=False 强制 CPU 推理
        self.reader = easyocr.Reader(["ch_sim", "en"], gpu=False)

    def ocr_from_file(self, image_path: str) -> str:
        """从文件路径识别图片文字，返回拼接后的纯文本。"""
        result = self.reader.readtext(image_path, detail=0)
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
        """将 easyocr 的原始结果（detail=0 时为纯文本列表）拼接为字符串。"""
        return "\n".join(line.strip() for line in ocr_result if line.strip())


if __name__ == "__main__":
    ocr_service = ImageOCRService()
    text = ocr_service.ocr_from_file("test_img.png")
    print(text)
