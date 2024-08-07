from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_htpasswd import HtPasswdAuth
from dateutil.relativedelta import relativedelta
import os
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.prompts.prompt import PromptTemplate
from mongoengine import connect
from models import Report, DailyReport, MonthlyReport, Category

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config["FLASK_HTPASSWD_PATH"] = ".htpasswd"
app.config["FLASK_SECRET"] = "yesthisissomethingsecure"
app.config["JSON_AS_ASCII"] = False

htpasswd = HtPasswdAuth(app)

# MongoDB-yhteyden luominen
connect(host=os.environ.get("MONGODB_URI", "mongodb://localhost"))


lang_dict = {"fi": "Finnish", "en": "English"}

def initialize_categories():
    categories = ['warehouse', 'maintenance', 'production', 'packaging', 'other']
    for category_name in categories:
        category = Category.objects(name=category_name).first()
        if not category:
            category = Category(name=category_name)
            category.save()

# Kutsu initialize_categories-funktiota ennen sovelluksen käynnistämistä
initialize_categories()


def process_with_llm(reports_str, language):
    llm = ChatOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "default"),
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    )
    prompt = PromptTemplate.from_template(
        "Generate daily report (in language {lang}) from these activities and include also brief summary about day: {reports} If there is no reports, return just something like no reports for that day."
    )
    question = prompt.format(reports=reports_str, lang=lang_dict[language])
    return llm.invoke(question).content

def process_monthly_with_llm(reports_str, language):
    llm = ChatOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "default"),
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    )
    prompt = PromptTemplate.from_template(
        "Generate monthly report (in language {lang}) from these activities and include also brief summary about day: {reports}. If there is no reports, return just something like no reports for that month."
    )
    question = prompt.format(reports=reports_str, lang=lang_dict[language])
    return llm.invoke(question).content


@app.route("/api/reports", methods=["POST"])
def create_report():
    report_data = request.json
    category_name = report_data['category']
    category = Category.objects(name=category_name).first()
    if not category:
        return jsonify({"error": "Invalid category"}), 400
    report_data['category'] = category
    report = Report(**report_data)
    report.save()
    return jsonify({"message": "Report created successfully", "id": str(report.id)}), 201


@app.route("/", methods=["GET"])
@htpasswd.required
def index(user):
    return render_template("reports.html")


@app.route("/daily", methods=["GET"])
@htpasswd.required
def daily(user):
    return render_template("daily_reports.html")

@app.route("/monthly", methods=["GET"])
@htpasswd.required
def monthly(user):
    return render_template("monthly_reports.html")


@app.route('/api/reports', methods=['GET'])
def get_reports():
    start_date = request.args.get('startdate')
    end_date = request.args.get('enddate')
    category_name = request.args.get('category')
    search_query = request.args.get('search')

    query = {}
    if start_date:
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        query['timestamp__gte'] = start_date
    if end_date:
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        query['timestamp__lte'] = end_date
    if category_name:
        category = Category.objects(name=category_name).first()
        if not category:
            return jsonify({"error": "Invalid category"}), 400
        query['category'] = category
    if search_query:
        query['$text'] = {'$search': search_query}

    reports = Report.objects(**query).order_by('-timestamp')
    if not start_date and not end_date and not category_name and not search_query:
        reports = reports.limit(10)

    report_list = []
    for report in reports:
        report_dict = {
            "_id": str(report.id),
            "reporter": report.reporter,
            "topic": report.topic,
            "location": report.location,
            "description": report.description,
            "category": report.category.name if report.category else None,
            "urgent": report.urgent,
            "more_details": report.more_details,
            "attachments": report.attachments,
            "timestamp": report.timestamp.isoformat()
        }
        report_list.append(report_dict)

    return jsonify(report_list)


@app.route('/api/daily_report', methods=['GET'])
def generate_daily_report():
    language = request.args.get('lang', 'fi')
    category_name = request.args.get('category')
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)

    query = {'timestamp__gte': start_date, 'timestamp__lte': end_date}
    if category_name:
        category = Category.objects(name=category_name).first()
        if not category:
            return jsonify({"error": "Invalid category"}), 400
        query['category'] = category

    reports = Report.objects(**query).order_by('-timestamp')

    formatted_data = []
    for i, report in enumerate(reports):
        report_content = f"Report {i + 1}: "
        for key, value in report.to_mongo().items():
            if key not in ['_id', 'id', 'category']:
                report_content += f"{key}: {value}, "
        formatted_data.append(report_content.rstrip(', '))

    formatted_data = "\n".join(formatted_data)
    summary = process_with_llm(formatted_data, language)

    category = category if category_name else None
    daily_report = DailyReport(
        summary=summary,
        report_count=len(reports),
        start_date=start_date,
        end_date=end_date,
        category=category
    )
    daily_report.save()

    return jsonify({
        "timestamp": daily_report.timestamp.isoformat(),
        "summary": daily_report.summary,
        "report_count": daily_report.report_count,
        "id": str(daily_report.id),
        "category": category_name if category else None
    })



@app.route('/api/daily_reports', methods=['GET'])
def get_daily_reports():
    start_date = request.args.get('startdate')
    end_date = request.args.get('enddate')
    category_name = request.args.get('category')

    query = {}
    if start_date:
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        query['timestamp__gte'] = start_date
    if end_date:
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        query['timestamp__lte'] = end_date
    if category_name:
        category = Category.objects(name=category_name).first()
        if not category:
            return jsonify({"error": "Invalid category"}), 400
        query['category'] = category

    daily_reports = DailyReport.objects(**query).order_by('-timestamp')

    # Serialize daily reports
    daily_report_list = []
    for daily_report in daily_reports:
        daily_report_dict = {
            "_id": str(daily_report.id),
            "timestamp": daily_report.timestamp.isoformat(),
            "summary": daily_report.summary,
            "report_count": daily_report.report_count,
            "start_date": daily_report.start_date.isoformat(),
            "category": daily_report.category.name if daily_report.category else None,  # Fetch the category name
            "end_date": daily_report.end_date.isoformat()
        }
        daily_report_list.append(daily_report_dict)

    return jsonify(daily_report_list)

@app.route('/api/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    report = Report.objects(id=report_id).first()

    if not report:
        return jsonify({"error": "Report not found"}), 404

    report_dict = {
        "_id": str(report.id),
        "reporter": report.reporter,
        "topic": report.topic,
        "location": report.location,
        "description": report.description,
        "category": report.category.name if report.category else None,  # Fetch the category name
        "urgent": report.urgent,
        "more_details": report.more_details,
        "attachments": report.attachments,
        "timestamp": report.timestamp.isoformat()
    }

    return jsonify(report_dict)

@app.route('/api/reports/daily/<report_id>', methods=['GET'])
def get_daily_report(report_id):
    daily_report = DailyReport.objects(id=report_id).first()

    if not daily_report:
        return jsonify({"error": "Daily report not found"}), 404

    daily_report_dict = {
        "_id": str(daily_report.id),
        "timestamp": daily_report.timestamp.isoformat(),
        "summary": daily_report.summary,
        "report_count": daily_report.report_count,
        "start_date": daily_report.start_date.isoformat(),
        "category": daily_report.category.name if daily_report.category else None,  # Fetch the category name
        "end_date": daily_report.end_date.isoformat()
    }

    return jsonify(daily_report_dict)

@app.route('/api/reports/monthly/<report_id>', methods=['GET'])
def get_monthly_report(report_id):
    monthly_report = MonthlyReport.objects(id=report_id).first()

    if not monthly_report:
        return jsonify({"error": "Monthly report not found"}), 404

    monthly_report_dict = {
        "_id": str(monthly_report.id),
        "timestamp": monthly_report.timestamp.isoformat(),
        "summary": monthly_report.summary,
        "report_count": monthly_report.report_count,
        "start_date": monthly_report.start_date.isoformat(),
        "category": monthly_report.category.name if monthly_report.category else None,  # Fetch the category name
        "end_date": monthly_report.end_date.isoformat()
    }

    return jsonify(monthly_report_dict)


@app.route('/api/monthly_report', methods=['GET'])
def generate_monthly_report():
    language = request.args.get('lang', 'fi')
    category_name = request.args.get('category')
    year = int(request.args.get('year'))
    month = int(request.args.get('month'))

    start_date = datetime(year, month, 1)
    end_date = start_date + relativedelta(months=1) - relativedelta(days=1)

    query = {'timestamp__gte': start_date, 'timestamp__lte': end_date}
    if category_name:
        category = Category.objects(name=category_name).first()
        if not category:
            return jsonify({"error": "Invalid category"}), 400
        query['category'] = category

    reports = Report.objects(**query).order_by('-timestamp')

    formatted_data = []
    for i, report in enumerate(reports):
        report_content = f"Report {i + 1}: "
        for key, value in report.to_mongo().items():
            if key not in ['_id', 'id', 'category']:
                report_content += f"{key}: {value}, "
        formatted_data.append(report_content.rstrip(', '))

    formatted_data = "\n".join(formatted_data)
    summary = process_monthly_with_llm(formatted_data, language)

    category = category if category_name else None
    monthly_report = MonthlyReport(
        summary=summary,
        report_count=len(reports),
        start_date=start_date,
        end_date=end_date,
        category=category
    )
    monthly_report.save()

    return jsonify({
        "timestamp": monthly_report.timestamp.isoformat(),
        "summary": monthly_report.summary,
        "report_count": monthly_report.report_count,
        "id": str(monthly_report.id),
        "category": category_name if category else None
    })


@app.route('/api/monthly_reports', methods=['GET'])
def get_monthly_reports():
    start_date = request.args.get('startdate')
    end_date = request.args.get('enddate')
    category_name = request.args.get('category')

    query = {}
    if start_date:
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        query['timestamp__gte'] = start_date
    if end_date:
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        query['timestamp__lte'] = end_date
    if category_name:
        category = Category.objects(name=category_name).first()
        if not category:
            return jsonify({"error": "Invalid category"}), 400
        query['category'] = category

    monthly_reports = MonthlyReport.objects(**query).order_by('-timestamp')

    # Serialize monthly reports
    monthly_report_list = []
    for monthly_report in monthly_reports:
        monthly_report_dict = {
            "_id": str(monthly_report.id),
            "timestamp": monthly_report.timestamp.isoformat(),
            "summary": monthly_report.summary,
            "report_count": monthly_report.report_count,
            "start_date": monthly_report.start_date.isoformat(),
            "category": monthly_report.category.name if monthly_report.category else None,  # Fetch the category name
            "end_date": monthly_report.end_date.isoformat()
        }
        monthly_report_list.append(monthly_report_dict)

    return jsonify(monthly_report_list)


@app.route('/api/reports/category/<category_name>', methods=['GET'])
def get_reports_by_category(category_name):
    start_date = request.args.get('startdate')
    end_date = request.args.get('enddate')

    category = Category.objects(name=category_name).first()
    if not category:
        return jsonify({"error": "Invalid category"}), 400

    query = {'category': category}
    if start_date:
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        query['timestamp__gte'] = start_date
    if end_date:
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        query['timestamp__lte'] = end_date

    reports = Report.objects(**query).order_by('-timestamp')

    # Serialize reports
    report_list = []
    for report in reports:
        report_dict = {
            "_id": str(report.id),
            "reporter": report.reporter,
            "topic": report.topic,
            "location": report.location,
            "description": report.description,
            "category": report.category.name if report.category else None,  # Fetch the category name
            "urgent": report.urgent,
            "more_details": report.more_details,
            "attachments": report.attachments,
            "timestamp": report.timestamp.isoformat()
        }
        report_list.append(report_dict)

    return jsonify(report_list)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.objects().order_by('name')
    category_names = [category.name for category in categories]
    return jsonify(category_names)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port="8080")
