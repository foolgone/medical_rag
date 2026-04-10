"""
医疗工具集 - 供Agent调用
"""
from langchain.tools import tool
from typing import Optional
from loguru import logger


@tool
def analyze_symptoms(symptoms: str, duration: str = "未知") -> str:
    """
    分析患者症状，提供初步疾病方向和建议

    Args:
        symptoms: 症状描述，如"头痛、发热、咳嗽"
        duration: 症状持续时间，如"3天"

    Returns:
        症状分析结果和建议
    """
    logger.info(f"调用症状分析工具: {symptoms}, 持续{duration}")

    try:
        # 导入RAG检索工具
        from tools.rag_tool import search_medical_knowledge

        # 构建检索查询
        query = f"{symptoms} 可能疾病 诊断建议"

        # 检索相关医学知识
        knowledge = search_medical_knowledge.invoke(query)

        if knowledge and "未找到" not in knowledge:
            return f"""📋 症状分析报告
━━━━━━━━━━━━━━━━━━
症状: {symptoms}
持续时间: {duration}

 相关医学知识:
{knowledge}

⚠️ 建议:
1. 以上信息仅供参考
2. 如症状持续或加重，请及时就医
3. 建议前往相关专科进行详细检查"""
        else:
            return f"""📋 症状分析
━━━━━━━━━━━━━━━━━━
症状: {symptoms}
持续时间: {duration}

⚠️ 提示:
知识库中未找到相关信息，建议:
1. 详细描述症状特点
2. 咨询专业医生
3. 必要时进行相关检查"""
    except Exception as e:
        logger.error(f"症状分析失败: {e}")
        return f"⚠️ 分析失败: {str(e)}，建议咨询专业医生"


@tool
def calculate_bmi(weight: float, height: float) -> str:
    """
    计算BMI并给出健康评估

    Args:
        weight: 体重（公斤）
        height: 身高（厘米）

    Returns:
        BMI计算结果和健康建议
    """
    logger.info(f"调用BMI计算工具: 体重{weight}kg, 身高{height}cm")

    try:
        height_m = height / 100
        bmi = round(weight / (height_m ** 2), 2)

        if bmi < 18.5:
            category = "体重过轻"
            advice = "建议增加营养摄入，适当增重"
        elif bmi < 24:
            category = "正常范围"
            advice = "体重正常，保持健康饮食和运动习惯"
        elif bmi < 28:
            category = "超重"
            advice = "建议控制饮食，增加运动量"
        else:
            category = "肥胖"
            advice = "建议咨询营养师，制定减重计划，定期体检"

        return f"""📊 BMI健康评估
━━━━━━━━━━━━━━━━━━
体重: {weight} kg
身高: {height} cm
BMI: {bmi}
分类: {category}

💡 建议:
{advice}

⚠️ 注意:
BMI仅为参考指标，建议结合体脂率、腰围等综合评估"""
    except Exception as e:
        logger.error(f"BMI计算失败: {e}")
        return f"⚠️ 计算失败: {str(e)}"


@tool
def classify_blood_pressure(systolic: float, diastolic: float) -> str:
    """
    根据血压值判断分级

    Args:
        systolic: 收缩压（mmHg）
        diastolic: 舒张压（mmHg）

    Returns:
        血压分级和建议
    """
    logger.info(f"调用血压分级工具: {systolic}/{diastolic} mmHg")

    try:
        if systolic < 120 and diastolic < 80:
            level = "正常血压"
            advice = "血压正常，保持健康生活方式"
        elif systolic < 140 or diastolic < 90:
            level = "1级高血压（轻度）"
            advice = "建议改善生活方式，低盐饮食，定期监测"
        elif systolic < 160 or diastolic < 100:
            level = "2级高血压（中度）"
            advice = "建议就医，可能需要药物治疗"
        else:
            level = "3级高血压（重度）"
            advice = "⚠️ 请立即就医，需要积极治疗"

        return f""" 血压评估
━━━━━━━━━━━━━━━━━━
收缩压: {systolic} mmHg
舒张压: {diastolic} mmHg
分级: {level}

💡 建议:
{advice}

📌 正常血压范围: <120/80 mmHg
⚠️ 以上仅供参考，请以医生诊断为准"""
    except Exception as e:
        logger.error(f"血压分级失败: {e}")
        return f"⚠️ 分级失败: {str(e)}"


@tool
def recommend_department(symptoms: str) -> str:
    """
    根据症状推荐就诊科室

    Args:
        symptoms: 症状描述

    Returns:
        推荐科室和就诊建议
    """
    logger.info(f"调用科室推荐工具: {symptoms}")

    dept_map = {
        "头痛": {"dept": "神经内科", "note": "可能需要做头颅CT/MRI"},
        "头晕": {"dept": "神经内科/耳鼻喉科", "note": "排除脑血管问题或耳石症"},
        "咳嗽": {"dept": "呼吸内科", "note": "可能需要胸部X光或CT"},
        "胸痛": {"dept": "心内科/急诊科", "note": "⚠️ 胸痛需警惕心脏问题，建议尽快就医"},
        "胃痛": {"dept": "消化内科", "note": "可能需要胃镜检查"},
        "腹痛": {"dept": "消化内科/普外科", "note": "根据疼痛位置判断具体科室"},
        "发热": {"dept": "发热门诊/感染科", "note": "持续高热建议就医"},
        "腰痛": {"dept": "骨科/泌尿外科", "note": "排除腰椎问题或泌尿系统疾病"},
        "关节痛": {"dept": "风湿免疫科/骨科", "note": "可能需要查血常规和风湿因子"},
        "皮疹": {"dept": "皮肤科", "note": "建议拍照记录皮疹变化"},
        "失眠": {"dept": "神经内科/心理科", "note": "可能需要睡眠监测"},
        "焦虑": {"dept": "心理科/精神科", "note": "心理评估和专业指导"},
        "视力下降": {"dept": "眼科", "note": "需要验光和眼底检查"},
        "听力下降": {"dept": "耳鼻喉科", "note": "需要听力测试"},
    }

    # 匹配症状
    matched_depts = []
    for symptom, info in dept_map.items():
        if symptom in symptoms:
            matched_depts.append(info)

    if matched_depts:
        dept_list = "\n".join([f"• {d['dept']} - {d['note']}" for d in matched_depts])
        return f"""🏥 科室推荐
━━━━━━━━━━━━━━━━━━
症状: {symptoms}

📋 推荐科室:
{dept_list}

💡 就诊建议:
1. 初次就诊建议先到综合内科
2. 携带既往病历和检查报告
3. 详细描述症状起始时间和变化
4. 如症状严重，建议直接急诊"""
    else:
        return f"""🏥 科室推荐
━━━━━━━━━━━━━━━━━━
症状: {symptoms}

📋 推荐科室: 内科（初诊）

💡 建议:
1. 初诊建议先到内科
2. 医生会根据具体情况转诊到专科
3. 请详细描述症状特点

⚠️ 如症状严重或突发，请直接前往急诊科"""


# 导出工具列表
medical_tools = [
    analyze_symptoms,
    calculate_bmi,
    classify_blood_pressure,
    recommend_department,
]
