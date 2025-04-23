from pydantic import BaseModel
from datetime import datetime

# Pydantic model to define the schemas of the data for GET, PUT, POST and DELETE endpoints.
class AuthDetails(BaseModel):
    username: str
    password: str

class Products(BaseModel):
    ProductID: int 
    Name: str 

class PersonContactTypeTable(BaseModel):
    ContactTypeID: int
    Name: str
    ModifiedDate: datetime

class SalesInfo(BaseModel):
    SalesOrderID: int
    OrderDate: datetime