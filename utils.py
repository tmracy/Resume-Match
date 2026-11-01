import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from logger import logger
import time

load_dotenv()
current_path=os.path.abspath(__file__)
root_path=os.path.dirname(current_path)

llm=ChatOpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('API_KEY_DOUBAO'),
    model='xxxx'
)

def timeit(name):
    def wrapper(func):
        def final(*args,**kwargs):
            start_time=time.time()
            result=func(*args,**kwargs)
            logger.info(f'{name}阶段耗时{time.time()-start_time:.2f}秒')
            return result
        return final
    return wrapper

