import smtplib

from string import Template

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask_cors import CORS

from flask import Flask, jsonify
import mysql.connector
from datetime import datetime

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
            "SELECT * FROM intake_phase_duration WHERE DATE(endDate) = DATE_ADD(%s, INTERVAL 7 DAY)")

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
                "SELECT studentName, email, mentorEmail FROM int_student WHERE intake = %s")
            cursor = db.cursor()
            cursor.execute(sql, (intake[1],))
            records = cursor.fetchall()

            row_count = cursor.rowcount

            if row_count > 0:
                stdNames = []
                students = []
                mentors = []

                for row in records:
                    stdNames.append(row[0])
                    students.append(row[1])
                    mentors.append(row[2])
                print(students)
                generate_student_mails(stdNames, students)
                generate_mentor_mails(mentors)

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


def generate_student_mails(studentNames, studentEmails):
    message_template = read_template('message.txt')

    print(message_template)

    # set up the SMTP server
    s = smtplib.SMTP(host='smtp-mail.outlook.com', port=587)
    s.starttls()
    s.login(MY_ADDRESS, PASSWORD)

    # For each contact, send the email:
    for name, email in zip(studentNames, studentEmails):
        msg = MIMEMultipart()       # create a messagetemplate

        # add in the actual person name to the message e
        message = message_template.substitute(PERSON_NAME=name.title())

        # Prints out the message body for our sake
        print(message)

        # setup the parameters of the message
        msg['From'] = MY_ADDRESS
        msg['To'] = email
        msg['Subject'] = "This is TEST"

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))

        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg

    # Terminate the SMTP session and close the connection
    s.quit()


def generate_mentor_mails(mentorEmails):
    message_template = read_template('mentor.txt')

    print(message_template)

    # set up the SMTP server
    s = smtplib.SMTP(host='smtp-mail.outlook.com', port=587)
    s.starttls()
    s.login(MY_ADDRESS, PASSWORD)

    # For each contact, send the email:
    for email in mentorEmails:
        msg = MIMEMultipart()       # create a messagetemplate

        # add in the actual person name to the message
        message = message_template.substitute()

        # Prints out the message body for our sake
        print(message)

        # setup the parameters of the message
        msg['From'] = MY_ADDRESS
        msg['To'] = email
        msg['Subject'] = "This is TEST"

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))

        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg

    # Terminate the SMTP session and close the connection
    s.quit()


if __name__ == '__main__':
    with app.app_context():
        check_intakes_seven_days_due()
