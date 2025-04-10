from pydantic import BaseModel, constr, condecimal, conint, EmailStr, validator
from typing import Optional

class Book(BaseModel):
    ISBN: constr(min_length=10, max_length=20)
    title: str
    Author: str
    description: str
    genre: str
    price: condecimal(gt=0, decimal_places=2)
    quantity: conint(ge=0)

    class Config:
        schema_extra = {
            "example": {
                "ISBN": "978-0321815736",
                "title": "Software Architecture in Practice",
                "Author": "Bass, L.",
                "description": "seminal book on software architecture",
                "genre": "non-fiction",
                "price": 59.95,
                "quantity": 106
            }
        }

class CustomerBase(BaseModel):
    userId: EmailStr
    name: str
    phone: str
    address: str
    address2: Optional[str] = None
    city: str
    state: constr(min_length=2, max_length=2)
    zipcode: str

    @validator('state')
    def validate_state(cls, v):
        valid_states = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        }
        if v.upper() not in valid_states:
            raise ValueError('Invalid US state code')
        return v.upper()

    class Config:
        schema_extra = {
            "example": {
                "userId": "starlord2002@gmail.com",
                "name": "Star Lord",
                "phone": "+14122144122",
                "address": "48 Galaxy Rd",
                "address2": "suite 4",
                "city": "Fargo",
                "state": "ND",
                "zipcode": "58102"
            }
        }

class CustomerResponse(CustomerBase):
    id: int  # Auto-generated unique customer ID

# Model for mobile client responses without address fields
class MobileCustomerResponse(BaseModel):
    id: int  
    userId: EmailStr
    name: str
    phone: str 
    
class RelatedBook(BaseModel):
    title: str
    authors: str
    isbn: str