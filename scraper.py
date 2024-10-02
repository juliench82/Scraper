import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
import telegram_send

# Load environment variables from .env file
load_dotenv()

# Get variables from .env
chrome_driver_path = os.getenv("CHROME_DRIVER_PATH")
user_data_dir = os.getenv("USER_DATA_DIR")
url = os.getenv("URL")
csv_path = os.getenv("CSV_PATH")
bot_token = os.getenv("BOT_TOKEN")
chat_id = os.getenv("CHAT_ID")

# Setup Selenium WebDriver (Chrome)
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
chrome_options.add_argument("--headless")

driver = webdriver.Chrome(executable_path=chrome_driver_path, options=chrome_options)

# Open the URL
driver.get(url)
driver.implicitly_wait(10)

# Close any modal that might appear
try:
    close_button = driver.find_element_by_css_selector('.modal-content button.close')
    close_button.click()
    driver.implicitly_wait(3)
except:
    pass

# Read CSV file
data = pd.read_csv(csv_path)

# Extract words starting with '$' and process them
dollar_words_map = {}
for tweet in data['tweetText']:
    words = tweet.split()
    for word in words:
        if word.startswith('$') and len(word) > 2 and word[1:].isalpha():
            cleaned_word = word[:6].lower().strip('.,?!;')
            if cleaned_word:
                if cleaned_word in dollar_words_map:
                    dollar_words_map[cleaned_word] += 1
                else:
                    dollar_words_map[cleaned_word] = 1

# Sort entries by count in descending order
sorted_entries = sorted(dollar_words_map.items(), key=lambda x: x[1], reverse=True)

# Prepare the message
message = "Most mentioned tokens by the top performing CT influencers in the past 24 hours (sorted by count):\n\n"
for word, count in sorted_entries:
    message += f"{word}: {count}\n"

# Send the message to the Telegram bot
telegram_send.send(messages=[message])

# Search for each word on the webpage
for word, count in sorted_entries:
    if count > 2:
        # Focus on the search input and type the word
        search_input = driver.find_element_by_css_selector('.overlay-search input')
        search_input.clear()
        search_input.send_keys(word)
        search_input.send_keys(Keys.RETURN)
        driver.implicitly_wait(5)
        
        # Get the page source and parse with BeautifulSoup
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Extract relevant information from the search results (example: token names and prices)
        results = soup.select('.token-container .token-item')  # Update the selector based on actual page structure
        search_results = []
        for result in results:
            token_name = result.select_one('.token-name').text.strip()
            token_price = result.select_one('.token-price').text.strip()
            search_results.append(f"{token_name}: {token_price}")

        # Prepare the detailed message
        detailed_message = f"Search results for {word}:\n"
        detailed_message += "\n".join(search_results)
        
        # Send the detailed message to the Telegram bot
        telegram_send.send(messages=[detailed_message])

# Close the browser
driver.quit()
