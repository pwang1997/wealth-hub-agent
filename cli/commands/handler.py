from typing import Any


def _handle_add(app: Any, args: list[str]) -> None:
    if not args:
        app.show_message("Usage: add <SYMBOL>")
        return

    symbol = args[0].upper()
    added = False
    with app.lock:
        if symbol not in app.symbols:
            app.symbols.append(symbol)
            added = True
    if added:
        app.websocket_client.subscribe(symbol)
        app.show_message(f"Added {symbol}")
        app.save_config()
    else:
        app.show_message(f"{symbol} already exists")


def _handle_remove(app: Any, args: list[str]) -> None:
    if not args:
        app.show_message("Usage: remove <SYMBOL>")
        return

    symbol = args[0].upper()
    removed = False
    with app.lock:
        if symbol in app.symbols:
            app.symbols.remove(symbol)
            removed = True
        if symbol in app.stock_data:
            del app.stock_data[symbol]
    if removed:
        app.websocket_client.unsubscribe(symbol)
        app.show_message(f"Removed {symbol}")
    else:
        app.show_message(f"{symbol} not found")


def _handle_list(app: Any, args: list[str]) -> None:
    with app.lock:
        symbols_str = ", ".join(app.symbols)
    app.show_message(f"Symbols: {symbols_str}")


def _handle_clear(app: Any, args: list[str]) -> None:
    with app.lock:
        symbols_to_remove = app.symbols.copy()
        app.symbols.clear()
        app.stock_data.clear()
    for symbol in symbols_to_remove:
        app.websocket_client.unsubscribe(symbol)
    app.save_config()
    app.show_message("Cleared all symbols")


def _handle_save(app: Any, args: list[str]) -> None:
    app.save_config()


def _handle_help(app: Any, args: list[str]) -> None:
    app.show_message("Commands: add <SYMBOL>, remove <SYMBOL>, list, clear, save, quit")


def _handle_quit(app: Any, args: list[str]) -> None:
    app.save_config()
    app.running = False


COMMANDS = {
    "add": _handle_add,
    "remove": _handle_remove,
    "list": _handle_list,
    "clear": _handle_clear,
    "save": _handle_save,
    "help": _handle_help,
    "?": _handle_help,
    "quit": _handle_quit,
    "exit": _handle_quit,
}


def execute_command(app: Any, raw_command: str) -> None:
    command = raw_command.strip().lower()
    if not command:
        return

    parts = command.split()
    cmd = parts[0]
    handler = COMMANDS.get(cmd)
    if handler:
        handler(app, parts[1:])
    else:
        app.show_message(f"Unknown command: {cmd}. Type 'help' for commands")
