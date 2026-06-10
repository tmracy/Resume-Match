from flask import Flask,Response,request
from src.match import Match
from src.search import ResearchBackGround
from logger import logger
import json
import traceback

app=Flask(__name__)

#gunicorn -c gunicorn.py entry.server:app

@app.route("/healthy",methods=['GET'])
def healthy():
    return Response(
        json.dumps(
            {'code':0,'info':'Success'},
            ensure_ascii=False,
            indent=3
        ),
        mimetype='application/json'
    )

@app.route('/resume/match',methods=['POST'])
def resume_match():
    try:
        request_data=request.json
        name=request_data.get('name')
        job_description=request_data.get('job_description')
        resume_json=request_data.get('resume_json')
        user_input=request_data.get('user_input')

        match=Match(
            name,
            job_description,
            resume_json,
            user_input
        )
        match_result=match.main()

        return Response(
            json.dumps(
                {'code':0,'info':'success','data':match_result},
                ensure_ascii=False,
                indent=3
            ),
            mimetype='application/json'
        )
    except Exception as e:
        error=traceback.format_exc()
        return Response(
            json.dumps(
                {'code':1,'info':'failed','data':error},
                ensure_ascii=False,
                indent=3
            ),
            mimetype='application/json'
        )

@app.route('/search',methods=['POST'])
def search_company():
    try:
        request_data=request.json
        name=request_data.get('name')
        search=ResearchBackGround(name)
        search_result=search.extract()

        return Response(
            json.dumps(
                {'code':0,'info':'success','data':search_result},
                ensure_ascii=False,
                indent=3
            ),
            mimetype='application/json'
        )
    except Exception as e:
        error=traceback.format_exc()
        return Response(
            json.dumps(
                {'code':1,'info':'failed','data':error},
                ensure_ascii=False,
                indent=3
            ),
            mimetype='application/json'
        )

if __name__=='__main__':
    logger.info('这里是简历匹配的服务入口！')
    app.run(host='0.0.0.0',port=8999,debug=False,use_reloader=False)



