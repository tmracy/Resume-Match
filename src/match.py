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
        logger.info(f'简历匹配的结果为:{result}')
        return result

if __name__=='__main__':
    job_description="""
    职位描述

    标签：C/C++、机器学习、图像算法、大模型算法、算法工程化经验、强化学习、优秀开源项目经历、模型加速/性能优化、Python

    岗位职责

    1. 算法研发：
    负责计算机视觉相关算法的研发，包括但不限于目标检测、图像分类、语义分割、姿态估计、图像生成等。

    2. 模型独立训练：
    独立负责模型的数据清洗、增强、训练、调参与评估，根据业务场景（如安防、工业质检、智能硬件）设计并迭代最优算法方案。

    3. 模型优化与部署：
    针对移动端/边缘端（如手机、嵌入式设备）进行模型压缩、剪枝、量化（INT8/FP16）等加速优化，配合工程团队完成模型转换（如TensorRT、NCNN、TFLite、OpenVINO）及端侧部署。

    4. 前沿技术跟进：
    跟踪CV领域最新论文与算法，并尝试将其落地到实际产品中。

    任职要求

    1. 学历专业：
    本科及以上学历（优秀大专亦可），3-5年经验，计算机视觉、模式识别、人工智能、数学等相关专业。

    2. 算法能力：
    深入理解深度学习理论基础，精通PyTorch或TensorFlow，具备扎实的Python/C++编程功底。

    3. 模型训练经验：
    必须具备从0到1独立完成模型训练的经验，包括数据预处理、模型选型、超参数调整、损失函数设计以及训练问题（如梯度爆炸/消失、过拟合）的排查解决。

    4. 视觉经验：
    在以下至少一个方向有深入实践经验：目标检测（YOLO系列、DETR）、图像分割（UNet、SegFormer）、多目标跟踪（SORT/DeepSORT）、图像生成（GAN/VAE/Diffusion Models）。

    5. 部署经验：
    熟悉模型部署全流程，熟练掌握至少一种推理引擎（TensorRT、ONNX Runtime、TFLite、NCNN），并有实际的上线或落地项目经验。

    加分项：
    有多模态（视觉+语言/视觉+音频）算法经验者优先。
    有CV顶会论文（CVPR/ICCV/ECCV）发表或知名开源项目贡献者优先。熟悉Cuda编程或模型底层算子优化者优先。
    """
    with open('/Data/tmracy.json','r',encoding='utf-8') as file:
        resume_json=json.load(file)
    name='新之星网络科技'
    match=Match(
        name,
        job_description,
        resume_json
    )
    result=match.main()
    print(result)