import MySQLdb

# Database configuration
db_config = {
    'host': '127.0.0.1',  # or use 'localhost' if you're confident it's connecting locally
    'user': 'root',
    'passwd': 'computing',
    'db': 'AdventureWorks2019',
    'port': 3307  # <-- important fix
}

  
# Create a connection to the database
conn = MySQLdb.connect(**db_config) 
