import yfinance as yf
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

@app.route("/stock-symbol-valid", methods=["GET"])
def get_stock_symbol_valid():
    symbol = request.args.get("symbol")
    if not symbol:
        return jsonify({"error": "Missing parameters"}), 400
    try:
        stock = yf.Ticker(symbol.lower())
        if stock.info:
            return jsonify(), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/watch-list-data", methods=["GET"])
def get_watch_list_data():
    watch_list_symbols = request.args.get("watch_list_symbols")
    if not watch_list_symbols:
        return jsonify({"error": "Missing parameters"}), 400

    symbols = watch_list_symbols.split(",")
    data = {}
    try:
        for symbol in symbols:
            print(symbol)
            stock = yf.Ticker(symbol.strip().lower())
            stock_info = stock.info
            data[symbol] = stock_info
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stock-data-symbol", methods=["GET"])
def get_stock_data_symbol():
    symbol = request.args.get("symbol")
    if not symbol:
        return jsonify({"error": "Missing parameters"}), 400
    try:
        stock = yf.Ticker(symbol.lower())
        option_chain = stock.option_chain()
        expirations = list(stock.options)

        stock_info = stock.info

        # Calculate mark price
        option_chain.calls["mark"] = (
            option_chain.calls["bid"] + option_chain.calls["ask"]
        ) / 2
        option_chain.puts["mark"] = (
            option_chain.puts["bid"] + option_chain.puts["ask"]
        ) / 2

        calls = option_chain.calls.fillna(value=0)
        strikes = option_chain.calls[["strike"]].fillna(value=0)
        puts = option_chain.puts.fillna(value=0)

        response = {
            "calls": calls.to_dict(orient="records"),
            "expirations": expirations,
            "strikes": strikes.to_dict(orient="records"),
            "puts": puts.to_dict(orient="records"),
            "info": stock_info,
        }

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stock-data-expiration", methods=["GET"])
def get_stock_data_expiration():
    symbol = request.args.get("symbol")
    expiration = request.args.get("expiration")
    if not symbol or not expiration:
        return jsonify({"error": "Missing parameters"}), 400
    try:
        stock = yf.Ticker(symbol.lower())
        option_chain = stock.option_chain(expiration)
        dates = list(stock.options)

        stock_info = stock.info

        # Calculate mark price
        option_chain.calls["mark"] = (
            option_chain.calls["bid"] + option_chain.calls["ask"]
        ) / 2
        option_chain.puts["mark"] = (
            option_chain.puts["bid"] + option_chain.puts["ask"]
        ) / 2

        calls = option_chain.calls.fillna(value=0)
        strikes = option_chain.calls[["strike"]].fillna(value=0)
        puts = option_chain.puts.fillna(value=0)

        response = {
            "calls": calls.to_dict(orient="records"),
            "dates": dates,
            "strikes": strikes.to_dict(orient="records"),
            "puts": puts.to_dict(orient="records"),
            "info": stock_info,
        }

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
