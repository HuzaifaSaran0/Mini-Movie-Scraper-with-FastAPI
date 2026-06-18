from typing import Optional
from sqlmodel import SQLModel, Field

# 1. The Base Model (Shared fields)
class MovieBase(SQLModel):
    title: str
    thumbnail_url: str
    genres: str  # We will store this as a comma-separated string (e.g., "Action, Sci-Fi") for simplicity
    release_year: int
    
    # The unique=True constraint is the magic that fulfills the requirement: 
    # "Running twice must not create duplicates"
    source_url: str = Field(unique=True, index=True)

# 2. The Database Table Model
# Adding table=True tells SQLModel this isn't just for validation; it's a real Postgres table.
class Movie(MovieBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

# 3. The Update Model (For PATCH /movies/{id})
# The requirements explicitly state we should only update title or genre.
class MovieUpdate(SQLModel):
    title: Optional[str] = None
    genres: Optional[str] = None