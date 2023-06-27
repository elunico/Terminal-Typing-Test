# Terminal Typing Test

This is a Python program that implements a typing speed test entirely in the terminal. It has several features which are outlined below

## Word selection
You can use the `-n INT` command line flag to determine how many words the test will consist of. Any number integer greater than 0 is allowed so long as space on the terminal allows.

You can use the `-l INT` command line flag to determine the maximum length of each word in the test. This can be any number greater than 0, but not all positive numbers will occur since this is limited to only valid, English words

## User Selection
When running the test you are first greeted with a user selection box. This allows you to choose your name or enter it if it is the first time you are using the program. Note the number next to each name
is the **user id**. This is important for later.

If you do not want to select your name each time you run the program, you can set the `user_id` environment variable to your user id as viewed in the name selection screen. So if my user id is 101 I could
run the program like this

```python
user_id=101 python3 test.py
```

to bypass the user selection screen and automatically start the test as me

## Score viewing
Currently, you can view all the previous tests for a single user. There is not currently a way to calculate statistics, see multiple users scores at once, or see any graphs/images related to the scores, though this
may be implemented in the future.

To see the scores of a user, first start the program and select the user whose scores you want to see (either with the menu or by setting the environment variable). Then once you are on the test screen press
`ESC` on the keyboard.

## Requirements
Running this program requires Python as well as sqlite3, dialog, and curses. sqlite3 comes with Python, but dialog and curses are often exclusive to POSIX platforms like macOS and Linux.
