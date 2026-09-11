import json
import re

from langchain_openai import ChatOpenAI

from app.classifier.base import ClassificationResult, Classifier
from app.config import get_settings


class DeepSeekClassifier(Classifier):
    model = "deepseek-chat"
    model_version = "0.1.0"
    prompt_version = "0.1.0"

    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.llm_model
        self._llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key or "missing",
            base_url=settings.llm_base_url,
            temperature=0,
        )

    def classify(self, content: str, available_domains: list[str]) -> ClassificationResult:
        if not get_settings().llm_api_key:
            return ClassificationResult(
                domains=[],
                confidence=0.0,
                reason="missing llm api key",
                raw_output="",
            )

        prompt = (
            "你是企业知识库的文档分类器。只允许从下面的域中选择一个或多个，"
            "不能创造新域。\n"
            f"可用域: {', '.join(available_domains)}\n\n"
            "请根据文档内容输出 JSON，格式如下：\n"
            '{"domains": ["域1"], "confidence": 0.85, "reason": "一句话理由"}\n\n'
            f"文档内容:\n{content}\n"
        )
        resp = self._llm.invoke(prompt)
        raw = str(resp.content) if hasattr(resp, "content") else str(resp)
        payload = self._parse_json(raw)
        if payload is None:
            return ClassificationResult(domains=[], confidence=0.0, reason="unparsable output", raw_output=raw)

        domains = payload.get("domains") or []
        if isinstance(domains, str):
            domains = [domains]
        return ClassificationResult(
            domains=[d for d in domains if d in available_domains],
            confidence=float(payload.get("confidence", 0.0)),
            reason=str(payload.get("reason", "")),
            raw_output=raw,
        )

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None