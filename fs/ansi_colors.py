def color(text, color):
    return f"{color}{text}{RESET}"

def crgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[92m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
REVERSED = "\033[7m"

SUCCESS = crgb(0, 255, 0)
WARNING = crgb(255, 255, 0)
ERROR = crgb(255, 0, 0)
INFO = crgb(0, 255, 255)
