from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.config['JSON_AS_ASCII'] = False

# MongoDB-yhteyden luominen
client = MongoClient(os.environ.get('MONGODB_URI', 'mongodb://localhost'))
db = client['telegram_bot']
reports_collection = db['reports']

@app.route('/api/reports', methods=['POST'])
def create_report():
    report_data = request.json
    
    report_data['timestamp'] = datetime.utcnow()
    report_data['reportId'] = str(ObjectId())
    
    result = reports_collection.insert_one(report_data)
    
    return jsonify({"message": "Report created successfully", "id": str(result.inserted_id)}), 201

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

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

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port="8080")