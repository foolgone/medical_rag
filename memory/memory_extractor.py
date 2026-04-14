"""
结构化事实记忆提取器
"""
import re
from typing import Dict, List


class MemoryExtractor:
    """从问答文本中抽取高价值事实记忆。"""

    DISEASE_KEYWORDS = [
        "高血压",
        "糖尿病",
        "冠心病",
        "哮喘",
        "慢阻肺",
        "甲状腺疾病",
    ]
    ALLERGY_KEYWORDS = [
        "青霉素",
        "头孢",
        "阿司匹林",
        "布洛芬",
    ]
    MEDICATION_KEYWORDS = [
        "二甲双胍",
        "胰岛素",
        "氨氯地平",
        "缬沙坦",
        "阿托伐他汀",
        "降压药",
    ]
    SYMPTOM_KEYWORDS = [
        "发热",
        "头痛",
        "咳嗽",
        "腹痛",
        "胸闷",
        "气短",
        "恶心",
        "呕吐",
        "乏力",
        "头晕",
    ]

    def extract_facts(self, question: str, answer: str, context: str = "") -> List[Dict]:
        """抽取结构化事实。"""
        text = " ".join(part for part in [question, answer, context] if part)
        facts: List[Dict] = []

        facts.extend(self._extract_age(text))
        facts.extend(self._extract_gender(text))
        facts.extend(self._extract_keyword_facts(question, self.DISEASE_KEYWORDS, "disease_history"))
        facts.extend(self._extract_keyword_facts(question, self.ALLERGY_KEYWORDS, "allergy"))
        facts.extend(self._extract_keyword_facts(question, self.MEDICATION_KEYWORDS, "medication"))
        facts.extend(self._extract_symptoms(question))

        return self.merge_fact_candidates(facts)

    @staticmethod
    def merge_fact_candidates(items: List[Dict]) -> List[Dict]:
        """按 fact_type + fact_key 去重，保留置信度更高的一项。"""
        merged = {}
        for item in items:
            key = (item["fact_type"], item["fact_key"])
            current = merged.get(key)
            if current is None or item.get("confidence", 0) >= current.get("confidence", 0):
                merged[key] = item
        return list(merged.values())

    @staticmethod
    def _build_fact(
        fact_type: str,
        fact_key: str,
        fact_value: str,
        confidence: float = 0.9,
        source: str = "user_explicit",
    ) -> Dict:
        return {
            "fact_type": fact_type,
            "fact_key": fact_key,
            "fact_value": fact_value,
            "confidence": confidence,
            "source": source,
            "status": "active",
        }

    def _extract_age(self, text: str) -> List[Dict]:
        facts = []
        match = re.search(r"(\d{1,3})\s*岁", text)
        if match:
            facts.append(self._build_fact("profile", "age", match.group(1), confidence=0.98))
        return facts

    def _extract_gender(self, text: str) -> List[Dict]:
        facts = []
        lowered = text.lower()
        if "女性" in text or re.search(r"\b女\b", text):
            facts.append(self._build_fact("profile", "gender", "女", confidence=0.98))
        elif "男性" in text or re.search(r"\b男\b", text):
            facts.append(self._build_fact("profile", "gender", "男", confidence=0.98))
        elif "female" in lowered:
            facts.append(self._build_fact("profile", "gender", "女", confidence=0.95))
        elif "male" in lowered:
            facts.append(self._build_fact("profile", "gender", "男", confidence=0.95))
        return facts

    def _extract_keyword_facts(self, text: str, keywords: List[str], fact_type: str) -> List[Dict]:
        facts = []
        for keyword in keywords:
            if keyword not in text:
                continue
            if self._looks_like_question(text, keyword):
                continue
            facts.append(
                self._build_fact(
                    fact_type=fact_type,
                    fact_key=keyword,
                    fact_value=keyword,
                    confidence=0.88,
                )
            )
        return facts

    def _extract_symptoms(self, text: str) -> List[Dict]:
        facts = []
        for keyword in self.SYMPTOM_KEYWORDS:
            if keyword not in text:
                continue
            duration = self._extract_duration(text, keyword)
            fact_value = duration or keyword
            facts.append(
                self._build_fact(
                    fact_type="persistent_symptom",
                    fact_key=keyword,
                    fact_value=fact_value,
                    confidence=0.82 if duration else 0.75,
                )
            )
        return facts

    @staticmethod
    def _extract_duration(text: str, symptom: str) -> str:
        pattern = rf"{re.escape(symptom)}.*?(\d+\s*(天|周|个月))"
        match = re.search(pattern, text)
        if match:
            return f"{symptom}{match.group(1)}"

        reverse_pattern = rf"(\d+\s*(天|周|个月)).*?{re.escape(symptom)}"
        reverse_match = re.search(reverse_pattern, text)
        if reverse_match:
            return f"{symptom}{reverse_match.group(1)}"
        return symptom

    @staticmethod
    def _looks_like_question(text: str, keyword: str) -> bool:
        question_patterns = [
            f"是不是{keyword}",
            f"会不会是{keyword}",
            f"可能是{keyword}",
            f"会是{keyword}吗",
            f"对{keyword}过敏吗",
        ]
        return any(pattern in text for pattern in question_patterns)
