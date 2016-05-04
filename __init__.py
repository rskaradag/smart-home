# -*- coding: utf-8 -*-
from flask import Flask,render_template, jsonify, abort, request, make_response, url_for,flash, redirect,session
from flask.ext.httpauth import HTTPBasicAuth
#from celery import Celery
import pylcdlib #i2c lib
import json
from content_management import *
from wtforms import Form, BooleanField, TextField, PasswordField, validators,IntegerField,RadioField,StringField
from wtforms.widgets import TextArea
from passlib.hash import sha256_crypt
from MySQLdb import escape_string as thwart
from functools import wraps
from pwhash import *
import collections
import base64
import serial
import time
from datetime import datetime

from dbconnect import connection
import gc 

app = Flask(__name__)

TOPIC_DICT = Content()

#app.config.from_pyfile('config.py')
#app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
#app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

auth = HTTPBasicAuth()

#celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
#celery.conf.update(app.config)

#lcd = pylcdlib.lcd(0x3F,1)

class RegistrationForm(Form):
	username=TextField('Username',[validators.Length(min=4, max=20)])
	name=TextField('Name',[validators.Length(min=4, max=20)])
	surname=TextField('Surname',[validators.Length(min=4, max=20)])
	email = TextField('Email Address',[validators.Length(min=6, max=50)])
	telephone = TextField('Telephone ',[validators.Length(min=10, max=11)])
	doorkey = TextField('Door Key ',[validators.Length(min=4, max=4)])
	password = PasswordField('Password',[validators.Required(),
										validators.EqualTo('confirm',message="Passwords must match")])
	confirm = PasswordField('Repeat Password')
	
class SetTextForm(Form):
	txt_time=TextField('',[validators.Length(min=5, max=5)])
	txt_process=IntegerField('',[validators.NumberRange(min=0, max=480)])
	radio_switch = RadioField('Switch', choices=[('On','On'),('Off','Off')])
	radio_interval = RadioField('Interval', choices=[('Weekdays','WeekDay'),('Weekends','Weekends'),('Always','Always')])
	note = StringField(u'note', widget=TextArea())

def sendserial(_id,_status):
	signal= str(_id) if _id>10 else "0"+str(_id)
	signal=signal + ("1" if _status=="On" else "0")
	signal=signal +"**"
	return signal	
	
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

@app.route('/tasks/',methods=['GET','POST'])
@login_required
def tasks():
	try:	
		data={}
		DEVICE_LIST=[]
		form = SetTextForm(request.form)
		c, conn = connection()
		c.execute("SELECT id,location,name FROM tb_device")
		i=0
		rows = c.fetchall()
	
		for row in rows:			
			data["id"]=row[0]
			data["location"]=row[1]
			data["name"]=row[2]			
			DEVICE_LIST.insert(i,data)
			data={}
			i=i+1			
		
		if request.method == "POST" and form.validate():
			_time =form.txt_time.data
			_process =form.txt_process.data
			_switch=form.radio_switch.data
			_note=form.note.data
			_interval=form.radio_interval.data
			_device_id=(request.form['device'])
			trigger=_time.split(':')
			try:			
				if int(trigger[0])>23 or int(trigger[1])>60:
					flash("Invalid data")
					c.close()
					conn.close()	
					return render_template("tasks.html",DEVICE_LIST=DEVICE_LIST,TASK_LIST=TASK_LIST,form=form)
				else:
					c.execute("""SELECT uid FROM tb_users WHERE username =(%s)""",session['username'])	
					_user_id=c.fetchone()[0]	
					now = datetime.now()
					now =now.strftime('%Y-%m-%d %H:%M:%S')	
					c.execute("""INSERT INTO tb_tasks(device_id,user_id,switch,triggertime,process,period,note,active,datetime) VALUES(%d,%d,'%s','%s',%d,'%s','%s',1,'%s')"""%(int(_device_id),int(_user_id),str(_switch),str(_time),int(_process),str(_interval),str(_note),str(now)))
					conn.commit()					
			except Exception as e:
				c.close()
				conn.close()
				flash("Invalid data")
				return render_template("tasks.html",DEVICE_LIST=DEVICE_LIST,form=form)
		
		data={}
		TASKS_LIST=[]
		c.execute("SELECT tb_tasks.id,tb_users.username, tb_device.name, tb_device.location,tb_tasks.switch,tb_tasks.triggertime, tb_tasks.process,tb_tasks.period, tb_tasks.note, tb_tasks.active, tb_tasks.datetime FROM tb_tasks,tb_device,tb_users WHERE tb_users.uid = tb_tasks.user_id AND tb_device.id = tb_tasks.device_id")	
		i=0
		rows = c.fetchall()	
		
		for row in rows:			
			data["id"]=row[0]
			data["username"]=row[1]
			data["device"]=row[3]+" "+row[2]
			data["switch"]=row[4]
			data["triggertime"]=row[5]
			data["process"]=row[6]
			data["period"]=row[7]
			data["note"]=row[8]	
			data["active"]=row[9]	
			data["datetime"]=row[10]			
			TASKS_LIST.insert(i,data)
			data={}
			i=i+1			
		c.close()
		conn.close()					
		
		return render_template("tasks.html",DEVICE_LIST=DEVICE_LIST,TASKS_LIST=TASKS_LIST,form=form) 
				
	except Exception as e:
		return(str(e))
			
	
@app.route('/register/',methods=['GET','POST'])
@login_required
def register_page():
	try:		
		form = RegistrationForm(request.form)
		
		if request.method == "POST" and form.validate():
			username =form.username.data
			email = form.email.data
			name = form.name.data
			surname = form.surname.data
			telephone = form.telephone.data
			doorkey = form.doorkey.data
			password = sha256_crypt.encrypt((str(form.password.data)))
			
			c,conn = connection()
			
			x = c.execute("SELECT * FROM tb_users WHERE username =(%s)",
							(thwart(username)))
			if int(x) > 0:
				flash("That email is already taken, please choose another")
				return render_template('register.html',form=form)
			else:
				c.execute("INSERT INTO tb_users (username,name,surname,telephone,doorkey,password,email) VALUES (%s,%s,%s,%s,%s,%s,%s)",
							(thwart(username),thwart(name),thwart(surname),thwart(telephone),thwart(doorkey),thwart(password),thwart(email)))
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
	try:	
		if session['logged_in']== True:		
			return redirect(url_for("userlist"))
		else:
			return render_template("login.html")
	except:
		return render_template("login.html")

@app.route('/userlist/')
@login_required
def userlist():
	error=''
	i=0
	try:
		data={}
		USER_LIST=[]
			
		c, conn = connection()	
		c.execute("SELECT uid,username,name,surname,email,telephone,authority,active FROM tb_users ")
		rows = c.fetchall()
		
		for row in rows:			
			data["ID"]=row[0]
			data["username"]=row[1]
			data["name"]=row[2]
			data["surname"]=row[3]
			data["email"]=row[4]
			data["telephone"]=row[5]
			data["authority"]=row[6]
			data["active"]=row[7]
							
			USER_LIST.insert(i,data)
			data={}
			i=i+1
			
		c.close()
		conn.close()
		return render_template("list.html",USER_LIST=USER_LIST) 	

	except Exception as e:
		flash(e)
		
@app.route('/devices/')
@login_required
def devices():
	try:
		i=0
		data={}
		DEVICE_LIST=[]
		c, conn = connection()
		c.execute("SELECT * FROM tb_device ")
		rows = c.fetchall()
		for row in rows:			
			data["ID"]=row[0]
			data["name"]=row[1]
			data["location"]=row[2]
			data["status"]=row[3]
			data["active"]=row[4]
							
			DEVICE_LIST.insert(i,data)
			data={}
			i=i+1
			
		c.close()
		conn.close()
		
		return render_template("device.html",DEVICE_LIST=DEVICE_LIST) 
		
	except Exception as e:
		return str(e)


@app.route('/activity/')
@login_required
def activity():
	error=''
	i=0
	try:
		data={}
		values=[]
		ACTIVITY_LIST=[]
			
		c, conn = connection()	
		c.execute("SELECT tb_users.username, tb_device.name, tb_activity.prevstatus, tb_activity.currentstatus,tb_activity.IP,tb_activity.DATE,tb_activity.error,tb_activity.report FROM tb_users, tb_activity, tb_device WHERE tb_users.uid=tb_activity.user_id and tb_device.id=tb_activity.device_id ")
		rows = c.fetchall()
		
		for row in rows:			
			data["Username"]=row[0]
			data["Device"]=row[1]
			data["Prevstatus"]=row[2]
			data["Currentstatus"]=row[3]
			data["IP"]=row[4]
			data["DATE-TIME"]=row[5]
			data["Error"]=row[6]
			data["Report"]=row[7]
							
			ACTIVITY_LIST.insert(i,data)
			data={}
			i=i+1
			
		c.close()
		conn.close()
		return render_template("activity.html",ACTIVITY_LIST=ACTIVITY_LIST) 	

	except Exception as e:
		flash(e)

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

		return ('{"user":['+json_data+"]}")

	except Exception as e:
		return(str(e))
	
@app.route('/rest/activity',methods=['POST'])
@auth.login_required
def rest_activity():
	try:
		deviceid=None
		c, conn = connection()
		#c.execute("SELECT tb_users.name, tb_device.name, tb_activity.prevstatus, tb_activity.nextstatus FROM tb_users, tb_activity, tb_device WHERE tb_users.uid=tb_activity.changer_id and tb_device.id=tb_activity.device_id")		
		jsonData=json.loads(request.data)
		for item in jsonData:
			if str(item) == "count":				
				count = str(jsonData[str(item)])
			if "deviceid" in jsonData:
				deviceid=str(jsonData["deviceid"])
				
		#c,conn = connection()
			
		#x = c.execute("SELECT * FROM tb_device WHERE id =(%d)",deviceid)		
		#if int(x)<1:
		#	abort(400)
		#else:
		ip=request.remote_addr
			#c.execute("INSERT INTO tb_activity(user_id,device_id,prevstatus,currentstatus,date,IP,error) VALUES(%d,%d,)");
			
		return jsonify({'count': count, 'deviceid':deviceid,'ip':ip}), 201
	except Exception as e:
		return(str(e))	

@app.route('/rest/switch',methods=['POST'])
@auth.login_required
def rest_switch():
	try:
		#c.execute("SELECT tb_users.name, tb_device.name, tb_activity.prevstatus, tb_activity.nextstatus FROM tb_users, tb_activity, tb_device WHERE tb_users.uid=tb_activity.changer_id and tb_device.id=tb_activity.device_id")		
		jsonData=json.loads(request.data)
		try:
			for item in jsonData:
				if str(item) == "status":				
					status = str(jsonData[str(item)])
				if "deviceid" in jsonData:
					device_id=str(jsonData["deviceid"])		
		except:
			return abort(400)
		
		c, conn = connection()		
		device_id=int(device_id)
		x = c.execute("""SELECT id,status FROM tb_device WHERE id =%d"""%(device_id))	
		if (int(x)<1) or (status!="On" and status!="Off"):
			abort(400)
		else:
			
			db_status=c.fetchone()[1]
			if db_status == status:
				abort(400)
			else:
				c.execute("""SELECT uid FROM tb_users WHERE username =(%s)""",auth.username())	
				user_id=c.fetchone()[0]	
				try:
					now = datetime.now()
					now =now.strftime('%Y-%m-%d %H:%M:%S')						
					ip=request.remote_addr
					err=0
										
					ser = serial.Serial('/dev/ttyACM0',9600)
					ser.writelines(sendserial(device_id,status))
									
									
					report="Passed"		
					c.execute("""INSERT INTO tb_activity(user_id,device_id,prevstatus,currentstatus,date,IP,error,report) VALUES(%d,%d,'%s','%s','%s','%s',%d,'%s')"""%(user_id,device_id,db_status,status,now,ip,err,report))			
					c.execute("""UPDATE tb_device SET status='%s' where id = %d"""%(status,int(device_id)))
					
					conn.commit()
					ser.flush()
					return jsonify({'user_id': user_id, 'deviceid':device_id,'ip':ip,'date':now,'status':status,'username':auth.username()}), 201
				except Exception as e:
					report=str(e)
					report=report.replace("'","")
					c.execute("""INSERT INTO tb_activity(user_id,device_id,prevstatus,currentstatus,date,IP,error,report) VALUES(%d,%d,'%s','%s','%s','%s',%d,'%s')"""%(user_id,device_id,db_status,db_status,now,ip,1,report))			
					conn.commit()
					abort(501)
	except Exception as e:
		return(str(e))

@app.route('/rest/status',methods=['GET','POST'])
@auth.login_required
def rest_status():
	try:
	#curl -u slck:slck123 -i -H "Content-Type:application/json" -X POST -d '{"ID":"5"}' 192.168.1.33/rest/status
		response={}
		data={}
		i=0
		json_data=""
		c, conn = connection()
		if request.method=="GET":				
			c.execute("SELECT * FROM tb_device ")
			rows = c.fetchall()
			
			for item in rows:
				data['ID']=item[0]
				data['name']=item[1]
				data['location']=item[2]
				data['status']=item[3]
				data['active']=item[4]

				response[int(item[0])]=data
				data={}
			c.close()
			conn.close()

			return jsonify({'device':response}), 201
		else:
			if not request.json or not 'deviceid' in request.json:
				abort(400)
			else: 
				deviceid=request.json["deviceid"]
				c.execute("SELECT * FROM tb_device WHERE id=(%d)"%int(deviceid))
				rows = c.fetchall()
			
				for item in rows:
					data['ID']=item[0]
					data['name']=item[1]
					data['location']=item[2]
					data['status']=item[3]
					data['active']=item[4]
					
				c.close()
				conn.close()
				return jsonify({'device':data}), 201
			
	except Exception as e:
		return(str(e))
		
@app.route('/rest/test',methods=['GET'])
@auth.login_required
def rest_test():
	try:
		
		ser = serial.Serial('/dev/ttyACM0',9600)

		ser.writelines('*****')
		time.sleep(1)
		x=ser.readline()
		ser.flush()
		
		return jsonify({'temperature':str(x)}), 201
	except Exception as e:
		return(str(e))	
	
@app.route('/rest/lcd',methods=['POST'])
@auth.login_required
def rest_lcd():
	try:
		jsonData=json.loads(request.data)
		
		line1=str(jsonData["first line"])
		line2=str(jsonData["second line"])
		time.sleep(1)
		lcd.lcd_puts(line1,1)
		time.sleep(1)
		lcd.lcd_puts(line2,2)

		
		return jsonify({'temperature':'sad'}), 200
	except Exception as e:
		return(str(e))	
		
@app.route('/rest/demo',methods=['GET'])
@auth.login_required
def rest_demo():
	try:
		return jsonify({'temperature':'26/30'}), 201
	except Exception as e:
		return(str(e))	
		

@app.route('/deltask/<int:task_id>',methods=['GET'])
@auth.login_required
def deltask(task_id):
	c,conn=connection()
	c.execute("DELETE FROM tb_tasks WHERE id=%d"%(task_id))
	conn.commit()
	c.close()
	conn.close()
	return redirect(url_for('tasks'))


@app.route('/rest/tasks',methods=['POST'])
@auth.login_required
def rest_tasks():
	return("test")


if __name__ == "__main__":
    app.run(debug=True)
