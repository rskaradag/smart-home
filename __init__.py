from flask import Flask, jsonify, abort, request, make_response, url_for
from flask.ext.httpauth import HTTPBasicAuth
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    if username=='slck':
        return True
    return False


@app.route('/home',methods=['GET','POST'])
def index():
	return "Hello "

@app.route('/login',methods=['GET','POST'])
@auth.login_required
def index2():
	return "Welcome "


if __name__ == '__main__':
	app.run(debug=True)
