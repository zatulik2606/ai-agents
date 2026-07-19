import re

_MEDICAL_MARKERS = (
    "диабет",
    "инсулин",
    "гипо",
    "гипер",
    "глюкоз",
    "сахар",
    "хе",
    "хлебн",
    "укол",
    "инъекц",
    "кето",
    "глюкометр",
)

_CHITCHAT_PHRASES = (
    "привет",
    "здравствуй",
    "здравствуйте",
    "добрый день",
    "добрый вечер",
    "доброе утро",
    "hi",
    "hello",
    "как дела",
    "как ты",
    "как сам",
    "спасибо",
    "благодарю",
    "пока",
    "до свидания",
    "ок",
    "хорошо",
    "понятно",
    "ясно",
)


def _normalize(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[!?.…]+$", "", cleaned)
    return " ".join(cleaned.split())


def is_chitchat(text: str) -> bool:
    """Приветствия, благодарности и small talk — без rag_search."""
    normalized = _normalize(text)
    if not normalized:
        return False

    if any(marker in normalized for marker in _MEDICAL_MARKERS):
        return False

    if normalized in _CHITCHAT_PHRASES:
        return True

    for phrase in _CHITCHAT_PHRASES:
        if normalized.startswith(f"{phrase} "):
            return True

    if normalized.startswith("спасибо"):
        return True

    if normalized.startswith("привет") and len(normalized) <= 30:
        return True

    return False


_REFERENCE_STARTERS = (
    "что такое",
    "что значит",
    "почему",
    "зачем",
    "отчего",
    "как леч",
    "как прояв",
    "какие симптом",
    "какие признак",
    "что делать",
    "чем опас",
    "можно ли",
    "нужно ли",
    "сколько инъек",
    "сколько раз",
    "расскажи про",
    "объясни",
)


_PRODUCT_MARKERS = (
    "полоск",
    "тест-полос",
    "cgm",
    "libre",
    "freestyle",
    "dexcom",
    "contour",
    "accu-chek",
    "акку-чек",
    "onetouch",
    "omnipod",
    "омнипод",
    "medtronic",
    "guardian",
    "минimed",
    "minimed",
    "novopen",
    "solostar",
    "humapen",
    "ланцет",
    "расходник",
    "сенсор",
    "инфузион",
)

_NUTRITION_MARKERS = (
    "кбжу",
    "углевод",
    "белк",
    "жир",
    "калор",
    "питательн",
)

_BOLUS_MARKERS = (
    "болюс",
    "докол",
    "на сколько ед",
    "сколько ед",
    "сколько хе",
    " х.е",
    "хе в",
    "ед на",
    "е.д. на",
    "коэффициент",
    "чувствительност",
)


def is_product_or_nutrition_question(text: str) -> bool:
    """Вопросы про расходники / КБЖУ / расчёт болюса — mode=tools (MCP)."""
    if is_chitchat(text):
        return False
    normalized = _normalize(text)
    if not normalized:
        return False
    if any(marker in normalized for marker in _PRODUCT_MARKERS):
        return True
    if any(marker in normalized for marker in _NUTRITION_MARKERS):
        return True
    if any(marker in normalized for marker in _BOLUS_MARKERS):
        return True
    return False


def is_reference_question(text: str) -> bool:
    """Справочный вопрос по диабету — агент обязан вызвать rag_search."""
    if is_chitchat(text):
        return False
    if is_product_or_nutrition_question(text):
        return False

    normalized = _normalize(text)
    if not normalized:
        return False

    if any(normalized.startswith(starter) for starter in _REFERENCE_STARTERS):
        return True

    question_words = ("что", "почему", "как", "когда", "где", "зачем", "сколько")
    if any(marker in normalized for marker in _MEDICAL_MARKERS) and any(
        word in normalized.split()[:3] for word in question_words
    ):
        return True

    return "?" in text and any(marker in normalized for marker in _MEDICAL_MARKERS)
