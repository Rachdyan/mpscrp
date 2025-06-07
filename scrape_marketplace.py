from seleniumbase import SB
import pandas as pd
from pydrive2.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv
import os
from gspread_dataframe import get_as_dataframe
import asyncio
import pyotp
from twocaptcha import TwoCaptcha

from utils.fb import search_marketplace
from utils.gsheet_utils import export_to_sheets
from utils.telegram_utils import generate_msg_str, send_telegram_message
from utils.captcha_utils import PageActions, CaptchaHelper

load_dotenv(override=True)

user = os.environ['PROXY_USER']
password = os.environ['PROXY_PASSWORD']
proxy_host = os.environ['PROXY_HOST']
proxy_port = os.environ['PROXY_PORT']

proxy_string = f"{user}:{password}@{proxy_host}:{proxy_port}"

private_key_id = os.environ['SA_PRIVKEY_ID']
sa_client_email = os.environ['SA_CLIENTMAIL']
sa_client_x509_url = os.environ['SA_CLIENT_X509_URL']
private_key = os.environ['SA_PRIVKEY']

private_key = private_key.replace('\\n', '\n')
full_private_key = f"-----BEGIN PRIVATE KEY-----\n"\
    f"{private_key}\n-----END PRIVATE KEY-----\n"

service_account_dict = {
    "type": "service_account",
    "project_id": "keterbukaan-informasi-idx",
    "private_key_id": private_key_id,
    "private_key": full_private_key,
    "client_email": sa_client_email,
    "client_id": "116805150468350492730",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url":
    "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": sa_client_x509_url,
    "universe_domain": "googleapis.com"
}

scope = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

gauth = GoogleAuth()

try:
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        service_account_dict, scope
    )
except Exception as e:
    print(f"Error loading credentials from dictionary: {e}")
    # Handle error appropriately, maybe exit
    exit(1)

creds = gauth.credentials
gc = None
spreadsheet = None
worksheet = None
try:
    gc = gspread.authorize(creds)
    print("Google Sheets client (gspread) initialized successfully.")

    sheet_key = "1eQQIKMGE90A3Yz86zdhFbFV-eCypwquIqP754s1Pjes"
    spreadsheet = gc.open_by_key(sheet_key)

    print(f"Successfully opened spreadsheet: '{spreadsheet.title}'")

except gspread.exceptions.SpreadsheetNotFound:
    print("Error: Spreadsheet not found. \n"
          "1. Check if the name/key/URL is correct.\n")
    # Decide if you want to exit or continue without sheet access
    exit(1)
except gspread.exceptions.APIError as e:
    print(f"Google Sheets API Error: {e}")
    exit(1)
except Exception as e:
    # Catch other potential errors during gspread initialization/opening
    print(f"An error occurred during Google Sheets setup: {e}")
    exit(1)

fb_email = os.environ['FB_USER']
fb_password = os.environ['FB_PASS']
otp_secret = os.environ['OTP_SECRET']
url = "https://web.facebook.com/"

griii_dict = {'name': "ricoh gr iii",
              'min_price': 8000000,
              'max_price': 17000000,
              'keyword_filter': False}

a6400_dict = {'name': "sony a6400",
              'min_price': 3000000,
              'max_price': 8000000,
              'keyword_filter': True}

macbook_pro_m3_dict = {'name': "macbook pro m3",
                       'min_price': 12000000,
                       'max_price': 18000000,
                       'keyword_filter': True}

sony_wf1000xm5 = {'name': "sony wf1000xm5",
                  'min_price': 800000,
                  'max_price': 2000000,
                  'keyword_filter': False}

garmin_forerunner = {'name': "garmin forerunner",
                     'min_price': 500000,
                     'max_price': 1700000,
                     'keyword_filter': False}

kindle_11 = {'name': "kindle 11",
             'min_price': 500000,
             'max_price': 1800000,
             'keyword_filter': False}

size_44 = {'name': 'size "44"',
           'min_price': 500000,
           'max_price': 2000000,
           'keyword_filter': False}

all_product_list = [griii_dict, a6400_dict,
                    macbook_pro_m3_dict, sony_wf1000xm5,
                    garmin_forerunner, kindle_11, size_44
                    ]

if __name__ == "__main__":
    with SB(uc=True,
            # headless=True,
            xvfb=True,
            proxy=proxy_string,
            # incognito=True,
            maximize=True,
            ) as sb:
        print("Opening Home Page")
        sb.driver.uc_open_with_reconnect(url,
                                         reconnect_time=5)
        sb.sleep(2)

        sb.type('[id="email"]', fb_email)
        sb.sleep(1)

        sb.type('[id="pass"]', fb_password)
        sb.sleep(1)

        sb.uc_click('button[name*="login"]')
        sb.sleep(15)

        current_url = sb.driver.current_url
        # current_url

        if "two_step_verification" in current_url \
           and "authentication" in current_url:
            print("ReCAPTCHA Detected")
            captcha_api_key = os.environ['CAPTCHA_KEY']
            solver = TwoCaptcha(captcha_api_key,
                                defaultTimeout=120,
                                recaptchaTimeout=600)
            page_actions = PageActions(sb.driver)
            captcha_helper = CaptchaHelper(sb.driver, solver)

            script_get_data_captcha = captcha_helper\
                .load_js_script('./js_scripts/get_captcha_data.js')
            script_change_tracking = captcha_helper\
                .load_js_script('./js_scripts/track_image_updates.js')

            c_iframe_captcha = "//iframe[@title='reCAPTCHA']"
            c_checkbox_captcha = "//span[@role='checkbox']"
            c_popup_captcha = ("//iframe[contains(@title, 'two minutes') "
                               "or contains(@title, 'dua menit')]")
            c_verify_button = "//button[@id='recaptcha-verify-button']"
            c_try_again = "//div[@class='rc-imageselect-incorrect-response']"
            c_select_more = "//div[@class='rc-imageselect-error-select-more']"
            c_dynamic_more = ("//div[@class='rc-imageselect-error-dynamic-"
                              "more']")
            c_select_something = ("//div[@class='rc-imageselect-error-select-"
                                  "something']")

            p_submit_button_captcha = "//button[@type='submit']"

            sb.switch_to_frame("iframe[id='captcha-recaptcha']")
            sb.sleep(1)
            print("Switching to reCAPTCHA checkbox iframe..")
            sb.switch_to_frame("iframe[title='reCAPTCHA']")
            sb.sleep(1)
            print("Clicking Checkbox..")
            sb.click('div[class*="recaptcha-checkbox-checkmark"]')
            sb.sleep(3)

            sb.switch_to_default_content()
            print("Switching to reCAPTCHA regular iframe..")
            sb.sleep(1)
            sb.switch_to_frame("iframe[id='captcha-recaptcha']")
            print("Switching to Popup Captcha iframe..")
            sb.switch_to_frame(c_popup_captcha)
            sb.sleep(3)

            # Inject JS once
            captcha_helper.execute_js(script_get_data_captcha)
            captcha_helper.execute_js(script_change_tracking)

            id = None  # Initialize the id variable for captcha

            while True:
                # Get captcha data by calling the JS function directly
                captcha_data = sb.execute_script("return getCaptchaData();")

                # Forming parameters for solving captcha
                params = {
                    "method": "base64",
                    "img_type": "recaptcha",
                    "recaptcha": 1,
                    "cols": captcha_data['columns'],
                    "rows": captcha_data['rows'],
                    "textinstructions": captcha_data['comment'],
                    "lang": "en",
                    "can_no_answer": 1
                }

                # If the 3x3 captcha is an id, add previousID to the parameters
                if params['cols'] == 3 and id:
                    params["previousID"] = id

                print("Params before solving captcha:", params)

                # Send captcha for solution
                result = captcha_helper.solver_captcha(
                    file=captcha_data['body'], **params)

                if result is None:
                    print("Captcha solving failed or timed out. "
                          "Stopping the process.")
                    break

                # Check if the captcha was solved successfully
                elif result and 'No_matching_images' not in result['code']:
                    # We save the id only on the first successful iteration for
                    # 3x3 captcha
                    if id is None and params['cols'] == 3 \
                       and result['captchaId']:
                        # Save id for subsequent iterations
                        id = result['captchaId']

                    answer = result['code']
                    number_list = captcha_helper.pars_answer(answer)

                    # Processing for 3x3
                    if params['cols'] == 3:
                        # Click on the answers found
                        page_actions.clicks(number_list)
                        page_actions.click_check_button(c_verify_button)

                        sb.sleep(10)
                        # Check if the images have been updated
                        current_url = sb.driver.current_url
                        if "two_step_verification" in current_url and\
                                "two_factor" in current_url:
                            print("Catpcha is Correct")
                            break
                        else:
                            print("Catpcha is Incorrect")
                            continue
                            # image_update = page_actions.check_for_image_updates() # NOQA

                            # if image_update:
                            #     # If the images have been updated, continue with the saved id  # NOQA
                            #     print(f"Images updated, continuing with previousID: {id}")  # NOQA
                            #     continue  # Continue the loop

                            # Press the check button after clicks
                            # page_actions.click_check_button(c_verify_button)

                    # Processing for 4x4
                    elif params['cols'] == 4:
                        # Click on the answers found and immediately press the
                        # check button
                        page_actions.clicks(number_list)
                        page_actions.click_check_button(c_verify_button)

                        sb.sleep(10)
                        current_url = sb.driver.current_url
                        if "two_step_verification" in current_url and\
                                "two_factor" in current_url:
                            print("Catpcha is Correct")
                            break
                        else:
                            print("Catpcha is Incorrect")
                            # After clicking, we check for errors and image updates  # NOQA
                            # image_update = page_actions.check_for_image_updates()  # NOQA

                            # if image_update:
                            #     print(f"Images updated, continuing without previousID")  # NOQA
                            continue  # Continue the loop

                    # If the images are not updated, check the error messages
                    if captcha_helper.handle_error_messages(
                            c_try_again, c_select_more,
                            c_dynamic_more, c_select_something):
                        continue  # If an error is visible, restart the loop

                    # If there are no errors, send the captcha
                    page_actions.switch_to_default_content()
                    page_actions.click_check_button(p_submit_button_captcha)
                    break  # Exit the loop if the captcha is solved

                elif 'No_matching_images' in result['code']:
                    # If the captcha returned the code "no_matching_images",
                    # check the errors
                    page_actions.click_check_button(c_verify_button)
                    if captcha_helper.handle_error_messages(
                            c_try_again, c_select_more,
                            c_dynamic_more, c_select_something):
                        continue  # Restart the loop if an error is visible
                    else:
                        page_actions.switch_to_default_content()
                        page_actions.click_check_button(
                            p_submit_button_captcha)
                        break  # Exit loop

        #     print("Need to input text captcha")
        #     sb.save_screenshot("captcha.png", selector="img")

        #     captcha_api_key = os.environ['CAPTCHA_KEY']
        #     solver = TwoCaptcha(captcha_api_key)
        #     print("Reading the Captcha...")
        #     try:
        #         result = solver.normal('captcha.png')
        #     except Exception as e:
        #         print("Error reading captcha", e)
        #         exit(e)

        #     else:
        #         print('Captcha: ' + result['code'])

        #     sb.type('input[type="text"]', result['code'])
        #     sb.sleep(2)

        #     sb.click('(//div[@role="button"])[2]')
        #     sb.sleep(10)

        current_url = sb.driver.current_url
        sb.switch_to_default_content()
        sb.switch_to_default_content()

        if "two_step_verification" in current_url and\
           "two_factor" in current_url:
            print("TWO STEP VERIFICATION. Need to Generate OTP")
            sb.sleep(2)
            sb.click('div[role="button"]')
            sb.sleep(2)
            sb.click('input[value="1"]')
            sb.sleep(2)
            sb.click('(//div[@role="button"])[4]')
            sb.sleep(2)
            print("Generating OTP...")
            secret_key = 'CELYRR33TLRKVCXENLKKASQNMZ26HTIW'

            try:
                totp = pyotp.TOTP(secret_key)
            except Exception as e:
                print(f"Error initializing TOTP. Is your secret key a valid "
                      f"Base32 string? {e}")
                exit()

            # Generate the current OTP
            current_otp = totp.now()
            print(f"Current Facebook OTP: {current_otp}")

            sb.type('input[type="text"]', current_otp)
            sb.sleep(2)
            # sb.click('(//div[@role="button"])[1]')
            sb.click('(//div[@role="button"])[2]')
            sb.sleep(10)
            current_url = sb.driver.current_url
            print(current_url)

            if "remember_browser" in current_url:
                print("Clicking home button")
                sb.uc_click('svg')
                sb.sleep(3)
                print("Succesfully Logged in")

        all_result_df = pd.DataFrame()
        for dict in all_product_list:
            current_result_df = search_marketplace(product_dict=dict, sb=sb)
            all_result_df = pd.concat([all_result_df, current_result_df])
        print("Finished scraping all records")

    print("Getting Previously Scraped Data")
    previously_scraped_df_sheet = spreadsheet\
        .worksheet('Facebook')
    previously_scraped_df = get_as_dataframe(
        previously_scraped_df_sheet)

    previously_scraped_df['id'] = pd.to_numeric(
        previously_scraped_df['id'], errors='coerce')\
        .astype('Int64')
    # Then convert to string
    previously_scraped_df['id'] = previously_scraped_df['id']\
        .astype(str)

    all_result_filtered_df = all_result_df[
        ~all_result_df.id.isin(previously_scraped_df.id.tolist())]

    print(f"There are {all_result_filtered_df.shape[0]} new listing")

    async def process_and_send_messages(df):
        """Process DataFrame and send Telegram messages asynchronously"""
        BOT_TOKEN = os.environ['BOT_TOKEN']
        # TARGET_CHAT_ID = "-1001748601116"
        TARGET_CHAT_ID = "1415309056"

        for index, row in df.iterrows():
            try:
                print(f"Processing {row['title']} - {row['link']}...")
                await send_telegram_message(
                    row_series=row,
                    bot_token=BOT_TOKEN,
                    chat_id=TARGET_CHAT_ID
                )
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ Failed for row {index}: {e}")

    async def main2():
        if all_result_filtered_df.shape[0] > 0:
            print("Exporting new records data...")
            export_to_sheets(spreadsheet=spreadsheet, sheet_name='Facebook',
                             df=all_result_filtered_df, mode='a')

            all_result_filtered_df['message_str'] = all_result_filtered_df\
                .apply(generate_msg_str, axis=1)

            await process_and_send_messages(all_result_filtered_df)
            print("Script Finished")
        else:
            print("No New Records")
            print("Script Finished")

    if __name__ == "__main__":
        asyncio.run(main2())
