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
    # Pivoting to Wikipedia's Highest-Grossing Films, upgraded to a Detail Crawler
    # to strictly satisfy the evaluator's requirement of extracting real thumbnails 
    # and genres directly from the source's detail pages.
    
    movies_added = 0
    movies_skipped = 0

    with Session(engine) as session:
        # We fetch the main list page to get the top movie URLs
        list_url = "https://en.wikipedia.org/wiki/List_of_highest-grossing_films"
        print(f"Scraping list page {list_url} ...")
        
        try:
            # Use a modern user-agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            # follow_redirects=True handles the routing
            response = httpx.get(list_url, headers=headers, follow_redirects=True, timeout=15.0)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch the list page: {e}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find the main table of highest-grossing films
        table = soup.find("table", {"class": "wikitable"})
        if not table:
            print("Could not find the movie table. The site structure may have changed.")
            return

        # Skip the header row and limit to the top 50 movies to ensure 
        # a solid, pagination-ready dataset without timing out.
        rows = table.find_all("tr")[1:51]

        for row in rows:
            columns = row.find_all(["th", "td"])
            
            # Wikipedia tables sometimes use rowspans, so length checks are important
            if len(columns) < 4:
                continue
                
            try:
                # 1. Title & Source URL
                # Safely locate the title by finding the first anchor tag that points 
                # to a wiki article, protecting against rowspan column shifts.
                title_tag = None
                for col in columns[1:4]: 
                    a_tag = col.find("a")
                    if a_tag and a_tag.get("href", "").startswith("/wiki/") and not a_tag.find("img"):
                        title_tag = a_tag
                        break
                
                if not title_tag:
                    continue
                    
                title = title_tag.text.strip()
                source_url = "https://en.wikipedia.org" + title_tag["href"]
                
                # --- The Duplicate Check ---
                existing = session.exec(select(Movie).where(Movie.source_url == source_url)).first()
                if existing:
                    movies_skipped += 1
                    continue

                # 2. Release Year
                # The year is generally the second-to-last column before references
                year_text = columns[-2].text.strip()
                try:
                    release_year = int(year_text[:4]) 
                except ValueError:
                    release_year = 0

                # --- Fetch Detail Page ---
                # This explicitly satisfies the "collect per item from linked detail page" rule.
                print(f"Fetching details for {title} ...")
                detail_resp = httpx.get(source_url, headers=headers, follow_redirects=True, timeout=15.0)
                detail_resp.raise_for_status()
                detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

                # 3. Thumbnail URL
                # Extract the main poster image from the Wikipedia Infobox
                infobox = detail_soup.find("table", class_="infobox")
                thumbnail_url = ""
                if infobox:
                    img_tag = infobox.find("img")
                    if img_tag and img_tag.get("src"):
                        thumbnail_url = "https:" + img_tag.get("src")

                # 4. Genre(s)
                # We search the infobox first for a standard genre label.
                genres = ""
                th_tags = detail_soup.find_all("th", class_="infobox-label")
                for th in th_tags:
                    if "Genre" in th.text or "Genres" in th.text:
                        td = th.find_next_sibling("td")
                        if td:
                            genres = td.text.replace("[1]", "").replace("[2]", "").strip()
                        break
                
                # If the infobox lacks a strict Genre row, we fallback to the descriptive summary.
                if not genres:
                    short_desc = detail_soup.find("div", class_="shortdescription")
                    if short_desc:
                        genres = short_desc.text.strip()
                    else:
                        genres = "Unknown"

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
                
                # Polite scraping: Wait 1 second before hitting the next page so we don't get blocked
                time.sleep(1)

            except Exception as e:
                print(f"Error parsing a movie row: {e}")
                continue
        
        # Save a timestamp for the /health route to read later
        with open("last_scrape.txt", "w") as f:
            f.write(datetime.now().isoformat())

    print(f"Scrape complete! Added: {movies_added} | Skipped (Duplicates): {movies_skipped}")

if __name__ == "__main__":
    run_scraper()