from random import SystemRandom
from flask import Flask, request, redirect, session, url_for, flash, jsonify, render_template
import os
import mysql.connector
from werkzeug.utils import secure_filename
import json
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.datastructures import ImmutableMultiDict
import io
from flask import send_file
import time
from threading import Timer
import smtplib
from string import Template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


random = SystemRandom()

app = Flask(__name__)
CORS(app)

def dictfetchall(cursor):
    # "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

# FORM RELATED API CALLS

# fetch form fields
@app.route('/getForm', methods=['GET'])
def get_form():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _fieldId = request.args.get('formId')

        cursor = db.cursor()
        db.row_factory = dictfetchall

        sql = ("SELECT formatID, name, type, if(required=1,'true','false') as required, display, if(selected=1,'true','false') as selected, title, `order` FROM FormFormat WHERE formID=%s")

        cursor.execute(sql, (_fieldId,))
        records = dictfetchall(cursor)
        for result in records:
            cursor.execute(
                "select `key`,label from optionsTable o, (SELECT formatID from formformat where `type`='select' OR `type`='multi') a where o.fieldID = a.formatID AND o.fieldID = '" + result['formatID'] + "'")
            row = dictfetchall(cursor)
            if row is not None:
                result['options'] = row

        return json.dumps(records)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# insert user input form data
@app.route('/insertFormVal', methods=['POST'])
def insert_form_value():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _fieldName = _json['fieldName']
        _studentID = _json['studentID']
        _fieldVal = _json['fieldVal']
        _taskId = _json['taskId']

        cursor = db.cursor(buffered=True, dictionary=True)
        check_existing = "SELECT * FROM FormFieldSubmission WHERE fieldID = %s && studentID = %s"
        check_values = (_fieldName, _studentID)
        cursor.execute(check_existing, check_values)

        row_count = cursor.rowcount

        print("number of found rows: {}".format(row_count))
        if row_count == 0:
            insert_sql = "INSERT INTO FormFieldSubmission (fieldID, studentID, value, taskID) VALUES (%s, %s, %s, %s)"
            values = (_fieldName, _studentID, _fieldVal, _taskId)
            cursor.execute(insert_sql, values)
        else:
            update_sql = "UPDATE FormFieldSubmission SET value = %s WHERE fieldID = %s AND studentID = %s AND taskID = %s"
            values = (_fieldVal, _fieldName, _studentID, _taskId)
            cursor.execute(update_sql, values)

        db.commit()

        resp = jsonify('Form data inserted successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# insert user input form data and record the submission time
@app.route('/recordSubmission', methods=['POST'])
def record_submission():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _studentId = _json['studentId']
        _taskId = _json['taskId']

        cursor = db.cursor(buffered=True, dictionary=True)
        check_existing = "SELECT * FROM submissionRecords WHERE taskID = %s && studentID = %s"
        check_values = (_taskId, _studentId)
        cursor.execute(check_existing, check_values)

        row_count = cursor.rowcount

        now = datetime.now()
        cur = now.strftime('%Y-%m-%d %H:%M:%S')

        print("number of found rows: {}".format(row_count))
        if row_count == 0:
            insert_sql = "INSERT INTO submissionRecords (studentID, taskID, submissionTime) VALUES (%s, %s, %s)"
            values = (_studentId, _taskId, cur)
            cursor.execute(insert_sql, values)
        else:
            update_sql = "UPDATE submissionRecords SET submissionTime = %s WHERE studentID = %s AND taskID = %s"
            values = (cur, _studentId, _taskId)
            cursor.execute(update_sql, values)

        db.commit()

        resp = jsonify('Submission is recorded successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# fetch completion status of student's task submission
@app.route('/getTaskCompletion', methods=['GET'])
def get_task_completion():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _studentId = request.args.get('studentId')

        cursor = db.cursor(buffered=True)
        sql = ("SELECT taskID from submissionRecords where studentID = %s")

        cursor.execute(sql, (_studentId,))

        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# fetch user inserted form data
@app.route('/loadFormVal', methods=['GET'])
def get_form_val():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _fieldId = request.args.get('fieldId')
        _stdId = request.args.get('stdId')
        _taskId = request.args.get('taskId')

        cursor = db.cursor(buffered=True)
        sql = ("SELECT value from FormFieldSubmission where studentID = %s AND fieldID = %s AND taskID = %s")
        val = (_stdId, _fieldId, _taskId)

        cursor.execute(sql, val)

        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# sends a list of existing forms
@app.route("/formNameValidation", methods=['GET'])
def check_form():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        cursor = db.cursor()
        getFormName = "SELECT FormID FROM FormTable"
        cursor.execute(getFormName)

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# sends a list of existing form names
@app.route("/formList", methods=['GET'])
def get_form_list():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        cursor = db.cursor()
        getFormName = "SELECT FormID, FormName, DateCreated FROM FormTable"
        cursor.execute(getFormName)

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# inserts a new form name
@app.route("/newForm", methods=['POST'])
def create_form():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _fname = _json['fname']
        _formId = _json['formId']

        now = datetime.now()
        cur = now.strftime('%Y-%m-%d %H:%M:%S')

        cursor = db.cursor()
        insertForm = "INSERT INTO FormTable (formID, formName, dateCreated) VALUES (%s, %s, %s)"
        form = (_formId, _fname, cur)
        cursor.execute(insertForm, form)

        db.commit()

        resp = jsonify('User updated successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# insert form fields
@app.route("/writeFields", methods=['POST'])
def sub_form():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _fname = _json['fname']
        _name = _json['name']
        _type = _json['type']
        _required = _json['required']
        _display = _json['display']
        _selected = _json['selected']
        _title = _json['title']
        _order = _json['order']
        _options = None
        try:
            _options = _json['options']
        except:
            print("This field has no options.")

        format_id = _name.lower()
        cursor = db.cursor()

        insertFields = "INSERT INTO FormFormat (formID, formatID, name, type, required, display, selected, title, `order`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        field = (_fname, format_id, _name, _type,
                _required, _display, _selected, _title, _order)

        cursor.execute(insertFields, field)

        insertOptions = "INSERT INTO optionsTable(fieldID, `key`, label) VALUES (%s, %s, %s)"

        if _options is not None:
            for option in _options:
                opt = (format_id, option.lower(), option)
                cursor.execute(insertOptions, opt)
        db.commit()

        resp = jsonify('Form is created successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# WORKFLOW RELATED API CALLS

# send existing workflows
@app.route("/workflowNameValidation", methods=['GET'])
def check_workflow():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        cursor = db.cursor()
        getWorkflowName = "SELECT WorkflowID FROM Workflow"
        cursor.execute(getWorkflowName)

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# inserts a new workflow name
@app.route("/newWorkflow", methods=['POST'])
def create_workflow():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _workflowId = _json['workflowId']
        _fname = _json['fname']

        now = datetime.now()
        cur = now.strftime('%Y-%m-%d %H:%M:%S')

        cursor = db.cursor()
        insertForm = "INSERT INTO Workflow (workflowID, workflowName, dateCreated) VALUES (%s, %s, %s)"
        form = (_workflowId, _fname, cur)
        cursor.execute(insertForm, form)

        db.commit()

        resp = jsonify('Workflow created successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# insert workflow phases
@app.route("/writePhases", methods=['POST'])
def sub_phases():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _workflowId = _json['workflowId']
        _phaseId = _json['phaseId']
        _phaseOrder = _json['phaseOrder']
        _phaseDuration = _json['phaseDuration']
        _phaseName = _json['phaseName']

        cursor = db.cursor()

        insertFields = "INSERT INTO WorkflowPhase (workflowID, phaseID, phaseOrder, phaseName, phaseDuration) VALUES (%s, %s, %s, %s, %s)"
        field = (_workflowId, _phaseId, _phaseOrder, _phaseName, _phaseDuration)

        cursor.execute(insertFields, field)

        db.commit()

        resp = jsonify('Workflow phases written successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# insert workflow tasks
@app.route("/writeTasks", methods=['POST'])
def sub_tasks():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _phaseId = _json['phaseId']
        _taskId = _json['taskId']
        _taskName = _json['taskName']
        _taskType = _json['taskType']
        _desc = _json['desc']
        _formId = None

        if _taskType == 'form':
            _formId = _json['formId']

        cursor = db.cursor()

        insertFields = "INSERT INTO WorkflowPhaseTasks (phaseID, taskID, taskName, `desc`, taskType, formID) VALUES (%s, %s, %s, %s, %s, %s)"
        field = (_phaseId, _taskId, _taskName, _desc, _taskType, _formId)

        cursor.execute(insertFields, field)

        db.commit()

        resp = jsonify('Workflow tasks written successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# sends a list of existing workflow names
@app.route("/workflowList", methods=['GET'])
def get_workflow_list():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        cursor = db.cursor()
        getFormName = "SELECT WorkflowID, WorkflowName, DateCreated FROM Workflow"
        cursor.execute(getFormName)

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# returns workflow details based on workflowId
@app.route("/getWorkflow", methods=['GET'])
def get_workflow():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _workflowId = request.args.get('workflowId')
        cursor = db.cursor()
        getWorkflow = "SELECT * FROM Workflow w INNER JOIN workflowphase p ON w.workflowID = p.workflowID INNER JOIN workflowphasetasks t ON p.phaseID = t.phaseID WHERE p.workflowID=%s ORDER BY p.phaseOrder"
        cursor.execute(getWorkflow, (_workflowId,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

 # sends phase info of selected workflow
@app.route("/phaseData", methods=['GET'])
def get_phases():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _workflowId = request.args.get('workflowId')
        print(_workflowId)
        cursor = db.cursor()
        getWorkflow = "select * from Workflow w inner join workflowphase p on w.workflowID = p.workflowID WHERE p.workflowID = %s order by p.phaseOrder"
        cursor.execute(getWorkflow, (_workflowId,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# insert workflow assignment
@app.route("/assignFlow", methods=['POST'])
def assign_workflow():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _intakeCode = _json['intakeCode']
        _workflowId = _json['workflowId']
        _startDate = _json['startDate']
        _endDate = _json['endDate']

        cursor = db.cursor()

        insertFields = "INSERT INTO Intake_Workflow (intakeCode, workflowId, startDate, endDate) VALUES (%s, %s, %s, %s)"
        field = (_intakeCode, _workflowId, _startDate, _endDate)

        cursor.execute(insertFields, field)

        db.commit()

        resp = jsonify('Workflow assignment written successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# insert phase date assignment
@app.route("/assignPhaseDates", methods=['POST'])
def assign_phase_dates():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _intakeCode = _json['intakeCode']
        _phaseId = _json['phaseId']
        _startDate = _json['startDate']
        _endDate = _json['endDate']

        cursor = db.cursor()

        insertFields = "INSERT INTO intake_phase_duration (intakeID, phaseID, startDate, endDate) VALUES (%s, %s, %s, %s)"
        field = (_intakeCode, _phaseId, _startDate, _endDate)

        cursor.execute(insertFields, field)

        db.commit()

        resp = jsonify('Phase date assignment written successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# receive student's intake and return a set of tasks from workflow
@app.route("/intakeTasks", methods=['GET'])
def get_intake_tasks():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _intakeId = request.args.get('intakeId')
        cursor = db.cursor()
        getTasks = "select * from workflowphase p INNER JOIN workflowphasetasks t on p.phaseID = t.phaseID INNER JOIN intake_workflow i on i.workflowID = p.workflowID where i.intakeCode = %s order by p.phaseOrder"
        cursor.execute(getTasks, (_intakeId,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()    

# return set of dates for intake specific workflow
@app.route("/intakeDates", methods=['GET'])
def get_intake_dates():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _intakeId = request.args.get('intakeId')

        cursor = db.cursor()
        getTasks = "select * from intake_phase_duration WHERE intakeID = %s"
        cursor.execute(getTasks, (_intakeId,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# gets a workflow assigned to the intake parameter
@app.route("/getIntakeToWorkflow", methods=['GET'])
def get_intake_to_workflow():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _intakeId = request.args.get('intakeId')

        cursor = db.cursor()
        sql = "select * from workflow w INNER JOIN intake_workflow iw on w.workflowID = iw.workflowID where iw.intakeCode = %s"
        cursor.execute(sql, (_intakeId,))

        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# gets a workflow assigned to the intake parameter
@app.route("/getWorkflowToIntakes", methods=['GET'])
def get_workflow_to_intakes():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _workflowId = request.args.get('workflowId')

        cursor = db.cursor()
        sql = "select * from workflow w INNER JOIN intake_workflow iw on w.workflowID = iw.workflowID where iw.workflowID = %s"
        cursor.execute(sql, (_workflowId,))

        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# TASK RELATED API CALLS
# sends task info for a file task
@app.route("/getFileTask", methods=['GET'])
def get_file_tasks():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _taskId = request.args.get('taskId')

        cursor = db.cursor()
        getTasks = "select * from workflowphaseTasks WHERE taskID = %s AND taskType = 'file'"
        cursor.execute(getTasks, (_taskId,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# MEETING CONFIRMATION API CALLS
# insert new discussion content request
@app.route("/newMeeting", methods=['POST'])
def create_meeting():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _mentorId = _json['mentorId']
        _studentId = _json['studentId']
        _content = _json['content']

        now = datetime.now()
        cur = now.strftime('%Y-%m-%d %H:%M:%S')

        cursor = db.cursor()
        insertMeet = "INSERT INTO meeting_confirmation (studentID, mentorID, content, isApproved, dateCreated) VALUES (%s, %s, %s, %s, %s)"
        meet = (_studentId, _mentorId, _content, 'PEND', cur)
        cursor.execute(insertMeet, meet)

        db.commit()

        sql = (
                "SELECT studentName, email, mentorEmail, intake FROM int_student WHERE studentId=%s")
        cursor = db.cursor()
        cursor.execute(sql, (_studentId,))
        records = cursor.fetchone()

        generateMail('DR', records[2], records[0])

        resp = jsonify('Request created successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# checks if a discussion content request exists, returns the record if it does
@app.route("/checkRequest", methods=['GET'])
def check_meet():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _studentId = request.args.get('studentId')

        cursor = db.cursor()
        getName = "SELECT * FROM meeting_confirmation WHERE studentID = %s ORDER BY FIELD(isApproved, 'PEND') desc, dateCreated desc"
        cursor.execute(getName, (_studentId,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# get all pending discussion content requests for a mentor
@app.route("/getRequests", methods=['GET'])
def get_requests():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _mentorId = request.args.get('mentorId')

        cursor = db.cursor()
        getReq = "SELECT i.studentName, mc.* FROM meeting_confirmation as mc INNER JOIN int_student as i on mc.studentID = i.studentID WHERE mc.mentorId = %s AND mc.isApproved = 'PEND' ORDER BY mc.dateCreated asc;"
        cursor.execute(getReq, (_mentorId,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# approve a discussion content request
@app.route("/approveRequest", methods=['POST'])
def approve_req():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _studentId = _json['studentId']
        _mentorId = _json['mentorId']

        cursor = db.cursor()
        sql = "UPDATE meeting_confirmation SET isApproved = 'APP' WHERE mentorId = %s AND studentId = %s AND isApproved = 'PEND'"
        val = (_mentorId, _studentId)

        cursor.execute(sql, val)

        db.commit()
        
        sql = "UPDATE int_student SET isApprovedMeeting = 'Y' WHERE studentId = %s"

        cursor.execute(sql, (_studentId,))

        db.commit()

        sql = (
                "SELECT studentName, email, mentorEmail, intake FROM int_student WHERE studentId=%s")
        cursor = db.cursor()
        cursor.execute(sql, (_studentId,))
        records = cursor.fetchone()

        generateMail('DA', records[1], records[0])

        resp = jsonify('Approval status updated successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()


# reject a discussion content request
@app.route("/rejectRequest", methods=['POST'])
def reject_req():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _studentId = _json['studentId']
        _mentorId = _json['mentorId']
        _rej = _json['rej']

        cursor = db.cursor()
        sql = "UPDATE meeting_confirmation SET isApproved = 'REJ', rejectComment = %s WHERE mentorId = %s AND studentId = %s AND isApproved = 'PEND'"
        val = (_rej, _mentorId, _studentId)

        cursor.execute(sql, val)

        db.commit()

        sql = (
                "SELECT studentName, email, mentorEmail, intake FROM int_student WHERE studentId=%s")
        cursor = db.cursor()
        cursor.execute(sql, (_studentId,))
        records = cursor.fetchone()

        generateMail('DA', records[1], records[0])

        resp = jsonify('Rejection status updated successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# insert new company application request
@app.route("/postInternshipRequest", methods=['POST'])
def create_com_app():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _mentorId = _json['mentorId']
        _studentId = _json['studentId']
        _companyID = _json['companyID']

        now = datetime.now()
        cur = now.strftime('%Y-%m-%d %H:%M:%S')

        cursor = db.cursor()
        insertMeet = "INSERT INTO company_approval_requests (studentID, mentorID, companyID, isApproved, dateCreated) VALUES (%s, %s, %s, %s, %s)"
        meet = (_studentId, _mentorId, _companyID, 'PEND', cur)
        cursor.execute(insertMeet, meet)

        db.commit()

        resp = jsonify('Request created successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# get all pending company application requests for a mentor
@app.route("/getCompanyRequests", methods=['GET'])
def get_com_requests():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _mentorId = request.args.get('mentorId')

        cursor = db.cursor()
        getReq = "SELECT i.studentName, ca.* FROM company_approval_requests as ca INNER JOIN int_student as i on ca.studentID = i.studentID WHERE ca.mentorId = %s AND ca.isApproved = 'PEND' ORDER BY ca.dateCreated asc;"
        cursor.execute(getReq, (_mentorId,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# checks if a discussion content request exists, returns the record if it does
@app.route("/checkCompanyRequests", methods=['GET'])
def check_com_req():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _studentId = request.args.get('studentId')

        cursor = db.cursor()
        getName = "SELECT * FROM company_approval_requests WHERE studentID = %s AND isApproved = 'PEND'"
        cursor.execute(getName, (_studentId,))
        cursor.fetchall()

        row_count = cursor.rowcount

        print("number of found rows for student: {}".format(row_count))
        if row_count == 0:
            resp = jsonify('Student has no pending application.')
            resp.status_code = 204
            return resp
        else:
            resp = jsonify('Student has a pending application.')
            resp.status_code = 200
            return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# approve a discussion content request
@app.route("/approveCompanyApplication", methods=['POST'])
def approve_com_app():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _studentId = _json['studentId']
        _mentorId = _json['mentorId']
        _companyId = _json['companyId']

        cursor = db.cursor()
        sql = "UPDATE company_approval_requests SET isApproved = 'APP' WHERE mentorId = %s AND studentId = %s AND companyId = %s AND isApproved = 'PEND'"
        val = (_mentorId, _studentId, _companyId)

        cursor.execute(sql, val)

        db.commit()
        
        sql = "UPDATE int_student SET isApprovedCompany = 'Y' WHERE studentId = %s"

        cursor.execute(sql, (_studentId,))

        db.commit()

        sql = (
                "SELECT studentName, email, mentorEmail, intake FROM int_student WHERE studentId=%s")
        cursor = db.cursor()
        cursor.execute(sql, (_studentId,))
        records = cursor.fetchone()

        generateMail('CA', records[1], records[0])

        resp = jsonify('Approval status updated successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()


# reject a discussion content request
@app.route("/rejectCompanyApplication", methods=['POST'])
def reject_com_app():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _studentId = _json['studentId']
        _mentorId = _json['mentorId']
        _companyId = _json['companyId']
        _rej = _json['rej']

        cursor = db.cursor()
        sql = "UPDATE company_approval_requests SET isApproved = 'REJ', rejectComment = %s WHERE mentorId = %s AND studentId = %s AND companyId = %s AND isApproved = 'PEND'"
        val = (_rej, _mentorId, _studentId, _companyId)

        cursor.execute(sql, val)

        db.commit()

        sql = (
                "SELECT studentName, email, mentorEmail, intake FROM int_student WHERE studentId=%s")
        cursor = db.cursor()
        cursor.execute(sql, (_studentId,))
        records = cursor.fetchone()

        generateMail('CA', records[1], records[0])
        
        resp = jsonify('Rejection status updated successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# FILE API CALLS
# Submit a file task
@app.route('/fileTaskSub', methods=['POST'])
def submit_file_task():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase",
            use_pure=True
        )

        data = dict(request.form)
        files = request.files['file']

        content = files.read()

        cursor = db.cursor(buffered=True, dictionary=True)

        check_existing = "SELECT * FROM fileSubmission WHERE taskID = %s AND studentID = %s"
        check_values = (data['taskId'], data['studentId'])
        cursor.execute(check_existing, check_values)

        row_count = cursor.rowcount

        print("number of found rows for file submission: {}".format(row_count))
        if row_count == 0:
            sql = "INSERT INTO fileSubmission (studentID, taskID, fileName, content) VALUES (%s, %s, %s, %s)"
            val = (data['studentId'], data['taskId'], files.filename, content)

            cursor.execute(sql, val)
        else:
            sql = "UPDATE fileSubmission SET fileName = %s, content = %s WHERE studentID = %s AND taskId = %s"
            val = (files.filename, content, data['studentId'], data['taskId'])

            cursor.execute(sql, val)

        db.commit()

        resp = jsonify('File uploaded successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# Submit a file as input from a form based task 
@app.route('/formFileSub', methods=['POST'])
def submit_form_file():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase",
            use_pure=True
        )

        data = dict(request.form)
        files = request.files['file']

        content = files.read()

        cursor = db.cursor(buffered=True, dictionary=True)

        check_existing = "SELECT * FROM fileSubmission WHERE taskID = %s AND studentID = %s AND formatID = %s"
        check_values = (data['taskId'], data['studentId'], data['formatId'])
        cursor.execute(check_existing, check_values)

        row_count = cursor.rowcount

        print("number of found rows: {}".format(row_count))
        if row_count == 0:
            sql = "INSERT INTO fileSubmission (studentID, taskID, fileName, content, formatID) VALUES (%s, %s, %s, %s, %s)"
            val = (data['studentId'], data['taskId'], files.filename, content, data['formatId'])

            cursor.execute(sql, val)
        else:
            sql = "UPDATE fileSubmission SET fileName = %s, content = %s WHERE studentID = %s AND taskID = %s AND formatID = %s"
            val = (files.filename, content, data['studentId'], data['taskId'], data['formatId'])

            cursor.execute(sql, val)

        db.commit()

        resp = jsonify('File uploaded successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# get existing form-based filename based on studentTP, taskId and formId
@app.route('/getFormFile', methods=['GET'])
def get_form_file():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase",
            use_pure=True
        )
        
        _formatId = request.args.get('formatId')
        _studentId = request.args.get('studentId')
        _taskId = request.args.get('taskId')

        cursor = db.cursor()
        getReq = "SELECT fileName FROM fileSubmission WHERE studentID = %s AND taskID = %s AND formatID = %s"
        val = (_studentId, _taskId, _formatId)
        cursor.execute(getReq, val)

        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)
        
    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# get existing task-based filename based on studentTP, taskId and formId
@app.route('/getTaskFile', methods=['GET'])
def get_task_file():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase",
            use_pure=True
        )
        
        _studentId = request.args.get('studentId')
        _taskId = request.args.get('taskId')

        cursor = db.cursor()
        getReq = "SELECT fileName FROM fileSubmission WHERE studentID = %s AND taskID = %s"
        val = (_studentId, _taskId)
        cursor.execute(getReq, val)

        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)
        
    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# get list of existing resource names based on faculty
@app.route('/getFileList', methods=['GET'])
def getFileList():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase",
            use_pure=True
        )
        
        _faculty = request.args.get('facultyId')
        
        cursor = db.cursor()
        if _faculty is not None:
            getReq = "select fileID, fileName, targetFaculty from internResources where targetFaculty=%s or targetFaculty='All' order by targetFaculty asc"
        else:
            getReq = "select fileID, fileName, targetFaculty from internResources where targetFaculty='All' order by targetFaculty asc"

        cursor.execute(getReq, (_faculty,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

        
    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# insert a new internship resource
@app.route('/insertResource', methods=['POST'])
def insert_resource():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        data = dict(request.form)
        files = request.files['file']

        content = files.read()

        cursor = db.cursor()
        sql = "INSERT INTO internResources (fileName, targetFaculty, content) VALUES (%s, %s, %s)"
        val = (files.filename, data['tFaculty'], content)

        cursor.execute(sql, val)

        db.commit()

        resp = jsonify('Resource uploaded successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# download a file
@app.route('/getFile', methods=['GET'])
def getInternFile():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase",
            use_pure=True
        )

        _fileID = request.args.get('fileId')

        cursor = db.cursor()

        getReq = "SELECT * FROM internResources WHERE fileID = %s"
        cursor.execute(getReq, (_fileID,))

        record = cursor.fetchone()
        name = record[1]
        content = record[3]
        file = io.BytesIO()
        file.write(content)
        file.seek(0)

        return send_file(file, attachment_filename=name, as_attachment=True)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()

    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# delete internship resource
@app.route('/deleteResource', methods=['POST'])
def delete_resource():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _fileId = _json['fileId']
        cursor = db.cursor()
        sql = "DELETE FROM internResources WHERE fileID = %s"

        cursor.execute(sql, (_fileId,))

        db.commit()

        resp = jsonify('File deleted successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp

    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# AUTHORITY RELATED API CALLS
# get accessible pages based on user role
@app.route("/getUserAccess", methods=['GET'])
def get_user_access():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _userRole = '%' + request.args.get('userRole') + '%'
        cursor = db.cursor()
        getPages = "SELECT * FROM access_authority WHERE accessedBy LIKE %s ORDER BY orderNum"
        cursor.execute(getPages, (_userRole,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# get pages with modifiable accessibility
@app.route("/getModPages", methods=['GET'])
def get_mod_pages():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        cursor = db.cursor()
        getPages = "SELECT * FROM access_authority WHERE isEditable = 'Y' ORDER BY pageID"
        cursor.execute(getPages)

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# update page accessibility
@app.route('/changeAccess', methods=['POST'])
def change_access():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _pageId = _json['pageId']
        _value = _json['value']
        cursor = db.cursor()
        sql = "UPDATE access_authority SET accessedBy = %s WHERE pageID = %s"
        val = (_value, _pageId)

        cursor.execute(sql, val)

        db.commit()

        resp = jsonify('Access updated successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp

    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# STUDENT INFORMATION RELATED API CALLS
# insert new student internship record after signing declaration
@app.route('/confirmDeclaration', methods=['POST'])
def declare_new_student():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _studentId = _json['studentId']
        _studentName = _json['studentName']
        _intake = _json['intake']
        _email = _json['email']
        _mentorEmail = _json['mentorEmail']

        now = datetime.now()
        cur = now.strftime('%Y-%m-%d %H:%M:%S')

        cursor = db.cursor()
        sql = "INSERT INTO int_student (studentID, studentName, intake, isExtended, extensionDate, isApprovedCompany, isApprovedMeeting, companyID, companyName, dateSigned, internshipStatus, email, mentorEmail) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        val = (_studentId, _studentName, _intake, 'N', '', 'N', 'N', '', '', cur, 'Active', _email, _mentorEmail)
        cursor.execute(sql, val)

        db.commit()

        resp = jsonify('Request created successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# Checks if a student is registered in the database. 
@app.route('/checkStudentExist', methods=['GET'])
def chk_student_existence():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _studentId = request.args.get('studentId')

        cursor = db.cursor()
        getStudent = "SELECT studentID FROM int_student WHERE studentID = %s"
        cursor.execute(getStudent, (_studentId,))
        cursor.fetchall()

        row_count = cursor.rowcount

        print("number of found rows for student: {}".format(row_count))
        if row_count == 0:
            resp = jsonify('This student has not registered.')
            resp.status_code = 204
            return resp
        else:
            resp = jsonify('The student exists in the database.')
            resp.status_code = 200
            return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# get a student profile with student ID
@app.route("/getStudent", methods=['GET'])
def get_student():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )
        
        _studentId = request.args.get('studentId')

        cursor = db.cursor()
        sql = "SELECT * FROM int_student a LEFT JOIN intake_workflow b on a.intake = b.intakeCode WHERE studentID = %s"
        cursor.execute(sql, (_studentId,))

        # this will extract row headers
        row_headers = [x[0] for x in cursor.description]
        records = cursor.fetchall()

        json_data = []
        for result in records:
            json_data.append(dict(zip(row_headers, result)))

        return json.dumps(json_data, default=str)

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# update a student's extension status and date
@app.route("/extendInternship", methods=['POST'])
def extend_internship():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _studentId = _json['studentId']
        _endDate = _json['endDate']

        cursor = db.cursor()

        sql = "UPDATE int_student SET isExtended = 'Y', extensionDate = %s WHERE studentID = %s"
        val = (_endDate, _studentId)

        cursor.execute(sql, val)
        print(cursor.statement)

        db.commit()

        resp = jsonify('Extension status updated successfully!')
        resp.status_code = 200
        return resp

    except mysql.connector.Error:
        print(cursor.statement)
        db.rollback()
        resp = jsonify('Something went wrong!')
        resp.status_code = 500
        return resp
        
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

# EMAIL GENERATION
MY_ADDRESS = 'TP041800@mail.apu.edu.my'
PASSWORD = 'TP041800'

def read_template(filename):
    """
    Returns a Template object comprising the contents of the 
    file specified by filename.
    """

    with open(filename, 'r', encoding='utf-8') as template_file:
        template_file_content = template_file.read()
    return Template(template_file_content)

def generateMail(mailType, email, name):

    if mailType == 'CA':
        message_template = read_template('companyApproval.txt')

        print(message_template)

        # set up the SMTP server
        s = smtplib.SMTP(host='smtp-mail.outlook.com', port=587)
        s.starttls()
        s.login(MY_ADDRESS, PASSWORD)

        msg = MIMEMultipart()       # create a messagetemplate

        # add in the actual person name to the message
        message = message_template.substitute(
            PERSON_NAME=name.title())

        # Prints out the message body for our sake
        print(message)

        # setup the parameters of the message
        msg['From'] = MY_ADDRESS
        msg['To'] = email
        msg['Subject'] = "Company Application Request Status Update"

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))

        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg

        # Terminate the SMTP session and close the connection
        s.quit()
    
    elif mailType == 'DA':
        message_template = read_template('discussionApproval.txt')

        print(message_template)

        # set up the SMTP server
        s = smtplib.SMTP(host='smtp-mail.outlook.com', port=587)
        s.starttls()
        s.login(MY_ADDRESS, PASSWORD)

        msg = MIMEMultipart()       # create a messagetemplate

        # add in the actual person name to the message
        message = message_template.substitute(
            PERSON_NAME=name.title())

        # Prints out the message body for our sake
        print(message)

        # setup the parameters of the message
        msg['From'] = MY_ADDRESS
        msg['To'] = email
        msg['Subject'] = "Discussion Content Approval Request Status Update"

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))

        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg

    elif mailType == 'DR':
        message_template = read_template('discussionRequest.txt')

        print(message_template)

        # set up the SMTP server
        s = smtplib.SMTP(host='smtp-mail.outlook.com', port=587)
        s.starttls()
        s.login(MY_ADDRESS, PASSWORD)

        msg = MIMEMultipart()       # create a messagetemplate

        # add in the actual person name to the message
        message = message_template.substitute(
            PERSON_NAME=name.title())

        # Prints out the message body for our sake
        print(message)

        # setup the parameters of the message
        msg['From'] = MY_ADDRESS
        msg['To'] = email
        msg['Subject'] = "New Discussion Request from Mentee"

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))

        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg

@app.route("/")
def home():
    return render_template("admin/admin_copy.html")


@app.route("/home")
def admin():
    return render_template("home.html")

if __name__ == '__main__':
    app.run(debug=True)
