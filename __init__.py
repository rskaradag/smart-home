from flask import Flask,render_template, jsonify, abort, request, make_response, url_for
from flask.ext.httpauth import HTTPBasicAuth

from content_management import *

TOPIC_DICT = Content()

app = Flask(__name__)
#app.config.from_pyfile('config.py')
auth = HTTPBasicAuth()
#db=SQLAlchemy(app)

@auth.verify_password
def verify_password(username, password):
    if username=='slck':
        return True
    return False


@app.route('/')
def homepage():
  return render_template("main.html")

@app.route('/dashboard/')
def dashboard():
  return render_template("dashboard.html", TOPIC_DICT = TOPIC_DICT)

@app.route('/home',methods=['GET','POST'])
def index():
	return "Hello "

@app.route('/login',methods=['GET','POST'])
@auth.login_required
def index2():
	return "Welcome "


if __name__ == '__main__':
	app.run(debug=True)
