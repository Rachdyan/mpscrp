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
        sb.sleep(3)

        current_url = sb.driver.current_url
        # current_url

        if "two_step_verification" in current_url \
           and "authentication" in current_url:
            print("Need to input text captcha")
            sb.save_screenshot("captcha.png", selector="img")

            captcha_api_key = os.environ['CAPTCHA_KEY']
            solver = TwoCaptcha(captcha_api_key)
            print("Reading the Captcha...")
            try:
                result = solver.normal('captcha.png')
            except Exception as e:
                print("Error reading captcha", e)
                exit(e)

            else:
                print('Captcha: ' + result['code'])

            sb.type('input[type="text"]', result['code'])
            sb.sleep(2)

            sb.click('(//div[@role="button"])[2]')
            sb.sleep(10)

        current_url = sb.driver.current_url

        if "two_step_verification" in current_url and\
           "two_factor" in current_url:
            print("TWO STEP VERIFICATION. Need to Generate OTP")
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
