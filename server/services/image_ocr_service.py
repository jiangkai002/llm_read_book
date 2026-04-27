import base64
import tempfile
import os

from cnocr import CnOcr
from cnstd.ppocr.rapid_detector import Config


def _default_model_root(env_name: str, app_name: str) -> str:
    """返回跨平台模型目录；Docker/服务器可用环境变量覆盖。"""
    configured = os.getenv(env_name)
    if configured:
        return configured
    if os.name == "nt":
        appdata = os.getenv("APPDATA", os.path.expanduser("~"))
        return os.path.join(appdata, app_name)
    return os.path.join(os.path.expanduser("~"), f".{app_name}")


CNOCR_ROOT = _default_model_root("CNOCR_ROOT", "cnocr")
CNSTD_ROOT = _default_model_root("CNSTD_ROOT", "cnstd")

_MODEL_FP = os.path.join(
    CNOCR_ROOT,
    "2.3",
    "densenet_lite_136-gru",
    "cnocr-v2.3-densenet_lite_136-gru-epoch=004-ft-model.onnx",
)

_DET_MODEL_FP = os.path.join(
    CNSTD_ROOT,
    "1.2",
    "ppocr",
    "ch_PP-OCRv5_det",
    "ch_PP-OCRv5_det_infer.onnx",
)


class ImageOCRService:
    def __init__(self):
        if not os.path.exists(_MODEL_FP):
            raise FileNotFoundError(f"CnOCR 识别模型不存在：{_MODEL_FP}")
        if not os.path.exists(_DET_MODEL_FP):
            raise FileNotFoundError(f"CnOCR 检测模型不存在：{_DET_MODEL_FP}")

        # cnstd 的 RapidDetector 会额外读取 model_root_dir。
        # 当前版本即使传了 det_model_fp，也可能没有自动填充该字段。
        Config.DEFAULT_CFG["model_root_dir"] = os.path.dirname(_DET_MODEL_FP)

        self.ocr = CnOcr(
            rec_model_name="densenet_lite_136-gru",
            rec_model_backend="onnx",
            rec_model_fp=_MODEL_FP,
            rec_root=CNOCR_ROOT,
            det_model_name="ch_PP-OCRv5_det",
            det_model_backend="onnx",
            det_model_fp=_DET_MODEL_FP,
            det_root=CNSTD_ROOT,
            context="cpu",
        )

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
        return "\n".join(
            item["text"].strip() for item in ocr_result if item.get("text", "").strip()
        )


if __name__ == "__main__":
    ocr_service = ImageOCRService()
    text = ocr_service.ocr_from_file("test.png")
    print(text)
