from typing import List, Optional
from typing import List, Optional
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# User Schemas
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "customer"

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Category Schemas
class CategoryCreate(BaseModel):
    name: str

class CategoryResponse(CategoryCreate):
    id: int

    class Config:
        from_attributes = True

# Booking Schemas
class BookingCreate(BaseModel):
    provider_id: int
    category_id: int

class BookingStatusUpdate(BaseModel):
    status: str

class BookingResponse(BaseModel):
    id: int
    user_id: int
    provider_id: int
    category_id: int
    date: datetime
    status: str

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    booking_id: int
    rating: int
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    booking_id: int
    user_id: int
    provider_id: int
    rating: int
    comment: Optional[str]

    class Config:
        from_attributes = True

class ProviderReviewSummary(BaseModel):
    provider_id: int
    total_reviews: int
    average_rating: float
    reviews: List[ReviewResponse]

    class Config:
        from_attributes = True
