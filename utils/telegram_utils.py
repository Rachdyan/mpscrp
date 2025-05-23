import telegram
import pandas as pd


def generate_msg_str(row):
    msg_str = f"<a href = '{row['link']}'>{row['title']}</a>"
    msg_str += '\n\n'
    msg_str += f"<b>Price</b>: {row['price']}"
    msg_str += '\n'
    msg_str += f"<b>Location</b>: {row['location']}"
    msg_str += '\n\n'
    msg_str += f"<b>Ori Keyword</b>: {row['original_keyword']}"
    return msg_str


async def send_telegram_message(row_series: pd.Series, bot_token: str,
                                chat_id: str):
    bot = telegram.Bot(token=bot_token)
    message = row_series['message_str']

    try:
        # Use await for async call and constants.ParseMode for v20+
        sent_message = await bot.send_message(chat_id=chat_id, text=message,
                                              parse_mode='html')
        send_status_id = sent_message.message_id
        print(send_status_id)
    except Exception as e:
        print(f"Error sending message for"
              f"{row_series.get('title', 'N/A')} - "
              f"{row_series.get('link', 'N/A')}\nError: {e}")
        # send_status_id remains None
