from random import SystemRandom
from flask import Flask, request, redirect, session, url_for, flash, jsonify
import os
from flask import render_template, url_for
import mysql.connector
from werkzeug.utils import secure_filename
import json
from flask_cors import CORS
from datetime import datetime
from werkzeug.datastructures import ImmutableMultiDict
import io
from flask import send_file

random = SystemRandom()

app = Flask(__name__)
CORS(app)

# TESTING API CALLS
@app.route('/getcon', methods=['GET'])
def get_contacts():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        cursor = db.cursor()
        cursor.execute("SELECT * FROM testTable")
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


@app.route('/upcon', methods=['POST'])
def update_contacts():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        _json = request.json
        _name = _json['data']
        _sid = _json['sid']
        cursor = db.cursor()
        sql = "UPDATE testTable SET stdName = %s WHERE id = %s"
        val = (_name, _sid)

        cursor.execute(sql, val)

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

        sql = ("SELECT formatID, name, type, if(required=1,'true','false') as required, display, if(selected=1,'true','false') as selected, title FROM FormFormat WHERE formID=%s")

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
        _options = None
        try:
            _options = _json['options']
        except:
            print("This field has no options.")

        format_id = _name.lower()
        cursor = db.cursor()

        insertFields = "INSERT INTO FormFormat (formID, formatID, name, type, required, display, selected, title) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        field = (_fname, format_id, _name, _type,
                _required, _display, _selected, _title)

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

# sends a list of existing form names
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

# sends a list of existing form names
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
# insert new meeting request
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

# sends a result of an existing meeting request
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

# get all pending requests for a mentor
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
        getReq = "SELECT * FROM meeting_confirmation WHERE mentorId = %s AND isApproved = 'PEND' ORDER BY dateCreated asc"
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

# approve a request
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


# reject a request
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

# @app.route('/fileSub', methods=['GET','POST'])
# def submit():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             flash('No file part')
#             return redirect(request.url)
#         file = request.files['file']
#         content = request.files['file'].read()

#         if file.filename == '':
#             flash('No file selected for uploading')
#             return redirect(request.url)

#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             try:
#                 cursor = db.cursor()

#                 query = """INSERT INTO fileTable (fileName, content) VALUES
#                 (%s,%s)"""

#                 subFile = (filename, content)

#                 result = cursor.execute(query, subFile)

#                 db.commit()
#                 print ("Image and file inserted successfully as a BLOB into fileTable table", result)
#             except mysql.connector.Error as error :
#                 print(cursor.statement)
#                 db.rollback()
#             finally:
#                 # closing database connection.
#                 if(db.is_connected()):
#                     cursor.close()
#                     db.close()
#             flash('File successfully uploaded')
#             return redirect('/')

#         else:
#             flash('Allowed file types are txt, pdf, png, jpg, jpeg, gif','docx')
#             return redirect(request.url)

@app.route("/")
def home():
    return render_template("admin/admin_copy.html")


@app.route("/home")
def admin():
    return render_template("home.html")

if __name__ == '__main__':
    app.run(debug=True)
