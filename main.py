from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional

import models, schemas, auth
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=" Vikori Gharzy")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def home():
    return {"message": "Welcome to Seva Mitra API!"}

# --- Auth Endpoints ---
@app.post("/signup", response_model=schemas.UserResponse, tags=["Authentication"])
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = auth.get_password_hash(user.password)
    new_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=hashed_pwd,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=schemas.UserResponse, tags=["Authentication"])
def get_current_user_profile(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

# --- Category Endpoints ---
@app.post("/categories/", response_model=schemas.CategoryResponse, tags=["Categories"])
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    db_cat = db.query(models.Category).filter(models.Category.name == category.name).first()
    if db_cat:
        raise HTTPException(status_code=400, detail="Category already exists")
    new_cat = models.Category(name=category.name)
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@app.get("/categories/", response_model=List[schemas.CategoryResponse], tags=["Categories"])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()

# --- Booking Endpoints ---
@app.post("/bookings/", response_model=schemas.BookingResponse, tags=["Bookings"])
def create_booking(
    booking: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    provider = db.query(models.User).filter(models.User.id == booking.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider user not found")

    category = db.query(models.Category).filter(models.Category.id == booking.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    new_booking = models.Booking(
        user_id=current_user.id,
        provider_id=booking.provider_id,
        category_id=booking.category_id,
        status="pending"
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

@app.get("/bookings/", response_model=List[schemas.BookingResponse], tags=["Bookings"])
def get_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role == "provider":
        return db.query(models.Booking).filter(models.Booking.provider_id == current_user.id).all()
    return db.query(models.Booking).filter(models.Booking.user_id == current_user.id).all()

@app.patch("/bookings/{booking_id}/status", response_model=schemas.BookingResponse, tags=["Bookings"])
def update_booking_status(
    booking_id: int,
    status_update: schemas.BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role != "provider" or booking.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this booking status")

    booking.status = status_update.status
    db.commit()
    db.refresh(booking)
    return booking

@app.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Bookings"])
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Sirf wahi customer ya assigned provider is booking ko cancel/delete kar sakta hai
    if booking.user_id != current_user.id and booking.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")

    db.delete(booking)
    db.commit()
    return None

# --- Provider Search / Filter Endpoint ---
@app.get("/providers/", response_model=List[schemas.UserResponse], tags=["Providers"])
def get_providers(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.User).filter(models.User.role == "provider")
    return query.all()

# --- Provider Search / Filter Endpoint ---
@app.get("/providers/", response_model=List[schemas.UserResponse], tags=["Providers"])
def get_providers(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.User).filter(models.User.role == "provider")
    return query.all()

# --- Reviews Endpoint ---
@app.post("/reviews/", response_model=schemas.ReviewResponse, tags=["Reviews"])
def create_review(
    review_data: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can leave reviews")

    booking = db.query(models.Booking).filter(models.Booking.id == review_data.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only review your own bookings")

    if review_data.rating < 1 or review_data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    new_review = models.Review(
        booking_id=booking.id,
        user_id=current_user.id,
        provider_id=booking.provider_id,
        rating=review_data.rating,
        comment=review_data.comment
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

# --- My Bookings Endpoint ---
@app.get("/bookings/me", response_model=List[schemas.BookingResponse], tags=["Bookings"])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role == "provider":
        bookings = db.query(models.Booking).filter(models.Booking.provider_id == current_user.id).all()
    else:
        bookings = db.query(models.Booking).filter(models.Booking.user_id == current_user.id).all()
    return bookings

# --- Provider Reviews & Rating Endpoint ---
@app.get("/reviews/provider/{provider_id}", response_model=schemas.ProviderReviewSummary, tags=["Reviews"])
def get_provider_reviews(provider_id: int, db: Session = Depends(get_db)):
    provider = db.query(models.User).filter(models.User.id == provider_id, models.User.role == "provider").first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    reviews = db.query(models.Review).filter(models.Review.provider_id == provider_id).all()
    total_reviews = len(reviews)
    avg_rating = round(sum(r.rating for r in reviews) / total_reviews, 2) if total_reviews > 0 else 0.0

    return {
        "provider_id": provider_id,
        "total_reviews": total_reviews,
        "average_rating": avg_rating,
        "reviews": reviews
    }
