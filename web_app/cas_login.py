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

random = SystemRandom()

app = Flask(__name__)

keys = requests.get('https://cas1.apiit.edu.my/cas/oidc/jwks').json()

db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="2247424yY",
    database="intdatabase"
)

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
    row_headers=[x[0] for x in cursor.description] #this will extract row headers
    records = cursor.fetchall()

    # INSERTION
    # values_to_insert = [("TP041800", "yeeseng", "yeesengxp@gmail.com" ),("TP041801", "yeesengx", "TP041800@mail.apu.edu.my" )]
    # query = "INSERT INTO testTable (Id, stdName, stdEmail) VALUES " + ",".join("(%s, %s, %s)" for _ in values_to_insert)
    # flattened_values = [item for sublist in values_to_insert for item in sublist]
    # mycursor.execute(query, flattened_values)
    # db.commit()

    json_data=[]
    for result in records:
        json_data.append(dict(zip(row_headers,result)))

    cursor.close()

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

@app.route('/getForm', methods=['GET'])
def get_Form():

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="2247424yY",
        database="intdatabase"
    )

    cursor = db.cursor()
    db.row_factory = dictfetchall
    cursor.execute("SELECT formatID, name, type, if(required=1,'true','false') as required, display, if(selected=1,'true','false') as selected, title FROM FormFormat WHERE formName='F1'")
    #row_headers=[x[0] for x in cursor.description] #this will extract row headers
    records = dictfetchall(cursor)
    print(records)
    #json_data=[]
    for result in records:
        cursor.execute("select `key`,label from optionsTable o, (SELECT formatID from formformat where `type`='select') a  where o.fieldID = a.formatID AND o.fieldID =" + str(result['formatID']))
        row = dictfetchall(cursor)
        print(row)
        if row is not None:
            result['options'] = row
        #json_data.append(dict(zip(row_headers,result)))

    cursor.close()
    return json.dumps(records)

@app.route("/newForm", methods=['POST'])
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
    _options = _json['options']
 
    format_id = _name.lower()
    print(format_id)

    cursor = db.cursor()
    insertFields = "INSERT INTO FormFormat (formName, formatID, name, type, required, display, selected, title) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    field = (_fname, format_id, _name, _type, _required, _display, _selected, _title)

    cursor.execute(insertFields, field)

    insertOptions = "INSERT INTO optionsTable(fieldID, `key`, label) VALUES (%s, %s, %s)"

    print(_options)
    if not _options :
        for option in _options :
            print(option)
            opt = (format_id, option.lower(), option)
            cursor.execute(insertOptions, opt)
    db.commit()

    cursor.close()

    resp = jsonify('User updated successfully!')
    resp.status_code = 200
    return resp

@app.route("/")
def home():
    return render_template("admin/admin_copy.html")


@app.route("/home")
def admin():
    return render_template("home.html")


app.secret_key = 'super secret key'

# To use http for openid Connect
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

CONFIG = {
    'client_id': 'this will be provided by CAS after you have registered your service successfully',
    'client_secret': "this will be provided by CAS after you have registered your service successfully",
    'auth_url': 'https://cas1.apiit.edu.my/cas/oidc/authorize',
    'token_url': 'https://cas1.apiit.edu.my/cas/oidc/accessToken',
    'scope': ['urn:globus:auth:scope:api.globus.org:all'],
    'redirect_uri': "http://localhost:5000/callback"
}

OIDC_CONFIG = {
    'jwt_pubkeys': keys,
    'scope': ['openid', 'email', 'profile'],
    'expected_issuer': 'https://cas1.apiit.edu.my/cas/oidc',
    'algorithm': 'RS256',
}
authorization_response = input('http://localhost:5000/callback')

CONFIG.update(OIDC_CONFIG)


@app.route('/login', methods=['GET'])
def login():
    provider = OAuth2Session(client_id=CONFIG['client_id'],
                             scope=CONFIG['scope'],
                             redirect_uri=CONFIG['redirect_uri'])
    nonce = str(random.randint(0, 1e10))

    url, state = provider.authorization_url(CONFIG['auth_url'],
                                            nonce=nonce)
    session['oauth2_state'] = state
    session['nonce'] = nonce
    return redirect(url)


@app.route('/callback', methods=['GET'])
def callback():
    provider = OAuth2Session(CONFIG['client_id'],
                             redirect_uri=CONFIG['redirect_uri'],
                             authorization_response=authorization_response,
                             state=session['oauth2_state'])
    response = provider.fetch_token(
        token_url=CONFIG['token_url'],
        client_secret=CONFIG['client_secret'])

    session['access_token'] = response['access_token']
    id_token = response['id_token']
    claims = jwt.decode(id_token,
                        key=CONFIG['jwt_pubkeys'],
                        issuer=CONFIG['expected_issuer'],
                        audience=CONFIG['client_id'],
                        algorithms=CONFIG['algorithm'],
                        access_token=response['access_token'])
    assert session['nonce'] == claims['nonce']
    session['user_id'] = claims['sub']
    session['user_email'] = claims['email']
    session['user_name'] = claims['name']
    return redirect(url_for('index'))


ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/fileSub', methods=['GET','POST'])
def submit():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        content = request.files['file'].read()

        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            try:
                cursor = db.cursor()

                query = """INSERT INTO fileTable (fileName, content) VALUES
                (%s,%s)"""
                
                subFile = (filename, content)

                result = cursor.execute(query, subFile)

                db.commit()
                print ("Image and file inserted successfully as a BLOB into fileTable table", result)
            except mysql.connector.Error as error :
                print(cursor.statement)
                db.rollback()
            finally:
                # closing database connection.
                if(db.is_connected()):
                    cursor.close()
                    db.close()
            flash('File successfully uploaded')
            return redirect('/')

        else:
            flash('Allowed file types are txt, pdf, png, jpg, jpeg, gif','docx')
            return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True)
