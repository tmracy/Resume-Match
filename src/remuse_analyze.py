from langchain_core.prompts import ChatPromptTemplate
import os
from logger import logger
from utils import (
    llm,
    root_path,
    timeit
)
import json
from concurrent.futures import ThreadPoolExecutor

analyze_prompt="""
我会发给你一份已经整理好的求职材料。不要联网搜索，也不要假装搜过。公司事实只能来自下面材料里的企业背景。

## 岗位、匹配结果与企业背景
{data}

这条 JSON 里：
- job：招聘 JD / 岗位海报原文
- name、link：公司名和职位链接
- strengths、gaps、overall_reason、score：上一轮匹配结论，score 满分 10
- company_background：企业背景，是一段 JSON 字符串。字段为公司简介、成立时间、公司规模、融资出资、主营业务、发展阶段、求职参考点。先按 JSON 理解这段字符串

## 个人简历
{resume}

请基于以上材料做求职决策分析。

约束：
- 公司事实只能引用 company_background。融资、人员规模、裁员或扩张、主营业务、发展阶段，以该字段原文为准
- 字段值为「未知」，或写明来源有分歧时，保持原样并说明不确定，不要补成确定事实
- 材料里没有的加班制度、上下班时间、职场口碑、组织架构、团队编制、竞业、股权激励，写「材料未提及」，不要给具体数字或制度
- 简历事实只能来自简历原文。年限、职位、项目不要拔高。简历没写的离职原因不要替我编
- JD 写明的硬性要求不要改写成「不是硬门槛」
- 最终建议要和 score、gaps 一致。存在明显硬缺口时，不要给「强烈推荐」
- 不复述 JD，不客套，直接讲真话

请按以下结构输出：

## 1. 真实日常

入职后每天到底在做什么？

请结合 JD 和 company_background 里的主营业务、发展阶段，分析：
- 核心工作内容
- 真实业务价值
- 这个岗位在团队里大概率承担什么角色
- 工作强度和加班：仅当材料里有依据时才写；没有就写「材料未提及」

## 2. 利弊与坑点

公司招我是为了什么？

请判断这个岗位更像是：
- 性价比用人
- 边缘业务补人
- 短期救火
- 实习生 / 新人打杂
- 有成长空间
- 能接触核心技术或核心业务

判断必须能回溯到 JD 或 company_background，不要凭行业印象下结论。

同时分析可能存在的：
- 隐形坑
- 业务不稳定风险
- 技术含量不足风险
- 转正 / 晋升 / 学习空间风险

材料没写到的管理风格、审批流程，不要写成既定事实。

## 3. 匹配度判断

这个岗位对能力的真实要求是什么？

请结合我的背景判断：
- 我的优势在哪里
- 我的短板在哪里
- 哪些要求是我已经基本满足的
- 哪些要求需要重点补
- 我需要补什么才能更稳
- 这个岗位是否适合我当前阶段

短板以 gaps 和简历原文为准，不要把上一轮 strengths 里偏松的表述再放大。

## 4. 沟通话术

给我一段可以直接发给 HR / Boss 的打招呼话术。

要求：
- 自然
- 不油腻
- 不像群发
- 体现我对岗位的理解，只使用 JD 和 company_background 里有的业务信息
- 结合我的背景，年限和职位与简历一致
- 语气积极但不过度讨好

最后一句话必须以：

可以发简历给您进一步了解吗？

结束。

## 5. 面试重点

请判断面试官最可能问什么。

包括：
- 技术问题
- 项目问题
- 业务理解问题
- 为什么投这个岗位
- 为什么觉得自己匹配
- 可能被追问的短板

同时告诉我：
- 我该怎么准备才能加分
- 哪些项目经历应该重点讲
- 哪些表达要避免
- 哪些问题可以反问面试官，优先问材料里标为未知或存在分歧的点

## 6. 最终决策建议

请给出明确结论：

强烈推荐 / 可以考虑 / 坚决避雷

并给出 2–3 条关键理由。

判断时请综合考虑：
- company_background 里已经写明的企业事实
- 岗位真实价值
- 技术成长性
- 与我背景的匹配度和 score
- 简历增益
- 材料里已经点明的风险；材料没写的风险不要当成结论
"""


class Analyze:
    def __init__(self,data,path,resume_data):
        self.data=data
        self.resume_data=resume_data
        self.path=path

    
    
    def download(self,path,data):
        with open(path,'w',encoding='utf-8') as file:
            json.dump(data,file,ensure_ascii=False,indent=3)

    
    @timeit('总的分析')
    def main(self):
        prompt=ChatPromptTemplate.from_template(analyze_prompt)
        chain=prompt | llm

        def one(nums):
            nums['final_result'] = chain.invoke({
                'data': json.dumps(nums, ensure_ascii=False, indent=3),
                'resume': json.dumps(self.resume_data, ensure_ascii=False, indent=3)
            }).content

            return nums

        with ThreadPoolExecutor(max_workers=8) as executor:
            result = list(executor.map(one, self.data))

        self.download(self.path,result)
        return result

if __name__=='__main__':
    def load_json(path):
        with open(path,'r',encoding='utf-8') as file:
            data=json.load(file)
        return data
    
    data=load_json('match_result.json')
    path='final_job_analyze.json'
    resume_data=load_json('name.json')
    analyze=Analyze(data,path,resume_data)
    print(analyze.main())


        