import MySQLdb

# database configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'passwd': 'computing',
    'db': 'AdventureWorks2019',
    'port': 3307
}
  
# creates a connection to the database
conn = MySQLdb.connect(**db_config) 
