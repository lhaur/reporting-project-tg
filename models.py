from mongoengine import Document, StringField, BooleanField, DateTimeField, IntField, ReferenceField
from datetime import datetime

class Category(Document):
    name = StringField(required=True, unique=True)

class Report(Document):
    reporter = StringField(required=True)
    topic = StringField(required=True)
    location = StringField()
    description = StringField(required=True)
    category = ReferenceField(Category, required=True)
    urgent = BooleanField(default=False)
    more_details = StringField()
    attachments = StringField()
    timestamp = DateTimeField(default=datetime.now)
    meta = {'indexes': [
        {'fields': ['$topic', '$description', '$more_details'],
         'default_language': 'english',
         'weights': {'topic': 10, 'description': 5, 'more_details': 2}}
    ]}

class DailyReport(Document):
    timestamp = DateTimeField(default=datetime.now)
    summary = StringField(required=True)
    report_count = IntField(default=0)
    start_date = DateTimeField(required=True)
    category = ReferenceField(Category)
    end_date = DateTimeField(required=True)

class MonthlyReport(Document):
    timestamp = DateTimeField(default=datetime.now)
    summary = StringField(required=True)
    report_count = IntField(default=0)
    start_date = DateTimeField(required=True)
    category = ReferenceField(Category)
    end_date = DateTimeField(required=True)