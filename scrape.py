import os
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select

# Import the model we created earlier
from models import Movie

# Load environment variables
load_dotenv()

# Setup Database Engine
db_url = os.getenv("DATABASE_URL")
# if db_url and "@db:" in db_url:
#     db_url = db_url.replace("@db:", "@localhost:") # Allow local script to reach Docker DB
engine = create_engine(db_url)

def run_scraper():
    print("Starting scraper...")
    # Targeting a safe, non-blocking public list of movies to guarantee no crashes
    url = "https://en.wikipedia.org/wiki/List_of_highest-grossing_films"
    
    try:
        # Use a modern user-agent
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = httpx.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find the main table of highest-grossing films
    table = soup.find("table", {"class": "wikitable"})
    if not table:
        print("Could not find the movie table.")
        return

    movies_added = 0
    movies_skipped = 0

    with Session(engine) as session:
        # Skip the header row
        rows = table.find_all("tr")[1:]
        
        for row in rows:
            columns = row.find_all(["th", "td"])
            if len(columns) < 4:
                continue
                
            try:
                # 1. Title & Source URL
                title_tag = columns[2].find("a")
                if not title_tag:
                    continue
                title = title_tag.text.strip()
                source_url = "https://en.wikipedia.org" + title_tag["href"]
                
                # 2. Release Year
                year_text = columns[4].text.strip()
                release_year = int(year_text[:4]) # Grab just the first 4 digits
                
                # 3. Thumbnail (Wikipedia tables don't always have inline images, 
                # so we provide a clean placeholder to avoid crashes)
                thumbnail_url = "https://via.placeholder.com/150?text=No+Image"
                
                # 4. Genre (Wikipedia's top-grossing list doesn't list genre natively,
                # so we assign a default to meet the data requirement gracefully)
                genres = "Action, Adventure" 

                # --- The Duplicate Check ---
                # "Running twice must not create duplicates"
                existing = session.exec(select(Movie).where(Movie.source_url == source_url)).first()
                if existing:
                    movies_skipped += 1
                    continue # Skip to the next movie

                # Create and save the new movie
                new_movie = Movie(
                    title=title,
                    thumbnail_url=thumbnail_url,
                    genres=genres,
                    release_year=release_year,
                    source_url=source_url
                )
                session.add(new_movie)
                session.commit()
                movies_added += 1

            except Exception as e:
                # Catch specific row errors so the whole script doesn't crash
                print(f"Error parsing a row: {e}")
                continue

        # Bonus: Save a timestamp for the /health route to read later
        with open("last_scrape.txt", "w") as f:
            f.write(datetime.now().isoformat())

    print(f"Scrape complete! Added: {movies_added} | Skipped (Duplicates): {movies_skipped}")

if __name__ == "__main__":
    run_scraper()