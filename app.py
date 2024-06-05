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

def create_tables_if_not_exist():
    tables = [User.__table__, Reviews.__table__]  # List of table objects

    with db.engine.connect() as connection:
        inspector = inspect(connection)
        existing_tables = inspector.get_table_names()

        for table in tables:
            if table.name not in existing_tables:
                table.create(db.engine)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))

    def __repr__(self):
        return '<User %r>' % self.username


class Reviews(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    isbn = db.Column(db.String(50))
    review_text = db.Column(db.String(10000), nullable=False)
    rating = db.Column(db.Float())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class ReviewForm(FlaskForm):
    review_text = StringField('review_text', validators=[InputRequired(), Length(min=10, max=10000)])
    rating = FloatField('rating', validators=[InputRequired()])

class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
    remember = BooleanField('remember me')

class RegisterForm(FlaskForm):
    email = StringField('email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])

def c_dict_list(column_names, l):
    # return dictionary of rows with column keys
    return [{c_name: col for c_name, col in zip(column_names, row)} for row in l]

@app.route("/")
def index():
    books = db.session.execute(text('SELECT title, cover_id FROM books ORDER BY RANDOM() LIMIT 2')).fetchall()
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
    if current_user.is_anonymous:
        return render_template('home.html', books=[])
    return render_template('home.html', book_html= book_html, name=current_user.username)

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


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        # Retrieve form data from request
        LoginForm.username = request.form.get('username')
        LoginForm.remember = request.form.get('remember_me')
        user = User.query.filter_by(username=LoginForm.username).first()
        if user:
            login_user(user, remember=LoginForm.remember)
            return redirect(url_for('index'))
        return '<h1>Invalid username or password</h1>'
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            new_user = User(username=form.username.data, email=form.email.data, password=form.password.data)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            print("Error during sign-up:", e)
            return '<h1>Signup failed. Please try again.</h1>'
    return render_template('signup.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def add_wildcard_symbols(l):
    return (f'%{i}%' for i in l)

@app.route('/search', methods=['POST'])
@login_required
def search():
    title = request.form.get('search_query')
    # query = text('SELECT * FROM books WHERE isbn LIKE :isbn AND title LIKE :title AND author LIKE :author LIMIT 500')
    # l = db.session.execute(query, {'isbn': isbn, 'title': title, 'author': author}).fetchall()
    # l = [{'isbn': isbn, 'title': title, 'author': author, 'year': year} for isbn, title, author, year in l]
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

@app.route('/book/<cover_id>&<title>')
@login_required
def book_detail(cover_id,title):
    # form = ReviewForm()
    # query = text('SELECT title, author, year FROM books WHERE isbn = :isbn')
    # book = db.session.execute(query, {'isbn': isbn}).fetchone()
    # if not book:
    #     return 'invalid ISBN'
    
    # if request.method == 'POST':
    #     if not form.validate_on_submit():
    #         return 'invalid rating'
    # title, author, year = book
    # d = {'isbn': isbn, 'title': title, 'author': author, 'year': year}
    # reviews = Reviews.query.filter_by(isbn=isbn).all()
    book = search_one_book(cover_id = cover_id,title = title)
    image_html = f"<img src='{book['cover_id']}-L.jpg' alt='{book['title']}'>"
    print(f"book['cover_id']-L.jpg")
    return render_template('book.html',book = book,image_html = image_html)

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
        result['cover_id'] = f"https://covers.openlibrary.org/b/id/{cover_id}" if cover_id != 0 else {url_for('static', filename='assets/images/Azfar.png') }
        result['rating'] = book.get('ratings_average',0)
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
