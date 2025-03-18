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
alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
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


# Alpha Vantage API URL
alpha_vantage_url = "https://www.alphavantage.co/query"


# Route for home
@app.route("/", methods=["GET"])
def home():
    return "Options Project API"


# Function to get symbol data from Alpha Vantage
# def get_symbol_data_alpha_vantage(symbol):
#     url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}apikey={alpha_vantage_api_key}"
#     response = requests.get(url)
#     index_data = response.json()
#     return index_data


# Function to get symbol data from Yahoo Finance
def get_symbol_data_yfinance(symbol):
    stock = yf.Ticker(symbol.strip().lower())
    stock_info = stock.info
    return stock_info


# @app.route("/indexes-data", methods=["GET"])
# def fetch_indexes_data():
#     try:
#         dia_data = get_symbol_data_yfinance("DIA")
#         qqq_data = get_symbol_data_yfinance("QQQ")
#         spy_data = get_symbol_data_yfinance("SPY")
#         return jsonify({"DIA": dia_data, "QQQ": qqq_data, "SPY": spy_data})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route("/news-data", methods=["GET"])
# @cross_origin(origin=site_url)
# def fetch_news_data():
#     try:
#         url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&apikey={alpha_vantage_api_key}"
#         response = requests.get(url)
#         news_data = response.json()
#         return jsonify(news_data)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@app.route("/data", methods=["GET"])
def fetch_stock_data():
    symbol = request.args.get("symbol")
    expiration_date = request.args.get("expirationDate")

    # if not symbol:
    #     return jsonify({"error": "Missing Symbol"}), 400

    try:
        dia_data = get_symbol_data_yfinance("DIA")
        qqq_data = get_symbol_data_yfinance("QQQ")
        spy_data = get_symbol_data_yfinance("SPY")

        index_data = {
            "DIA": dia_data,
            "QQQ": qqq_data,
            "SPY": spy_data
        }

        # aapl_data = get_symbol_data_yfinance("AAPL")
        # tsla_data = get_symbol_data_yfinance("TSLA")
        # amzn_data = get_symbol_data_yfinance("AMZN")
        # googl_data = get_symbol_data_yfinance("GOOGL")
        # msft_data = get_symbol_data_yfinance("MSFT")
        # fb_data = get_symbol_data_yfinance("META")
        # nvda_data = get_symbol_data_yfinance("NVDA")
        # pypl_data = get_symbol_data_yfinance("PYPL")
        # nflx_data = get_symbol_data_yfinance("NFLX")
        # wmt_data = get_symbol_data_yfinance("WMT")
        # jnj_data = get_symbol_data_yfinance("JNJ")
        # jpm_data = get_symbol_data_yfinance("JPM")
        # brk_data = get_symbol_data_yfinance("BRK-B")
        # pg_data = get_symbol_data_yfinance("PG")
        # v_data = get_symbol_data_yfinance("V")
        # hd_data = get_symbol_data_yfinance("HD")
        # dis_data = get_symbol_data_yfinance("DIS")
        # ma_data = get_symbol_data_yfinance("MA")
        # baba_data = get_symbol_data_yfinance("BABA")
        # bac_data = get_symbol_data_yfinance("BAC")

        # popular_data = {
        #     "AAPL": aapl_data,
        #     "TSLA": tsla_data,
        #     "AMZN": amzn_data,
        #     "GOOGL": googl_data,
        #     "MSFT": msft_data,
        #     "FB": fb_data,
        #     "NVDA": nvda_data,
        #     "PYPL": pypl_data,
        #     "NFLX": nflx_data,
        #     "WMT": wmt_data,
        #     "JNJ": jnj_data,
        #     "JPM": jpm_data,
        #     "BRK-B": brk_data,
        #     "PG": pg_data,
        #     "V": v_data,
        #     "HD": hd_data,
        #     "DIS": dis_data,
        #     "MA": ma_data,
        #     "BABA": baba_data,
        #     "BAC": bac_data
        # }

        if not symbol:
            response = {
                "indexes": index_data,
                # "popular": popular_data
            }
            return jsonify(response)

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

        call_strikes = calls["strike"].tolist()

        response = {
            "calls": calls.to_dict(orient="records"),
            "dates": dates,
            "puts": puts.to_dict(orient="records"),
            "info": stock_info,
            "strikes": call_strikes,
            "indexes": index_data,
            # "popular": popular_data
        }

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# @app.route("/watch-list-data", methods=["GET"])
# def fetch_watch_list_data():
#     watch_list = request.args.get("watch_list")
#     try:
#         if watch_list:
#             watch_list_symbols = watch_list.split(",")
#         watch_list_data = {}
#         for symbol in watch_list_symbols:
#             stock_info = get_symbol_data_yfinance(symbol)
#             watch_list_data[symbol] = stock_info

#         response = {
#             "watchList": watch_list_data,
#         }

#         return jsonify(response)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)