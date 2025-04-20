import MySQLdb

def get_connection():
    return MySQLdb.connect(
        host="localhost",
        user="root",
        passwd="computing", # root?
        db="Cloud&WebServicesAssessment1"
    )
