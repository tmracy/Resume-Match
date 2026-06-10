from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from utils import (
    llm,
    timeit,
    root_path
)
import os
import json
import traceback
from logger import logger
from tavily import TavilyClient
from dotenv import load_dotenv
import requests

load_dotenv()
rewrite_path=os.path.join(root_path,'Prompt','rewrite_query.md')
extract_path=os.path.join(root_path,'Prompt','extract_company_background.md')
tavily_client=TavilyClient(api_key=os.getenv('Tavily_API_KEY'))


class ResearchBackGround:
    def __init__(self,name):
        self.name=name

    @staticmethod
    def load_prompt(path):
        with open(path,'r',encoding='utf-8') as file:
            data=file.read()
        
        return data
    
    @staticmethod
    def serper(query):
        url = "https://google.serper.dev/search"

        payload = {
        "q": query,
        "gl": "cn",
        'page':2
        }
        headers = {
        'X-API-KEY': os.getenv('SERPER_API_KEY'),
        'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, json=payload)

        return response.text

    
    def rewrite(self):
        prompt=ChatPromptTemplate.from_template(self.load_prompt(rewrite_path))
        chain=prompt | llm
        response=chain.invoke(
            {'company_name':self.name}
        )
        try:
            #{ "company_normalized": "<标准化 / 补全后的企业名称>", "query": "<改写后的搜索查询语句>" }
            result=json.loads(response.content)
            logger.info(f'改写后的查询语句为:{result}')
            

        except Exception as e:
            error=traceback.format_exc()
            logger.error(f'rewrite出现了错误:{error}')
            result=f'请根据这个企业名称:{self.name},查询其背景信息'
        
        return result

    
    def search_message(self):
        rewrite_query=self.rewrite()
        if isinstance(rewrite_query,dict):
            query=rewrite_query.get('query')
            search_answer=self.serper(query)
        elif isinstance(rewrite_query,str):
            search_answer=self.serper(rewrite_query)
        else:
            search_answer='None'
        return search_answer
    
    @timeit('企业背景信息')
    def extract(self):
        search_answer=self.search_message()
        prompt=ChatPromptTemplate.from_template(self.load_prompt(extract_path))
        #company_name,search_results
        chain=prompt | llm
        response=chain.invoke({
            'company_name':self.name,
            'search_results':search_answer
        }).content
        try:
            result=json.loads(response)
            logger.info(f'企业背景信息为:{result}')
        except Exception as e:
            error=traceback.format_exc()
            logger.error(f'企业背景出现错误:{error}')
            result='企业背景信息没有找到'
        
        return result

if __name__=='__main__':
    name='阿里巴巴'
    research=ResearchBackGround(name)
    result=research.extract()
    print(result)
        

            
        