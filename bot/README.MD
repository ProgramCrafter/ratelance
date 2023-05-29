# Purpose

This is source code of @ratelance_bot (Telegram). This bot provides you an easy access to Ratelance contracts system, however it **has** access to your keys used for negotiating payments on job contracts.

You are welcome to launch your own instances of bot.  
Put the bot token in `utils.py` in following format:

```py
TOKEN = '1234569870:ANKJANDSMLK...'
```

All libraries should get installed automatically when you launch `main.py`.

# Additional features

1. With a few changes, bot can be migrated to [Stem bridge](https://stem.fomalhaut.me).
1. It also supports autotests according to the dialogue script specified in `test.py`.

# State

Work in progress.

1. Listing jobs: works, needs a redesign :white_check_mark:
1. Listing offers for a job: not implemented
1. Checking details of a job: not implemented
