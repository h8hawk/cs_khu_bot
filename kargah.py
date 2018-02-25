#@author : h8hawk

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import MessageHandler, Filters, CommandHandler, CallbackQueryHandler, Updater, Dispatcher
import telegram
import sys
import json
import os
import time
import asyncio
from tinydb import TinyDB, Query
from jalali import Gregorian
from typing import Dict, Callable, List
import datetime

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

# config telegram bot token and password

with open(os.path.join(__location__, 'token.json')) as f:
    js = json.load(f)
    token = js['token']
    admin_password = js['password']
    f.close()

# First reply keyboard

reply_text1 = "درباره انجمن"
reply_text2 = "ثبت نام در کارگاه"

reply_texts_set = {reply_text1, reply_text2}

start_reply_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text=reply_text2)],
    [KeyboardButton(text=reply_text1)]
], resize_keyboard=True)


numeric_error = """
شماره دانشجویی اشتباه وارد شده است
"""

#######################################################################################
# reply keyboard about : dar morede

about_keyboard_about_khu_cs = 'توضیح در مورد انجمن'
about_keyboard_list = 'لیست کارگاه ها'
back = 'بازگشت ⬅️'

course_list_text = """
🔹کارگاه‌های فعال 🔹

لطفا کارگاهی که می‌خواهید در آن ثبت‌نام کنید را از منوی زیر انتخاب نمایید:
"""

about_keyboard_keys_set = {about_keyboard_about_khu_cs,
                           about_keyboard_list, back}

about_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text=about_keyboard_about_khu_cs)],
    [KeyboardButton(text=about_keyboard_list)],
    [KeyboardButton(text=back)]
], resize_keyboard=True)

#######################################################################################
# courses inline keyboard. saved in json file
json_path = os.path.join(__location__, 'courses.json')
with open(json_path, 'r') as json_file:
    course_dict: dict = json.load(json_file, strict=False)
    assert isinstance(course_dict, dict), 'Json file must be dict'
    assert len(course_dict) != 0, 'Json file is empty'

    for i in course_dict:
        assert isinstance(i, str) and isinstance(
            course_dict[i], list), 'Json file must be contained only string and list'
    json_file.close()
    del json_file


courses_regiser_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text=course_dict[i][0], callback_data=i + 'register')] for i in course_dict.keys()])

courses_register_dict = {
    i + 'register': course_dict[i][0] for i in course_dict.keys()}

courses_overveiw_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text=course_dict[i][0], callback_data=i + 'overveiw')] for i in course_dict.keys()])

courses_overview_dict = {
    i + 'overveiw': course_dict[i][1] for i in course_dict.keys()}

#######################################################################################
# Database loading

database_file_path = os.path.join(__location__, 'registerydb.json')
db = TinyDB(database_file_path)
user = Query()


#######################################################################################


with open(os.path.join(__location__, 'messages','about_us.txt'), 'r') as f:
    tozih_text: str = f.read()
    f.close()

#######################################################################################
# Calback functins
with open(os.path.join(__location__, 'messages','sabtenam.json')) as f:
    sabtenam_list = json.load(f, strict=False)
    f.close()

# Verfication class for verfying object


class Verification:
    def __init__(self, db: TinyDB):
        self._second_timers = set()
        self._third_timers = set()
        self._block_list = set()
        self.db = db
        self._sabtenam_text = sabtenam_list[3:6]

    def _is_verify(self, chat_id)->bool:
        if chat_id in self._block_list:
            return False
        else:
            return True

    def _append_chat_id(self, chat_id):
        if chat_id in self._block_list:
            pass
        elif chat_id in self._third_timers:
            self._block_list.add(chat_id)
        elif chat_id in self._second_timers:
            self._third_timers.add(chat_id)
        else:
            self._second_timers.add(chat_id)

    def _sname_validation(self, snumber: str):
        if snumber.isnumeric() and len(snumber) == 9 and snumber[0] == '9':
            return True
        else:
            return False

    def sabtenam(self, bot: telegram.bot.Bot, chat_id, sabtenam_details: list, kargah, telegram_name):
        if self._is_verify(chat_id):
            if self._sname_validation(sabtenam_details[1].replace(' ', '')):
                db.insert(
                    {
                        'name': sabtenam_details[0],
                        'telegram_name': telegram_name,
                        'snumber': sabtenam_details[1],
                        'major': sabtenam_details[2],
                        'kargah': kargah,
                        'date': Gregorian(str(datetime.date.today())).persian_string(),
                        'chat_id': chat_id,
                    }
                )
                self._append_chat_id(chat_id)
                bot.send_message(
                    chat_id, text=sabtenam_details[0] + ', ' + self._sabtenam_text[-1])
            else:
                bot.send_message(chat_id, text=numeric_error)
        else:
            bot.send_message(
                chat_id, text='Dont spam us! you are blocked from registery!')


# iterator functor for registering

def sabtenam_iterator(chat_id,
                      kargah,
                      bot: telegram.bot.Bot,
                      verify: Verification) -> Callable[[str], bool]:

    current = 0
    sabtenam_text = sabtenam_list[3:6]
    sabtenam_details = list()

    def iterrator(recieved_text: str, telegram_name: str)->bool:
        nonlocal chat_id
        nonlocal bot
        nonlocal current
        if current < len(sabtenam_text) - 1:
            bot.send_message(chat_id, text=sabtenam_text[current])
            current += 1
            sabtenam_details.append(recieved_text)
            return True
        else:
            sabtenam_details.append(recieved_text)
            verify.sabtenam(bot, chat_id, sabtenam_details,
                            kargah, telegram_name)
            return False
    return iterrator


class Handler:
    def __init__(self, db: TinyDB):
        self._verify = Verification(db=db)
        self._sabtenam_dict: Dict[str, Callable[[str], bool]] = dict()

    def _sequence_verify(self, chat_id, bot: telegram.bot.Bot):
        if chat_id in self._sabtenam_dict:
            self._sabtenam_dict.pop(chat_id)
            bot.send_message(chat_id, text=sabtenam_list[6])

    # Handler for handling queries .
    def on_callback_query(self, bot: telegram.bot.Bot, update: telegram.update.Update):
        self._sabtenam_dict
        query = update.callback_query
        chat_id, query_data = query.message.chat_id, query.data

        # This is for showing overviewing courses
        if query_data in courses_overview_dict:
            self._sequence_verify(chat_id, bot)
            bot.send_message(chat_id, text=courses_overview_dict[query_data])

        # This is for registeration
        elif query_data in courses_register_dict:
            self._sequence_verify(chat_id, bot)
            bot.send_message(
                chat_id,
                text=sabtenam_list[0] + courses_register_dict[query_data] + sabtenam_list[1],
                parse_mode=telegram.ParseMode.HTML)
            bot.send_message(chat_id, text=sabtenam_list[2])
            self._sabtenam_dict[chat_id] = sabtenam_iterator(
                chat_id, query_data[:-len('register')], bot, self._verify)

    # handler for texts
    def text_handler(self, bot: telegram.bot.Bot, update: telegram.update.Update):
        text = update.message.text
        chat_id = update.message.chat_id
        # For /start
        message: telegram.Message = update.message
        from_user = message.from_user
#        print(from_user.first_name)
#        print(from_user.last_name)
#        print(from_user.name)
#        print(from_user.is_bot)
#        print(from_user.id)
#        print(from_user.username)
        if text == '/start':
            self._sequence_verify(chat_id, bot)
            bot.send_message(chat_id=chat_id, text='hi',
                             reply_markup=start_reply_keyboard)

        # For reply_text1 in start_reply_keyboard
        elif text == reply_text1:
            self._sequence_verify(chat_id, bot)
            bot.send_message(chat_id, text='About menu',
                             reply_markup=about_keyboard)

        elif text == reply_text2:
            self._sequence_verify(chat_id, bot)
            bot.send_message(chat_id, text=course_list_text,
                             reply_markup=courses_regiser_keyboard)

        # For pressing back
        elif text == back:
            self._sequence_verify(chat_id, bot)
            bot.send_message(chat_id, text='Menu',
                             reply_markup=start_reply_keyboard)

        elif text == about_keyboard_about_khu_cs:
            self._sequence_verify(chat_id, bot)
            bot.send_message(chat_id, text=tozih_text)

        elif text == about_keyboard_list:
            self._sequence_verify(chat_id, bot)
            bot.send_message(chat_id, text=about_keyboard_list,
                             reply_markup=courses_overveiw_keyboard)

        elif text[-len(admin_password):] == admin_password:
            bot.send_message(chat_id,
                             text='\n'.join([i['telegram_name'] for i in db.all()]))

        if chat_id in self._sabtenam_dict:
            if not self._sabtenam_dict[chat_id](text,
                                                update.message.from_user.first_name):
                self._sabtenam_dict.pop(chat_id)


if __name__ == '__main__':
    print('main')
    main_handler = Handler(db)
    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    text_handler = MessageHandler(
        Filters.text | Filters.command, callback=main_handler.text_handler)
    dispatcher.add_handler(text_handler)
    # Query handler
    query_handler = telegram.ext.CallbackQueryHandler(
        main_handler.on_callback_query)
    dispatcher.add_handler(query_handler)
    updater.start_polling()
