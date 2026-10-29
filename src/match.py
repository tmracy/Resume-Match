from pydantic import BaseModel,Field
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from utils import (
    llm,
    root_path,
    timeit
)
from src.search import ResearchBackGround
import os
from enum import Enum
import json
from logger import logger

class WEIGHTS(Enum):
    hard_skill=0.35  # 硬技能最重要
    experience=0.3   # 经验次之
    company_fit=0.2   # 企业契合
    education=0.1  # 学历门槛
    soft_fit=0.05  # 软性补充
        

prompt_path=os.path.join(root_path,'Prompt','match_score.md')

class DimensionScore(BaseModel):
    evidence: str = Field(description="从简历或 JD 中引用的原文证据片段，找不到则填 '无'")
    reason: str = Field(description="基于证据的简要评估理由")
    status: Literal["满足", "部分满足", "缺失"] = Field(description="该维度的满足状态")
    score: int = Field(ge=0, le=10, description="该维度 0-10 的整数子分")


class Data(BaseModel):
    hard_skill: DimensionScore = Field(description="硬技能匹配：编程语言、框架、工具、技术栈是否匹配 JD")
    experience: DimensionScore = Field(description="经验匹配：工作年限、项目复杂度、岗位职责相关性")
    education: DimensionScore = Field(description="教育 / 硬性门槛：学历、专业、证书等硬性条件")
    company_fit: DimensionScore = Field(description="企业契合度：结合企业背景评估候选人是否契合这家公司")
    soft_fit: DimensionScore = Field(description="软性 / 补充匹配：稳定性、潜力、软技能等加减分因素")
    strengths: list[str] = Field(description="匹配亮点列表")
    gaps: list[str] = Field(description="差距或风险列表")
    overall_reason: str = Field(description="综合总评，3-5 句话")


class Match:
    def __init__(self,name,job_description,resume_json,user_input:str=None):
        self.company_background=ResearchBackGround(name).extract()
        self.job_description=job_description
        self.resume_json=resume_json
        self.user_input=user_input
    
    @staticmethod
    def load_prompt(path):
        with open(path,'r',encoding='utf-8') as file:
            data=file.read()
        
        return data
    
    def process(self):
        prompt=ChatPromptTemplate.from_template(self.load_prompt(prompt_path))
        struct_llm=llm.with_structured_output(Data)
        chain=prompt | struct_llm

        response=chain.invoke({
            'job_description':self.job_description,
            'company_background':json.dumps(self.company_background,ensure_ascii=False),
            'resume_json':json.dumps(self.resume_json,ensure_ascii=False),
            'user_input':self.user_input
        })

        return {
            'hard_skill':response.hard_skill,
            'experience':response.experience,
            'education':response.education,
            'company_fit':response.company_fit,
            'soft_fit':response.soft_fit,
            'strengths':response.strengths,
            'gaps':response.gaps,
            'overall_reason':response.overall_reason
        }

    @timeit('简历匹配')
    def main(self):
        data=self.process()
        result={key:value for key,value in data.items() if key in ['strengths','gaps','overall_reason']}
        score=0
        for key,values in data.items():
            try:
                key_score=WEIGHTS[key].value*values.score
                score+=key_score
            except Exception as e:
                continue
        result['score']=score
        result['company_background']=json.dumps(self.company_background,ensure_ascii=False)
        logger.info(f'简历匹配的结果为:{result}')
        return result

if __name__=='__main__':
    def load_data(path):
        with open(path,'r',encoding='utf-8') as file:
            data=json.load(file)
        
        return data
    
    resume_json=load_data('huanghao.json')
    job_messages=load_data('job_data.json')
    result=[]
    #path=os.path.join(root_path,'resume_match.json')
    for data in job_messages:
        name=data['name']
        job_description=data['job']
        match=Match(name,job_description,resume_json)
        final=match.main()
        data.update(final)
        result.append(data)

    
    with open('match_result.json','w',encoding='utf-8') as file:
        json.dump(result,file,ensure_ascii=False,indent=3)


    