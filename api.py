import requests
from term_image.image import from_url

def get_book_info(title, isbn,author):
    title = title.strip().replace(' ','+')
    author = author.strip().replace(' ','%20')
    url = f"https://openlibrary.org/search.json?title={title}"
    print(url)
    response = requests.get(url)
    if response.status_code == 200: 
        data = response.json()
        for i in range(len(data)):
            # print(data['docs'][i].keys())
            if 'cover_i' in data['docs'][i]:

                print("Title:  ",data['docs'][i]['title'])
                print('Author: ',data['docs'][i].get('author_name',['Anonymous'])[0])
                print('Cover Page ID: ',data['docs'][i]['cover_i'])
                print('ISBN',data['docs'][i].get('isbn','No ISBN'))
                if 'ratings_count' in data['docs'][i]:
                    
                    print('Average Ratings: ',data['docs'][i]['ratings_average'])
                    print('Ratings: ',data['docs'][i]['ratings_count'])
                    print('1: ',data['docs'][i]['ratings_count_1'])
                    print('2: ',data['docs'][i]['ratings_count_2'])
                    print('3: ',data['docs'][i]['ratings_count_3'])
                    print('4: ',data['docs'][i]['ratings_count_4'])
                    print('5: ',data['docs'][i]['ratings_count_5'])
                    print('People wanting to read: ',data['docs'][i]['want_to_read_count'])
                    print('People currently reading: ',data['docs'][i]['currently_reading_count'])
                    print('People already Read: ',data['docs'][i]['already_read_count'])
                print('Published in: ',data['docs'][i].get('first_publish_year','NA'))



        # image = requests.get(f"https://covers.openlibrary.org/b/id/{data['docs'][i]['cover_i']}-S.jpg")
                print('\n\n')

def search(title):
    books = []
    title = title.strip().replace(' ','+')
    url = f"https://openlibrary.org/search.json?title={title}"
    response = requests.get(url)
    if response.status_code == 200: 
        data = response.json()
        for book in data['docs']:
            if 'cover_i' in book:
                    books.append(book)
    return books

title = "Tom and Jerry"
answer = search(title=title)
                    



        # image = requests.get(f"https://covers.openlibrary.org/b/id/{data['docs'][i]['cover_i']}-S.jpg")

# Example usage

# get_book_info(title,isbn,author)