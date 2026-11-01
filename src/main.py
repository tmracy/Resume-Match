from logger import logger
from src.data_process import Data,root_path
from src.match import Match
from src.remuse_analyze import Analyze
import json
import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

class Main:
    def __init__(self,input_job_path,input_resume_path,resume_name:str,job_name:str,job_process_name:str,job_final_name:str):
        self.input_job_path=input_job_path
        self.input_resume_path=input_resume_path

        self.resume_path=os.path.join(root_path,resume_name)
        self.job_path=os.path.join(root_path,job_name)
        self.job_process_path=os.path.join(root_path,job_process_name)
        self.job_final_path=os.path.join(root_path,job_final_name)
        

    def data_process(self):
        data=Data()
        data=data.main(self.input_job_path,self.input_resume_path,self.job_path,self.resume_path)
        logger.info('数据处理成功')
        
    @staticmethod
    def load_json(path):
        with open(path,'r',encoding='utf-8') as file:
            data=json.load(file)
        
        return data

    def match(self):
        resume_data=self.load_json(self.resume_path)
        job_data=self.load_json(self.job_path)

        def one(data):
            final = Match(data['name'], data['job'], resume_data).main()
            data.update(final)
            return data

        with ThreadPoolExecutor(max_workers=8) as executor:
            result = list(executor.map(one, job_data))

        if result:
            with open(self.job_process_path,'w',encoding='utf-8') as file:
                json.dump(result,file,ensure_ascii=False,indent=3)
            
            logger.info('职位匹配成功')
        else:
            logger.info('职位匹配为空')
        
    
    def analyze(self,final_path):
        self.data_process()
        self.match()
        job_process_data=self.load_json(self.job_process_path)
        resume_data=self.load_json(self.resume_path)
        analyze_data=Analyze(job_process_data,self.job_final_path,resume_data).main()

        df=pd.DataFrame(analyze_data)
        df.to_csv(final_path,index=False)
        logger.info('岗位匹配分析全部完毕')