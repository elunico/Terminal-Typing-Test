import curses
import time
import random
import requests
import sys

targets = [
    # 'The quick brown fox jumps over the lazy dog.',
    '''It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.'''
]

with open('words.txt') as f:
    words = [i.strip() for i in f.readlines()]

logfile = open('log.txt', 'w')


def log(msg):
    logfile.write(msg + '\n')
    logfile.flush()


def get_cols():
    return 80


def curses_start():
    screen = curses.initscr()
    curses.start_color()
    curses.init_color(1, 1000, 0, 0)
    curses.init_color(2, 1000, 1000, 0)
    curses.init_pair(2, 2, 0)
    curses.init_pair(1, 1, 0)
    curses.noecho()
    return screen


def place_target(screen, target):
    cols = get_cols()
    words = target.split(' ')
    linecount, lines = 0, 0
    rets = []
    for word in words:
        if linecount + len(word) + 2 >= cols:
            lines += 2
            screen.move(lines, 0)
            rets.append(None)
            rets.append(linecount)
            linecount = 0
        screen.addstr(word + ' ')
        linecount += len(word) + 1
    return rets


def main():
    # target = random.choice(targets)
    if len(sys.argv) == 1:
        sys.argv.append(20)
    target = ' '.join(random.choice(words) for i in range(int(sys.argv[1])))
    all_word_count = len(target.split(' '))
    screen = curses_start()
    rets = place_target(screen, target)
    screen.move(1, 0)

    try:
        start = 0.0
        user_data = ''
        idx = 0
        lc, line = 0, 1
        kc = 0
        log(','.join([str(i) for i in rets]))
        while idx < len(target):
            ch = screen.getch()
            if not start:
                start = time.time()
            if ch == 0x7f or ch == curses.KEY_BACKSPACE:
                if lc > 0:
                    screen.delch(line, lc-1)
                    idx -= 1
                    kc -= 1
                    lc -= 1
                continue
            kc += 1
            if ch != ord(target[idx]):
                screen.attrset(curses.color_pair(1))
            else:
                screen.attrset(curses.color_pair(2))
            screen.addch(ch)
            user_data += chr(ch)
            idx += 1
            lc += 1
            log(','.join([str(i) for i in rets]))
            log(str(lc))
            log(str(line))
            log('\n')
            if line < len(rets) and lc == rets[line]:
                lc = 0
                line += 2
                screen.move(line, 0)

    except KeyboardInterrupt:
        pass

    end = time.time()
    seconds = end - start
    curses.endwin()
    data = user_data.split(' ')
    errors = len(list(filter(lambda t: t[0] != t[1], zip(data, target))))
    print('Keystrokes registered:'.rjust(23) + ' {}'.format(kc))
    print('Words typed'.rjust(23) + ' {:.2f}'.format(all_word_count))
    print('Seconds taken'.rjust(23) + ' {:.2f}'.format(seconds))
    print('Chars per second'.rjust(23) + ' {:.2f}'.format((kc / seconds)))
    print("Errors made".rjust(23) + ' {}'.format(errors))
    print('WPM:'.rjust(23) + ' {:.2f}'.format(all_word_count / (seconds / 60)))
    print('Adjusted WPM:'.rjust(23) + ' {:.2f}'.format((all_word_count / (seconds / 60)) - (errors/5)))


if __name__ == '__main__':
    status = main()
    logfile.close()
    exit(status)
