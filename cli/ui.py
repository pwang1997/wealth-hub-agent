import time

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def create_stock_table(stock_data, symbols, lock):
    """Build a table of tracked symbols with the latest price data."""
    table = Table(show_header=True, header_style="bold green", border_style="green", expand=True)
    table.add_column("TICKER", style="white", width=12)
    table.add_column("PRICE", style="white", width=15)
    table.add_column("CHANGE", style="white", width=15)
    table.add_column("TIMESTAMP", style="dim", width=15)

    with lock:
        for symbol in symbols:
            if symbol in stock_data:
                data = stock_data[symbol]
                price = f"${data['price']:.2f}"
                change = data.get("change", 0)
                change_text = f"{change:+.2f}%"
                change_style = "green" if change >= 0 else "red"
                timestamp = data["timestamp"]

                table.add_row(
                    symbol,
                    price,
                    Text(change_text, style=change_style),
                    timestamp,
                )
            else:
                table.add_row(symbol, "Loading...", "...", "...")

    return table


def create_layout(table, symbol_count, user_input, message, message_time):
    """Compose the full terminal layout from the supplied pieces."""
    layout = Layout()
    layout.split_column(
        Layout(name="main", ratio=9),
        Layout(name="status", size=3),
        Layout(name="prompt", size=3),
    )

    layout["main"].update(
        Panel(
            table,
            title="[bold green]Stock Ticker - Real-time Monitor[/]",
            border_style="green",
        )
    )

    status_text = Text()
    status_text.append("● ", style="green")
    status_text.append("Connected to Finnhub WebSocket", style="green")
    status_text.append(f"    {symbol_count} symbols", style="dim")

    if message and (time.time() - message_time < 3):
        status_text.append(f"    | {message}", style="yellow")

    layout["status"].update(Panel(status_text, border_style="green"))

    prompt_text = Text()
    prompt_text.append("> ", style="green")
    prompt_text.append(user_input, style="white")
    prompt_text.append("█", style="white")

    layout["prompt"].update(Panel(prompt_text, border_style="green"))
    return layout
