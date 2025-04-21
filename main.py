from itertools import product
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from dbConn import conn
from auth import AuthHandler
from schemas import AuthDetails, Products, PersonContactTypeTable, SalesInfo, datetime


app = FastAPI()
auth_handler = AuthHandler()

# follow this up with "/docs" to make use of the other endpoints
@app.get("/") # this doesn't count as an assessed endpoint as it only prints an introduction for the user.
def root():
    return {"message": "Introducing my coursework"}

### AUTHENTICATION ###

# instance created of the authentication handler
auth_handler = AuthHandler()

# empty list that will store successfully registered users
users = []

# POST endpoint allows users to enter a username and password
@app.post('/register', status_code=201)
def register(auth_details: AuthDetails):
    
    # checks whether username is taken
    if any(x['username'] == auth_details.username for x in users):
        raise HTTPException(status_code=400, detail='Username is taken')
    hashed_password = auth_handler.get_password_hash(auth_details.password)
    
    # adds the username and password to the users list
    users.append({
        'username': auth_details.username,
        'password': hashed_password    
    })
    return

# this username and password is authenticated via this PUT endpoint
@app.put('/token')
def get_token(auth_details: AuthDetails):
    user = None
    for x in users:
        if x['username'] == auth_details.username:
            user = x
            break

    if (user is None) or (not auth_handler.verify_password(auth_details.password, user['password'])):
        raise HTTPException(status_code=401, detail='Invalid username and/or password')
    
    token = auth_handler.encode_token(user['username'])
    return {'token': token}

# DELETE endpoint deletes from the authenticated users list
@app.delete("/deleteusers")
def delete_user(auth_details: AuthDetails, username=Depends(auth_handler.auth_wrapper)):
    user = None
    for u in users:
        if u['username'] == auth_details.username:
            user = u
            break

    if user is None or not auth_handler.verify_password(auth_details.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    users.remove(user)
    return {"message": f"User '{auth_details.username}' has been deleted successfully."}

# PUT endpoint for authentication (UPDATE query?)


# datetime sample: 2025-04-21 16:47:34.123456

### ASSESSED ENDPOINTS ###
# GET endpoints
@app.get("/last24hours", response_model=SalesInfo)
def get_last_24_hours_products():
    cursor = conn.cursor()
    query = """
        SELECT SalesOrderID, OrderDate
        FROM Sales_SalesOrderHeader
        WHERE OrderDate < NOW()
        ORDER BY OrderDate
    """
    cursor.execute(query)
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        raise HTTPException(status_code=404, detail="No products sold in the last 24 hours")

    return {
            "SalesOrderID": row[0],
            "OrderDate": row[1]
        }

# GET endpoint with parameters to retrieve data from Person_ContactType
@app.get("/getpersoncontacttype/{ctypeID}", response_model=PersonContactTypeTable)
def get_person_contact_type(ctypeID: int):

    cursor = conn.cursor()
    query = """
        SELECT ContactTypeID, Name, ModifiedDate
        FROM Person_ContactType
        WHERE ContactTypeID = %s
    """
    cursor.execute(query, (ctypeID,))
    result = cursor.fetchone()
    cursor.close()

    if result:
        return {
            "ContactTypeID": result[0],
            "Name": result[1],
            "ModifiedDate": result[2]
        }
    else:
        raise HTTPException(status_code=404, detail="Record not found")


# POST endpoint inserts data into this specified table 
@app.post("/insertintopersoncontacttypetable/{ctypeID}/{name}/{modDate}", response_model=PersonContactTypeTable)
def insertIntoPersonContactTypeTable(cTypeID: int, name: str, modDate: str):
    cursor = conn.cursor()
    query = """
        INSERT INTO Person_ContactType (ContactTypeID, Name, ModifiedDate)
        VALUES (%s, %s, %s)
    """
    try:
        cursor.execute(query, (cTypeID, name, modDate))
        conn.commit()
    except Exception as e:
        cursor.close()
        raise HTTPException(status_code=400, detail=f"Unable to complete your POST request: {str(e)}")
    cursor.close()
    return {
        "ContactTypeID": cTypeID,
        "Name": name,
        "ModifiedDate": modDate
    }

# PUT endpoint to update data in the chosen table
@app.put("/updatepersoncontacttypetable/{ctypeID}", response_model=PersonContactTypeTable)
def update_contact_type(ctypeID: int, data: PersonContactTypeTable):
    cursor = conn.cursor()

    # Optional existence check
    cursor.execute("SELECT 1 FROM Person_ContactType WHERE ContactTypeID = %s", (ctypeID,))
    if not cursor.fetchone():
        cursor.close()
        raise HTTPException(status_code=404, detail=f"ContactTypeID {ctypeID} does not exist.")

    # Update query
    query = """
        UPDATE Person_ContactType
        SET Name = %s, ModifiedDate = %s
        WHERE ContactTypeID = %s
    """
    try:
        cursor.execute(query, (data.Name, data.ModifiedDate, ctypeID))
        conn.commit()
    except Exception as e:
        cursor.close()
        raise HTTPException(status_code=400, detail=f"PUT failed: {str(e)}")
    
    cursor.close()
    return {"ContactTypeID": ctypeID, "Name": data.Name, "ModifiedDate": data.ModifiedDate}


# DELETE endpoints
# deletes data from the chosen table
@app.delete("/deletefrompersoncontacttypetable/{ctypeID}/{name}/{modDate}", response_model=PersonContactTypeTable)
def deleteFromPersonContactTypeTabel(cTypeID: int, name: str, modDate: str):
    try:
        # Parse and reformat to match MySQL DATETIME format
        formatted_mod_date = datetime.fromisoformat(modDate).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    cursor = conn.cursor()
    query = """
        DELETE FROM Person_ContactType
        WHERE ContactTypeID = %s AND Name = %s AND ModifiedDate = %s
    """
    try:
        cursor.execute(query, (cTypeID, name, formatted_mod_date))
        conn.commit()
    except Exception as e:
        cursor.close()
        raise HTTPException(status_code=400, detail=f"Unable to complete your DELETE request: {str(e)}")
    cursor.close()
    return {"ContactTypeID": cTypeID, "Name": name, "ModifiedDate": modDate}