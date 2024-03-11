from dotenv import load_dotenv
from pyrogram import Client, filters
from kucoin.client import Market, Trade
from pyrogram.types import Message
import os
import time
import re
from datetime import datetime

load_dotenv()

TELEGRAM_API_ID = os.getenv('TELEGRAM_APP_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
CHANNEL_NAMES = os.getenv("CHANNEL_NAMES").split(",")
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET")
KUCOIN_PASSPHRASE = os.getenv("KUCOIN_PASSPHRASE")
TAKE_PROFIT = float(os.getenv("TAKE_PROFIT"))
FUNDS = os.getenv("FUNDS")


app = Client("my_session", api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)

ku_client = Market(
        key=KUCOIN_API_KEY,
        url='https://api.kucoin.com',
        secret=KUCOIN_API_SECRET,
        passphrase=KUCOIN_PASSPHRASE)

ku_trade = Trade(
        key=KUCOIN_API_KEY,
        url='https://api.kucoin.com',
        secret=KUCOIN_API_SECRET,
        passphrase=KUCOIN_PASSPHRASE)

symbol_list = ku_client.get_symbol_list_v2()

def get_increment_values(target_symbol):
     """Get coin increment values"""

     for symbol in symbol_list:
        if symbol['symbol'] == target_symbol:
            return {
                'baseIncrement': symbol['baseIncrement'],
                'quoteIncrement': symbol['quoteIncrement'],
                'priceIncrement': symbol['priceIncrement']
            }


def adjust_to_increment(value, increment):
    """
    Adjusts a value to be a multiple of the increment.

    :param value: The original value to be adjusted.
    :param increment: The increment that the value must be a multiple of.
    :return: The adjusted value.
    """
    parts = len(str(increment).split('.')[1])    
    return format(value, f".{parts}f")
    

def make_orders(coin_name: str):
    now = datetime.now()
    print(f'buying {coin_name} at {now.strftime("%Y-%m-%d %H:%M:%S")}')
    increment_values = get_increment_values(f"{coin_name}-USDT")

    order_id = ku_trade.create_market_order(
            symbol=f"{coin_name}-USDT",
            side="buy",
            funds=FUNDS
            )['orderId']
    now = datetime.now()

    print(f"Bought {coin_name} at {now.strftime('%Y-%m-%d %H:%M:%S')}, ORDER_ID is {order_id}")

    time.sleep(0.5)
    buy_order_details = ku_trade.get_order_details(order_id)
    executed_amount = float(buy_order_details['dealSize'])
    if not executed_amount:
        print("Order was not completed")
        return
    total_funds = float(buy_order_details['dealFunds'])
    average_buy_price = total_funds / executed_amount if executed_amount else 0
    sell_price = average_buy_price * TAKE_PROFIT
    adjusted_sell_price = adjust_to_increment(sell_price, increment_values['priceIncrement'])
    adjusted_executed_amount = adjust_to_increment(executed_amount, increment_values['baseIncrement'])
    now = datetime.now()
    print(f"Bought coins for {average_buy_price}")
    sell_order_id = ku_trade.create_limit_order(symbol=f"{coin_name}-USDT", side="sell", price=adjusted_sell_price, size=adjusted_executed_amount)
    now = datetime.now()
    print(
        f"Created sell order for  coin {coin_name} price {average_buy_price} at {now.strftime('%Y-%m-%d %H:%M:%S')} with Order id {sell_order_id}")


def main():
    print("started")
    chats = []
    with app:
        dialogs = app.get_dialogs()
        chats = []
        for dialog in dialogs:
            if dialog.chat.title in CHANNEL_NAMES:
                chats.append(dialog.chat.id)


    @app.on_message(filters=filters.chat(chats))
    def handle_message(client, message: Message):
        now = datetime.now()
        print(now.strftime("%Y-%m-%d %H:%M:%S"), message.text)
        match = re.search(r'The coin we (?:are pumping|have picked to pump) today is ?: (\w+)', message.text)
        if match:
            coin_name = match.group(1)
            print(f"Buying coin: {coin_name}")
            make_orders(coin_name)


app.run(main())
