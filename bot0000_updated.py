import time
import logging
import json
import asyncio
import websockets
from binance import ThreadedWebsocketManager
from binance.client import AsyncClient, Client
from binance.streams import BinanceSocketManager
from decimal import Decimal
import traceback
import ccxt.async_support as ccxt
import aiohttp
from datetime import datetime, timezone




# Configure logging 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
   asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def get_readable_time(timestamp=None):
    if timestamp:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

readable_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # تنسيق الوقت القابل للقراءة
print(readable_time)


# إعدادات الحساب التجريبي أو الحقيقي
api_key = 'qUyT24eo68CdF8oyVPPwEtXKIITO8JkzDJHqfyklciTt5o1dbJWqxvtbEeAKbJjz'
api_secret = 'rJDZ13qDNopf3a0gmvqutwJDCN8i7GUMYIl3w3EKJX3z5T9Dw4DqOhuP4C0y4IiU'
testnet = True  # تعيين True للحساب التجريبي أو False للحساب الحقيقي

# الاتصال بواجهة Binance Testnet Spot مع تمكين مزامنة الوقت
try:
    if testnet:
        binance = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True  # تمكين مزامنة الوقت التلقائية
            },
            'urls': {
                'api': {
                    'public': 'https://testnet.binance.vision',  # عنوان API للحساب التجريبي
                    'private': 'https://testnet.binance.vision'  # عنوان API الخاص بالحساب التجريبي
                }
            }
        })
    if testnet:
        binance.set_sandbox_mode(True)
        
except ccxt.BaseError as e:
    print(f"CCTX Error: {e}")


symbol = input("Enter the trading pair symbol: ")
print("The entered trading symbol is:", symbol)





async def handle_trade_stream(symbol):
    uri = f"wss://testnet.binance.vision/ws/{symbol.lower()}@trade"

    while True:  # إعادة المحاولة بشكل دائم عند انقطاع الاتصال
        try:
            async with websockets.connect(uri, ping_interval=None) as websocket:
                logging.info(f"Connected to WebSocket for {symbol}.")
                current_millisecond = None
                open_price = None
                close_price = None
                last_candle_color = None  # لتعقب لون الشمعة الأخير

                while True:
                    try:
                        # استقبال البيانات
                        response = await websocket.recv()
                        data = json.loads(response)

                        # استخراج البيانات المهمة
                        trade_price = Decimal(data['p'])
                        trade_time = int(data['T'])  # الوقت بالمللي ثانية

                        # تحديث بيانات الشمعة اللحظية
                        if current_millisecond is None:
                            current_millisecond = trade_time
                            open_price = trade_price

                        if trade_time == current_millisecond:
                            close_price = trade_price
                        else:
                            # إنهاء الشمعة السابقة
                            candle_color = "Green" if close_price >= open_price else "Red"

                            # عرض اللون مرة واحدة فقط عند التغير
                            if candle_color != last_candle_color:
                                timestamp = await get_readable_time(current_millisecond / 1000)
                                total_balance = trade_manager.total_balance
                                profit_or_loss = total_balance - trade_manager.initial_balance
                                print(f"Millisecond: {current_millisecond}, Open: {open_price}, Close: {close_price}, Color: {candle_color}")
                                last_candle_color = candle_color  # تحديث اللون الأخير

                                # اتخاذ القرار بناءً على لون الشمعة
                                if candle_color == "Green":
                                    await execute_buy_order(symbol, close_price)

                                elif candle_color == "Red":
                                    await execute_sell_order(symbol, close_price)

                            # بدء شمعة جديدة
                            current_millisecond = trade_time
                            open_price = trade_price
                            close_price = trade_price
                    except websockets.exceptions.ConnectionClosed as e:
                        logging.error(f"Connection closed for {symbol}: {e}")
                        break
        except Exception as e:
            logging.error(f"Error during WebSocket connection for {symbol}: {e}")
            await asyncio.sleep(5)  # انتظار قبل إعادة المحاولة



# نموذج حالة التداول
class TradeManager:
    def __init__(self, initial_balance):
        self.has_open_trade = False
        self.buy_price = None
        self.sell_price = None
        self.recently_sold = False
        self.profit_or_loss = Decimal('0.0')
        self.previous_price = None
        self.current_price = Decimal('0.0')
        self.previous_candle_color = None
        self.candle_color = None
        self.first_run = True        
        self.buy_price = Decimal('0.0')
        self.previous_price = Decimal('0.0')
        self.current_price = Decimal('0.0')
        self.coin = None  # To store the coin being traded
        self.open_price = Decimal('0.0')  # Open price of the current candle
        self.close_price = Decimal('0.0')  # Close price of the current candle
        self.candle_time = None  # Time of the current candle
        self.initial_balance = Decimal(initial_balance)
        self.total_balance = Decimal(initial_balance)  # Initialize total_balance with initial_balance
       



    def update_after_buy(self, buy_price, coin, open_price, close_price, candle_time):
        self.has_open_trade = True
        self.buy_price = buy_price
        self.coin = coin
        self.open_price = open_price
        self.close_price = close_price
        self.candle_time = candle_time

        
    def update_after_sell(self, sell_price, coin, open_price, close_price, candle_time):
        self.has_open_trade = False
        self.sell_price = sell_price
        self.coin = coin
        self.open_price = open_price
        self.close_price = close_price
        self.candle_time = candle_time
       
        # حساب المكسب أو الخسارة
        self.profit_or_loss = self.total_balance - self.initial_balance
    
        # تحديث الرصيد الإجمالي بعد البيع بناءً على المكسب أو الخسارة
        self.total_balance += self.profit_or_loss

          

    def reset_trade_status(self):
        self.has_open_trade = False
        self.buy_price = None
        self.sell_price = None
        self.recently_sold = False

                      
# طباعة ملخص الصفقة
def display_trade_status(action, candle_color, symbol, open_price, close_price=None, profit_or_loss=None, initial_balance=None, total_balance=None, timestamp=None):
    print("\n--- Trade Summary ---")    
    print(f"Timestamp: {timestamp}")  # توقيت الصفقة
    print(f"Symbol: {symbol}")  # نوع العملة
    print(f"Candle Color: {candle_color}")  # لون الشمعة
    print(f"Action: {action}")  # حالة الصفقة (شراء/بيع)
    print(f"Open Price: {open_price:.2f} USDT")  # السعر المفتوح
    
    if close_price is not None:
        print(f"Close Price: {close_price:.2f} USDT")  # السعر المغلق إذا وجد

    if profit_or_loss is not None:
       print(f"Profit/Loss: {profit_or_loss:.2f} USDT")  # الربح أو الخسارة إذا حسبت


    if initial_balance is not None:
        print(f"Initial Balance: {initial_balance:.2f} USDT")  # الرصيد الابتدائي

    if total_balance is not None:
        print(f"Total Balance: {total_balance:.2f} USDT")  # إجمالي الرصيد
        print("----------------------------------------")

    

# إدخال الرصيد الابتدائي كـ Decimal
initial_balance = Decimal(input("Enter the initial balance: "))

# تهيئة كائن TradeManager
trade_manager = TradeManager(initial_balance)




# دالة غير متزامنة لتنفيذ عملية الشراء
async def execute_buy_order(symbol, buy_price):
    candle_color = "Green"    
    if not trade_manager.has_open_trade:  # التحقق من عدم وجود صفقة مفتوحة
        coin = symbol
        open_price = trade_manager.open_price
        close_price = trade_manager.current_price
        candle_time = await get_readable_time()  # جلب الوقت الحالي
       # تحديث حالة الصفقة بعد الشراء
        trade_manager.update_after_buy(buy_price, coin, open_price, close_price, candle_time)
         

      
        display_trade_status(
            action="BUY",
            candle_color=candle_color,
            symbol=symbol,
            open_price=trade_manager.buy_price,
            close_price=None,  # ليس هناك سعر إغلاق عند الشراء
            profit_or_loss=None,
            initial_balance=trade_manager.initial_balance,
            total_balance=trade_manager.total_balance,
            timestamp=candle_time
        )

    else:
        print("Buy order ignored: An open trade already exists.")




# دالة غير متزامنة لتنفيذ عملية البيع
async def execute_sell_order(symbol, sell_price):
    candle_color = "Red"           
    if trade_manager.has_open_trade:  # التحقق من وجود صفقة مفتوحة
       coin = symbol
       open_price = trade_manager.open_price
       close_price = trade_manager.current_price
       candle_time = await get_readable_time()  # جلب الوقت الحالي
       # تحديث حالة الصفقة بعد البيع
       trade_manager.update_after_sell(sell_price, coin, open_price, close_price, candle_time)

       
      # حساب المكسب أو الخسارة بناءً على الرصيد الإجمالي
       profit_or_loss = trade_manager.total_balance - trade_manager.initial_balance

      # تحديث الرصيد الإجمالي بعد البيع بناءً على المكسب أو الخسارة
       trade_manager.total_balance += profit_or_loss


    
        
        trade_manager.update_after_sell(sell_price)
        print(f"SELL Order placed for {symbol} at {sell_price}. Current Balance: {trade_manager.total_balance}")
            
    else:
        print("Sell order ignored: No open trade exists.")



# تعريف الدالة fetch_ticker_data
async def fetch_ticker_data(symbol):
    try:
        # افتراض أن binance هو كائن تم تهيئته من ccxt.async_support
        response = await binance.fetch_ticker(symbol)
        print("Ticker Data:", response)
        
        # تحويل القيم الأساسية إلى Decimal
        last_price = Decimal(response['last'])
        high_price = Decimal(response['high'])
        low_price = Decimal(response['low'])
        open_price = Decimal(response['open'])
        volume = Decimal(response['quoteVolume'])
        
        print("The entered trading symbol is:", symbol)
        
        print("Ticker Data:")
        print(f"Last Price: {last_price}")
        print(f"High Price: {high_price}")
        print(f"Low Price: {low_price}")
        print(f"Open Price: {open_price}")
        print(f"Volume: {volume}")
        
        return {
            "last_price": last_price,
            "high_price": high_price,
            "low_price": low_price,
            "open_price": open_price,
            "volume": volume
        }
        
    except Exception as e:
        logging.error(f"Error fetching ticker data for {symbol}: {e}")
        return None

# التحقق من توفر السيولة قبل التداول
async def check_balance(symbol, retries=3):
    for attempt in range(retries):
        try:
            # استخدام await للحصول على البيانات بشكل غير متزامن
            balance = await binance.fetch_balance()
            asset = symbol.split('/')[0]  # الرمز الأساسي مثل STORJ
            usdt_balance = Decimal(balance['total'].get('USDT', 0))
            asset_balance = Decimal(balance['total'].get(asset, 0))
            storj_balance = Decimal(balance['total'].get('STORJ', 0))

            # إرجاع النتائج
            logging.info(f"USDT Balance: {usdt_balance}, Asset Balance ({asset}): {asset_balance}")
            if usdt_balance < 0 or asset_balance < 0:
                raise ValueError("Invalid balance value.")
            return usdt_balance, storj_balance

        except Exception as e:
            logging.error(f"Error fetching balance (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)  # استخدام asyncio.sleep بدلاً من time.sleep
            else:
                return 0, 0
            

# دالة البيع بشكل غير متزامن
async def sell(symbol, amount, buy_price):
    global current_balance
    try:
        ticker = await binance.fetch_ticker(symbol)
        sell_price = ticker['last']  # تحديد سعر البيع الحالي

        # تنفيذ أمر البيع
        order = await binance.create_market_sell_order(symbol, amount)
        print(f"Sell order executed: {order}")
        # إغلاق الصفقة بعد تنفيذ أمر البيع
        # طباعة ملخص الصفقة
        print_trade_summary(total_balance_before_sell, total_balance_after_sell, sell_price, buy_price, amount)

    except Exception as e:
        print(f"Error executing sell order: {e}")


async def handle_tick_data(symbol, data):
    """
    معالجة بيانات التداول اللحظية
    """
    try:
        trade_id = data['a']
        price = Decimal(data['p'])
        quantity = Decimal(data['q'])
        event_time = data['T']

        print(f"Trade ID: {trade_id}, Price: {price}, Quantity: {quantity}, Time: {event_time}")

        # يمكنك إضافة استراتيجيتك هنا بناءً على البيانات اللحظية
    except Exception as e:
        logging.error(f"Error handling tick data: {e}")


async def sync_time(fetch_server_time, retries=5, acceptable_difference=1):
    """
    مزامنة الوقت مع خادم خارجي حتى يكون الفارق الزمني مقبولاً.

    Args:
        fetch_server_time: دالة لجلب الوقت من الخادم (يجب أن تكون قابلة للاستدعاء باستخدام await).
        retries: عدد المحاولات.
        acceptable_difference: الحد الأقصى للفارق المسموح به بين الوقت المحلي ووقت الخادم (بالثواني).

    Returns:
        الفارق الزمني بين الوقت المحلي والخادم أو None إذا فشلت المزامنة.
    """
    for attempt in range(retries):
        try:
            # جلب الوقت من الخادم
            server_time = await fetch_server_time()
            server_timestamp = int(server_time)
            local_timestamp = int(time.time())

            # حساب الفارق الزمني
            time_difference = server_timestamp - local_timestamp
            logging.info(f"Time difference: {time_difference} seconds")

            # التحقق من أن الفرق الزمني مقبول
            if -acceptable_difference <= abs(time_difference) <= acceptable_difference:
                logging.info(f"Time synchronized successfully with acceptable difference: {time_difference} seconds.")
                return time_difference
            else:
                logging.warning(f"Time difference ({time_difference} seconds) exceeds acceptable limit. Retrying...")

        except Exception as e:
            logging.error(f"Error syncing time (attempt {attempt + 1}/{retries}): {e}")

        # تأخير بين المحاولات
        await asyncio.sleep(2 ** attempt)

    # في حالة فشل المزامنة بعد المحاولات
    logging.error("Failed to sync time after multiple attempts.")
    return None


async def fetch_server_time():
    # جلب الوقت من خادم Binance API
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.binance.com/api/v3/time") as response:
            data = await response.json()
            return data['serverTime'] // 1000  # تحويل من ميلي ثانية إلى ثانية


# دالة رئيسية
async def main():
    retry_count = 3
    for attempt in range(retry_count):
        try:
            # مزامنة الوقت مع خادم Binance
            time_diff = await sync_time(fetch_server_time)
            if time_diff is None:
                logging.error("Time synchronization failed. Exiting.")
                return  # الخروج إذا لم تنجح مزامنة الوقت

            logging.info(f"Time synchronized successfully: {time_diff} seconds difference.")

            # بدء WebSocket لمعالجة البيانات اللحظية
            await handle_trade_stream(symbol)  # تمرير الرمز للعملة
            break  # الخروج عند النجاح
        except asyncio.TimeoutError:
            logging.warning(f"Attempt {attempt + 1}: WebSocket connection timeout. Retrying...")
        except Exception as e:
            logging.error(f"Attempt {attempt + 1}: WebSocket connection failed: {e}")
        finally:
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt  # الفاصل الزمني المتزايد (2, 4, 8 ثوانٍ)
                logging.info(f"Retrying connection after {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logging.error("WebSocket connection failed after multiple attempts. Exiting.")

if __name__ == "__main__":
    asyncio.run(main())


RECEIVE_TIMEOUT = None 
# دالة لجلب بيانات السعر اللحظي باستخدام WebSocket
async def get_realtime_price(symbol):
    global previous_price, has_open_trade
    uri = f"wss://testnet.binance.vision/ws/{symbol.lower()}@trade"  # WebSocket لبيانات السعر اللحظي
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                # تلقي الرسالة مع ضبط المهلة الزمنية
                response = await asyncio.wait_for(websocket.recv(), timeout=RECEIVE_TIMEOUT)
                data = json.loads(response)

                # جلب السعر اللحظي (سعر التداول الحالي)
                current_price = Decimal(data['p'])

                # إذا كان لدينا سعر سابق
                if previous_price is not None:
                    # نقارن السعر الحالي بالسعر السابق
                    if current_price < previous_price and has_open_trade:
                        print(f"Price dropped from {previous_price} to {current_price}, executing sell order...")
                        amount = Decimal('10')  # مثال على الكمية المطلوبة للبيع
                        await execute_sell_order(symbol, sell_price=current_price, amount=amount)
                        has_open_trade = False  # تحديث حالة الصفقة لتكون مغلقة
                        previous_price = current_price  # تحديث السعر السابق بعد التنفيذ
                        return  # إنهاء الدالة بعد تنفيذ الصفقة

                # تحديث `previous_price` إلى `current_price`
                previous_price = current_price

                # طباعة السعر اللحظي
                print(f"Current Price: {current_price}")

            except asyncio.TimeoutError:
                print("Timeout error: WebSocket response took too long. Retrying connection...")
                break  # الخروج من الحلقة في حالة المهلة


# التحقق من أن جميع القيم تم استخراجها بنجاح
def process_data(timestamp, symbol):
    if timestamp is None or symbol is None:
        logging.error("Missing critical data in message (timestamp or symbol is None).")
        return


profit_or_loss = 0  # الربح أو الخسارة الأولية
first_run = True  # تحديد أن الطباعة الأولى لم تتم بعد
# طباعة المعلومات عند أول تشغيل فقط
if first_run:
    logging.info(f"[{readable_time}] - Initial Balance: {initial_balance}")
    print(f"[{readable_time}] - Initial Balance: {initial_balance}")
    first_run = False  # إيقاف الطباعة بعد أول مرة

logging.info(f"Sell order executed. Profit/Loss: {profit_or_loss}. Balance updated to: {initial_balance}") # طباعة معلومات البيع وتحديث الرصيد
print(f"[{readable_time}] - Sell executed. Total Balance: {initial_balance}, Total Profit/Loss: {profit_or_loss}")

# معالجة الأخطاء
try:
    # الكود الذي يحتمل أن يسبب خطأ هنا
    pass
except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    print(f"An error occurred: {str(e)}")


# وظيفة لحساب الكمية المطلوبة بالدولار
async def calculate_trade_amount(symbol, usd_amount, retries=3):
    global initial_balance
    for attempt in range(retries):
        try:
            # Fetch ticker data بشكل غير متزامن
            ticker = await binance.fetch_ticker(symbol)
            current_price = Decimal(ticker['last'])

            # Fetch balance بشكل غير متزامن
            usdt_balance, _ = await check_balance("Initial Balance Check")
            initial_balance = usdt_balance
            logging.info(f"Trade amount set to: {initial_balance} USDT")

            if current_price <= 0:
                raise ValueError("Invalid price value.")
            logging.info(f"Current price for {symbol}: {current_price}")
            return usd_amount / current_price

        except Exception as e:
            logging.error(f"Error calculating trade amount (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)  # استخدام asyncio.sleep بدلاً من time.sleep
            else:
                return 0
       

async def check_market_liquidity(symbol, retries=3):
    attempt_counter = 0  # Initialize attempt counter

    for attempt in range(retries):
        try:
            # Fetch the order book for the given symbol asynchronously
            depth = await binance.fetch_order_book(symbol, limit=5)
            if not depth or 'bids' not in depth or 'asks' not in depth:
                raise ValueError("Invalid order book data.")

            # Calculate the total highest bid and lowest ask
            highest_bid = sum([Decimal(bid[1]) for bid in depth['bids']])
            lowest_ask = sum([Decimal(ask[1]) for ask in depth['asks']])  # Fixed the missing closing parenthesis
            logging.info(f"Market liquidity - Bid: {highest_bid}, Ask: {lowest_ask}")

            # Check available liquidity against the current balance
            usdt_balance, asset_balance = await check_balance(symbol)
            if usdt_balance < initial_balance:
                logging.warning(f"Insufficient USDT balance: {usdt_balance}. Cannot execute trade.")
                await asyncio.sleep(5)  # Wait before the next attempt asynchronously
                attempt_counter += 1  # Increase attempt counter
                continue  # Retry fetching market liquidity

            return highest_bid, lowest_ask  # Return liquidity if sufficient balance

        except Exception as e:
            logging.error(f"Error fetching market liquidity (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)  # Wait before retrying asynchronously
            else:
                return 0, 0  # Return default values on failure

    return 0, 0  # Final fallback return in case of failure after retries


