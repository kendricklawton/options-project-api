from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])


@app.route("/stock-data", methods=["GET"])
def get_stock_data():
    symbol = request.args.get("symbol")
    expiration_date = request.args.get("expirationDate")
    if not symbol:
        return jsonify({"error": "Missing Symbol"}), 400
    try:
        print("Symbol: ", symbol)
        stock = yf.Ticker(symbol.lower())
        if not stock:
            return jsonify({"error": "Invalid Symbol"}), 400
        if expiration_date:
            print("Expirate Date: ", expiration_date)
            option_chain = stock.option_chain(expiration_date)
        else:
            print("No Expiration Date")
            option_chain = stock.option_chain()
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
            "puts": puts.to_dict(orient="records"),
            "info": stock_info,
            "strikes": strikes.to_dict(orient="records"),
        }

        return jsonify(response)
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


if __name__ == "__main__":
    app.run(debug=True)
