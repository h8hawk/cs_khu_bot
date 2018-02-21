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
from typing import Dict, Callable
import datetime

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

token = 'xxxxxx'

#######################################################################################
# First reply keyboard

reply_text1 = "about"
reply_text2 = "Sabtenam"

reply_texts_set = {reply_text1, reply_text2}

start_reply_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text=reply_text1)],
    [KeyboardButton(text=reply_text2)]
])


#######################################################################################
# reply keyboard about : dar morede

about_keyboard_about_khu_cs = 'توضیح در مورد انجمن'
about_keyboard_list = 'لیست کارگاه ها'
back = 'Back'

about_keyboard_keys_set = {about_keyboard_about_khu_cs,
                           about_keyboard_list, back}

about_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text=about_keyboard_about_khu_cs)],
    [KeyboardButton(text=about_keyboard_list)],
    [KeyboardButton(text=back)]
]
)

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

with open(os.path.join(__location__, 'sabtenam.txt'), 'r') as f:
    sabtenam_text: str = f.read()
    f.close()

with open(os.path.join(__location__, 'tozih.txt'), 'r') as f:
    tozih_text: str = f.read()
    f.close()

#######################################################################################
# Calback functins

sabtenam_global_dict: Dict[str, Callable[[str], bool]] = dict()
sabtenam_list = sabtenam_text.split('\n')

# iterator functor for registering


def sabtenam_iterator(chat_id, kargah,  bot: telegram.bot.Bot, db=db) -> Callable[[str], bool]:
    current = 0
    sabtenam_text = sabtenam_list[3:6]
    sabtenam_details = list()

    def iterrator(recieved_text: str)->bool:
        nonlocal db
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
            db.insert({
                'name': sabtenam_details[0],
                'snumber': sabtenam_details[1],
                'major': sabtenam_details[2],
                'kargah': kargah,
                'date': Gregorian(str(datetime.date.today())).persian_string()
            })
            bot.send_message(
                chat_id, text=sabtenam_details[0] + ', ' + sabtenam_text[-1])
            return False
    return iterrator

# handler for texts


def text_handler(bot: telegram.bot.Bot, update: telegram.update.Update):
    text = update.message.text
    chat_id = update.message.chat_id
    # For /start
    global sabtenam_global_dict
    print(text)
    if text == '/start':
        if chat_id in sabtenam_global_dict:
            sabtenam_global_dict.pop(chat_id)
            bot.send_message(chat_id, sabtenam_list[6])
        bot.send_message(chat_id=chat_id, text='hi',
                         reply_markup=start_reply_keyboard)

    # For reply_text1 in start_reply_keyboard
    elif text == reply_text1:
        if chat_id in sabtenam_global_dict:
            sabtenam_global_dict.pop(chat_id)
            bot.send_message(chat_id, sabtenam_list[6])
        bot.send_message(chat_id, text='About menu',
                         reply_markup=about_keyboard)

    # For
    elif text == reply_text2:
        if chat_id in sabtenam_global_dict:
            sabtenam_global_dict.pop(chat_id)
            bot.send_message(chat_id, sabtenam_list[6])
        bot.send_message(chat_id, text='Courses list',
                         reply_markup=courses_regiser_keyboard)

    # For pressing back
    elif text == back:
        if chat_id in sabtenam_global_dict:
            sabtenam_global_dict.pop(chat_id)
            bot.send_message(chat_id, sabtenam_list[6])
        bot.send_message(chat_id, text='Menu',
                         reply_markup=start_reply_keyboard)

    elif text == about_keyboard_about_khu_cs:
        if chat_id in sabtenam_global_dict:
            sabtenam_global_dict.pop(chat_id)
            bot.send_message(chat_id, sabtenam_list[6])
        bot.send_message(chat_id, text=tozih_text)

    elif text == about_keyboard_list:
        if chat_id in sabtenam_global_dict:
            sabtenam_global_dict.pop(chat_id)
            bot.send_message(chat_id, sabtenam_list[6])
        bot.send_message(chat_id, text=about_keyboard_list,
                         reply_markup=courses_overveiw_keyboard)

    if chat_id in sabtenam_global_dict:
        if not sabtenam_global_dict[chat_id](text):
            sabtenam_global_dict.pop(chat_id)


# handler for callback queries


def on_callback_query(bot: telegram.bot.Bot, update: telegram.update.Update):
    global sabtenam_global_dict
    print(sabtenam_global_dict)
    query = update.callback_query
    chat_id, query_data = query.message.chat_id, query.data
    print('Callback Query:', query_data)
    if query_data in courses_overview_dict:
        if chat_id in sabtenam_global_dict:
            sabtenam_global_dict.pop(chat_id)
            bot.send_message(chat_id, sabtenam_list[6])
        print(courses_overview_dict[query_data])
        bot.send_message(chat_id, text=courses_overview_dict[query_data])
    elif query_data in courses_register_dict:
        if chat_id in sabtenam_global_dict:
            sabtenam_global_dict.pop(chat_id)
            bot.send_message(chat_id=chat_id, text=sabtenam_list[6])
        print(courses_register_dict[query_data])
        bot.send_message(
            chat_id, text=sabtenam_list[0] + ' ' + courses_register_dict[query_data] + ' ' + sabtenam_list[1])
        bot.send_message(chat_id, text=sabtenam_list[2])
        sabtenam_global_dict[chat_id] = sabtenam_iterator(
            chat_id, query_data[:-len('register')], bot=bot, db=db)
        print(sabtenam_global_dict)


if __name__ == '__main__':
    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    text_handler = MessageHandler(
        Filters.text | Filters.command, callback=text_handler)
    dispatcher.add_handler(text_handler)
    query_handler = telegram.ext.CallbackQueryHandler(on_callback_query)
    dispatcher.add_handler(query_handler)
    updater.start_polling()
