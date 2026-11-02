# Resume-Match

> 上传一份职位 CSV 和一份简历 PDF，程序会逐个岗位联网调研企业背景，由 LLM 完成五个维度的证据化评估，再由代码按权重聚合出 0–10 的匹配分，最后为每个岗位生成一份求职决策分析，整理成 CSV 下载。

核心思路：**检索 → 抽取 → 结构化评估 → 确定性聚合 → 求职分析**。总分不由单次 prompt 直接生成，而是由程序对五个维度的子分加权计算，保证评分过程可控、可审计。

三种使用方式：

| 方式 | 入口 | 适合场景 |
|---|---|---|
| Streamlit 网页 | `app.py` | 上传文件批量跑，结果在浏览器下载，文件不落盘 |
| 本地批处理 | `src/main.py` 的 `Main` | 本地脚本跑批，中间结果和最终结果写到项目根目录 |
| HTTP API | `entry/server.py` | 单个岗位匹配、单独查企业背景，供其他服务调用 |

## 效果示例

同一份 NLP / 大模型方向的简历，分别匹配两类岗位：

| 岗位类型 | 总分 | 结论摘要 |
|---|---|---|
| 大模型 Agent 算法岗 | 8.65 / 10 | 硬技能与经验高度匹配，学历为主要风险点 |
| CV 视觉算法岗（要求 C++ / TensorRT） | 3.25 / 10 | 无 CV 经验、缺 C++，硬技能维度存在严重缺口 |

两类岗位的得分差超过 5 分，评分对岗位差异具备区分度，而非集中在中间分数段。

## 架构

### 批量流程（Streamlit 与 main.py）

```mermaid
flowchart LR
    A["职位 CSV<br/>JD 列"] --> B["data_process.py<br/>提取公司名、职位链接"]
    R["简历 PDF"] --> C["data_process.py<br/>pypdf 转文本"]
    B --> D["match.py<br/>每个岗位：企业调研 + 五维打分<br/>8 线程并行"]
    C --> D
    D --> E["remuse_analyze.py<br/>求职决策分析<br/>8 线程并行"]
    C --> E
    E --> F["CSV 结果"]
```

### 单个岗位的匹配管线（match.py）

```mermaid
flowchart LR
    A[企业名称] --> B["LLM 改写检索词<br/>rewrite_query.md"]
    B --> C["Serper (Google) 搜索"]
    C --> D["LLM 抽取企业背景<br/>extract_company_background.md"]
    D --> E["LLM 五维证据打分<br/>match_score.md<br/>Pydantic 结构化输出"]
    F[岗位 JD] --> E
    G["简历（PDF 文本或 JSON）"] --> E
    H[用户补充说明] --> E
    E --> I["Python 加权聚合<br/>WEIGHTS"]
    I --> J["score 0-10<br/>+ 亮点 / 差距 / 总评<br/>+ 企业背景"]
```

### 设计要点

1. **检索词改写，不直接搜索企业名**：企业名称先经 LLM 标准化补全，并改写为面向求职场景的检索词（公司简介、成立时间、团队规模、融资情况等）；改写失败时自动降级为兜底查询语句。
2. **证据先行的结构化打分**：每个维度按 `evidence → reason → status → score` 的固定顺序产出，证据必须引用简历或 JD 原文，无证据则标记"缺失"并降低分数。输出格式由 Pydantic 模型（`Literal` 状态枚举 + `ge/le` 分数边界）配合 `with_structured_output` 强约束。
3. **总分由代码计算**：LLM 仅输出五个 0–10 的维度子分，总分由程序按 `WEIGHTS` 权重表加权求和。权重可调整、结果可复算，避免大模型计算总分时引入的算术误差。
4. **全链路兜底与可观测**：每一步 JSON 解析失败均有降级路径；loguru 日志按 info / error 双文件分流（9 MB 轮转、保留 30 天），关键阶段带耗时埋点。
5. **岗位间并行**：单个岗位内部的检索和 LLM 调用有先后依赖，按顺序执行；不同岗位之间互不依赖，匹配和分析两步各用 8 个线程并行。

### 评分维度与权重

| 维度 | 评估内容 | 权重 |
|---|---|---|
| `hard_skill` | 编程语言、框架、工具、技术栈是否匹配 JD | 0.35 |
| `experience` | 工作年限、项目复杂度、岗位职责相关性 | 0.30 |
| `company_fit` | 结合企业背景评估候选人与公司的契合度 | 0.20 |
| `education` | 学历、专业、证书等硬性门槛 | 0.10 |
| `soft_fit` | 稳定性、潜力、软技能等加减分因素 | 0.05 |

## 项目结构

```
Resume-Match/
├── app.py                          # Streamlit 网页：上传 CSV + PDF 批量跑，内存处理后下载 CSV
├── requirements.txt
├── utils.py                        # LLM 客户端、计时装饰器、根路径
├── logger.py                       # loguru 日志配置（stdout + info.log + error.log）
├── gunicorn.py                     # gunicorn 配置（2 worker × 4 线程，timeout 180s）
├── entry/
│   └── server.py                   # Flask 入口：/healthy /resume/match /search
├── src/
│   ├── search.py                   # 企业背景调研：改写 → Serper 搜索 → LLM 抽取
│   ├── match.py                    # 五维打分 + WEIGHTS 加权聚合
│   ├── data_process.py             # 职位 CSV 解析（公司名、职位链接）与简历 PDF 转文本
│   ├── remuse_analyze.py           # 逐岗位求职决策分析（真实日常、坑点、话术、面试重点、建议）
│   └── main.py                     # 本地批处理 Main：预处理 → 匹配 → 分析，结果写入磁盘
├── Prompt/
│   ├── rewrite_query.md            # 企业名 → 检索词
│   ├── extract_company_background.md  # 搜索结果 → 求职者视角的企业背景 JSON
│   └── match_score.md              # 五维证据打分
├── Data/                           # 简历 JSON 数据目录
└── logs/                           # 运行日志（已 gitignore）
```

## 快速开始

### 1. 安装依赖

需要 Python 3.10 及以上版本。

```bash
pip install -r requirements.txt
```

### 2. 配置 .env（项目根目录）

```ini
API_KEY_DOUBAO=火山方舟 ARK API Key
SERPER_API_KEY=serper.dev API Key
Tavily_API_KEY=tavily.com API Key
```

说明：

- **LLM**：默认使用火山方舟（豆包）的 OpenAI 兼容接口，`utils.py` 中的 `model` 为推理接入点 ID（`ep-...`），需替换为自己的接入点；如需切换其他 OpenAI 兼容服务，修改 `base_url` 与 `model` 即可。
- **SERPER_API_KEY**：联网检索的主链路，走 Google 搜索。
- **Tavily_API_KEY**：`src/search.py` 导入时会初始化 Tavily 客户端，因此需要配置；当前检索主链路不经过它。

### 3. 准备输入文件

**职位 CSV**：必须有一列叫 `JD`，每行一个岗位的完整描述。程序会用正则从 JD 文本里提取：

- `公司：xxx` 或 `公司:xxx` → 公司名，用于联网调研企业背景（缺失时公司名为空）
- `职位链接：xxx` → 职位链接，原样带到结果里（缺失时为空）

示例：

```csv
JD
"公司：阿里巴巴
职位链接：https://example.com/job/123
岗位职责：负责大模型 Agent 应用研发……
任职要求：熟悉 Python、LangChain……"
```

**简历 PDF**：普通文本型 PDF 即可，程序用 pypdf 提取全部页面文字。扫描件图片 PDF 提取不到文字。

### 4a. 网页使用（Streamlit）

在项目根目录执行：

```bash
streamlit run app.py
```

浏览器打开 `http://localhost:8501`：

1. 上传「职位 CSV」和「简历 PDF」
2. 点击「开始跑」，等待全部岗位完成（岗位多时需要几十分钟，期间不要关闭页面）
3. 点击「下载 CSV」得到 `final_job_analyze.csv`

上传的文件和生成的 CSV 都只在内存中处理，不写入服务器磁盘；`logs/` 下仍会记录运行日志（包含匹配结论和企业背景）。页面底部的「企业背景调研」可以单独查一家公司，对应 `POST /search`。

> macOS 上如果 Chrome 点击「Browse files」没有弹出选文件窗口，通常是系统隐私设置没给 Chrome 文件访问权限：到「系统设置 → 隐私与安全性」给 Chrome 授权后，用 Command+Q 完全退出再打开。也可以直接把文件拖进上传框。

### 4b. 本地批处理（main.py）

`src/main.py` 提供 `Main` 类，没有命令行入口，需要在项目根目录写几行 Python 调用：

```python
from src.main import Main

main = Main(
    input_job_path="招聘信息.csv",          # 输入：职位 CSV
    input_resume_path="简历.pdf",           # 输入：简历 PDF
    resume_name="resume.json",              # 中间文件：简历文本
    job_name="job_data.json",               # 中间文件：解析后的职位列表
    job_process_name="match_result.json",   # 中间文件：匹配结果
    job_final_name="final_job_analyze.json",  # 输出：分析结果 JSON
)
main.analyze("final_job_analyze.csv")        # 输出：分析结果 CSV
```

`analyze()` 依次执行三步：

1. `data_process()`：解析 CSV 和 PDF，写出 `job_name` 和 `resume_name`
2. `match()`：8 线程并行做企业调研 + 五维打分，写出 `job_process_name`
3. 调用 `Analyze` 做求职分析，写出 `job_final_name`（JSON），再写出 `analyze()` 参数指定的 CSV

`resume_name`、`job_name`、`job_process_name`、`job_final_name` 都会拼到项目根目录下；`analyze()` 的 CSV 路径按原样使用，相对路径相对于当前工作目录。这些文件包含个人简历和求职信息，不要提交到仓库。

### 输出字段

网页下载的 CSV 和 `main.py` 生成的 CSV 字段一致，每行一个岗位：

| 字段 | 含义 |
|---|---|
| `job` | JD 原文 |
| `name` | 公司名 |
| `link` | 职位链接 |
| `strengths` | 匹配亮点 |
| `gaps` | 差距或风险 |
| `overall_reason` | 综合总评 |
| `score` | 0–10 加权总分 |
| `company_background` | 企业背景（JSON 字符串） |
| `final_result` | 求职决策分析：真实日常、利弊与坑点、匹配度、打招呼话术、面试重点、最终建议 |

### 4c. API 服务（Flask + gunicorn）

```bash
gunicorn -c gunicorn.py entry.server:app
```

服务监听 `0.0.0.0:8999`。

## API 文档

### GET /healthy

健康检查。

```json
{"code": 0, "info": "Success"}
```

### POST /resume/match

完整匹配管线：企业背景调研 + 五维打分 + 加权总分。

请求体：

```json
{
    "name": "阿里巴巴",
    "job_description": "岗位职责与任职要求全文…",
    "resume_json": { "见下方简历 JSON 格式": "…" },
    "user_input": "可选的补充说明，如期望薪资、到岗时间等"
}
```

成功响应：

```json
{
    "code": 0,
    "info": "success",
    "data": {
        "strengths": ["匹配亮点1", "匹配亮点2"],
        "gaps": ["差距或风险1", "差距或风险2"],
        "overall_reason": "综合总评，3-5 句话",
        "score": 7.55,
        "company_background": {
            "公司简介": "…",
            "成立时间": "…",
            "公司规模": "…",
            "融资出资": "…",
            "主营业务": "…",
            "发展阶段": "…",
            "求职参考点": "…"
        }
    }
}
```

`company_background` 与 `POST /search` 的 `data` 同结构。抽取失败时，这个字段是说明字符串，不是对象。

失败响应：`{"code": 1, "info": "failed", "data": "<traceback 文本>"}`

### POST /search

独立的企业背景调研。

请求体：`{"name": "阿里巴巴"}`

成功响应：

```json
{
    "code": 0,
    "info": "success",
    "data": {
        "公司简介": "互联网行业头部企业，业务覆盖电商、云计算等领域…",
        "成立时间": "1999 年，约 27 年",
        "公司规模": "…",
        "融资出资": "…",
        "主营业务": "…",
        "发展阶段": "成熟期，已上市…",
        "求职参考点": "…"
    }
}
```

检索不到的字段如实填"未知"，不做编造。失败响应与 `/resume/match` 一致：`{"code": 1, "info": "failed", "data": "<traceback 文本>"}`

### 耗时说明

参考耗时：企业背景调研约 20~100 秒，五维打分约 1~2 分钟，单次完整匹配约 1.5~3.5 分钟（联网检索 + 多次 LLM 调用，单个请求内部按顺序执行）。gunicorn 的 `timeout=180` 据此设置。

批量跑时每个岗位还要多一次求职分析调用。岗位之间用 8 线程并行，实际耗时取决于岗位数量和 LLM / Serper 接口的限流情况。批量任务请用 Streamlit 或 `main.py`，不要放进单个 HTTP 请求里。

## 简历 JSON 格式（API）

`/resume/match` 接口的简历以结构化 JSON 传入（Streamlit 和 `main.py` 直接使用 PDF 提取的文本，不需要这个格式），整个 JSON 会序列化后注入打分 prompt，**字段结构不做强制限定**，以下仅为参考示例：

```json
{
    "基本信息": {"姓名": "张三", "电话": "138****0000", "邮箱": "zhangsan@example.com"},
    "求职意向": {"目标职位": "AI 算法工程师", "工作经验": "3 年"},
    "教育背景": {"时间": "2015-2019", "学历": "本科", "学校": "某大学", "学位": "学士"},
    "工作经历": [
        {
            "公司名称": "某科技公司",
            "职位": "算法工程师",
            "工作时间": "2021-2025",
            "工作职责": ["负责…", "基于 Python/PyTorch…"]
        }
    ],
    "技能清单": {"编程语言": {"Python": "熟练掌握"}},
    "其他信息": "…",
    "项目经验": "…"
}
```

## 声明

本项目用于学习与技术演示。评分结果由大模型生成，仅供参考，不构成任何招聘或求职决策依据。
