import serial
import MySQLdb
from datetime import datetime
from dbconnect import connection
import serial
import time

baseminute = datetime.now().minute
basehour = datetime.now().hour
tasklist={}
detentlist={}
data={}
i=0


def addminute(hour,minute):
	currentMinute = datetime.now().minute
	currentHour = datetime.now().hour
	hour=currentHour

	minute = currentMinute + minute
	hour = hour + minute/60
	minute=minute % 60
	hour=hour%24
	return hour,minute


def sendserial(_id,_status):
	signal= str(_id) if _id>10 else "0"+str(_id)
	signal=signal + ("1" if _status=="On" else "0")
	signal=signal +"**"
	return signal
	
def adddetent(_taskid,_deviceid,_switch,_hour,_minute):
	data['id']=_taskid
	data['switch']=_switch
	data['device_id']=_switch
	data['hour']=_hour
	data['minute']=_minute
	
	detentlist[int(_taskid)]=data
	data={}
	
def syn_tasks():
	c, conn = connection()
	c.execute("SELECT * FROM tb_tasks WHERE active=1")
	rows = c.fetchall()
	data={}
	for item in rows:
		data['id']=item[0]
		data['device_id']=item[1]
		data['user_id']=item[2]
		data['switch']=item[3]
		data['triggertime']=item[4]
		data['process']=item[5]
		data['period']=item[6]
		data['note']=item[7]
		x=item[4].split(':')
		data['hour']=x[0]
		data['minute']=x[1]
		tasklist[int(item[0])]=data
		data={}
		
	c.close()
	conn.close()

	
def insert_db(_status,_device_id):
	c, conn = connection()
	pre="On" if _status=="Off" else "Off"
	now = datetime.now()
	now =now.strftime('%Y-%m-%d %H:%M:%S')
	c.execute("""INSERT INTO tb_activity(user_id,device_id,prevstatus,currentstatus,date,IP,error,report) VALUES(8,%d,'%s','%s','%s','127.0.0.1',0,'passed')"""%(_device_id,pre,_status,now))			
	c.execute("""UPDATE tb_device SET status='%s' where id = %d"""%(_status,int(_device_id)))
	conn.commit()
	c.close()
	conn.close()
	
def finishtask(_taskid):
	c, conn = connection()
	
	c.execute("""UPDATE tb_tasks SET active=0 where id = %d"""%(_taskid))
	
	conn.commit()
	c.close()
	conn.close()
		
data={}
item={}
syn_tasks()
ser = serial.Serial('/dev/ttyACM0',9600)


	
while True:
	
	if baseminute!=datetime.now().minute:
		syn_tasks()
		currentHour=datetime.now().hour
		for item in tasklist:
			data=tasklist[item]
			if data['hour']==currentHour and data['minute']==currentMinute:
				ser.writelines(sendserial(data['device_id'],data['switch']))
				time.sleep(1)
				insert_db(data['switch'],data['device_id'])
				hour,minute=addminute(data['hour'],data['minute'])
				adddetent(data['id'],data['device_id'],"On" if data['switch']=="Off" else "Off",hour,minute)
		
		for item2 in detentlist:
			data2=detentlist[item2]
			if data2['hour']==currentHour and data2['minute']==currentMinute:
				ser.writelines(sendserial(data2['device_id'],data2['switch']))
				time.sleep(1)
				insert_db(data2['switch'],data2['device_id'])
				finishtask(data2['id'])
				del detentlist[data2['id']]
				
		baseminute=datetime.now().minute
	

