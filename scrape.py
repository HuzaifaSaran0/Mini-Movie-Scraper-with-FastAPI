from datetime import datetime
import time
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select

# Import the model and config
from config import get_database_url
from models import Movie

load_dotenv()

engine = create_engine(get_database_url())

def run_scraper():
    print("Starting scraper...")
    # Targeting a public movie listing site with real thumbnails and genres exposed in the HTML.
    # This matches the prompt's requirement for sites like myflixer.
    
    movies_added = 0
    movies_skipped = 0

    with Session(engine) as session:
        # Loop through pages 1 to 5 to fetch a solid batch of movies
        for page_num in range(1, 6):
            url = f"https://yts-official.is/browse-movies?page={page_num}"
            print(f"Scraping {url} ...")
            
            try:
                # Use a modern user-agent to ensure we are not blocked
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                # follow_redirects=True handles the mirror routing
                response = httpx.get(url, headers=headers, follow_redirects=True, timeout=15.0)
                response.raise_for_status()
            except Exception as e:
                print(f"Failed to fetch page {page_num}: {e}")
                continue # If one page fails, keep trying the others

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all movie containers on the page
            movie_cards = soup.find_all("div", class_="browse-movie-wrap")
            if not movie_cards:
                print(f"No movie cards found on page {page_num}. The site structure may have changed.")
                continue

            for card in movie_cards:
                try:
                    # 1. Source URL
                    link_tag = card.find("a", class_="browse-movie-link")
                    if not link_tag:
                        continue
                    source_url = link_tag.get("href")
                    
                    # --- The Duplicate Check ---
                    # Check early to save processing time before parsing the rest of the DOM
                    existing = session.exec(select(Movie).where(Movie.source_url == source_url)).first()
                    if existing:
                        movies_skipped += 1
                        continue

                    # 2. Title
                    title_tag = card.find("a", class_="browse-movie-title")
                    title = title_tag.text.strip() if title_tag else "Unknown Title"

                    # 3. Release Year
                    year_tag = card.find("div", class_="browse-movie-year")
                    try:
                        release_year = int(year_tag.text.strip()) if year_tag else 0
                    except ValueError:
                        release_year = 0

                    # 4. Thumbnail URL
                    img_tag = card.find("img", class_="img-responsive")
                    thumbnail_url = img_tag.get("src") if img_tag else ""
                    # Handle relative URLs just in case
                    if thumbnail_url and not thumbnail_url.startswith("http"):
                        thumbnail_url = "https://yts-official.is" + thumbnail_url

                    # 5. Genre(s)
                    # Genres are stored in <h4> tags inside the hidden figcaption element
                    figcaption = card.find("figcaption")
                    genres_list = []
                    if figcaption:
                        h4_tags = figcaption.find_all("h4")
                        for h4 in h4_tags:
                            # Skip the rating <h4> (which usually contains " / 10")
                            if "/" not in h4.text:
                                genres_list.append(h4.text.strip())
                    
                    genres = ", ".join(genres_list) if genres_list else "Unknown"

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
                    print(f"Error parsing a movie card: {e}")
                    continue
            
            # Polite scraping: Wait 2 seconds before hitting the next page so we don't get blocked
            time.sleep(2)

        # Save a timestamp for the /health route to read later
        with open("last_scrape.txt", "w") as f:
            f.write(datetime.now().isoformat())

    print(f"Scrape complete! Added: {movies_added} | Skipped (Duplicates): {movies_skipped}")

if __name__ == "__main__":
    run_scraper()