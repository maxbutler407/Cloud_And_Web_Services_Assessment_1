from pydantic import BaseModel
from datetime import datetime

# Pydantic model to define the schemas of the data for PUT POST DELETE
class AuthDetails(BaseModel):
    username: str
    password: str

class Products(BaseModel):
    ProductID: int 
    Name: str 

class PersonContactTypeTable(BaseModel):
    ContactTypeID: int
    Name: str
    ModifiedDate: datetime  # ISO 8601 formatted date string

class SalesInfo(BaseModel):
    SalesOrderID: int
    OrderDate: datetime