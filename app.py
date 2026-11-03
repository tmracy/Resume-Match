"""
Resume-Match —— Streamlit 演示界面

启动方式（在项目根目录执行）：
    streamlit run app.py

说明：
- 本文件只是展示层薄壳，核心逻辑复用 src/ 下的真实服务代码。
- 批量匹配在本文件内完成：上传 CSV + PDF，结果只留在内存里供下载。
- 企业背景调研 -> src.search.ResearchBackGround （对应 POST /search 接口）
- 运行前需在项目根目录配置好 .env（API_KEY_DOUBAO / SERPER_API_KEY / Tavily_API_KEY）。
"""
import io
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st

# 保证无论从哪个目录启动，src/ utils logger 都能被导入
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

st.set_page_config(page_title="Resume-Match | 简历匹配 Agent", page_icon="🎯", layout="wide")

try:
    from src.data_process import Data
    from src.main import Main
    from src.match import Match, WEIGHTS
    from src.remuse_analyze import Analyze
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
class MemoryAnalyze(Analyze):
    """沿用 Analyze.main 的分析流程，但不把结果写到磁盘。"""

    def download(self, path, data):
        return


def run_uploaded(job_file, resume_file):
    processor = Data()
    job_data = processor.process(io.BytesIO(job_file.getvalue()))
    resume_data = processor.pdf_to_text(io.BytesIO(resume_file.getvalue()))

    def one(data):
        final = Match(data["name"], data["job"], resume_data).main()
        data.update(final)
        return data

    with ThreadPoolExecutor(max_workers=8) as executor:
        result = list(executor.map(one, job_data))
    if not result:
        raise ValueError("职位文件里没有可用岗位")

    analyzed = MemoryAnalyze(result, None, resume_data).main()
    df = pd.DataFrame(analyzed)
    df["打招呼语"] = df["final_result"].apply(lambda x: Main._greetings(x) or "error")
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()


def render_background(bg):
    """企业背景既可能是 dict（提取成功），也可能是兜底字符串（提取失败）"""
    if isinstance(bg, dict):
        for key, value in bg.items():
            st.markdown(f"**{key}**：{value}")
    else:
        st.warning(str(bg))


# ---------------- 侧边栏 ----------------
with st.sidebar:
    st.title("🎯 Resume-Match")
    st.caption("上传职位 CSV 和简历 PDF，批量匹配并生成求职分析。文件只在内存中处理。")
    st.divider()

    st.markdown("**评分权重**（总分 = Σ 子分 × 权重）")
    st.table([{"维度": DIM_LABELS[m.name], "权重": f"{m.value:.0%}"} for m in WEIGHTS])

    st.divider()
    st.caption("⏱ 岗位较多时可能需要几十分钟。\n\n结果由 LLM 生成，仅供求职参考。")

# ---------------- 主界面 ----------------
st.title("简历匹配 Agent")
st.caption("职位 CSV 需要有 JD 列。简历为 PDF。处理过程和下载内容都不写入磁盘。")
job_file = st.file_uploader("职位 CSV")
resume_file = st.file_uploader("简历 PDF")

if st.button("🚀 开始跑", type="primary", use_container_width=True):
    if job_file is None:
        st.error("请上传职位 CSV")
    elif resume_file is None:
        st.error("请上传简历 PDF")
    elif not job_file.name.lower().endswith(".csv"):
        st.error("职位文件请上传 .csv")
    elif not resume_file.name.lower().endswith(".pdf"):
        st.error("简历请上传 .pdf")
    else:
        try:
            with st.status("批量跑批中，岗位较多时可能需要几十分钟，请勿关闭页面…", expanded=True) as status:
                csv_text = run_uploaded(job_file, resume_file)
                status.update(label="✅ 跑完了", state="complete", expanded=False)
            st.session_state["batch_result"] = csv_text
        except KeyError:
            st.error("职位 CSV 需要包含 JD 列")
        except Exception:
            st.error("跑批失败，错误详情如下（logs/error.log 中也有记录）")
            st.code(traceback.format_exc())

batch = st.session_state.get("batch_result")
if batch:
    st.divider()
    st.download_button(
        "下载 CSV",
        data=batch.encode("utf-8-sig"),
        file_name="final_job_analyze.csv",
        mime="text/csv",
    )

st.divider()
with st.expander("企业背景调研"):
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
