import os
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, create_engine, select
import bcrypt
from jose import JWTError, jwt
from dotenv import load_dotenv

from config import require_env, get_database_url
from models import Movie, MovieUpdate

load_dotenv()

# --- Config & Security ---
SECRET_KEY = require_env("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
ADMIN_USER = require_env("ADMIN_USERNAME")
ADMIN_PASSWORD = require_env("ADMIN_PASSWORD")

# --- Database Setup ---
engine = create_engine(get_database_url())

def get_session():
    with Session(engine) as session:
        yield session

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

# --- Auth Dependencies ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)

# Hash the hardcoded admin password securely
ADMIN_HASH = get_password_hash(ADMIN_PASSWORD)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username != ADMIN_USER:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username

# --- FastAPI App ---
app = FastAPI(title="Movie Scraper API")

# --- Bonus: Health Check ---
@app.get("/health")
def health_check():
    last_scrape = "Never"
    if os.path.exists("last_scrape.txt"):
        with open("last_scrape.txt", "r") as f:
            last_scrape = f.read().strip()
    return {"status": "healthy", "last_scrape_timestamp": last_scrape}

# --- Routes ---

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != ADMIN_USER or not verify_password(form_data.password, ADMIN_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/movies")
def get_movies(
    page: int = Query(1, ge=1), 
    limit: int = Query(10, ge=1, le=100), 
    session: Session = Depends(get_session),
    user: str = Depends(get_current_user) # Protects the route
):
    offset = (page - 1) * limit
    movies = session.exec(select(Movie).offset(offset).limit(limit)).all()
    return movies

@app.get("/movies/{movie_id}")
def get_movie(
    movie_id: int, 
    session: Session = Depends(get_session),
    user: str = Depends(get_current_user)
):
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie

@app.patch("/movies/{movie_id}")
def update_movie(
    movie_id: int, 
    movie_update: MovieUpdate, 
    session: Session = Depends(get_session),
    user: str = Depends(get_current_user)
):
    db_movie = session.get(Movie, movie_id)
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    # Update only the fields provided in the PATCH payload
    update_data = movie_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_movie, key, value)
        
    session.add(db_movie)
    session.commit()
    session.refresh(db_movie)
    return db_movie

@app.delete("/movies/{movie_id}")
def delete_movie(
    movie_id: int, 
    session: Session = Depends(get_session),
    user: str = Depends(get_current_user)
):
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    session.delete(movie)
    session.commit()
    return {"ok": True, "message": "Movie deleted"}