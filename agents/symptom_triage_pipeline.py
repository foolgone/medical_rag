"""症状咨询多阶段编排（确定性流水线）。

目标：宁可漏判也不误判。仅对非常明确的“本人/家属出现症状并求处理建议”问题触发。

流水线阶段：
1) 症状抽取
2) 风险分层
3) 知识检索（复用现有 RAG 链路）
4) 科室推荐（复用现有映射规则）

最终回答由上层（MedicalAgent）调用 LLM 汇总生成，并可按需流式输出。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


FIRST_PERSON_TERMS = (
    "我",
    "本人",
    "孩子",
    "宝宝",
    "家人",
    "父母",
    "妈妈",
    "爸爸",
    "老人",
    "孕妇",
)

HELP_INTENT_TERMS = (
    "怎么办",
    "严重吗",
    "要不要去医院",
    "要去医院吗",
    "该看什么科",
    "挂什么科",
    "需要检查吗",
    "怎么处理",
    "怎么缓解",
    "如何处理",
    "要紧吗",
)

# 偏保守：症状词表用于“触发”，不是用于抽取完整实体。
SYMPTOM_TRIGGER_TERMS = (
    "发热",
    "发烧",
    "咳嗽",
    "胸痛",
    "腹痛",
    "头痛",
    "头晕",
    "恶心",
    "呕吐",
    "腹泻",
    "皮疹",
    "呼吸困难",
    "气短",
    "心悸",
    "乏力",
    "疼痛",
    "出血",
    "昏厥",
    "晕倒",
)

CALC_EXCLUDE_TERMS = (
    "BMI",
    "身高",
    "体重",
    "收缩压",
    "舒张压",
    "mmhg",
    "血糖",
    "心率",
    "体温",
    "指数",
    "计算",
    "多少算正常",
)

EXPLAIN_EXCLUDE_TERMS = (
    "是什么",
    "为什么",
    "原因",
    "机制",
    "定义",
    "区别",
    "指南",
    "原理",
    "流程",
)

DISEASE_EXPLAIN_PATTERNS = (
    "的症状有哪些",
    "怎么治疗",
    "如何治疗",
    "怎么预防",
    "如何预防",
)

TIME_HINT_TERMS = (
    "几天",
    "几小时",
    "一周",
    "两周",
    "一个月",
    "持续",
    "反复",
    "今天",
    "昨晚",
)


@dataclass
class SymptomExtraction:
    symptoms_text: str
    duration_text: str
    retrieval_query: str
    matched_symptoms: List[str]


@dataclass
class RiskAssessment:
    risk_level: str
    reasons: List[str]
    next_action: str


def should_route_to_symptom_pipeline(question: str) -> Tuple[bool, str]:
    """高精度触发：宁可漏判也不误判。"""
    q = (question or "").strip()
    if not q:
        return False, "empty"

    q_lower = q.lower()

    if any(term.lower() in q_lower for term in CALC_EXCLUDE_TERMS):
        return False, "exclude:calc"

    # 解释/科普类：如果缺少第一人称+求助意图，则直接排除
    if any(term in q for term in EXPLAIN_EXCLUDE_TERMS) and not any(t in q for t in FIRST_PERSON_TERMS):
        return False, "exclude:explain"

    if any(pat in q for pat in DISEASE_EXPLAIN_PATTERNS) and not any(t in q for t in FIRST_PERSON_TERMS):
        return False, "exclude:disease_explain"

    has_first_person = any(t in q for t in FIRST_PERSON_TERMS)
    if not has_first_person:
        return False, "miss:first_person"

    has_symptom = any(t in q for t in SYMPTOM_TRIGGER_TERMS)
    if not has_symptom:
        return False, "miss:symptom"

    has_help_intent = any(t in q for t in HELP_INTENT_TERMS)
    if not has_help_intent:
        return False, "miss:help_intent"

    return True, "match:high_precision"


_DURATION_RE = re.compile(r"(?P<num>\d{1,3})\s*(?P<unit>分钟|分|小时|时|天|日|周|星期|个月|月|年)")


def extract_symptoms(question: str) -> SymptomExtraction:
    q = (question or "").strip()

    matched = [term for term in SYMPTOM_TRIGGER_TERMS if term in q]
    symptoms_text = "、".join(matched) if matched else q

    duration_text = "未知"
    m = _DURATION_RE.search(q)
    if m:
        duration_text = f"{m.group('num')}{m.group('unit')}"
    else:
        for hint in TIME_HINT_TERMS:
            if hint in q:
                duration_text = hint
                break

    retrieval_query = f"{symptoms_text} 可能原因 处理建议 就医指征"
    return SymptomExtraction(
        symptoms_text=symptoms_text,
        duration_text=duration_text,
        retrieval_query=retrieval_query,
        matched_symptoms=matched,
    )


_HIGH_RISK_TERMS = (
    "呼吸困难",
    "气短",
    "胸痛",
    "昏厥",
    "晕倒",
    "意识模糊",
    "抽搐",
    "呕血",
    "便血",
    "黑便",
    "剧烈",
)

_MEDIUM_RISK_TERMS = (
    "高烧",
    "持续高热",
    "反复",
    "加重",
    "脱水",
    "无法进食",
    "无法饮水",
)


def assess_risk(symptoms_text: str, question: str = "") -> RiskAssessment:
    text = f"{symptoms_text} {question}".strip()

    high_hits = [t for t in _HIGH_RISK_TERMS if t in text]
    if high_hits:
        return RiskAssessment(
            risk_level="高风险",
            reasons=[f"命中高风险提示：{', '.join(high_hits)}"],
            next_action="建议尽快就医/急诊评估（尤其出现呼吸困难、胸痛、意识改变等）。",
        )

    medium_hits = [t for t in _MEDIUM_RISK_TERMS if t in text]
    if medium_hits:
        return RiskAssessment(
            risk_level="中风险",
            reasons=[f"命中中风险提示：{', '.join(medium_hits)}"],
            next_action="建议尽快线下就诊或在医生指导下处理，并密切观察症状变化。",
        )

    return RiskAssessment(
        risk_level="低风险",
        reasons=["未命中明显高风险提示（仅基于文本规则，不能替代医生判断）。"],
        next_action="可先进行对症处理与观察；若症状持续/加重或出现高风险表现，请及时就医。",
    )


def build_stage_tool_call(
    *,
    name: str,
    args: Dict[str, Any],
    stage: int,
    status: str,
    output: Optional[str] = None,
    error: Optional[str] = None,
    depends_on: Optional[List[str]] = None,
    duration_ms: Optional[int] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": name,
        "args": args or {},
        "stage": stage,
        "status": status,
    }

    if output is not None:
        payload["output"] = output
    if error is not None:
        payload["error"] = error
    if depends_on is not None:
        payload["depends_on"] = depends_on
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms

    return payload
