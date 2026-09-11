import re

# 标准字段 -> 别名
FIELD_ALIASES: dict[str, list[str]] = {
    "name": ["姓名", "客户姓名", "name", "customer_name"],
    "company": ["公司", "公司名", "单位", "company"],
    "phone": ["手机号", "手机", "电话", "phone", "mobile"],
    "email": ["邮箱", "email", "mail"],
    "city": ["城市", "所在城市", "city"],
}

FILENAME_KEYWORDS = ["客户", "合作伙伴", "customer", "partner"]

PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

_alias_to_field: dict[str, str] = {}
for field, aliases in FIELD_ALIASES.items():
    for alias in aliases:
        _alias_to_field[alias.lower()] = field


def normalize_fields(fields: dict) -> dict:
    """把原始字段键归一化到标准字段；未命中的保留原键。"""
    normalized: dict = {}
    for key, value in fields.items():
        canonical = _alias_to_field.get(str(key).strip().lower())
        if canonical is not None:
            normalized[canonical] = value
        else:
            normalized[str(key)] = value
    return normalized


def extract_pii(text: str) -> dict:
    """从文本抽取手机号与邮箱。"""
    phones = PHONE_RE.findall(text)
    emails = EMAIL_RE.findall(text)
    result: dict = {}
    if phones:
        result["phone"] = phones[0]
    if emails:
        result["email"] = emails[0]
    return result


def filename_hit(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in FILENAME_KEYWORDS)


def fields_hit(fields: dict | None) -> bool:
    if not fields:
        return False
    return any(k in FIELD_ALIASES for k in fields.keys())