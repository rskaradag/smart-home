import MySQLdb

def connection():
	conn = MySQLdb.connect(host="localhost",
							user="root",
							passwd="gzkq7ead4", 
							db="smarthome")
	c =conn.cursor()
	
	return c,conn
	
