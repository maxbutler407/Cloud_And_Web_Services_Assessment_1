from itertools import product
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from dbConn import conn, get_connection
from auth import AuthHandler
from schemas import AuthDetails

conn = get_connection()
app = FastAPI()
auth_handler = AuthHandler()
    
# Pydantic model to define the schema of the data for PUT POST DELETE
class Products(BaseModel):
    ProductID: int 
    Name: str 

class AuthDetails(BaseModel):
    username: str
    password: str

class PersonContactTypeTable(BaseModel):
    ContactTypeID: int
    Name: str
    ModifiedDate: str  # ISO 8601 formatted date string
    
class NewProductDesc(BaseModel):
    ProductDescriptionID: int
    Description: str
    rowguid: str
    ModifiedDate: str  # ISO 8601 formatted date string

class AuthDetails(BaseModel):
    username: str
    password: str

class SalesInfo(BaseModel):
    SalesOrderID: int
    OrderDate: datetime



@app.get("/")
def root():
    return {"message": "Introducing my coursework"}

### AUTHENTICATION ###
auth_handler = AuthHandler()
users = []

@app.post('/register', status_code=201)
def register(auth_details: AuthDetails):
    if any(x['username'] == auth_details.username for x in users):
        raise HTTPException(status_code=400, detail='Username is taken')
    hashed_password = auth_handler.get_password_hash(auth_details.password)
    users.append({
        'username': auth_details.username,
        'password': hashed_password    
    })
    return


@app.post('/login')
def login(auth_details: AuthDetails):
    user = None
    for x in users:
        if x['username'] == auth_details.username:
            user = x
            break
    
    if (user is None) or (not auth_handler.verify_password(auth_details.password, user['password'])):
        raise HTTPException(status_code=401, detail='Invalid username and/or password')
    token = auth_handler.encode_token(user['username'])
    return { 'token': token }


### ASSESSED ENDPOINTS ###
# GET endpoints
@app.get("/last24hours", response_model=SalesInfo)
def get_last_24_hours_products():
    cursor = conn.cursor()
    query = """
        SELECT SalesOrderID, OrderDate
        FROM Sales_SalesOrderHeader
        WHERE OrderDate >= NOW() - INTERVAL 1 DAY
        LIMIT 1
    """
    cursor.execute(query)
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        raise HTTPException(status_code=404, detail="No products sold in the last 24 hours")

    return {"SalesOrderID": row[0], "OrderDate": row[1]}

# GET endpoint with parameters to retrieve data from Person_ContactType
@app.get("/getpersoncontacttype/{ctypeID}/{name}/{modDate}", response_model=PersonContactTypeTable)
def get_person_contact_type(ctypeID: int, name: str, modDate: str):
    try:
        formatted_mod_date = datetime.fromisoformat(modDate).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    cursor = conn.cursor()
    query = """
        SELECT ContactTypeID, Name, ModifiedDate
        FROM Person_ContactType
        WHERE ContactTypeID = %s AND Name = %s AND ModifiedDate = %s
    """
    cursor.execute(query, (ctypeID, name, formatted_mod_date))
    result = cursor.fetchone()
    cursor.close()

    if result:
        return {
            "ContactTypeID": result[0],
            "Name": result[1],
            "ModifiedDate": result[2].isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail="Record not found")


# POST endpoint inserts data into this specified table 
@app.post("/insertnewproductdesc/{descID}/{desc}/{rowguid}/{modDate}", response_model=NewProductDesc)
def addNewProductDesc(descID: int, desc: str, rowguid: str, modDate: str):
    cursor = conn.cursor()
    query = """
        INSERT INTO Production_ProductDescription (ProductDescriptionID, Description, rowguid, ModifiedDate)
        VALUES (%s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (descID, desc, rowguid, modDate))
        conn.commit()
    except Exception as e:
        cursor.close()
        raise HTTPException(status_code=400, detail=f"Unable to complete your POST request: {str(e)}")
    cursor.close()
    return {
        "ProductDescriptionID": descID,
        "Description": desc,
        "rowguid": rowguid,
        "ModifiedDate": modDate
    }

# PUT endpoint to update data in the chosen table
@app.put("/updatepersoncontacttypetable/{ctypeID}/{name}/{modDate}", response_model=PersonContactTypeTable)
def updatePersonContactTypeTabel(cTypeID: int, name: str, modDate: str):
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
        raise HTTPException(status_code=400, detail=f"Unable to complete your PUT request: {str(e)}")
    cursor.close()
    return {"ContactTypeID": cTypeID, "Name": name, "ModifiedDate": modDate}


# DELETE endpoints
# deletes from the authenticated users list
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