import gevent
from gevent import monkey

monkey.patch_all()

import pytz
from datetime import datetime, date
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import signal
import sys
import yfinance as yf
import pandas as pd


# Initialize Flask application
app = Flask(__name__)


# Load environment variables
load_dotenv()


# Environment variables
site_url_one = os.getenv("SITE_URL_ONE")
site_url_two = os.getenv("SITE_URL_TWO")
site_url_three = os.getenv("SITE_URL_THREE")


# Enable CORS for specific origins
CORS(app, origins=[site_url_one, site_url_two, site_url_three])


# Initialize SocketIO with gevent async_mode
socketio = SocketIO(
    app,
    cors_allowed_origins=[site_url_one, site_url_two, site_url_three],
    async_mode="gevent",
)


# Dictionary to store user subscriptions and their corresponding tasks
user_tasks = {}


# List of market holidays (example for 2025)
MARKET_HOLIDAYS = [
    date(2025, 1, 1),  # New Year's Day
    date(2025, 7, 4),  # Independence Day
    date(2025, 11, 27),  # Thanksgiving Day
    date(2025, 12, 25),  # Christmas Day
]


# Function to check if the stock market is open
def is_market_open():
    # # Define the timezone for Eastern Time (ET)
    # eastern = pytz.timezone("US/Eastern")
    # now = datetime.now(eastern)

    # # Define market open and close times
    # market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    # market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    # # Check if today is a weekday (Monday to Friday)
    # if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
    #     return False

    # # Check if today is a market holiday
    # if now.date() in MARKET_HOLIDAYS:
    #     return False

    # # Check if the current time is within market hours
    # if market_open <= now <= market_close:
    #     return True

    return False


# Function to close all market tasks
def close_market_tasks():
    print("Closing market tasks...")
    for sid, task in user_tasks.items():
        # Signal the stop event to stop the task
        task["stop_event"].set()
        # Kill the greenlet thread
        task["thread"].kill()
    # Clear the user_tasks dictionary
    user_tasks.clear()
    print("All market tasks have been stopped and cleared.")


# Function to get symbol data from Yahoo Finance
def get_symbol_data_yfinance(symbol):
    stock = yf.Ticker(symbol.strip().lower())
    stock_info = stock.info
    return stock_info


# Function to fetch index data and emit updates every 15 seconds
def send_index_data():
    print("Sending index data")
    try:
        while True:
            qqq = get_symbol_data_yfinance("QQQ")
            spy = get_symbol_data_yfinance("SPY")
            dia = get_symbol_data_yfinance("DIA")
            socketio.emit(
                "data",
                {
                    "QQQ": qqq,
                    "SPY": spy,
                    "DIA": dia,
                },
                namespace="/indexes",
            )
            gevent.sleep(15)  # Wait for 15 seconds
    except Exception as e:
        socketio.emit("error", {"error": str(e)}, namespace="/indexes")


# Function to fetch stock data and emit updates every 15 seconds
def send_stock_data(
    symbol, sid, stop_event, expiration_date, near_price, total_strikes
):
    print(
        f"Sending stock data for symbol: {symbol} to sid: {sid} with expiration date: {expiration_date}"
    )

    try:
        while not stop_event.is_set():
            if not is_market_open():
                print("Market is closed. Stopping tasks...")
                close_market_tasks()
                emit(
                    "error", {"error": "Stock Market Closed - Live Data Not Available"}
                )
                break
            stock = yf.Ticker(symbol.strip().lower())
            dates = list(stock.options)
            stock_info = stock.info

            if expiration_date:
                option_chain = stock.option_chain(expiration_date)
            else:
                option_chain = stock.option_chain()

            option_chain.calls["mark"] = (
                option_chain.calls["bid"] + option_chain.calls["ask"]
            ) / 2
            option_chain.puts["mark"] = (
                option_chain.puts["bid"] + option_chain.puts["ask"]
            ) / 2

            calls = option_chain.calls.fillna(value=0)
            puts = option_chain.puts.fillna(value=0)

            all_strikes = pd.concat(
                [calls[["strike"]], puts[["strike"]]]
            ).drop_duplicates()

            # Merge the strikes with calls and puts
            calls = all_strikes.merge(calls, on="strike", how="outer").fillna(0)
            puts = all_strikes.merge(puts, on="strike", how="outer").fillna(0)

            # Drop the lastTradeDate column if it exists // Need To Convert To A String Later
            calls = calls.drop(columns=["lastTradeDate"], errors="ignore")
            puts = puts.drop(columns=["lastTradeDate"], errors="ignore")

            strikes = calls["strike"].tolist()
            socketio.emit(
                "data",
                {
                    "calls": calls.to_dict(orient="records"),
                    "dates": dates,
                    "info": stock_info,
                    "puts": puts.to_dict(orient="records"),
                    "strikes": strikes,
                    "expirationDate": expiration_date,
                    "nearPrice": near_price,
                    "totalStrikes": total_strikes,
                },
                to=sid,
                namespace="/stock",
            )
            stop_event.wait(15)  # Wait for 15 seconds or until the stop event is set
    except Exception as e:
        socketio.emit("error", {"error": str(e)}, to=sid, namespace="/stock")
    finally:
        # Cleanup user task if needed
        user_tasks.pop(sid, None)


# Middleware to check the Origin header
@app.before_request
def before_request():
    origin = request.headers.get("Origin")
    if origin not in [site_url_one, site_url_two, site_url_three]:
        return jsonify({"error": "Invalid Origin"}), 403


# Route for home
@app.route("/", methods=["GET"])
def home():
    return "Options Project API"


# Route for Stock Data
@app.route("/stock-data", methods=["GET"])
def fetch_stock_data():
    symbol = request.args.get("symbol")
    expiration_date = request.args.get("expirationDate")

    if not symbol:
        return jsonify({"error": "Missing Symbol"}), 400

    try:
        stock = yf.Ticker(symbol.strip().lower())
        dates = list(stock.options)
        stock_info = stock.info

        if expiration_date:
            option_chain = stock.option_chain(expiration_date)
        else:
            option_chain = stock.option_chain()

        option_chain.calls["mark"] = (
            option_chain.calls["bid"] + option_chain.calls["ask"]
        ) / 2
        option_chain.puts["mark"] = (
            option_chain.puts["bid"] + option_chain.puts["ask"]
        ) / 2

        calls = option_chain.calls.fillna(value=0)
        puts = option_chain.puts.fillna(value=0)

        # Merge strikes from calls and puts
        all_strikes = pd.concat([calls[["strike"]], puts[["strike"]]]).drop_duplicates()

        # Merge the strikes with calls and puts
        calls = all_strikes.merge(calls, on="strike", how="outer").fillna(0)
        puts = all_strikes.merge(puts, on="strike", how="outer").fillna(0)

        strikes = calls["strike"].tolist()

        response = {
            "calls": calls.to_dict(orient="records"),
            "dates": dates,
            "puts": puts.to_dict(orient="records"),
            "info": stock_info,
            "strikes": strikes,
        }

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route for Indexes Data
@app.route("/indexes-data", methods=["GET"])
def fetch_indexes_list_data():
    try:
        response = {
            "QQQ": get_symbol_data_yfinance("QQQ"),
            "SPY": get_symbol_data_yfinance("SPY"),
            "DIA": get_symbol_data_yfinance("DIA"),
        }

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# SOCKET IO NAMESPACES #


# Index Namespaces
@socketio.on("connect", namespace="/indexes")
def on_connect_indexes():
    try:
        if not is_market_open():
            print("Market is closed. Closing all tasks...")
            close_market_tasks()  # Stop all tasks and clear the dictionary
            emit("error", {"error": "Stock Market Closed - Live Data Not Available"})
            return
        print("Connected to stock namespace")
        emit("message", {"message": "Connected to stock namespace"})
    except Exception as e:
        emit("error", {"error": str(e)})
        return


@socketio.on("disconnect", namespace="/indexes")
def on_disconnect_indexes(sid):
    try:
        if sid in user_tasks:
            # Stop the task gracefully if it exists
            user_tasks[sid]["stop_event"].set()
            user_tasks[sid]["thread"].join()
            del user_tasks[sid]
        print("Disconnected from stock namespace")
        emit("disconnect", {"message": "Disconnected from stock namespace"})
    except Exception as e:
        emit("error", {"error": str(e)})
        return


@socketio.on("subscribe", namespace="/indexes")
def on_subscribe_indexes():
    try:
        if not is_market_open():
            print("Market is closed. Closing all tasks...")
            close_market_tasks()  # Stop all tasks and clear the dictionary
            emit("error", {"error": "Stock Market Closed - Live Data Not Available"})
            return

        sid = request.sid
        # Stop any existing task for this user
        if sid in user_tasks:
            user_tasks[sid]["stop_event"].set()
            user_tasks[sid]["thread"].join()

        # Create a new stop event and thread for the subscription
        stop_event = gevent.event.Event()
        thread = gevent.spawn(send_index_data)
        user_tasks[sid] = {"thread": thread, "stop_event": stop_event}
        print("Subscribe - User Tasks:", user_tasks)
        emit("message", {"message": "Subscribed to indexes data"})
    except Exception as e:
        emit("error", {"error": str(e)})
        return


# Stock namespaces # Need To Improve
@socketio.on("connect", namespace="/stock")
def on_connect_stock():
    try:
        if not is_market_open():
            print("Market is closed. Closing all tasks...")
            close_market_tasks()  # Stop all tasks and clear the dictionary
            emit("error", {"error": "Stock Market Closed - Live Data Not Available"})
            return
        print("Connected to stock namespace")
        emit("message", {"message": "Connected to stock namespace"})
    except Exception as e:
        emit("error", {"error": str(e)})
        return


@socketio.on("disconnect", namespace="/stock")
def on_disconnect_stock(sid):
    if sid in user_tasks:
        # Stop the task gracefully if it exists
        user_tasks[sid]["stop_event"].set()
        user_tasks[sid]["thread"].join()
        del user_tasks[sid]
    print("Disconnected from stock namespace")
    emit("disconnect", {"message": "Disconnected from stock namespace"})


@socketio.on("subscribe", namespace="/stock")
def on_subscribe_stock(data):
    if not is_market_open():
        print("Market is closed. Closing all tasks...")
        close_market_tasks()  # Stop all tasks and clear the dictionary
        emit("error", {"error": "Stock Market Closed - Live Data Not Available"})
        return
    sid = request.sid
    expiration_date = data.get("expirationDate") or None
    near_price = data.get("nearPrice") or None
    total_strikes = data.get("totalStrikes") or None

    symbol = data.get("symbol")
    if not symbol:
        emit("error", {"error": "Symbol is required"})
        return

    # Stop any existing task for this user
    if sid in user_tasks:
        user_tasks[sid]["stop_event"].set()
        user_tasks[sid]["thread"].join()

    # Create a new stop event and thread for the subscription
    stop_event = gevent.event.Event()
    thread = gevent.spawn(
        send_stock_data,
        symbol,
        sid,
        stop_event,
        expiration_date,
        near_price,
        total_strikes,
    )
    user_tasks[sid] = {"thread": thread, "stop_event": stop_event}
    print("Subscribe - User Tasks:", user_tasks)
    emit("message", {"message": f"Subscribed to symbol: {symbol}"})


@socketio.on("update", namespace="/stock")
def on_update_stock(data):
    if not is_market_open():
        print("Market is closed. Closing all tasks...")
        close_market_tasks()  # Stop all tasks and clear the dictionary
        emit("error", {"error": "Stock Market Closed - Live Data Not Available"})
        return
    sid = request.sid
    expiration_date = data.get("expirationDate") or None
    near_price = data.get("nearPrice") or None
    total_strikes = data.get("totalStrikes") or None
    symbol = data.get("symbol")
    if not symbol:
        emit("error", {"error": "Symbol is required"})
        return

    # Stop the current task and start a new one with the updated symbol
    if sid in user_tasks:
        user_tasks[sid]["stop_event"].set()
        user_tasks[sid]["thread"].join()

    stop_event = gevent.event.Event()
    thread = gevent.spawn(
        send_stock_data,
        symbol,
        sid,
        stop_event,
        expiration_date,
        near_price,
        total_strikes,
    )
    user_tasks[sid] = {"thread": thread, "stop_event": stop_event}
    print(f"Update - User Tasks:, {user_tasks}")
    emit("message", {"message": f"Updated subscription to symbol: {symbol}"})


# Graceful shutdown handler // Need To Improve
def handle_shutdown(signal, frame):
    print("\nShutting down gracefully...")
    close_market_tasks()  # Stop all tasks and clear the dictionary
    sys.exit(0)


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port, use_reloader=False)
