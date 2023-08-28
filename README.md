# Gab Social Media Scraper

This script is designed to extract posts-related information from Gab public groups or user accounts using web scraping. It utilizes the Beautiful Soup library and a session manager for making requests. The script allows you to gather posts' data from groups using keywords or group links, as well as retrieve posts from user accounts using their usernames.

## Requirements

- Python 3.x
- Beautiful Soup
- Requests-html

Install the required packages using the following command:
```pip install beautifulsoup4 requests-html pymongo```

## Approach

The script provides a class with methods to fetch posts from Gab public groups or user accounts based on keywords or group links.

### Input

For groups:
- You can provide a keyword to find groups related to that keyword (e.g., `food`).
- Alternatively, you can provide a group link (e.g., `https://gab.com/groups/158`) which contains the group id (158 in this case).

For accounts:
- You need to provide the username of the account to scrape its posts.

### Extraction

The process involves:

1. Initializing the class:
   - The script creates an HtmlSession to make requests through a JavaScript environment.
   - It requests the signin page to obtain the authenticity token (required for login) and x-csrf-token (needed for request legitimacy).
   - If authentication is successful, the session is stored.
   - Login is necessary to view more than 4 pages or 80 posts per group or account.

2. Group Extraction:
   - If a keyword is provided, the script loops until it gets a zero response length in the JSON format. This indicates that all group ids related to the keyword have been obtained.
   - The script maps each group id to the `profile_detail_group` function to retrieve data from each group.
   - If no group ids are obtained in the response, it means the script has all the required group ids for the keyword.
   - The `profile_detail_group` function retrieves information about a group using the API link.
   - The `get_data_group` function fetches all posts for the respective group, iterating through the site until it receives a response with zero length.
   - Each request for group posts retrieves 20 posts' related information, which is then processed to extract required data.
   - If there are multiple media attachments or quotes, the script loops through them.

3. Link-based Group Extraction:
   - If a group link is provided, the script directly obtains the group id from the end of the link and continues with the `profile_detail_group` function.

Note: Detailed methods and API endpoints mentioned in this README might be subject to change based on updates to the Gab platform.

## Usage

1. Clone this repository to your local machine.
2. Install the required packages as mentioned in the "Requirements" section.
3. Modify the script to configure group keywords, links, or account usernames as required.
4. Run the script using the command:
   ```python gab_scraper.py```

Ensure you review and update the script regularly to accommodate any changes in the Gab platform's structure or policies.

## Disclaimer

This script is intended for educational purposes and adheres to the platform's terms of use. Ensure you use it responsibly and respect the website's policies.


