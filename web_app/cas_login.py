from random import SystemRandom
from flask import Flask, request, redirect, session, url_for, flash, jsonify
from requests_oauthlib import OAuth2Session
import requests
from jose import jwt
import os
from flask import render_template, url_for
import mysql.connector
from werkzeug.utils import secure_filename
import json
from flask_cors import CORS
from datetime import datetime

random = SystemRandom()

app = Flask(__name__)
CORS(app)

keys = requests.get('https://cas1.apiit.edu.my/cas/oidc/jwks').json()

# TESTING API CALLS
@app.route('/getcon', methods=['GET'])
def get_contacts():

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

    # INSERTION
    # values_to_insert = [("TP041800", "yeeseng", "yeesengxp@gmail.com" ),("TP041801", "yeesengx", "TP041800@mail.apu.edu.my" )]
    # query = "INSERT INTO testTable (Id, stdName, stdEmail) VALUES " + ",".join("(%s, %s, %s)" for _ in values_to_insert)
    # flattened_values = [item for sublist in values_to_insert for item in sublist]
    # mycursor.execute(query, flattened_values)
    # db.commit()

    json_data = []
    for result in records:
        json_data.append(dict(zip(row_headers, result)))

    cursor.close()
    db.close()

    return json.dumps(json_data)


@app.route('/upcon', methods=['POST'])
def update_contacts():
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

    cursor.close()
    db.close()

    resp = jsonify('User updated successfully!')
    resp.status_code = 200
    return resp


def dictfetchall(cursor):
    #"Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

# FORM RELATED API CALLS

# fetch form fields
@app.route('/getForm', methods=['GET'])
def get_form():
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
    # row_headers=[x[0] for x in cursor.description] #this will extract row headers
    records = dictfetchall(cursor)
    # json_data=[]
    for result in records:
        cursor.execute(
            "select `key`,label from optionsTable o, (SELECT formatID from formformat where `type`='select' OR `type`='multi') a where o.fieldID = a.formatID AND o.fieldID = '" + result['formatID'] + "'")
        row = dictfetchall(cursor)
        if row is not None:
            result['options'] = row
        # json_data.append(dict(zip(row_headers,result)))

    cursor.close()
    db.close()

    return json.dumps(records)

# insert user input form data
@app.route('/insertFormVal', methods=['POST'])
def insert_form_value():
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

    cursor = db.cursor(buffered=True, dictionary=True)
    check_existing = "SELECT * FROM FormFieldSubmission WHERE fieldID = %s && studentID = %s"
    check_values = (_fieldName, _studentID)
    cursor.execute(check_existing, check_values)

    row_count = cursor.rowcount

    print("number of found rows: {}".format(row_count))
    if row_count == 0:
        insert_sql = "INSERT INTO FormFieldSubmission (fieldID, studentID, value) VALUES (%s, %s, %s)"
        values = (_fieldName, _studentID, _fieldVal)
        cursor.execute(insert_sql, values)
        print("record is inserted")
    else:
        update_sql = "UPDATE FormFieldSubmission SET value = %s WHERE fieldID = %s AND studentID = %s"
        values = (_fieldVal, _fieldName, _studentID)
        cursor.execute(update_sql, values)
        print("record is updated")

    db.commit()

    cursor.close()
    db.close()

    resp = jsonify('Form data inserted successfully!')
    resp.status_code = 200
    return resp

# fetch user inserted form data
@app.route('/loadFormVal', methods=['GET'])
def get_form_val():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="2247424yY",
        database="intdatabase"
    )

    _fieldId = request.args.get('fieldId')
    _stdId = request.args.get('stdId')

    cursor = db.cursor(buffered=True)
    sql = ("SELECT value from FormFieldSubmission where studentID = %s AND fieldID = %s")
    val = (_stdId, _fieldId)

    cursor.execute(sql, val)

    row_headers = [x[0] for x in cursor.description]
    records = cursor.fetchall()

    json_data = []
    for result in records:
        json_data.append(dict(zip(row_headers, result)))
    cursor.close()
    db.close()

    return json.dumps(json_data)

# sends a list of existing forms
@app.route("/formNameValidation", methods=['GET'])
def check_form():
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

    cursor.close()
    db.close()

    return json.dumps(json_data)

# sends a list of existing form names
@app.route("/formList", methods=['GET'])
def get_form_list():
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

    cursor.close()
    db.close()

    return json.dumps(json_data, default=str)

# inserts a new form name
@app.route("/newForm", methods=['POST'])
def create_form():
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

    cursor.close()
    db.close()

    resp = jsonify('User updated successfully!')
    resp.status_code = 200
    return resp

# insert form fields
@app.route("/writeFields", methods=['POST'])
def sub_form():
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
            print(option)
            opt = (format_id, option.lower(), option)
            cursor.execute(insertOptions, opt)
    db.commit()

    cursor.close()
    db.close()

    resp = jsonify('Form is created successfully!')
    resp.status_code = 200
    return resp

# WORKFLOW RELATED API CALLS

# send existing workflows
@app.route("/workflowNameValidation", methods=['GET'])
def check_workflow():
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

    cursor.close()
    db.close()

    return json.dumps(json_data)

# inserts a new workflow name
@app.route("/newWorkflow", methods=['POST'])
def create_workflow():
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

    cursor.close()
    db.close()

    resp = jsonify('Workflow created successfully!')
    resp.status_code = 200
    return resp

# insert workflow phases
@app.route("/writePhases", methods=['POST'])
def sub_phases():
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

    cursor.close()
    db.close()

    resp = jsonify('Workflow phases written successfully!')
    resp.status_code = 200
    return resp

# insert workflow tasks
@app.route("/writeTasks", methods=['POST'])
def sub_tasks():
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
    _formId = None

    if _taskType == 'form':
        _formId = _json['formId']

    cursor = db.cursor()

    insertFields = "INSERT INTO WorkflowPhaseTasks (phaseID, taskID, taskName, taskType, formID) VALUES (%s, %s, %s, %s, %s)"
    field = (_phaseId, _taskId, _taskName, _taskType, _formId)

    cursor.execute(insertFields, field)

    db.commit()

    cursor.close()
    db.close()

    resp = jsonify('Workflow tasks written successfully!')
    resp.status_code = 200
    return resp

# sends a list of existing form names
@app.route("/workflowList", methods=['GET'])
def get_workflow_list():
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

    cursor.close()
    db.close()

    return json.dumps(json_data, default=str)

# sends a list of existing form names
@app.route("/getWorkflow", methods=['GET'])
def get_workflow():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="2247424yY",
        database="intdatabase"
    )

    _workflowId = request.args.get('workflowId')
    print(_workflowId)
    cursor = db.cursor()
    getWorkflow = "SELECT * FROM Workflow w INNER JOIN workflowphase p ON w.workflowID = p.workflowID INNER JOIN workflowphasetasks t ON p.phaseID = t.phaseID WHERE p.workflowID=%s ORDER BY p.phaseOrder"
    cursor.execute(getWorkflow, (_workflowId,))

    # this will extract row headers
    row_headers = [x[0] for x in cursor.description]
    records = cursor.fetchall()

    json_data = []
    for result in records:
        json_data.append(dict(zip(row_headers, result)))

    cursor.close()
    db.close()

    return json.dumps(json_data, default=str)

 # sends phase info of selected workflow
@app.route("/phaseData", methods=['GET'])
def get_phases():
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

    cursor.close()
    db.close()

    return json.dumps(json_data, default=str)

# insert workflow assignment
@app.route("/assignFlow", methods=['POST'])
def assign_workflow():
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

    cursor.close()
    db.close()

    resp = jsonify('Workflow assignment written successfully!')
    resp.status_code = 200
    return resp

@app.route("/")
def home():
    return render_template("admin/admin_copy.html")


@app.route("/home")
def admin():
    return render_template("home.html")


# ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx'])


# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
if __name__ == '__main__':
    app.run(debug=True)
