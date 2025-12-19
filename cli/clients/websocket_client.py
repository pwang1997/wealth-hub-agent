import json
import threading

import websocket


class FinnhubWebSocketClient:
    def __init__(self, api_key, symbol_supplier, trade_handler):
        self.api_key = api_key
        self.symbol_supplier = symbol_supplier
        self.trade_handler = trade_handler
        self.ws = None
        self.ws_thread = None

    def _run(self):
        websocket_url = f"wss://ws.finnhub.io?token={self.api_key}"
        self.ws = websocket.WebSocketApp(
            websocket_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )
        self.ws.run_forever()

    def _send(self, message):
        if self.ws:
            self.ws.send(message)

    def start(self):
        if self.ws_thread and self.ws_thread.is_alive():
            return
        self.ws_thread = threading.Thread(target=self._run, daemon=True)
        self.ws_thread.start()

    def stop(self):
        if self.ws:
            self.ws.close()

    def subscribe(self, symbol):
        subscribe_message = {"type": "subscribe", "symbol": symbol}
        self._send(json.dumps(subscribe_message))

    def unsubscribe(self, symbol):
        unsubscribe_message = {"type": "unsubscribe", "symbol": symbol}
        self._send(json.dumps(unsubscribe_message))

    def _on_message(self, ws, message):
        data = json.loads(message)
        if data.get("type") == "trade":
            for trade in data.get("data", []):
                self.trade_handler(trade)

    def _on_open(self, ws):
        for symbol in self.symbol_supplier():
            self.subscribe(symbol)

    def _on_error(self, ws, error):
        # Errors are intentionally ignored, but this hook exists for extensibility.
        pass

    def _on_close(self, ws, close_status_code, close_msg):
        pass
