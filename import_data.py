import csv
import os
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable, prioritize URL from secrets.py
if not os.getenv("DATABASE_URL"):
    try:
        from config import DATABASE_URL
    except ImportError:
        raise ImportError("DATABASE_URL is not set and no secrets.py found")
else:
    DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))

# Create the books table
# db.execute(text('''
#     CREATE TABLE IF NOT EXISTS books (
#         isbn VARCHAR PRIMARY KEY,
#         title VARCHAR NOT NULL,
#         author VARCHAR NOT NULL,
#         year INTEGER NOT NULL
#     )
# '''))
# db.commit()

# Import data from CSV file
with open('books.csv', 'r') as f:
    reader = csv.reader(f, delimiter=',')
    next(reader, None)  # Skip the header row
    x = 0
    for title, author in reader:
        if x == 200:
            break
        url = f"https://openlibrary.org/search.json?title={title.strip().replace(' ','+')}&limit=1"
        
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200 or len(data['docs']) == 0:
            continue
        
        if 'cover_i' in data['docs'][0]:
            cover_id = data['docs'][0]['cover_i']
            print('Cover Page ID: ',data['docs'][0]['cover_i'])

            db.execute(text('''
                INSERT INTO books (cover_id, title, author)
                VALUES (:cover_id, :title, :author)
            '''), {'cover_id':cover_id, 'title': title, 'author': author})
            print(title," Insertion Successful")
            x += 1

db.commit()

print('Import successful')
