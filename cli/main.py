import os
import select
import sys
import termios
import threading
import time
import tty
from datetime import datetime

from rich.console import Console
from rich.live import Live

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

from cli.clients.websocket_client import FinnhubWebSocketClient
from cli.commands.handler import execute_command
from cli.ui import create_layout, create_stock_table
from cli.utils import load_symbols_from_config, save_symbols_to_config


class StockTickerApp:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.console = Console()
        self.stock_data = {}
        self.symbols = []
        self.config_file = 'stock_config.yml'
        self.running = True
        self.lock = threading.Lock()
        self.user_input = ''
        self.command_history = []
        self.message = ''
        self.message_time = 0

        self.load_config()
        self.websocket_client = FinnhubWebSocketClient(
            api_key,
            self.get_tracked_symbols,
            self.handle_trade_update,
        )

    def show_message(self, msg: str) -> None:
        """Display a temporary message in the status bar."""
        self.message = msg
        self.message_time = time.time()

    def get_tracked_symbols(self):
        with self.lock:
            return self.symbols.copy()

    def handle_trade_update(self, trade):
        symbol = trade.get('s')
        if not symbol:
            return

        with self.lock:
            if symbol not in self.symbols:
                return

        price = trade.get('p')
        timestamp_value = trade.get('t')
        if price is None or timestamp_value is None:
            return

        timestamp = datetime.fromtimestamp(timestamp_value / 1000).strftime('%H:%M:%S')

        with self.lock:
            old_price = self.stock_data.get(symbol, {}).get('price')
            if old_price and old_price != 0:
                change = ((price - old_price) / old_price) * 100
            else:
                change = 0

            self.stock_data[symbol] = {
                'price': price,
                'change': change,
                'timestamp': timestamp,
            }

    def load_config(self) -> None:
        self.symbols = load_symbols_from_config(self.config_file, [])

    def save_config(self) -> None:
        try:
            save_symbols_to_config(self.config_file, self.symbols)
            self.show_message(f"Configuration saved to {self.config_file}")
        except Exception as exc:
            self.show_message(f"Error saving config: {exc}")

    def process_command(self, command: str) -> None:
        execute_command(self, command)

    def get_char(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None

    def run(self):
        self.websocket_client.start()
        time.sleep(2)

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            with Live(
                create_layout(
                    create_stock_table(self.stock_data, self.symbols, self.lock),
                    len(self.symbols),
                    self.user_input,
                    self.message,
                    self.message_time,
                ),
                refresh_per_second=4,
                console=self.console,
                screen=True,
            ) as live:
                self.show_message("Type 'help' for commands")
                while self.running:
                    char = self.get_char()
                    if char:
                        if char in ('\n', '\r'):
                            self.command_history.append(self.user_input)
                            self.process_command(self.user_input)
                            self.user_input = ''
                        elif char == '\x7f':
                            self.user_input = self.user_input[:-1]
                        elif char == '\x03':
                            break
                        elif char.isprintable():
                            self.user_input += char

                    live.update(
                        create_layout(
                            create_stock_table(self.stock_data, self.symbols, self.lock),
                            len(self.symbols),
                            self.user_input,
                            self.message,
                            self.message_time,
                        )
                    )
                    time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.running = False
            self.websocket_client.stop()
            self.console.print("\n[yellow]Application closed[/]")


if __name__ == '__main__':
    import dotenv
    
    dotenv.load_dotenv()
    API_KEY = dotenv.get_key('.env', 'FINNHUB_API_KEY') or 'your_finnhub_api_key_here'

    if API_KEY == 'your_finnhub_api_key_here':
        print('⚠️  Please set your Finnhub API key in the code')
        print('Get your free API key at: https://finnhub.io/register')
        print('\nCommands available:')
        print('  add <SYMBOL>    - Add a stock ticker')
        print('  remove <SYMBOL> - Remove a stock ticker')
        print('  list            - List all tracked symbols')
        print('  clear           - Remove all symbols')
        print('  save            - Manually save configuration')
        print('  help            - Show help message')
        print('  quit/exit       - Exit application (auto-saves)')
        print("\nConfiguration is saved to 'stock_config.yml'")
        sys.exit(1)

    app = StockTickerApp(API_KEY)
    app.run()
