import argparse
import curses
import os
import random
import subprocess
import sys
import time
import uuid
import dialog
import sqlite3

with open('words.txt') as f:
    words = [i.strip() for i in f.readlines() if 2 <= len(i) <= 8]

logfile = open('log.txt', 'w')


class ViewScores(Exception):
    pass


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
    args = ap.parse_args()

    if args.length < 1 and args.length != -1:
        ap.error('length must be greater than 0 or -1')
    if args.number < 1:
        ap.error('number must be greater than 0')

    return args


database = sqlite3.connect('./database.db')


def random_id():
    return int(uuid.uuid4().__str__()[:7].replace('-', ''), 16)


def main():
    sentinel = object()

    d = dialog.Dialog()

    users = database.execute('select * from users')
    users = users.fetchall()

    def choose_player():
        if os.environ['user_id']:
            return os.environ['user_id']
        result = d.menu(text='Choose your name', choices=[*zip([str(i[1]) for i in users], [str(i[0]) for i in users]), ('*', '<new user>')])
        if result[0] != 'ok':
            return None
        if result[1] == '*':
            while True:
                name = d.inputbox(text="Enter your name")
                if name[0] != 'ok':
                    return None
                name = name[1]
                if name in users:
                    d.msgbox(text='That name already exists! Try again')
                else:
                    user = name
                    user_id = random_id()
                    database.execute('insert into users (name, id) values (?, ?)', [name, user_id])
                    database.commit()
                    return user_id
        else:
            user_id = result[1]
            return user_id

    def interior(user_id):
        args = parse_args()
        candidates = [word for word in words if len(word) <= args.length or args.length == -1]
        target = ' '.join(random.choice(candidates) for i in range(args.number))
        all_word_count = len(target) / 5
        screen = curses_start()
        rets = place_target(screen, target)
        screen.move(1, 0)

        start = 0.0
        end = 0.0
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
                if ch == ord('\t'):
                    screen.clear()
                    return sentinel
                if ch == 27:
                    raise ViewScores()
                if ch == 0x7f or ch == curses.KEY_BACKSPACE:
                    if lc > 0:
                        screen.delch(line, lc - 1)
                        idx -= 1
                        kc -= 1
                        lc -= 1
                    continue
                idx += 1
                if idx >= len(target):
                    end = time.time()
                    raise StopIteration
                kc += 1
                if ch != ord(target[idx-1]):
                    screen.attrset(curses.color_pair(1))
                else:
                    screen.attrset(curses.color_pair(2))
                screen.addch(ch)
                user_data += chr(ch)
                lc += 1
                log(','.join([str(i) for i in rets]))
                log(str(lc))
                log(str(line))
                log('\n')
                if line < len(rets) and lc == rets[line]:
                    lc = 0
                    line += 2
                    screen.move(line, 0)
        except ViewScores:
            # result = d.menu(text='Choose your name', choices=[*zip([i[1] for i in users], [i[0] for i in users])])
            # if result[0] != 'ok':
            #     return None
            # else:
            #     user_id = result[1]
            scores = database.execute('select * from scores where user=?', [user_id]).fetchall()
            curses.endwin()
            print('|'.join(['user'.ljust(15), 'keystrokes'.ljust(15), 'words_typed'.ljust(15), 's taken'.ljust(15), 'chars/s'.ljust(15), 'errs'.ljust(15), 'wpm'.ljust(15), 'awpm'.ljust(15), 'id']))
            print('\n'.join(str('|'.join(list(str(round(j, 5)).rjust(15) for j in i))) for i in scores))
        except KeyboardInterrupt:
            end = time.time() if not end else end
            seconds = end - start
            curses.endwin()
            print('Keystrokes registered:'.rjust(23) + ' {}'.format(kc))
            print('Words typed:'.rjust(23) + ' {:.2f}'.format(all_word_count))
            print('Seconds taken:'.rjust(23) + ' {:.2f}'.format(seconds))
            print()
            print('Test was interrupted and is invalid!')
        except StopIteration:
            end = time.time() if not end else end
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
            database.execute('''
            INSERT INTO scores (user, keystrokes, words_typed, seconds_taken, chars_per_second, errors_made, wpm, awpm, id) VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [user_id, kc, all_word_count, seconds, kc//seconds, errors, all_word_count/(seconds/60), (all_word_count / (seconds / 60)) - (errors / 5), random_id()])
            return None

    result = choose_player()
    if result is None:
        return

    while interior(result):
        pass


if __name__ == '__main__':
    main()
    logfile.close()
    database.commit()
    database.close()
    exit()
