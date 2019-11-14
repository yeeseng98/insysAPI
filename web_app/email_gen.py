import smtplib
from string import Template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask_cors import CORS
from flask import Flask, jsonify
import mysql.connector
from datetime import datetime, timedelta
import time
from threading import Timer
import schedule
import time

MY_ADDRESS = 'TP041800@mail.apu.edu.my'
PASSWORD = 'TP041800'

app = Flask(__name__)
CORS(app)


def check_intakes_seven_days_due():

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        now = datetime.now()
        cur = now.strftime('%Y-%m-%d')

        print(cur)
        sql = (
            "SELECT wp.phaseID, intakeID, startDate, endDate, phaseName FROM intake_phase_duration ip INNER JOIN workflowPhase wp on ip.phaseID = wp.phaseID WHERE DATE(endDate) = DATE_ADD(%s, INTERVAL 7 DAY)")

        cursor = db.cursor()
        cursor.execute(sql, (cur,))

        records = cursor.fetchall()

        row_count = cursor.rowcount

        if row_count > 0:
            dueIntakes = []

            for row in records:
                dueIntakes.append(row)
            print(dueIntakes)
            return find_students(dueIntakes)

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


def find_students(dueIntakes):

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="2247424yY",
            database="intdatabase"
        )

        for intake in dueIntakes:
            sql = (
                "SELECT studentName, email, mentorEmail, intake FROM int_student WHERE intake = %s")
            cursor = db.cursor()
            cursor.execute(sql, (intake[1],))
            records = cursor.fetchall()

            row_count = cursor.rowcount

            if row_count > 0:
                stdNames = []
                students = []
                mentors = []
                intakes = []

                for row in records:
                    stdNames.append(row[0])
                    students.append(row[1])
                    mentors.append(row[2])
                    intakes.append(row[3])
                print(students)
                generate_student_mails(
                    stdNames, students, intake[3], intake[4])
                generate_mentor_mails(
                    mentors, stdNames, intakes, intake[3], intake[4])

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


def read_template(filename):
    """
    Returns a Template object comprising the contents of the 
    file specified by filename.
    """

    with open(filename, 'r', encoding='utf-8') as template_file:
        template_file_content = template_file.read()
    return Template(template_file_content)


def generate_student_mails(studentNames, studentEmails, endDate, phaseName):
    message_template = read_template('studentDue7.txt')

    print(message_template)

    # set up the SMTP server
    s = smtplib.SMTP(host='smtp-mail.outlook.com', port=587)
    s.starttls()
    s.login(MY_ADDRESS, PASSWORD)

    # For each contact, send the email:
    for name, email in zip(studentNames, studentEmails):
        msg = MIMEMultipart()       # create a messagetemplate

        # add in the actual person name to the message e
        message = message_template.substitute(
            PERSON_NAME=name.title(), END_DATE=endDate.title(), PHASE=phaseName.title())

        # Prints out the message body for our sake
        print(message)

        # setup the parameters of the message
        msg['From'] = MY_ADDRESS
        msg['To'] = email
        msg['Subject'] = "Reminder for internship phase closure"

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))

        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg

    # Terminate the SMTP session and close the connection
    s.quit()


def generate_mentor_mails(mentorEmails, studentNames, intakes, endDate, phaseName):
    message_template = read_template('mentorDue7.txt')

    print(message_template)

    # set up the SMTP server
    s = smtplib.SMTP(host='smtp-mail.outlook.com', port=587)
    s.starttls()
    s.login(MY_ADDRESS, PASSWORD)

    # For each contact, send the email:
    for email, stdName, intake in zip(mentorEmails, studentNames, intakes):
        msg = MIMEMultipart()       # create a messagetemplate

        # add in the actual person name to the message
        message = message_template.substitute(
            PERSON_NAME=stdName.title(), INTAKE=intake.title(), END_DATE=endDate.title(), PHASE=phaseName.title())

        # Prints out the message body for our sake
        print(message)

        # setup the parameters of the message
        msg['From'] = MY_ADDRESS
        msg['To'] = email
        msg['Subject'] = "Reminder for internship phase closure"

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))

        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg

    # Terminate the SMTP session and close the connection
    s.quit()


# x = datetime.today()
# y = x.replace(day=x.day, hour=12, minute=40, second=0,
#               microsecond=0) + timedelta(days=1)
# print(x)
# print(y)
# delta_t = y-x
# print(delta_t)
# secs = delta_t.total_seconds()

# t = Timer(secs, check_intakes_seven_days_due)
# t.start()

schedule.every().day.at("12:00").do(check_intakes_seven_days_due)

while True:
    schedule.run_pending()
    time.sleep(1)

if __name__ == '__main__':
    app.run(debug=True)
