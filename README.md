# Насб кардан

1. Ин папкаро (english_bot) пурра ба Desktop кӯчонед
2. Дар CMD:
   ```
   cd Desktop\english_bot
   python -m pip install -r requirements.txt
   ```
3. Файли `bot.py`-ро бо Notepad кушоед, хати зеринро ёбед:
   ```python
   BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
   ```
   ва токени аз @BotFather гирифтаатро ба ҷои `PUT_YOUR_BOT_TOKEN_HERE` гузоред. Захира кунед (Ctrl+S).
4. Дар CMD:
   ```
   python bot.py
   ```

## Тағйирот дар ин версия
Ин версия аз китобхонаи "job-queue" (APScheduler) истифода намекунад, зеро он бо баъзе версияҳои нави Python (masalan 3.14) мушкилот дошт. Ба ҷои он, худи бот дар дохили худ ҳар 30 сония вақтро санҷида, дар вақти муайяншуда (SEND_HOUR:SEND_MINUTE дар bot.py) калимаҳоро мефиристад. Функсионалӣ айнан ҳамон аст.

Дигар чизеро дар код тағйир надиҳед — фақат хати токенро.
