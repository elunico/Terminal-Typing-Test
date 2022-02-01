import argparse
import curses
import os
import random
import subprocess
import sys
import time

with open('words.txt') as f:
    words = [i.strip() for i in f.readlines() if 2 <= len(i) <= 8]

logfile = open('log.txt', 'w')


def log(msg):
    logfile.write(str(msg) + '\n')
    logfile.flush()


def get_cols():
    if 'COLUMNS' in os.environ:
        return int(os.environ['COLUMNS'])
    status, output = subprocess.getstatusoutput('stty size')
    if output:
        return int(output.split(' ')[1])
    return 80


def curses_start():
    scr = curses.initscr()
    screen = scr.subwin(1, 0)
    curses.start_color()
    curses.init_color(1, 1000, 0, 0)
    curses.init_color(2, 1000, 1000, 0)
    curses.init_pair(2, 2, 0)
    curses.init_pair(1, 1, 0)
    curses.noecho()

    scr.addstr(0, 0, 'Typing Test'.center(get_cols()), curses.A_REVERSE)
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

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('-n', '--number', type=int, default=20, help='Number of words to type')
    ap.add_argument('-l', '--length', type=int, default=-1, help='Max length of words to type or -1 for no limit')
    args =  ap.parse_args()

    if args.length < 1 and args.length != -1:
        ap.error('length must be greater than 0 or -1')
    if args.number < 1:
        ap.error('number must be greater than 0')

    return args

def main():
    args = parse_args()
    candidates = [word for word in words if len(word) <= args.length or args.length == -1]
    target = ' '.join(random.choice(candidates) for i in range(args.number))
    all_word_count = len(target) / 5
    screen = curses_start()
    rets = place_target(screen, target)
    screen.move(1, 0)

    start = 0.0
    user_data = ''
    idx = 0
    lc, line = 0, 1
    kc = 0
    try:
        log(','.join([str(i) for i in rets]))
        while idx < len(target):
            ch = screen.getch()
            if not start:
                start = time.time()
            if ch == 0x7f or ch == curses.KEY_BACKSPACE:
                if lc > 0:
                    screen.delch(line, lc - 1)
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
    t = target.split(' ')
    log([pair for pair in zip(data, t)])
    errors = len([pair[0] != pair[1] for pair in zip(data, t) if pair[0] != pair[1]])
    log(data)
    log(t)
    errors += abs(len(data) - len(t))
    print('Keystrokes registered:'.rjust(23) + ' {}'.format(kc))
    print('Words typed'.rjust(23) + ' {:.2f}'.format(all_word_count))
    print('Seconds taken'.rjust(23) + ' {:.2f}'.format(seconds))
    print('Chars per second'.rjust(23) + ' {:.2f}'.format((kc / seconds)))
    print("Errors made".rjust(23) + ' {}'.format(errors))
    print('WPM:'.rjust(23) + ' {:.2f}'.format(all_word_count / (seconds / 60)))
    print('Adjusted WPM:'.rjust(23) + ' {:.2f}'.format((all_word_count / (seconds / 60)) - (errors / 5)))

if __name__ == '__main__':
    main()
    logfile.close()
    exit()
