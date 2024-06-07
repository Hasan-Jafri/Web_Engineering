import os
import requests
from flask import Flask, session, render_template, redirect, url_for, request
from flask_session import Session
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, FloatField
from wtforms.validators import InputRequired, Email, Length
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import inspect

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

app = Flask(__name__)
Bootstrap(app)
app.config['SECRET_KEY'] = "I'M A SECRET"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Users(UserMixin, db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))

    def __repr__(self):
        return '<User %r>' % self.username
    def get_id(self):
        return str(self.user_id)


class Reviews(db.Model):
    review_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,nullable=False)
    book_id = db.Column(db.Integer,nullable=False)
    review_text = db.Column(db.String(1000), nullable=False)
    rating = db.Column(db.Float(),nullable=False)

class Books(db.Model):
    book_id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String,nullable=False)
    author = db.Column(db.String,nullable=False)
    cover_id = db.Column(db.Integer,nullable=False)

def get_rating_stars(rating):
    if rating == 0:
        return '-'
    full_stars = '★' * int(rating)
    empty_stars = '☆' * (5 - int(rating))
    return full_stars + empty_stars

def find_Rating(cover_id,title):
    url = f"https://openlibrary.org/search.json?title={title.strip().replace(' ','+')}&cover_i={cover_id}&limit=1"
    response = requests.get(url)
    data = response.json()
    for x in data['docs']:
        if x.get('cover_i',0) == cover_id:
            return x.get('ratings_average',0)
    return 0

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
    remember = BooleanField('remember me')

# Home Page
@app.route("/")
def index():
    if current_user.is_anonymous:
        return render_template('login.html')
    books = db.session.execute(text('SELECT title, cover_id FROM books ORDER BY RANDOM() LIMIT 10')).fetchall()
    book_html = ""
    for book in books:
        rating = find_Rating(cover_id=book[1],title=book[0])
        book_html += f"""
        
            <div class="book-item">
                <a href = "/book/{book[1]}&{book[0]}" class = "book-item" >
                <img src="https://covers.openlibrary.org/b/id/{book[1]}-L.jpg" alt="{book[0]}">
                </a>
                <p class="title">{book[0]}</p>
                <div class="rating">{get_rating_stars(rating)}</div>
            </div>
        """

    return render_template('home.html', book_html= book_html, name=current_user.username)

# Login Credentials
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        # Retrieve form data from request
        LoginForm.username = request.form.get('username')
        LoginForm.remember = request.form.get('remember_me')
        user = Users.query.filter_by(username=LoginForm.username).first()
        if user:
            login_user(user, remember=LoginForm.remember)
            return redirect(url_for('index'))
        return '<h1>Invalid username or password</h1>'
    return render_template('login.html', form=form)

# Sign Up details
@app.route('/signup', methods = ['GET', "POST"])
def signup():
    if request.method == 'POST':
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        users = db.session.execute(text("SELECT username, email FROM users WHERE email = :email"),{'email' : email}).fetchone()
        if users:
            return render_template('signup.html',message = "Email Already Registered")
        try:
            new_user = Users(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print("Error during sign-up:", e)
            return '<h1>Signup failed. Please try again.</h1>'
    else:
        return render_template('signup.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Searching
@app.route('/search', methods=['POST'])
@login_required
def search():
    title = request.form.get('search_query')
    result = search(title)
    book_html = ""
    for book in result:
        rating = book.get('ratings_average',0)
        book_html += f"""
            <div class="book-item">
            <a href = "/book/{book['cover_i']}&{book['title']}" class = "books-item">
                <img src="https://covers.openlibrary.org/b/id/{book['cover_i']}-L.jpg" alt="{book['title']}">
                </a>
                <p class="title">{book['title']}</p>
                <div class="rating">{get_rating_stars(rating)}</div>
            </div>
        """
    return render_template('searchresults.html', book_html=book_html, name=current_user.username,text = title)

# Book Details
@app.route('/book/<cover_id>&<title>', methods=['GET', 'POST'])
@app.route("/book/addReview", methods=['POST'])
@login_required
def book_detail(cover_id=None, title=None):
    if not title and not cover_id and request.method == 'POST':
        title = request.form.get('title').replace("''","'")
        cover_id = request.form.get('cover_id')
    escaped_title = title.replace("'", "''")
    
    book = db.session.execute(
        text(f"SELECT book_id, title, author FROM books WHERE title = '{escaped_title}' AND cover_id = '{cover_id}'")
    ).fetchone()
    
    
    title_ = title
    cover_id_ = cover_id
    book_details = search_one_book(cover_id=cover_id, title=title)
    
    if not book:
        # Book not in the database, fetch details and add it
        
        new_book = Books(title=book_details['title'], author=book_details['author'], cover_id=book_details['cover_id'])
        try:
            db.session.add(new_book)
            db.session.commit()
            title_ = title
            cover_id_ = cover_id
        except Exception as e:
            db.session.rollback()
            print("Error during adding book:", e)
            return '<h1>An Error Occurred. Try Again.</h1>'
    
    if request.method == 'POST':
        # Add the review for the book
        user_id = db.session.execute(text("SELECT user_id FROM users WHERE username = :username"),{'username':current_user.username}).fetchone()
        
        new_review = Reviews(
            book_id=book[0],
            review_text=request.form.get('review'),
            rating=int(request.form.get('rating')),
            user_id=user_id[0]
        )
        try:
            db.session.add(new_review)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("Error during adding review:", e)
            return '<h1>Error Occurred in Adding Review</h1>'
    
    reviews = db.session.execute(text(f"SELECT r.review_text, r.rating, u.username FROM reviews r JOIN users u ON r.user_id = u.user_id WHERE r.book_id = {book[0]}")).fetchall()
    reviews_html = ''
    if reviews:
        for review in reviews:
            reviews_html += f"""
            <div class "single-review">
            <div class="review-details">
                <p class ="username" >{review[2]}</p>
                <div class = "rating">{get_rating_stars(review[1])}</div>
                </div>
                <div class = "review-text">{review[0]}</div></div>"""
    
    image_html = f"<img src='https://covers.openlibrary.org/b/id/{cover_id_}-L.jpg' alt='{title_}'>"
    
    return render_template('book.html', book=book_details, image_html=image_html, reviews_html=reviews_html)



def search(title):
    books = []
    title = title.strip().replace(' ','+')
    url = f"https://openlibrary.org/search.json?title={title}"
    response = requests.get(url)
    if response.status_code == 200: 
        data = response.json()
        for book in data['docs']:
            if book.get('cover_i',0) != 0 and book.get('ratings_average',0) != 0:
                    books.append(book)
    return books

def search_one_book(title,cover_id):
    result = {}
    url = f"https://openlibrary.org/search.json?title={title.strip().replace(' ','+')}&cover_i={cover_id}&limit=1"
    response = requests.get(url)
    if response.status_code == 200: 
        data = response.json()
        book = data['docs'][0]
        result['cover_id'] = cover_id
        result['rating'] = f"{book.get('ratings_average', 0):.2f}"
        result['title'] = title
        result['author'] = book.get('author_name',['Anonymous'])[0]
        result['rating_count'] = book.get('ratings_count',0)
        result['one_star'] = book.get('ratings_count_1',0)
        result['two_star'] = book.get('ratings_count_2',0)
        result['three_star'] = book.get('ratings_count_3',0)
        result['four_star'] = book.get('ratings_count_4',0)
        result['five_star'] = book.get('ratings_count_5',0)
        result['people_wanting_to_read'] = book.get('want_to_read_count',0)
        result['already_read_count'] = book.get('already_read_count',0)
        result['currently_reading_count'] = book.get('currently_reading_count',0)
        result['published'] = book.get('first_publish_year','NA')
    return result

if __name__ == '__main__':
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Database connected:", result.scalar())
    except Exception as e:
        print("Database connection error:", e)
    app.debug = True
