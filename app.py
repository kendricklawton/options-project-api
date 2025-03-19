from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import cross_origin, CORS
import os
import requests
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
        call_strikes = option_chain.calls[["strike"]].fillna(value=0)
        puts = option_chain.puts.fillna(value=0)
        put_strikes = option_chain.puts[["strike"]].fillna(value=0)

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
            "strikes": strikes
        }

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Function to get symbol data from Yahoo Finance
def get_symbol_data_yfinance(symbol):
    print(symbol)
    stock = yf.Ticker(symbol.strip().lower())
    stock_info = stock.info
    return stock_info


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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)