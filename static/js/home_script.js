document.addEventListener('DOMContentLoaded', function(book) {
    const books = [
        { image: 'https://covers.openlibrary.org/b/id/6982647-L.jpg', title: 'Kung Fu Panda', rating: 4 },
        { image: 'https://ia800404.us.archive.org/view_archive.php?archive=/33/items/l_covers_0010/l_covers_0010_52.zip&file=0010523466-L.jpg', title: 'Harry Potter and the Order of the Phoenix', rating: 3 },
        { image: 'https://covers.openlibrary.org/b/id/6692866-L.jpg', title: 'Tom and Jerry', rating: 5 },
        { image: "static/assets/images/sample_cover_L.png", title: 'God of Mercy', rating: 5 },
        { image: "static/assets/images/sample_cover_L.png", title: 'After the Sun', rating: 5 },
        { image: "static/assets/images/sample_cover_L.png", title: 'My Friend Natalie', rating: 5 },
        { image: "static/assets/images/sample_cover_L.png", title: 'Mona', rating: 5 },
        { image: "static/assets/images/Azfar.png", title: 'Sad Life of Azfar Ali', rating: 5 },
    ];

    const bookGrid = document.getElementById('book-grid');
    books.forEach(book => {
        const bookItem = document.createElement('div');
        bookItem.classList.add('book-item');
        
        const bookImage = document.createElement('img');
        bookImage.src = book.image;
        bookImage.alt = book.title;
        
        const bookTitle = document.createElement('p');
        bookTitle.classList.add('title');
        bookTitle.textContent = book.title;
        
        const bookRating = document.createElement('div');
        bookRating.classList.add('rating');
        bookRating.innerHTML = getRatingStars(book.rating);
        
        bookItem.appendChild(bookImage);
        bookItem.appendChild(bookTitle);
        bookItem.appendChild(bookRating);
        
        bookGrid.appendChild(bookItem);
    });
});

function getRatingStars(rating) {
    const fullStars = '★'.repeat(Math.floor(rating));
    const emptyStars = '☆'.repeat(5 - Math.floor(rating));
    return fullStars + emptyStars;
}
