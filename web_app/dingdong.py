from random import SystemRandom
from flask import Flask, request, redirect, session, url_for, flash, jsonify
import os
from flask import render_template, url_for
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
import requests

random = SystemRandom()

app = Flask(__name__)
CORS(app)

# NOTIFICATION SCHEDULING

x = datetime.today()
y = x.replace(day=x.day, hour=15, minute=0, second=0,
              microsecond=0) + timedelta(seconds=3)
delta_t = y-x

secs = delta_t.total_seconds()


def hello_world():
    print("hello world")


t = Timer(secs, hello_world)
t.start()

USER = "TP041800"
PASSWORD = "TP041800"


@app.route("/generate")
def generate_st(service_url):
    credentials = (USER + ":" + PASSWORD).split(':')
    resp = requests.post('https://cas.apiit.edu.my' + '/cas/v1/tickets/',
                         data={'username': credentials[0], 'password': credentials[1]})
    if resp.status_code == 201:
        resp = requests.post(resp.headers['Location'], data={
                             'service': service_url})

    if resp.status_code == 200:
        return resp.text


@app.route("/push")
def push():
    msg = "Custom message"
    payload = {'title': 'Test of the notification', 'msg': 'testing',
               'to': [{'item': 'TP041800', 'type': 'staff/student'}]
               }

    headers = {'Authorization': 'Bearer ' +
               generate_st("https://api.apiit.edu.my/dingdong/new")}
    r = requests.post('https://api.apiit.edu.my/dingdong/new',
                      json=payload, headers=headers)
    print("d " + str(r.status_code))
    print("e " + r.text)


if __name__ == '__main__':
    app.run(debug=True)
