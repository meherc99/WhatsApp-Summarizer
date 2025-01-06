# from bs4 import BeautifulSoup
from time import sleep
import os
from dotenv import load_dotenv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException


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
            expected_conditions.presence_of_element_located((By.ID, 'pane-side')))
        return True
    except TimeoutException:
        return False
    
    

def get_chats(driver):
    '''Traverses the WhatsApp chat-pane via keyboard input and collects chat information such as person/group name, last chat time and msg'''

    print("Loading your chats...", end="\r")

    # Wrap entire function in a retryable try/catch because chat-pane DOM changes frequently due to users typing, sending messages, and occasional WhatsApp notifications
    retry_attempts = 0
    while retry_attempts < 3:
        retry_attempts += 1

        # Try traversing the chat-pane
        try:
            # Find the chat search (xpath == 'Search or start new chat' element)
            chat_search = driver.find_element_by_xpath(
                '//*[@id="side"]/div[1]/div/label/div/div[2]')
            chat_search.click()

            # Count how many chat records there are below the search input by using keyboard navigation because HTML is dynamically changed depending on viewport and location in DOM
            selected_chat = driver.switch_to.active_element
            prev_chat_id = None
            is_last_chat = False
            chats = []

            # Descend through the chats
            while True:
                # Navigate to next chat
                selected_chat.send_keys(Keys.DOWN)

                # Set active element to new chat (without this we can't access the elements '.text' value used below for name/time/msg)
                selected_chat = driver.switch_to.active_element

                # Check if we are on the last chat by comparing current to previous chat
                if selected_chat.id == prev_chat_id:
                    is_last_chat = True
                else:
                    prev_chat_id = selected_chat.id

                # Gather chat info (chat name, chat time, and last chat message)
                if is_last_chat:
                    break
                else:
                    # Get the container of the contact card's title (xpath == parent div container to the span w/ title attribute set to chat name)
                    contact_title_container = selected_chat.find_element_by_xpath(
                        "./div/div[2]/div/div[1]")
                    # Then get all the spans it contains
                    contact_title_container_spans = contact_title_container.find_elements_by_tag_name(
                        'span')
                    # Then loop through all those until we find one w/ a title property
                    for span_title in contact_title_container_spans:
                        if span_title.get_property('title'):
                            name_of_chat = span_title.get_property('title')
                            break

                    # Get the time (xpath == div element that holds last chat time e.g. 'Wednesday' or '1/1/2021')
                    last_chat_time = selected_chat.find_element_by_xpath(
                        "./div/div[2]/div/div[2]").text

                    # Get the last message (xpath == div element that holds a span w/ title attribute set to last chat message)
                    last_chat_msg_element = selected_chat.find_element_by_xpath(
                        "./div/div[2]/div[2]/div")
                    last_chat_msg = last_chat_msg_element.find_element_by_tag_name(
                        'span').get_attribute('title')

                    # Strip last message of left-to-right directional encoding ('\u202a' and '\u202c') if it exists
                    if '\u202a' in last_chat_msg or '\u202c' in last_chat_msg:
                        last_chat_msg = last_chat_msg.lstrip(
                            u'\u202a')
                        last_chat_msg = last_chat_msg.rstrip(
                            u'\u202c')

                    # Check if last message is a group chat and if so prefix the senders name to the message
                    last_chat_msg_sender = last_chat_msg_element.find_element_by_tag_name(
                        'span').text
                    if '\n: \n' in last_chat_msg_sender:
                        # Group have multiple spans to separate sender, colon, and msg contents e.g. '<sender>: <msg>', so we take the first item after splitting to capture the senders name
                        last_chat_msg_sender = last_chat_msg_sender.split('\n')[
                            0]

                        # Prefix the message w/ senders name
                        last_chat_msg = f"{last_chat_msg_sender}: {last_chat_msg}"

                    # Store chat info within a dict
                    chat = {"name": name_of_chat,
                            "time": last_chat_time, "message": last_chat_msg}
                    chats.append(chat)

            # Navigate back to the top of the chat list
            chat_search.click()
            chat_search.send_keys(Keys.DOWN)

            print("Success! Your chats have been loaded.")
            break

        # Catch errors related to DOM changes
        except (StaleElementReferenceException, ElementNotInteractableException) as e:
            if retry_attempts == 3:
                # Make sure we grant user option to exit if DOM keeps changing while scanning chat list
                print("This is taking longer than usual...")
                while True:
                    response = input(
                        "Try loading chats again (y/n)? ")
                    if response.strip().lower() in {'n', 'no'}:
                        print(
                            'Error! Aborting chat load by user due to frequent DOM changes.')
                        if type(e).__name__ == 'StaleElementReferenceException':
                            raise StaleElementReferenceException
                        else:
                            raise ElementNotInteractableException
                    elif response.strip().lower() in {'y', 'yes'}:
                        retry_attempts = 0
                        break
                    else:
                        continue
            else:
                pass

    return chats
