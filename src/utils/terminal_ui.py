import os
import sys

# Enable ANSI escape sequences on Windows console
if sys.platform == "win32":
    os.system("")


def display_success_card(title: str, details: dict[str, str]) -> None:
    """
    Print a clean, structured success box in the terminal.
    """
    is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    green = "\033[32m" if is_tty else ""
    bold = "\033[1m" if is_tty else ""
    dim = "\033[90m" if is_tty else ""
    reset = "\033[0m" if is_tty else ""

    formatted_items = [
        (k, v) for k, v in details.items()
    ]
    max_label_len = max((len(k) for k, _ in formatted_items), default=8)

    content_width = max(
        (len(k) + len(v) + 5 for k, v in formatted_items),
        default=40,
    )
    box_width = max(content_width + 4, len(title) + 8, 56)

    top_border = f"{green}┌{'─' * (box_width - 2)}┐{reset}"
    header = f"{green}│ {bold}✔ {title.ljust(box_width - 6)}{reset}{green} │{reset}"
    divider = f"{green}├{'─' * (box_width - 2)}┤{reset}"
    bottom_border = f"{green}└{'─' * (box_width - 2)}┘{reset}"

    print()
    print(top_border)
    print(header)
    print(divider)
    for k, v in formatted_items:
        label = k.ljust(max_label_len)
        print(f"{green}│{reset}  {dim}{label}{reset} : {bold}{v}{reset}")
    print(bottom_border)
    print()


def display_error_card(title: str, message: str, tip: str | None = None) -> None:
    """
    Print a clean, structured error box with actionable troubleshooting tips.
    """
    is_tty = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()
    red = "\033[31m" if is_tty else ""
    yellow = "\033[33m" if is_tty else ""
    bold = "\033[1m" if is_tty else ""
    reset = "\033[0m" if is_tty else ""

    box_width = 64
    top_border = f"{red}┌{'─' * (box_width - 2)}┐{reset}"
    header = f"{red}│ {bold}✖ {title.ljust(box_width - 6)}{reset}{red} │{reset}"
    divider = f"{red}├{'─' * (box_width - 2)}┤{reset}"
    bottom_border = f"{red}└{'─' * (box_width - 2)}┘{reset}"

    print(file=sys.stderr)
    print(top_border, file=sys.stderr)
    print(header, file=sys.stderr)
    print(divider, file=sys.stderr)
    print(f"{red}│{reset}  {bold}Message:{reset} {message}", file=sys.stderr)
    if tip:
        print(f"{red}│{reset}  {yellow}{bold}Tip    :{reset} {tip}", file=sys.stderr)
    print(bottom_border, file=sys.stderr)
    print(file=sys.stderr)
