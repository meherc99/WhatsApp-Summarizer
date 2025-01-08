# from bs4 import BeautifulSoup
from time import sleep
import os
from dotenv import load_dotenv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException


# from selectors import XPATH_SELECTORS

def main():
    # Setup selenium to use Chrome browser w/ profile options
    driver = setup_selenium()
    
    # Load WhatsApp
    if not whatsapp_is_loaded(driver):
        print("Task quit.")
        driver.quit()
        return

    # Get chats
    chats = get_chats(driver)

    # Print chat summary
    # print_chats(chats)

    # Prompt user to select a chat for export, then locate and load it in WhatsApp
    finished = False
    while not finished:
        chat_is_loaded = False
        while not chat_is_loaded:
            # Select a chat and locate in WhatsApp
            chat_is_loadable = False
            while not chat_is_loadable:
                # Ask user what chat to export
                selected_chat = select_chat(chats)
                if not selected_chat:
                    print("You've quit WhatSoup.")
                    driver.quit()
                    return

                # Find the selected chat in WhatsApp
                found_selected_chat = find_selected_chat(driver, selected_chat)
                if found_selected_chat:
                    # Break and proceed to load/scrape the chat
                    chat_is_loadable = True
                else:
                    # Clear chat search
                    driver.find_element_by_xpath(
                        '//*[@id="side"]/div[1]/div/span/button').click()

            # Load entire chat history
            chat_is_loaded = load_selected_chat(driver)

        # Scrape the chat history
        scraped = scrape_chat(driver)

        # Export the chat
        scrape_is_exported(selected_chat, scraped)

        # Ask user if they wish to finish and exit WhatSoup
        finished = user_is_finished()

    # Quit WhatSoup
    print("You've quit WhatSoup.")
    driver.quit()
    return


def setup_selenium(browser='firefox'):
    '''Setup Selenium to use webdriver'''

    # Load driver and chrome profile from local directories
    load_dotenv()
    if browser == 'chrome':
        CHROME_BINARY_PATH = os.getenv('CHROME_BINARY_PATH') 
        CHROME_PROFILE = os.getenv('CHROME_PROFILE')
        options.add_argument(f"user-data-dir={CHROME_PROFILE}")
        options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(
        executable_path=CHROME_BINARY_PATH, options=options)
    elif browser == 'firefox':
        # FIREFOX_BINARY_PATH = '/usr/local/bin/geckodriver'
        # FIREFOX_PROFILE = '/home/meher-changlani/snap/firefox/common/.mozilla/firefox/n8nrc8s0.default '
        FIREFOX_BINARY_PATH = os.getenv('FIREFOX_BINARY_PATH')
        FIREFOX_PROFILE = os.getenv('FIREFOX_PROFILE')
       
        options = webdriver.FirefoxOptions()
        options.profile = webdriver.FirefoxProfile(FIREFOX_PROFILE)  
        options.binary_location = FIREFOX_BINARY_PATH
        driver = webdriver.Firefox(options=options)

    # Change default script timeout from 30sec to 90sec for execute_script tasks which slow down significantly in very large chats
    driver.set_script_timeout(90)

    return driver


def whatsapp_is_loaded(driver):
    '''Attempts to load WhatsApp in the browser'''

    print("Loading WhatsApp...", end="\r")

    # Open WhatsApp
    driver.get('https://web.whatsapp.com/')

    # Check if user is already logged in
    logged_in, wait_time = False, 20
    while not logged_in:

        # Try logging in
        logged_in = user_is_logged_in(driver, wait_time)

        # Allow user to try again and extend the wait time for WhatsApp to load
        if not logged_in:
            # Display error to user
            print(
                f"Error: WhatsApp did not load within {wait_time} seconds. Make sure you are logged in and let's try again.")

            is_valid_response = False
            while not is_valid_response:
                # Ask user if they want to try loading WhatsApp again
                err_response = input("Proceed (y/n)? ")

                # Try again
                if err_response.strip().lower() in {'y', 'yes'}:
                    is_valid_response = True
                    continue
                # Abort loading WhatsApp
                elif err_response.strip().lower() in {'n', 'no'}:
                    is_valid_response = True
                    return False
                # Re-prompt the question
                else:
                    is_valid_response = False
                    continue

    # Success
    print("Success! WhatsApp finished loading and is ready.")
    return True


def user_is_logged_in(driver, wait_time):
    '''Checks if the user is logged in to WhatsApp by looking for the pressence of the chat-pane'''

    try:
        chat_pane = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.ID, 'pane-side')))
        return True
    except TimeoutException:
        return False
    
    
def scrape_chat(driver, group_name, num_msgs=5):
    '''Turns the chat into soup and scrapes it for key export information: message sender, message date/time, message contents'''

    wait = WebDriverWait(driver, timeout=10)
    
    print("Scraping messages...", end="\r")

    driver.find_element(By.XPATH, f"//div[contains(@aria-label,'Chat list')]//div[contains(@role,'listitem') and descendant::span[contains(text(),'{group_name}')]]").click()
    try:
        unread_messages = int(wait.until(EC.presence_of_element_located((By.XPATH, f"//div[contains(@aria-label,'Chat list')]//div[contains(@role,'listitem') and descendant::span[contains(text(),'{group_name}')]]//span[contains(@aria-label,'unread message')]"))).text)
    except:
        unread_messages = 0
        
    # message_plane = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@role,'application')]")))
    
    num_messages_visible=0
    num_msgs_to_scrape = max(num_msgs, unread_messages)

    while num_messages_visible<num_msgs_to_scrape:
        message_elems = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'message-in')]")))
        num_messages_visible = len(message_elems)
        driver.execute_script("arguments[0].scrollIntoView(true);", message_elems[0])
        sleep(1)
        # print(num_messages_visible)
  
    messages = parse_messages(message_elems)
    
    print("Scraping Complete!") 
    print(f"Messages scraped {len(message_elems)}")
    print(f"Messages parsed {len(messages)}")
    
    return messages


def parse_messages(message_elems):
    messages = []
    for message in message_elems:
        try:
            copyable_scrape={'message': None, 'sender': None, 'datetime': None, 'recalled_msg': False, 'has_images': False}
            msg_text = message.find_elements(By.XPATH, ".//span[contains(@class, 'selectable-text')]")
            if msg_text:
                copyable_scrape['message'] = msg_text[0].text
            
                temp = message.find_element(By.XPATH, ".//div[contains(@class, 'copyable-text')]").get_attribute('data-pre-plain-text').strip()[1:-1].split('] ')
                copyable_scrape['sender'] = temp[1]
                copyable_scrape['datetime'] = temp[0]
            
            if message.find_elements(By.XPATH, ".//span[contains(@class, 'quoted-mention')]"):
                copyable_scrape['recalled_msg'] = True
                
            imgs = message.find_elements(By.XPATH, ".//div[contains(@aria-label, 'Open picture')]")
            if imgs:
                copyable_scrape['has_images'] = True
                # imgs[0].find_element(By.XPATH, ".//img").get_attribute('src')
            messages.append(copyable_scrape)
        except:
            continue
    
    return messages
