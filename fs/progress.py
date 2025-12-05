import sys
import asyncio

spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
spinner_index = 0

# ANSI escape code for hiding the cursor
def hide_cursor():
    sys.stdout.write("\033[?25l")  # hide cursor

def print_spinner(toggle_cb=None):
    global spinner_index
    if toggle_cb:
        toggle_cb()
    sys.stdout.write(spinner[spinner_index])   # write the next character
    sys.stdout.write('\b')            # erase the last written char
    spinner_index = (spinner_index + 1) % len(spinner)


async def wait_spinner(seconds, toggle_cb=None, end_cb=None):
    seconds_elapsed = 0.0
    while True:
        print_spinner(toggle_cb)
        await asyncio.sleep(0.1)
        seconds_elapsed += 0.1
        if seconds_elapsed >= seconds:
            break

    if end_cb:
        end_cb()

def print_progress_bar(step, total_steps, bar_length=30, toggle_cb=None):
    if toggle_cb:
        toggle_cb()
    percent = step / total_steps
    filled_length = int(bar_length * percent)
    bar = '▓' * filled_length + '░' * (bar_length - filled_length)
    sys.stdout.write(f'\r{bar}')
    if step == total_steps:
        sys.stdout.write('\n')


async def show_progress_bar(total_steps, duration, bar_length=30, toggle_cb=None, end_cb=None):
    step_duration = duration / total_steps
    for step in range(1, total_steps + 1):
        print_progress_bar(step, total_steps, bar_length, toggle_cb)
        if toggle_cb:
            toggle_cb()
        await asyncio.sleep(step_duration)

    if end_cb:
        end_cb()
