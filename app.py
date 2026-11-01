"""
Resume-Match —— Streamlit 演示界面

启动方式（在项目根目录执行）：
    streamlit run app.py

说明：
- 本文件只是展示层薄壳，核心逻辑全部复用 src/ 下的真实服务代码：
    - 企业背景调研  -> src.search.ResearchBackGround （对应 POST /search 接口）
    - 简历匹配打分  -> src.match.Match               （对应 POST /resume/match 接口）
- 运行前需在项目根目录配置好 .env（API_KEY_DOUBAO / SERPER_API_KEY / Tavily_API_KEY）。
"""
import json
import os
import sys
import traceback

import streamlit as st

# 保证无论从哪个目录启动，src/ utils logger 都能被导入
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

st.set_page_config(page_title="Resume-Match | 简历匹配 Agent", page_icon="🎯", layout="wide")

try:
    from src.match import Match, WEIGHTS
    from src.search import ResearchBackGround
except Exception:
    st.error(
        "初始化失败：请确认项目根目录存在 .env，"
        "且已配置 API_KEY_DOUBAO / SERPER_API_KEY / Tavily_API_KEY"
    )
    st.code(traceback.format_exc())
    st.stop()

DIM_LABELS = {
    "hard_skill": "硬技能",
    "experience": "经验",
    "education": "学历门槛",
    "company_fit": "企业契合",
    "soft_fit": "软性素质",
}
STATUS_ICON = {"满足": "✅", "部分满足": "⚠️", "缺失": "❌"}
SAMPLE_RESUME_PATH = os.path.join(ROOT, "Data", "tmracy.json")

RESUME_PLACEHOLDER = """{
    "基本信息": {"姓名": "张三", "电话": "138****0000", "邮箱": "zhangsan@example.com"},
    "求职意向": {"目标职位": "AI 算法工程师", "工作经验": "3 年"},
    "教育背景": {"学历": "本科", "学校": "某大学", "主要课程": "..."},
    "工作经历": [{"公司名称": "某公司", "职位": "算法工程师", "工作职责": ["..."]}],
    "技能清单": {"编程语言": {"Python": "熟练掌握"}}
}"""


def render_background(bg):
    """企业背景既可能是 dict（提取成功），也可能是兜底字符串（提取失败）"""
    if isinstance(bg, dict):
        for key, value in bg.items():
            st.markdown(f"**{key}**：{value}")
    else:
        st.warning(str(bg))


def read_resume(source, uploaded, pasted):
    """根据简历来源解析出 dict，返回 (resume_dict, 错误信息)"""
    try:
        if source.startswith("🧪"):
            with open(SAMPLE_RESUME_PATH, "r", encoding="utf-8") as file:
                return json.load(file), None
        if source.startswith("📁"):
            if uploaded is None:
                return None, "请先上传简历 JSON 文件"
            return json.load(uploaded), None
        if not pasted.strip():
            return None, "请先粘贴简历 JSON 内容"
        return json.loads(pasted), None
    except Exception as e:  # JSON 语法错误、非 UTF-8 编码文件等
        return None, f"简历 JSON 解析失败：{e}"


# ---------------- 侧边栏 ----------------
with st.sidebar:
    st.title("🎯 Resume-Match")
    st.caption("JD + 企业名称 + 简历 → 联网调研企业背景 → 五维证据打分 → 加权总分（0-10）")
    st.divider()

    st.markdown("**评分权重**（总分 = Σ 子分 × 权重）")
    st.table([{"维度": DIM_LABELS[m.name], "权重": f"{m.value:.0%}"} for m in WEIGHTS])

    st.markdown("**环境变量检查**")
    for key in ("API_KEY_DOUBAO", "SERPER_API_KEY", "Tavily_API_KEY"):
        st.markdown(f"{'✅' if os.getenv(key) else '❌'} `{key}`")

    st.divider()
    st.caption("⏱ 完整匹配约 1~3 分钟（联网检索 + 多次 LLM 调用）。\n\n结果由 LLM 生成，仅供求职参考。")

# ---------------- 主界面 ----------------
st.title("简历匹配 Agent")
tab_match, tab_search = st.tabs(["🎯 简历匹配打分", "🔍 企业背景调研"])

# ============ Tab 1：完整匹配（对应 POST /resume/match） ============
with tab_match:
    col_left, col_right = st.columns(2)
    with col_left:
        company = st.text_input("企业名称 *", placeholder="例如：阿里巴巴")
        user_input = st.text_area(
            "补充说明（可选）",
            height=150,
            placeholder="例如：期望薪资 / 到岗时间 / 自我评价等，会进入 soft_fit 维度评估",
        )
    with col_right:
        jd = st.text_area("岗位描述 JD *", height=235, placeholder="粘贴完整的岗位职责与任职要求…")

    resume_options = ["📋 粘贴 JSON", "📁 上传 JSON 文件"]
    if os.path.exists(SAMPLE_RESUME_PATH):
        resume_options.append("🧪 使用示例简历（Data/tmracy.json）")
    resume_source = st.radio("简历来源", resume_options, horizontal=True)

    uploaded_file = None
    pasted_text = ""
    if resume_source.startswith("📁"):
        uploaded_file = st.file_uploader("上传简历 JSON", type=["json"])
    elif resume_source.startswith("📋"):
        pasted_text = st.text_area("粘贴简历 JSON", height=220, placeholder=RESUME_PLACEHOLDER)

    if st.button("🚀 开始匹配", type="primary", use_container_width=True):
        resume_json, err = read_resume(resume_source, uploaded_file, pasted_text)
        if not company.strip():
            st.error("请填写企业名称")
        elif not jd.strip():
            st.error("请填写岗位描述")
        elif err:
            st.error(err)
        else:
            try:
                with st.status("匹配管线运行中，全程约 1~3 分钟，请勿关闭页面…", expanded=True) as status:
                    st.write("① 企业背景调研：LLM 改写检索词 → Serper 搜索 → LLM 提取背景…")
                    match = Match(company.strip(), jd, resume_json, user_input.strip() or None)
                    st.write("② 五维证据打分：LLM 结构化输出中…")
                    dims = match.process()
                    status.update(label="✅ 匹配完成", state="complete", expanded=False)

                # 与 src.match.Match.main() 相同的加权逻辑，权重同源于 WEIGHTS
                score = round(
                    sum(WEIGHTS[name].value * dims[name].score for name in WEIGHTS.__members__), 2
                )
                st.session_state["match_result"] = {
                    "company": company.strip(),
                    "background": match.company_background,
                    "dims": dims,
                    "score": score,
                }
            except Exception:
                st.error("匹配失败，错误详情如下（logs/error.log 中也有记录）")
                st.code(traceback.format_exc())

    result = st.session_state.get("match_result")
    if result:
        dims, score = result["dims"], result["score"]
        st.divider()
        st.subheader(f"匹配报告 — {result['company']}")

        col_metric, col_bar = st.columns([1, 3])
        col_metric.metric("综合匹配分", f"{score} / 10")
        col_bar.progress(min(score / 10, 1.0))

        dim_cols = st.columns(5)
        for col, (name, label) in zip(dim_cols, DIM_LABELS.items()):
            d = dims[name]
            col.metric(label, f"{d.score}/10")
            col.caption(f"{STATUS_ICON.get(d.status, '')} {d.status} · 权重 {WEIGHTS[name].value:.0%}")

        with st.expander("📋 各维度证据与理由", expanded=True):
            for name, label in DIM_LABELS.items():
                d = dims[name]
                st.markdown(f"**{STATUS_ICON.get(d.status, '')} {label}（{d.score}/10，{d.status}）**")
                st.markdown(f"> 证据：{d.evidence}")
                st.markdown(f"理由：{d.reason}")

        col_s, col_g = st.columns(2)
        with col_s:
            st.markdown("##### ✨ 匹配亮点")
            for item in dims["strengths"]:
                st.success(item, icon="✅")
        with col_g:
            st.markdown("##### ⚠️ 差距与风险")
            for item in dims["gaps"]:
                st.warning(item, icon="⚠️")
        st.info(f"**综合总评**：{dims['overall_reason']}")

        with st.expander("🏢 企业背景调研结果"):
            render_background(result["background"])
        with st.expander("🧾 结果 JSON（与 POST /resume/match 返回的 data 字段同构）"):
            st.json(
                {
                    "strengths": dims["strengths"],
                    "gaps": dims["gaps"],
                    "overall_reason": dims["overall_reason"],
                    "score": score,
                    "company_background": result["background"],
                }
            )

# ============ Tab 2：企业背景调研（对应 POST /search） ============
with tab_search:
    st.caption("独立的企业背景调研：LLM 改写检索词 → Serper 搜索 → LLM 结构化提取，耗时约 30~100 秒。")
    search_company = st.text_input("企业名称", key="search_company", placeholder="例如：阿里巴巴")

    if st.button("🔍 开始调研", use_container_width=True):
        if not search_company.strip():
            st.error("请填写企业名称")
        else:
            try:
                with st.spinner("调研中（约 30~100 秒）…"):
                    background = ResearchBackGround(search_company.strip()).extract()
                st.session_state["search_result"] = {
                    "company": search_company.strip(),
                    "background": background,
                }
            except Exception:
                st.error("调研失败，错误详情如下")
                st.code(traceback.format_exc())

    search_result = st.session_state.get("search_result")
    if search_result:
        st.divider()
        st.subheader(f"企业背景 — {search_result['company']}")
        render_background(search_result["background"])
        if isinstance(search_result["background"], dict):
            with st.expander("🧾 原始 JSON（与 POST /search 返回的 data 字段同构）"):
                st.json(search_result["background"])
