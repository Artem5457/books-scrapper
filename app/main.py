import csv
from math import ceil
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook

base_url = 'https://books.toscrape.com/'
headers = {
    "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
}
MAX_BOOKS_PER_PAGE = 20


def get_categories() -> list[dict]:
    try:
        res = requests.get(base_url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')
        nav_list = soup.find('ul', class_='nav-list').find_all('a')[1:]
        return [
            {
                "page_url": urljoin(base_url, category['href']),
                "category_name": category.text.strip()
            }
            for category in nav_list
        ]
    except requests.exceptions.RequestException as e:
        print(f'Error loading categories: {e}')
        return []


def get_pages_count(category_page) -> int:
    category_books_count = category_page.find(
        'form', class_='form-horizontal').find('strong').text.strip()
    pages = ceil(int(category_books_count) / MAX_BOOKS_PER_PAGE)
    return int(pages)


def get_book_info(soup, category: dict) -> dict:
    title = soup.find('h1').text
    price = soup.find('p', class_='price_color').text.replace('Â£', '')
    rating = soup.find('p', class_='star-rating')['class'][1]
    description_tag = soup.find(id='product_description')
    upc = soup.find('td').text
    if description_tag:
        description = description_tag.find_next_sibling('p').text
    else:
        description = '----'
    return {
        'category': category['category_name'],
        'title': title,
        'price': price,
        'rating': rating,
        'description': description,
        'upc': upc
    }


def get_books_by_page(page, category: dict) -> list[dict]:
    books_on_page = page.find_all('article', class_='product_pod')
    books = []
    for book in books_on_page:
        book_url = urljoin(category['page_url'], book.find('a')['href'])
        try:
            res = requests.get(book_url, headers=headers)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'lxml')
            books.append(get_book_info(soup, category))
        except requests.exceptions.RequestException as e:
            print(f"Error loading book page {book_url}: {e}")
    return books


def get_books_by_category(category: dict) -> list[dict]:
    try:
        res = requests.get(category['page_url'], headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')
        pages_count = get_pages_count(soup)
        first_page_books = get_books_by_page(soup, category)
        books = first_page_books

        if pages_count == 1:
            return books
        for i in range(2, pages_count + 1):
            url = urljoin(category['page_url'], f'page-{i}.html')
            try:
                res_i = requests.get(url, headers=headers)
                res_i.raise_for_status()
                soup_i = BeautifulSoup(res_i.text, 'lxml')
                page_i_books = get_books_by_page(soup_i, category)
                books.extend(page_i_books)
            except requests.exceptions.RequestException as e:
                print(
                    f"Error loading page {i} of category {category['category_name']}: {e}")
        return books
    except requests.exceptions.RequestException as e:
        print(f"Error loading category {category['category_name']}: {e}")
        return []


def get_all_books(categories: list[dict]) -> list[dict]:
    all_books = []
    for category in categories:
        category_books = get_books_by_category(category)
        all_books.extend(category_books)
    return all_books


def write_to_csv(books: list[dict]) -> None:
    try:
        with open('books.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Category', 'Title', 'Price,£',
                            'Rating', 'Description', 'UPC'])
            for book in books:
                writer.writerow(
                    [
                        book['category'],
                        book['title'],
                        book['price'],
                        book['rating'],
                        book['description'],
                        book['upc']
                    ]
                )
    except IOError as e:
        print(f'Error writing to CSV: {e}')


def write_to_excel(books: list[dict]) -> None:
    try:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Books'
        sheet.append(['Category', 'Title', 'Price,£',
                      'Rating', 'Description', 'UPC'])
        for book in books:
            sheet.append([
                book['category'],
                book['title'],
                book['price'],
                book['rating'],
                book['description'],
                book['upc']
            ])
        workbook.save('books.xlsx')
    except IOError as e:
        print(f'Error writing to Excel: {e}')


def main() -> None:
    categories = get_categories()
    if categories:
        all_books = get_all_books(categories)
        write_to_csv(all_books)
        write_to_excel(all_books)


if __name__ == '__main__':
    main()
