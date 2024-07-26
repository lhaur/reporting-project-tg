from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_htpasswd import HtPasswdAuth
from pymongo import MongoClient
from bson import ObjectId
import os
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.prompts.prompt import PromptTemplate

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config['FLASK_HTPASSWD_PATH'] = ".htpasswd"
app.config['FLASK_SECRET'] = "yesthisissomethingsecure"
app.config['JSON_AS_ASCII'] = False

htpasswd = HtPasswdAuth(app)

# MongoDB-yhteyden luominen
client = MongoClient(os.environ.get('MONGODB_URI', 'mongodb://localhost/'))
db = client['telegram_bot']
reports_collection = db['reports']
daily_reports_collection = db['daily_reports']

def process_with_llm(reports_str):
    llm = ChatOpenAI(api_key=os.environ.get('OPENAI_API_KEY', "default"), model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    prompt = PromptTemplate.from_template("Generate daily report from these activities and include also brief summary about day: {reports}")
    question = prompt.format(reports=reports_str)
    return llm.invoke(question).content

@app.route('/api/reports', methods=['POST'])
def create_report():
    report_data = request.json
    
    report_data['timestamp'] = datetime.now()
    report_data['reportId'] = str(ObjectId())
    
    result = reports_collection.insert_one(report_data)
    
    return jsonify({"message": "Report created successfully", "id": str(result.inserted_id)}), 201

@app.route('/', methods=['GET'])
@htpasswd.required
def index(user):
    return render_template('reports.html')

@app.route('/daily', methods=['GET'])
@htpasswd.required
def daily(user):
    return render_template('daily_reports.html')

@app.route('/api/reports', methods=['GET'])
def get_reports():
    start_date = request.args.get('startdate')
    end_date = request.args.get('enddate')

    if start_date:
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if end_date:
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

    query = {}
    if start_date or end_date:
        query['timestamp'] = {}
        if start_date:
            query['timestamp']['$gte'] = start_date
        if end_date:
            query['timestamp']['$lte'] = end_date

    if start_date or end_date:
        reports = list(reports_collection.find(query).sort('timestamp', -1))
    else:
        reports = list(reports_collection.find().sort('timestamp', -1).limit(10))

    for report in reports:
        report['_id'] = str(report['_id'])
        if isinstance(report.get('timestamp'), datetime):
            report['timestamp'] = report['timestamp'].isoformat()

    return jsonify(reports)


@app.route('/api/daily_report', methods=['GET'])
def generate_daily_report():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    query = {
        'timestamp': {
            '$gte': start_date,
            '$lte': end_date
        }
    }
    
    reports = list(reports_collection.find(query).sort('timestamp', -1))
    
    formatted_data = []
    for i, report in enumerate(reports):
        report_content = "Report {}: ".format(i+1)
        for key, value in report.items():
            if key not in ['_id', 'id']: # Removed reportid from the list
                report_content += f"{key}: {value}, "
        formatted_data.append(report_content.rstrip(', '))
    
    formatted_data = "\n".join(formatted_data)
    print(formatted_data)
    summary = process_with_llm(formatted_data)
    
    daily_report = {
        "timestamp": end_date,
        "summary": summary,
        "report_count": len(reports),
        "start_date": start_date,
        "end_date": end_date
    }
    
    result = daily_reports_collection.insert_one(daily_report)
    
    return jsonify({
        "timestamp": end_date.isoformat(),
        "summary": summary,
        "report_count": len(reports),
        "id": str(result.inserted_id)
    })

@app.route('/api/daily_reports', methods=['GET'])
def get_daily_reports():
    start_date = request.args.get('startdate')
    end_date = request.args.get('enddate')

    if start_date:
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if end_date:
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

    query = {}
    if start_date or end_date:
        query['timestamp'] = {}
        if start_date:
            query['timestamp']['$gte'] = start_date
        if end_date:
            query['timestamp']['$lte'] = end_date

    daily_reports = list(daily_reports_collection.find(query).sort('timestamp', -1))

    for report in daily_reports:
        report['_id'] = str(report['_id'])
        report['timestamp'] = report['timestamp'].isoformat()
        report['start_date'] = report['start_date'].isoformat()
        report['end_date'] = report['end_date'].isoformat()

    return jsonify(daily_reports)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port="8080")