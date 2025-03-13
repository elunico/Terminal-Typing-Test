import argparse
import curses
import hashlib
import os
import random
import string
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


def safe_remove(map, keys):
    for i in keys:
        try:
            del map[i]
        except KeyError:
            # why is this the only way to do this?
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
    ap.add_argument('-n', '--number', type=int, default=20,
                    help='Number of words to type')
    ap.add_argument('-l', '--length', type=int, default=-1,
                    help='Max length of words to type or -1 for no limit')
    ap.add_argument('--list', choices=["words", 'users', 'scores', *[f'words:{l}' for l in string.ascii_lowercase]], type=str, default=None, required=False,
                    help='show a list of data. choices are "words", "users", "scores"')
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
    global words 
    sentinel = object()

    try:
        d = dialog.Dialog()
    except dialog.ExecutableNotFound as e:
        raise SystemError(
            "You must install the dialog program for your system to continue\nTry sudo apt install dialog or brew install dialog") from e


    args = parse_args()
    if args.list:
        if args.list.startswith('words'):
            if ':' in args.list: 
                mode, sw = args.list.split(':')
                words = [i for i in words if i.startswith(sw)]
            d.msgbox(text='\n'.join(words), height=25, width=80)
            return sentinel
        elif args.list == 'users':
            users = [('id','name')]
            # users = []
            users.extend(database.execute(
                'select id, name from users').fetchall())
            
            d.msgbox(text='\n'.join(['\t'.join([str(id), name]) for id, name in users]), height=25, width=80)
            return sentinel
        elif args.list == 'scores':
            scores = database.execute(
                'select * from scores').fetchall()
            if not scores:
                d.msgbox(text='No scores found!')
                return sentinel
            d.msgbox(text='\n'.join(['|'.join(list(str(round(float(j), 2)).rjust(11)
                                    for j in i[:-1])) + '|' + time.ctime(i[-1]) for i in scores]), height=25, width=80)
            return sentinel
        else:
            d.msgbox(text='Invalid list choice')
            return sentinel
    
    
    
    try:
        users = database.execute('select * from users')
    except sqlite3.OperationalError:
        database.execute(
            'create table users (name text, id int, hash text, salt text, primary key(id))')
        users = database.execute('select * from users')

    users = users.fetchall()

    def new_password():
        pw = d.passwordbox(text='Enter a password')[1]
        salt = os.urandom(16)
        hashed = hashlib.sha256()
        hashed.update(pw.encode())
        hashed.update(salt)
        return hashed.digest(), salt

    def check_password(hash, salt, attempt):
        h = hashlib.sha256()
        h.update(attempt.encode())
        h.update(salt)
        digest = h.digest()
        if digest == hash:
            return True
        else:
            return False

    def attempt_authentication(user_id):
        try:
            hash, salt = database.execute(
            'select hash, salt from users where id=?', [user_id]).fetchone()
        except TypeError:
            d.msgbox(text=f'User ID "{user_id}" not found! Try again')
            return False
        count = 5
        while True:
            pw = d.passwordbox(text="Password")

            if pw[0] != 'ok':
                safe_remove(os.environ, ['user_id', 'password'])
                return choose_player()

            correct = check_password(hash, salt, pw[1])

            if not correct:
                count -= 1
                d.msgbox(
                    text="Invalid password! {} attempts remaining".format(count))

            if count <= 0:
                return False
            elif count > 0 and correct:
                return True
            else:
                continue

    def choose_player():
        if 'user_id' in os.environ:
            user_id = os.environ['user_id']
            if 'password' in os.environ:
                try:
                    hash, salt = database.execute(
                    'select hash, salt from users where id=?', [user_id]).fetchone()
                except TypeError:
                    d.msgbox(text=f'User ID "{user_id}" not found! Try again')
                    return None
                if check_password(hash, salt, os.environ['password']):
                    return user_id
                elif attempt_authentication(user_id):
                    return user_id
                else:
                    return None
            elif attempt_authentication(user_id):
                return user_id
            else:
                return None
        result = d.menu(text='Choose your name', choices=[
                        *zip([str(i[1]) for i in users], [str(i[0]) for i in users]), ('*', '<new user>')])
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
                    user_id = random_id()
                    hashed, salt = new_password()
                    database.execute('insert into users (name, id, hash, salt) values (?, ?, ?, ?)', [
                                     name, user_id, hashed, salt])
                    database.commit()
                    return user_id
        else:
            user_id = result[1]
            if attempt_authentication(user_id):
                return user_id
            else:
                return None

    def interior(user_id):
        nonlocal args 
        candidates = [word for word in words if len(
            word) <= args.length or args.length == -1]
        target = ' '.join(random.choice(candidates)
                          for i in range(args.number))
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
            scores = database.execute(
                'select * from scores where user=?', [user_id]).fetchall()
            curses.endwin()
            print('|'.join(['user'.ljust(11), 'keystrokes'.ljust(11), 'words typed'.ljust(11), 'sec taken'.ljust(
                11), 'chars/s'.ljust(11), 'errs'.ljust(11), 'wpm'.ljust(11), 'awpm'.ljust(11), 'id'.ljust(11), 'time'.ljust(11), ]))
            for row in scores:
                print(str('|'.join(list(str(round(j, 5)).rjust(11)
                      for j in row[:-1]))), end='')
                print('|' + time.ctime(row[-1]).rjust(11))
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
            errors = len([pair[0] != pair[1]
                         for pair in zip(data, t) if pair[0] != pair[1]])
            log(data)
            log(t)
            errors += abs(len(data) - len(t))
            print('Keystrokes registered:'.rjust(23) + ' {}'.format(kc))
            print('Words typed'.rjust(23) + ' {:.2f}'.format(all_word_count))
            print('Seconds taken'.rjust(23) + ' {:.2f}'.format(seconds))
            print('Chars per second'.rjust(23) +
                  ' {:.2f}'.format((kc / seconds)))
            print("Errors made".rjust(23) + ' {}'.format(errors))
            print('WPM:'.rjust(23) +
                  ' {:.2f}'.format(all_word_count / (seconds / 60)))
            print('Adjusted WPM:'.rjust(
                23) + ' {:.2f}'.format((all_word_count / (seconds / 60)) - (errors / 5)))
            database.execute('''
            INSERT INTO scores (user, keystrokes, words_typed, seconds_taken, chars_per_second, errors_made, wpm, awpm, id, time) VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [user_id, kc, all_word_count, seconds, kc//seconds, errors, all_word_count/(seconds/60), (all_word_count / (seconds / 60)) - (errors / 5), random_id(), time.time()])
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
