import http.cookiejar
import json
import os
import time

import flask
import mechanize
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
cookies_file = "cookies.json"

app = flask.Flask(__name__)


def login() -> dict:
    # if cookies.txt is more than 1 day old, delete it, else return it
    if os.path.exists(cookies_file):
        if os.path.getmtime(cookies_file) < time.time() - 86400:
            os.remove(cookies_file)
        else:
            with open(cookies_file, "r", encoding="utf-8") as f:
                cookies = json.loads(f.read())
            return cookies

    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")

    # Initialize mechanize
    br = mechanize.Browser()

    # Create a cookie jar
    cj = http.cookiejar.CookieJar()
    br.set_cookiejar(cj)

    # Open the URL
    br.open("https://www.thriftbooks.com/account/login/")

    # Select the login form
    br.select_form(
        nr=0
    )  # replace 0 with the index of the login form if it's not the first form

    # Input the username and password
    br.form["ExistingAccount.EmailAddress"] = (
        username  # replace 'username' with the actual field name
    )
    br.form["ExistingAccount.Password"] = (
        password  # replace 'password' with the actual field name
    )

    # Submit the form
    br.submit()

    # Save the cookies to a variable
    cookies = requests.utils.dict_from_cookiejar(cj)
    with open(cookies_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(cookies))
    return cookies


def get_item_details(isbn: int, cookies: dict) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Site": "same-origin",
        "Accept-Language": "en-SG,en-GB;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Mode": "cors",
        "Host": "www.thriftbooks.com",
        "Origin": "https://www.thriftbooks.com",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://www.thriftbooks.com/buyback/",
        "Content-Length": "47",
        "Connection": "keep-alive",
    }

    data = {"identifiers": [str(isbn)], "addedFrom": 3}

    # Use the cookies to make a request to an API endpoint
    response = requests.post(
        "https://www.thriftbooks.com/tb-api/buyback/get-quotes/",
        json=data,
        cookies=cookies,
        headers=headers,
        timeout=20,
    )

    with open(f"debug/{isbn}.json", "w", encoding="utf-8") as f:
        f.write(response.text)

    return parse_response(response.json())


def parse_response(response: dict) -> dict:
    # save response to local json file
    if "sellListItems" in response and len(response["sellListItems"]) > 0:
        item = response["sellListItems"][0]
        isbn = item["userEnteredIdentifier"]
        with open(f"data/{isbn}.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(response))
        return item
    elif "messages" in response and len(response["messages"]) > 0:
        raise Exception(response["messages"][0]["message"])


def get_title_price(isbn: int, cookies: dict) -> dict:
    try:
        item = get_item_details(isbn, cookies)
    except Exception as e:
        return {"error": str(e)}
    return {
        "title": item["title"],
        "price": item["quotePrice"],
    }


@app.route("/api/quote/<int:isbn>")
def get_quote(isbn: int):
    cookies = login()
    return get_title_price(isbn, cookies)


def main():
    app.run(port=5000)


if __name__ == "__main__":
    main()

# isbns = [
#     9780030314612,
#     9781849515306,
#     9780750687621,
#     9780735711020,
#     9780143109259,
#     9780684808185,
#     9780525947585,
#     9781982133122,
# ]

# Sample response
# {
#     "messages": [
#         {
#             "message": "1 item added to My Sell List (not buying).",
#             "severity": "informative",
#             "title": None,
#         }
#     ],
#     "sellListItems": [
#         {
#             "idBuyBackSellListItem": 1856976,
#             "idAmazon": 1936171,
#             "quantity": 0,
#             "isSelected": False,
#             "isAccepted": False,
#             "userEnteredIdentifier": "9780030314612",
#             "buyBackIdentifierType": "EAN",
#             "identifiers": [
#                 {"identifierType": "EAN", "identifierValue": "9780030314612"},
#                 {"identifierType": "ISBN", "identifierValue": "0030314615"},
#             ],
#             "updatedDate": None,
#             "quotePrice": 0,
#             "quoteGenDate": None,
#             "genDate": "0001-01-01T00:00:00",
#             "title": "Fundamentals of Financial Management",
#             "media": "Hardcover",
#             "imageUrl": "https://i.thriftbooks.com/api/imagehandler/s/C823EE8823463FFCA3A67450B4C8DAF37A3A68FE.jpeg",
#             "estimatedWeight": 4.7,
#             "message": "",
#             "lastViewedQuotes": None,
#             "sellListUpdatedDate": None,
#         }
#     ],
#     "errors": {"validationErrors": [], "isValid": True},
# }
