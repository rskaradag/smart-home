
# -*- coding: utf-8 -*-
from flask import Flask,render_template, jsonify, abort, request, make_response, url_for,flash, redirect,session
from flask.ext.httpauth import HTTPBasicAuth
import json
from content_management import *
from wtforms import Form, BooleanField, TextField, PasswordField, validators
from passlib.hash import sha256_crypt
from MySQLdb import escape_string as thwart
from functools import wraps
from pwhash import *
import collections
import base64
import api

import serial

from dbconnect import connection
import gc 

TOPIC_DICT = Content()

app = Flask(__name__)
#app.config.from_pyfile('config.py')
auth = HTTPBasicAuth()
#db=SQLAlchemy(app)


#USER_LIST = content_users()

tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]

class user(object):

	def __init__(self,id,username,name,surname,telephone,email,authority,active):
		self.username=username
		self.name=name
		self.surname=surname
		self.id=id
		self.telephone=telephone
		self.email=email
		self.authority=authority
		self.active=active
	
	def get_id(self):
		return self.id
	
	def get_username(self):
		return self.username

	def get_name(self):
		return self.name
	
class RegistrationForm(Form):
	username=TextField('Username',[validators.Length(min=4, max=20)])
	email = TextField('Email Address',[validators.Length(min=6, max=50)])
	password = PasswordField('Password',[validators.Required(),
										validators.EqualTo('confirm',message="Passwords must match")])
	confirm = PasswordField('Repeat Password')
	accept_tos=BooleanField('I accept the <a href="/tos/">Terms of Service</a> and the <a href="/privacy/">Privacy Notice</a> (Last updated Jan 15 2016',[validators.Required()])
	
def turkish_character(data):
	data=data.replace("\u011f","ğ");
	data=data.replace("\u00fc","ü");
	data=data.replace("\u0131","ı");
	data=data.replace("\u015f","ş");
	data=data.replace("\u00e7","ç");
	data=data.replace("\u00f6","ö");
	data=data.replace("\u00dc","Ü");
	data=data.replace("\u011e","Ğ");
	data=data.replace("\u0130","İ");
	data=data.replace("\u015e","Ş");
	data=data.replace("\u00c7","Ç");
	data=data.replace("\u00d6","Ö");
	data=data.replace("}{","},{");
	return data
	
def login_required(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash("You need to login first")
			return redirect(url_for('login_page'))
	return wrap
		
@app.route("/logout/")
@login_required
def logout():
    session.clear()
    flash("You have been logged out!")
    gc.collect()
    return redirect(url_for('dashboard'))
	
	
@app.route('/register/',methods=['GET','POST'])
def register_page():
	try:		
		form = RegistrationForm(request.form)
		
		if request.method == "POST" and form.validate():
			username =form.username.data
			email = form.email.data
			password = sha256_crypt.encrypt((str(form.password.data)))
			
			c,conn = connection()
			
			x = c.execute("SELECT * FROM tb_users WHERE username =(%s)",
							(thwart(username)))
			if int(x) > 0:
				flash("That email is already taken, please choose another")
				return render_template('register.html',form=form)
			else:
				c.execute("INSERT INTO tb_users (username,password,email) VALUES (%s,%s,%s)",
							(thwart(username),thwart(password),thwart(email)))
				conn.commit()
				flash("Thanks for registering ! ")
				c.close()
				conn.close()
				gc.collect()				
				session['logged_in']= True				
				session['username'] = username				
				return redirect(url_for('dashboard'))
		return render_template("register.html",form=form)
			
			
	except Exception as e:
		return(str(e))
			
@app.errorhandler(404)
def not_found(e):
  return render_template("404.html")
  
@app.errorhandler(405)
def method_not_found(e):
  return render_template("405.html")

def rest_login_user(username,password):	
	if username != "" and password != "":	
		c, conn = connection()
		data = c.execute("SELECT username, password FROM tb_users WHERE username = (%s)", username)
					
		data = c.fetchone()[1]
			
		if sha256_crypt.verify(password,data):
			return True
		else:
			return False
	else:
		return False
  
@auth.verify_password
def verify_password(username, password):
	if username != "" and password != "":
		auth_header = request.headers.get('Authorization', None)
		if auth_header is None:
			return False
		else:		
			auth_header = auth_header.replace('Basic ', '')
			auth_header2=base64.b64decode(auth_header)
			username, password = auth_header2.split(':', 1)
			return rest_login_user(username,password)	
	else:
		return False
	
@app.route('/')
def homepage():
  return render_template("header.html")

@app.route('/login/', methods=['GET','POST'])
def login_page():
    error = ''
    try:
        c, conn = connection()
        if request.method == "POST":
						
            data = c.execute("SELECT username, password FROM tb_users WHERE username = (%s)", thwart(request.form['username']))
            
            data = c.fetchone()[1]

            if sha256_crypt.verify(request.form['password'], data):
                session['logged_in'] = True
                session['username'] = request.form['username']

                flash("You are now logged in")
                return redirect(url_for("userlist"))

            else:
                error = "Invalid credentials, try again 1."

        gc.collect()

        return render_template("login.html", error=error)

    except Exception as e:
        flash(e)
        error = "Invalid credentials, try again."
        return render_template("login.html", error = error)  
		
		
@app.route('/dashboard/')
@login_required
def dashboard():
  return render_template("dashboard.html", TOPIC_DICT = TOPIC_DICT)
  
@app.route('/userlist/')
@login_required
def userlist():
	error=''
	try:
		i=0
		htmlresponse=''
		values=[]
		USER_LIST=[]
		c, conn = connection()	
		c.execute("SET NAMES utf8")
		c.execute("SELECT uid,username,name,surname,telephone,email,authority,active FROM tb_users ")
		rows = c.fetchall()
		
		for row in rows:
			values.append(user(row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7]))
			#htmlresponse=htmlresponse+'<tr><td>'+str(row[0])+'</td><td>'+str(row[1])+'</td></tr>'
					
		c.close()
		conn.close()
		return render_template("list.html",values=values) 	

	except Exception as e:
		flash(e)
		return render_template("login.html",error=e)  

@app.route('/slashboard/')
@login_required
def slashboard():
  try:
    return render_template("slahsboard.html", TOPIC_DICT = TOPIC_DICT) 
  except Exception as e:
    return render_template("500.html",error=e)
  
@app.route('/home',methods=['GET','POST'])
@login_required
def index():
	return "Hello "

@app.route('/tirrekanil',methods=['GET','POST'])
@auth.login_required
def tirrekanil():
	return jsonify({'tasks': tasks})
	
@app.route('/tirrekanil/add', methods=['POST'])
@auth.login_required
def create_task():
    if not request.json or not 'title' in request.json:
        abort(400)
    task = {
        'id': tasks[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    tasks.append(task)
    return jsonify({'task': task}), 201
	
@app.route('/rest/login',methods=['GET','POST'])
@auth.login_required
def rest_login():
	return "Hello, %s!" % auth.username()

@app.route('/rest/users',methods=['GET','POST'])
@auth.login_required
def rest_users():
	try:
		response=[]
		data={}

		json_data=""
		c, conn = connection()
		if request.method=="GET":				
			c.execute("SET NAMES utf8")
			c.execute("SELECT uid,username,name,surname,telephone,email,authority FROM tb_users ")
			rows = c.fetchall()
			
			for item in rows:
				data['ID']=item[0]
				data['name']=item[2]
				data['surname']=item[3]
				data['telephone']=item[4]
				data['email']=item[5]
				data['authority']=item[6]

				json_data=json_data + json.dumps(data)
				
			c.close()
			conn.close()
			
			json_data=turkish_character(json_data)

			return ('{"user":['+json_data+"]}")
		else:
			if not request.json or not 'ID' in request.json:
				abort(400)
			else: 
				c.execute("SELECT uid,username,name,surname,telephone,email,authority FROM tb_users WHERE uid=(%s)",str(request.json['ID']))
				rows = c.fetchall()
			
				for row in rows:
					temp["ID"]=row[0]
					temp["username"]=row[1]
					temp["name"]=row[2]
					temp["surname"]=row[3]
					temp["telephone"]=row[4]
					temp["email"]=row[5]
					temp["authority"]=row[6]
					listusers.append(temp)
					temp={}
				c.close()
				conn.close()
				return jsonify({'user': listusers}), 201
			
	except Exception as e:
		return(str(e))
	
@app.route('/rest/activity',methods=['POST'])
@auth.login_required
def rest_activity():
	try:
		deviceid=None
		#c, conn = connection()
		#c.execute("SELECT tb_users.name, tb_device.name, tb_activity.prevstatus, tb_activity.nextstatus FROM tb_users, tb_activity, tb_device WHERE tb_users.uid=tb_activity.changer_id and tb_device.id=tb_activity.device_id")
		jsonData=json.loads(request.data)
		for item in jsonData:
			if str(item) == "count":				
				count = str(jsonData[str(item)])
			if "deviceid" in jsonData:
				deviceid=str(jsonData["deviceid"])

			#deviceid = item.get("deviceid")
		
		return jsonify({'count': count, 'deviceid':deviceid}), 201
	except Exception as e:
		return(str(e))
	
@app.route('/rest/servo120',methods=['GET'])
def rest_servo120():
	try:
		ser = serial.Serial('/dev/ttyAMA0', 9600)
		if ser.isOpen():
			ser.write('120')
		else:
			ser.open()
			ser.write('120')
		return jsonify({'count': '40acıda'}), 201
	except Exception as e:
		return(str(e))	

@app.route('/rest/servo121',methods=['GET'])
def rest_servo121():
	try:
		ser = serial.Serial('/dev/ttyAMA0', 9600)
		if ser.isOpen():
			ser.write('121')
		else:
			ser.open()
			ser.write('121')

		
		return jsonify({'count': '130acıda'}), 201
	except Exception as e:
		return(str(e))		
	
if __name__ == '__main__':
	app.run(debug=True)
