from flask import Flask,render_template, jsonify, abort, request, make_response, url_for,flash, redirect,session
from flask.ext.httpauth import HTTPBasicAuth

from content_management import *
from wtforms import Form, BooleanField, TextField, PasswordField, validators
from passlib.hash import sha256_crypt
from MySQLdb import escape_string as thwart
from functools import wraps
from pwhash import *

from dbconnect import connection
import gc

TOPIC_DICT = Content()

app = Flask(__name__)
#app.config.from_pyfile('config.py')
auth = HTTPBasicAuth()
#db=SQLAlchemy(app)


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


class RegistrationForm(Form):
	username=TextField('Username',[validators.Length(min=4, max=20)])
	email = TextField('Email Address',[validators.Length(min=6, max=50)])
	password = PasswordField('Password',[validators.Required(),
										validators.EqualTo('confirm',message="Passwords must match")])
	confirm = PasswordField('Repeat Password')
	accept_tos=BooleanField('I accept the <a href="/tos/">Terms of Service</a> and the <a href="/privacy/">Privacy Notice</a> (Last updated Jan 15 2016',[validators.Required()])
	
	
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
				flash("That username is already taken, please choose another")
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
	return rest_login_user(username,password)

	
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
                return redirect(url_for("dashboard"))

            else:
                error = "Invalid credentials, try again 1."

        gc.collect()

        return render_template("login.html", error=error)

    except Exception as e:
        flash(e)
        error = "Invalid credentials, try again."
        return render_template("login.html", error = error)  
		
		
@app.route('/dashboard/')
def dashboard():
  return render_template("dashboard.html", TOPIC_DICT = TOPIC_DICT)

@app.route('/slashboard/')
def slashboard():
  try:
    return render_template("slahsboard.html", TOPIC_DICT = TOPIC_DICT) 
  except Exception as e:
    return render_template("500.html",error=e)
  
@app.route('/home',methods=['GET','POST'])
def index():
	return "Hello "

@app.route('/tirrekanil',methods=['GET','POST'])
def tirrekanil():
	return jsonify({'tasks': tasks})
	
@app.route('/tirrekanil/add', methods=['POST'])
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


if __name__ == '__main__':
	app.run(debug=True)
