from itertools import product
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from dbConn import conn
from auth import AuthHandler
from schemas import AuthDetails, Products, PersonContactTypeTable, SalesInfo, datetime

# DATETIME SAMPLE: 2025-04-21 16:47:34.123456

# instantiates FastAPI
app = FastAPI()

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

# this username and password is authenticated via this POST endpoint
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

# DELETE endpoint deletes from the authenticated users list
@app.delete("/deleteusers", tags=["Protected"])
def delete_user(auth_details: AuthDetails, username=Depends(auth_handler.auth_wrapper)):
    user = None
    
    # checks if username is part of the list and password is correct    
    for u in users:
        if u['username'] == auth_details.username:
            user = u
            break

    if user is None or not auth_handler.verify_password(auth_details.password, user['password']):
        raise HTTPException(status_code=404, detail="Username or password record does not exist")

    # calls the remove() function to delete the user from the list
    users.remove(user)
    return {"message": f"User '{auth_details.username}' has been deleted successfully."}



### ENDPOINTS ###
# GET endpoint retrieves products sold in the last 24 hours (no input params)
@app.get("/last24hours", response_model=SalesInfo)
def get_last_24_hours_products():
    
    # creates a connection for querying using a cursor
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
        raise HTTPException(status_code=404, detail="No records of products sold in the last 24 hours")

    # query output
    return {
            "SalesOrderID": row[0],
            "OrderDate": row[1]
        }

# GET endpoint with parameters to retrieve data from Person_ContactType (1 input param)
@app.get("/getpersoncontacttype/{ctypeID}", response_model=PersonContactTypeTable)
def get_person_contact_type(ctypeID: int):

    # check that the record exists
    cursor.execute("SELECT 1 FROM Person_ContactType WHERE ContactTypeID = %s", (ctypeID,))
    if not cursor.fetchone():
        cursor.close()
        raise HTTPException(status_code=404, detail=f"ContactTypeID {ctypeID} does not exist.")

    # creates a connection for querying using a cursor
    cursor = conn.cursor()
    query = """
        SELECT ContactTypeID, Name, ModifiedDate
        FROM Person_ContactType
        WHERE ContactTypeID = %s
    """
    cursor.execute(query, (ctypeID,))
    result = cursor.fetchone()
    cursor.close()

    # query output
    if result:
        return {
            "ContactTypeID": result[0],
            "Name": result[1],
            "ModifiedDate": result[2]
        }
    else:
        raise HTTPException(status_code=404, detail="Record not found")

# POST endpoint inserts data into this specified table  (3 input params)
@app.post("/insertintopersoncontacttypetable/{ctypeID}/{name}/{modDate}", response_model=PersonContactTypeTable)
def insert_into_PersonContactType_table(cTypeID: int, name: str, modDate: str):
    
    # ensures the datetime is in the correct format
    try:
        formattedModDate = datetime.fromisoformat(modDate).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    # creates a connection for querying using a cursor
    cursor = conn.cursor()
    
    # check that the record exists
    cursor.execute(
        "SELECT 1 FROM Person_ContactType WHERE ContactTypeID = %s AND Name = %s AND ModifiedDate = %s",
        (cTypeID, name, formattedModDate)
    )
    if not cursor.fetchone():
        cursor.close()
        raise HTTPException(status_code=404, detail=f"Record not found with the given details.")
    
    query = """
        INSERT INTO Person_ContactType (ContactTypeID, Name, ModifiedDate)
        VALUES (%s, %s, %s)
    """
    try:
        cursor.execute(query, (cTypeID, name, formattedModDate))
        conn.commit()
    except Exception as e:
        cursor.close()
        raise HTTPException(status_code=400, detail=f"Unable to complete your POST request: {str(e)}")
    cursor.close()
    
    # query output
    return {
        "ContactTypeID": cTypeID,
        "Name": name,
        "ModifiedDate": formattedModDate
    }

# POST endpoint inserts data into this specified table (4 input params)
@app.post("/products/new/review/{productId}/{reviewerName}/{emailAddress}/{rating}", tags=["Protected"])
def add_new_product_review(productId: int, reviewerName: str, emailAddress: str, rating: int, comment: str, username: str = Depends(auth_handler.auth_wrapper)):
    
    cursor = conn.cursor()
    
    # Error handling and data consistency, ensures that the ProductID/product to be reviewed already exist in the database.
    query = ("SELECT ProductID FROM AdventureWorks2019.Production_Product WHERE ProductID=%s;")
    cursor.execute (query, (productId,))
    item = cursor.fetchone()
    if item is None:
        raise HTTPException(status_code=404, detail=f"Product ID {productId} record does not exist")
    
    # Data consistency ensures that the rating can only be between 1 and 5.
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Product is only rated between 1 and 5")
    
    # Retrieves the new unique primary key identifier for the INSERT INTO query.
    query = ("SELECT IFNULL((SELECT (MAX(ProductReviewID) +1) FROM AdventureWorks2019.Production_ProductReview), '1');")
    cursor.execute (query)
    productReviewId = cursor.fetchone()
    
    # Query, execute and commit below will POST the data to the database.
    query = ("INSERT INTO AdventureWorks2019.Production_ProductReview VALUES (%s , %s, %s, (NOW()), %s, %s, %s, (NOW())); ")
    cursor.execute (query, (productReviewId, productId, reviewerName, emailAddress, rating, comment))
    conn.commit()
    cursor.close()
    
    # HTTPException is used to confirm that the POST has succeeded.
    return {
        "message": "New product review has been added successfully",
        "reviewed_by": username,
        "product_id": productId
    }

# PUT endpoint to update data in the chosen table (with params)
@app.put("/updatepersoncontacttypetable/{ctypeID}", response_model=PersonContactTypeTable, tags=["Protected"])
def update_contact_type(ctypeID: int, data: PersonContactTypeTable, username=Depends(auth_handler.auth_wrapper)):
    
    # creates a connection for querying using a cursor
    cursor = conn.cursor()

    # check that record exists
    cursor.execute("SELECT 1 FROM Person_ContactType WHERE ContactTypeID = %s", (ctypeID,))
    if not cursor.fetchone():
        cursor.close()
        raise HTTPException(status_code=404, detail=f"ContactTypeID {ctypeID} does not exist.")

    query = """
        UPDATE Person_ContactType
        SET Name = %s, ModifiedDate = %s
        WHERE ContactTypeID = %s
    """
    
    # exception handling for endpoint failures
    try:
        cursor.execute(query, (data.Name, data.ModifiedDate, ctypeID))
        conn.commit()
    except Exception as e:
        cursor.close()
        raise HTTPException(status_code=400, detail=f"PUT failed: {str(e)}")
    
    # query output
    cursor.close()
    return {"ContactTypeID": ctypeID, "Name": data.Name, "ModifiedDate": data.ModifiedDate}

# PUT endpoint allows list price information stored in the Production_Product table to be changed/updated
@app.put("/products/change/listprice/{productId}/{listPrice}")
def update_list_price(productId: int, listPrice: float):
    
    cursor = conn.cursor()
    
    # Error handling ensures that the ProductID/product exists before changes are made.
    query = ("SELECT ProductID FROM AdventureWorks2019.Production_Product WHERE ProductID=%s;")
    cursor.execute (query, (productId,))
    item = cursor.fetchone()
    if item is None:
        raise HTTPException(status_code=404, detail=f"ProductID {productId} record not found")
    
    # Query, execute and commit will PUT the new data to the database.
    query = ("UPDATE AdventureWorks2019.Production_Product SET ListPrice=%s, ModifiedDate=Now() WHERE ProductID=%s;")
    cursor.execute (query, (listPrice, productId))
    conn.commit()
    cursor.close()
    
    # HTTPException is used to confirm that the PUT has completed.
    raise HTTPException(status_code=200, detail="Price has been updated")

# DELETE endpoint deletes data from the chosen table
@app.delete("/deletefrompersoncontacttypetable/{ctypeID}/{name}/{modDate}", response_model=PersonContactTypeTable)
def delete_from_PersonContactType_table(cTypeID: int, name: str, modDate: str):

    # ensures the datetime is in the correct format
    try:
        formattedModDate = datetime.fromisoformat(modDate).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    # creates a connection for querying using a cursor
    cursor = conn.cursor()
    
    # check that the record exists
    cursor.execute(
        "SELECT 1 FROM Person_ContactType WHERE ContactTypeID = %s AND Name = %s AND ModifiedDate = %s",
        (cTypeID, name, formattedModDate)
    )
    if not cursor.fetchone():
        cursor.close()
        raise HTTPException(status_code=404, detail=f"Record not found with the given details.")
    
    query = """
        DELETE FROM Person_ContactType
        WHERE ContactTypeID = %s AND Name = %s AND ModifiedDate = %s
    """
    
    # exception handling
    try:
        cursor.execute(query, (cTypeID, name, formattedModDate))
        conn.commit()
    except Exception as e:
        cursor.close()
        raise HTTPException(status_code=400, detail=f"Unable to complete your DELETE request: {str(e)}")
    cursor.close()
    
    # query output
    return {"ContactTypeID": cTypeID, "Name": name, "ModifiedDate": formattedModDate}