import json
from logging import root
import os
from logger import logger
import pandas as pd
import re
from pypdf import PdfReader

current_path=os.path.abspath(__file__)
root_path=os.path.dirname(os.path.dirname(current_path))

class Data:

    @staticmethod
    def _company_name(job_data):
        match = re.search(r'公司[：:]\s*([^\n]+)', job_data)
        if not match:
            return None
        return match.group(1).strip()
    
    def process(self,path):
        df=pd.read_csv(path)
        data=[]
        for idx,rows in df.iterrows():
            nums=rows['JD']
            name=self._company_name(nums) if self._company_name(nums) else ''
            data.append(
                {
                    'job':nums,
                    'name':name,
                    'link':self._job_link(nums)
                }
            )
        return data
    @staticmethod
    def pdf_to_text(pdf_path):
        reader=PdfReader(pdf_path)
        texts=[]
        for page in reader.pages:
            texts.append(page.extract_text() or '')
        
        return '\n'.join(texts)
    
    @staticmethod
    def _job_link(job_data):
        match = re.search(r'职位链接[：:]\s*([^\n]+)', job_data)
        if not match:
            return None
        return match.group(1).strip()
    
    def main(self,path,pdf_path):
        data=self.process(path)
        download_path=os.path.join(root_path,'job_data.json')
        download_resume_path=os.path.join(root_path,'huanghao.json')
        resume_data=self.pdf_to_text(pdf_path)
        with open(download_path,'w',encoding='utf-8') as file:
            json.dump(data,file,ensure_ascii=False,indent=3)
        
        with open(download_resume_path,'w',encoding='utf-8') as file:
            json.dump(resume_data,file,ensure_ascii=False,indent=3)
        
        logger.info('成功处理好了职位数据和简历数据')

if __name__=='__main__':
    path='/Users/yiwise/Downloads/招聘信息_10.29.csv'
    pdf_path='/Users/yiwise/Downloads/黄灏简历新.pdf'
    data=Data()
    print(data.main(path,pdf_path))