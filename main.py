from telebot import TeleBot
from telebot.types import Message, CallbackQuery, BotCommand
from project.config import BOT_TOKEN, SYSTEM_PROMPT, SYSTEM_PROMPT_TRANSLATION

from validation import (is_user_amount_limit, is_gpt_tokens_limit_per_message)
from project.database import (create_table_tests, add_user_to_tests_table, get_tests_info, is_user_in_tests, add_level_info, create_table_prompts, create_table_limits, user_in_table,
                              insert_row_into_limits, update_tts_tokens_in_limits, insert_row_into_prompts,
                              update_stt_blocks_in_limits, update_gpt_tokens_in_limits, get_last_session,
                              update_session_id, get_start_dialog, get_theme_dialog, update_start_dialog, update_theme_dialog,
                              update_message_translation, get_last_message_and_translation)
import logging
from math import ceil
from project.keyboards import menu_keyboard, inline_menu_keyboard
from project.info import topics
from utils import get_markdownv2_text
from project.dialog_pipeline import stt, ttt, tts
import random
import json
from vocab import get_info_of_word
bot = TeleBot(token=BOT_TOKEN)


@bot.message_handler(commands=['vocab'])
def vocab(message: Message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'введите слово для его перевода')
    bot.register_next_step_handler(message=message, callback=translate)


def translate(message: Message):
    user_id = message.from_user.id
    definition, example, audio = get_info_of_word(message.text)
    bot.send_message(user_id, definition)
    bot.send_message(user_id, example)
    bot.send_audio(user_id, audio)


@bot.message_handler(commands=['start'])
def start(message: Message):
    user_id = message.from_user.id
    #bot.send_message(user_id, f'<b><i> jfkdf </i></b>', parse_mode='HTML')
    #a = requests.get('https://api.dictionaryapi.dev/api/v2/entries/en/Get DoWn')
    #print(a.text)
    #b = requests.get('https://dictionary.yandex.net/api/v1/dicservice.json/lookup?key=dict.1.1.20240515T133831Z.58b53730f3d829fe.05407e0a86e9f254c8806804406bce295ff4358a&lang=en-ru&text= Get  DoWn ')
    #print(b.text)
    # Проверяем, достигли ли мы лимита пользователей


    # Проверяем, есть ли пользователь в нашей таблице лимитов токенов, если нет - добавляем.
    if not user_in_table(user_id):
        insert_row_into_limits(user_id)

        logging.info(f'New user_id {user_id} just connected')

    bot.send_message(user_id, 'привет, чтобы взаимодействаовать введите команду /menu')


@bot.message_handler(commands=['help'])
def menu(message: Message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Функция хелп в разрабокте')


@bot.message_handler(commands=['menu'])
def menu(message: Message):
    user_id = message.from_user.id
    markup = inline_menu_keyboard([['Тесты', 'tests'], ['Диалог', 'dialog'], ['Вокабуляр', 'vocabulary']], rows=3)
    bot.send_message(user_id, 'Выберите режим для тренировки:', reply_markup=markup)


@bot.message_handler(commands=['stop_dialog'])
def stop_dialog(message: Message):
    user_id = message.from_user.id
    if get_start_dialog(user_id) == 'False':
        bot.send_message(user_id, 'Вы еще не начали диалог.')
    else:
        update_start_dialog(user_id, 'False')
        bot.send_message(user_id, 'Диалог остановлен')


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: CallbackQuery):
    user_id = call.message.chat.id

    if call.data == 'tests':
        if not is_user_in_tests(user_id):
            add_user_to_tests_table(user_id)

        markup = inline_menu_keyboard([['Тесты', 'Null'], ['Диалог', 'Null'], ['Вокабуляр', 'Null']], rows=3)
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=markup)
        markup = inline_menu_keyboard([['A1', 'A1'], ['A2', 'A2'], ['B1', 'B1'],
                                       ['B2', 'B2'], ['C1', 'C1'], ['C2', 'C2']], rows=2)
        bot.send_message(user_id, ('Внизу представлены тесты различных уровней, '
                                   'выберите подходящий и вперед!'), reply_markup=markup)

    elif call.data in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
        if not is_user_in_tests(user_id):
            add_user_to_tests_table(user_id)
        if call.data in ['C1', 'C2']:
            bot.send_message(user_id, 'В разработке. Недоступны C1, C2')
            return
        chosen_level = call.data
        tests_of_level = tests_dict[chosen_level]
        state, num_of_question, amount_of_correct_answers, message_id = get_tests_info(user_id, chosen_level).split(', ')
        amount_of_questions = len(tests_of_level)
        if int(num_of_question) > amount_of_questions:
            markup = inline_menu_keyboard([['Пройти еще раз', 'test_start_over'],
                                           ['Выйти', 'exit']], rows=1)
            bot.send_message(chat_id=user_id,
                             text=f'{chosen_level} уровень. Вы уже прошли данное тестирование, хотите пройти его еще раз?', reply_markup=markup)
            #state = 'Finished'
            #num_of_question = 1
            #amount_of_correct_answers = 0
            #message_id = 'None'
            #add_level_info(user_id, chosen_level, f'{state}, {num_of_question}, {amount_of_correct_answers}, {message_id}')
            return
        if state == "Start":
            bot.delete_message(chat_id=user_id, message_id=message_id)
            markup = inline_menu_keyboard([['Продолжить тестирование', 'test_continue'],
                                           ['Начать сначала', 'test_start_over']], rows=1)
            bot.send_message(user_id, (f'{chosen_level} уровень. У вас есть незавершенное тестирование\n'
                                       f'Хотите продолжить?'), reply_markup=markup)
        else:
            question = tests_of_level[num_of_question]["question"]
            markup = inline_menu_keyboard(tests_of_level[num_of_question]["options"].items(), rows=2)
            message = bot.send_message(user_id, (f'{call.data}. Вопрос {int(num_of_question)}/{amount_of_questions}\n\n'
                                       f'{question}'), reply_markup=markup)
            add_level_info(user_id, chosen_level,
                           f'Start, {num_of_question}, {amount_of_correct_answers}, {message.message_id}')

    elif call.data in ['test_continue', 'test_start_over', 'exit']:
        level = call.message.text[:2]
        if call.data == 'exit':
            bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        if call.data == 'test_continue':
            state, num_of_question, amount_of_correct_answers, message_id = get_tests_info(user_id, level).split(', ')

            tests_of_level = tests_dict[level]
            state, num_of_question, amount_of_correct_answers, message_id = get_tests_info(user_id, level).split(', ')
            amount_of_questions = len(tests_of_level)
            question = tests_of_level[num_of_question]["question"]

            add_level_info(user_id, level,
                           f'Start, {num_of_question}, {amount_of_correct_answers}, {call.message.id}')
            markup = inline_menu_keyboard(tests_of_level[num_of_question]["options"].items(), rows=2)
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=(f'{level}. Вопрос {int(num_of_question)}/{amount_of_questions}\n\n'
                                       f'{question}'), reply_markup=markup)

        elif call.data == 'test_start_over':
            state = 'Start'
            num_of_question = 1
            amount_of_correct_answers = 0
            message_id = call.message.message_id
            add_level_info(user_id, level, f'{state}, {num_of_question}, {amount_of_correct_answers}, {message_id}')
            state, num_of_question, amount_of_correct_answers, message_id = get_tests_info(user_id, level).split(', ')
            tests_of_level = tests_dict[level]
            amount_of_questions = len(tests_of_level)
            question = tests_of_level[num_of_question]["question"]
            markup = inline_menu_keyboard(tests_of_level[num_of_question]["options"].items(), rows=2)
            bot.edit_message_text(chat_id=user_id, message_id=message_id, text=(f'{level}. Вопрос {int(num_of_question)}/{amount_of_questions}\n\n'
                                       f'{question}'), reply_markup=markup)

    elif call.data in ['1', '2', '3', '4']:
        if not is_user_in_tests(user_id):
            bot.send_message(user_id, 'запустите тест заново')
            return
        level = call.message.text[:2]

        tests_of_level = tests_dict[level]
        state, num_of_question, amount_of_correct_answers, message_id = get_tests_info(user_id, level).split(', ')
        amount_of_questions = len(tests_of_level)
        message_id = call.message.id #maybe delete

        chosen_answer = call.data
        correct_answer = tests_of_level[num_of_question]['correct_answer']
        if chosen_answer == correct_answer:
            amount_of_correct_answers = int(amount_of_correct_answers) + 1
        if int(num_of_question) == amount_of_questions:

            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                  text=(f'В тесте уровня {level} ваш результат {amount_of_correct_answers} '
                                        f'правильных ответов из {amount_of_questions}\n\n'
                                        f'СУПЕР ГУД, {call.from_user.first_name}.'))
            add_level_info(user_id, level, f'Finished, {int(num_of_question)+1}, {amount_of_correct_answers}, {"None"}')
            return
        add_level_info(user_id, level, f'Start, {int(num_of_question)+1}, {amount_of_correct_answers}, {message_id}')
        question = tests_of_level[str(int(num_of_question) + 1)]["question"]
        markup = inline_menu_keyboard(tests_of_level[str(int(num_of_question) + 1)]["options"].items(), rows=2)
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                              text=(f'{level}. Вопрос {int(num_of_question) + 1}/{amount_of_questions}\n\n'
                                    f'{question}'), reply_markup=markup)

    elif call.data == 'dialog':

        if not is_user_amount_limit(user_id):
            bot.send_message(user_id, ('Бот достиг максимального числа пользователей. '
                                       'К сожалению, вы не сможете им воспользоваться.'))

            logging.info(f'Amount of users is full and user_id {user_id} tried to connect to the bot')
            return

        markup = inline_menu_keyboard([['Тесты', 'Null'], ['Диалог', 'Null'], ['Вокабуляр', 'Null']], rows=3)
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=markup)
        update_start_dialog(user_id, 'True')
        markup = inline_menu_keyboard([['Задай ты', 'dialog_bot'], ['Я задам', 'dialog_user']], rows=3)
        bot.send_message(user_id, 'Хотите, чтобы я задал тему беседы или же вы зададите ее сами?', reply_markup=markup)

    elif call.data in ['dialog_bot', 'dialog_user']:
        markup = inline_menu_keyboard([['Задай ты', 'Null'], ['Я задам', 'Null']], rows=3)
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=markup)

        if call.data == 'dialog_bot':
            update_theme_dialog(user_id, 'bot')
            initial_text = random.choice(topics)
        elif call.data == 'dialog_user':
            update_theme_dialog(user_id, 'user')
            initial_text = 'What do you want to talk about?'

        last_session_id = get_last_session(user_id)
        insert_row_into_prompts((user_id, 'assistant', initial_text, last_session_id + 1))

        status, output = tts(user_id, initial_text)

        if status == 'SUCCESS':
            update_tts_tokens_in_limits(user_id, len(initial_text))

            markup = menu_keyboard(['✍ Перевести на русский'])

            bot.send_message(user_id, 'Here we go!!!\nВы сможете завершить диалог командой /stop_dialog')
            bot.send_voice(user_id, output)
            text = get_markdownv2_text(initial_text)
            bot.send_message(user_id, f'"""||{text}||"""', parse_mode='MarkdownV2', reply_markup=markup)

        elif status == 'LIMITS':
            markup = menu_keyboard(['✍ Перевести на русский'])
            bot.send_message(output)
            bot.send_message(user_id, 'Here we go!!!\nВы сможете завершить диалог командой /stop_dialog')
            text = get_markdownv2_text(initial_text)
            bot.send_message(user_id, f'"""||{text}||"""', parse_mode='MarkdownV2', reply_markup=markup)
            return

        elif status == 'IEM_ERROR':
            bot.send_message(output)
            return

        update_session_id(user_id, last_session_id+1)


@bot.message_handler(content_types=['voice', 'text'])
def chatting(message: Message):
    user_id = message.from_user.id

    if get_start_dialog(user_id) == 'False':
        bot.send_message(user_id, "Вы еще не начали диалог. Начните его через команду /menu")
        return

    if get_theme_dialog(user_id) == 'False':
        bot.send_message(user_id, 'Вы не выбрали тему диалог, пожалуйста, выберите.')
        return

    if message.text == '✍ Перевести на русский':
        original_message, translated_message = get_last_message_and_translation(user_id)
        if translated_message:
            bot.send_message(user_id, 'Текст уже переведен.')
            return
        session_id = get_last_session(user_id)
        is_limit, tokens = is_gpt_tokens_limit_per_message(original_message, SYSTEM_PROMPT_TRANSLATION)
        status, translation = ttt(user_id, original_message, session_id, is_limit, 'translation')

        if status == 'SUCCESS':
            update_gpt_tokens_in_limits(user_id, tokens)
            session_id = get_last_session(user_id)
            bot.send_message(user_id, translation)
            update_message_translation(user_id, translation)
            return
        elif status in ['IEM_ERROR', 'LIMIT', 'TTT_ERROR']:
            bot.send_message(user_id, translation)
            return

    if not is_user_amount_limit(user_id):
        bot.send_message(user_id, ('Бот достиг максимального числа пользователей. '
                                   'К сожалению, вы не сможете им воспользоваться.'))
        logging.info(f'Amount of users is full and user_id {user_id} tried to connect to the bot')
        return

    if not user_in_table(user_id):
        bot.send_message(user_id, 'Нажмите для начала /start, для регистрации.')
        logging.warning(f'User_id {user_id} got access to commands without registration')
        return

    if message.content_type == 'voice':

        file_id = message.voice.file_id  # получаем id голосового сообщения
        file_info = bot.get_file(file_id)  # получаем информацию о голосовом сообщении
        file = bot.download_file(file_info.file_path)  # скачиваем голосовое сообщение

        status, output = stt(user_id, file, message.voice.duration, 'english')

        if status == 'SUCCESS':
            text = output
            update_stt_blocks_in_limits(user_id, ceil(message.voice.duration / 15))
        elif status in ['LIMIT', 'IEM_ERROR', 'STT_ERROR']:
            bot.send_message(user_id, output)
            return

        if not text:
            status, output = stt(user_id, file, message.voice.duration, 'russian')

            if status == 'SUCCESS':
                text = output
                update_stt_blocks_in_limits(user_id, ceil(message.voice.duration / 15))
            elif status in ['LIMIT', 'IEM_ERROR', 'STT_ERROR']:
                bot.send_message(user_id, output)
                return

        if not text:
            bot.send_message(user_id, 'Не удалось распознать речь. Учтите, что бот понимает только английский и русский.')
            return
    else:
        text = message.text

    session_id = get_last_session(user_id)
    insert_row_into_prompts((user_id, "user", text, session_id))
    is_limit, tokens = is_gpt_tokens_limit_per_message(text, SYSTEM_PROMPT)
    status, gpt_text = ttt(user_id, text, session_id, is_limit, 'generating')

    if status == 'SUCCESS':
        update_gpt_tokens_in_limits(user_id, tokens)
        session_id = get_last_session(user_id)
        insert_row_into_prompts((user_id, "assistant", gpt_text, session_id))
    elif status in ['IEM_ERROR', 'LIMIT', 'TTT_ERROR']:
        bot.send_message(user_id, gpt_text)
        return

    #return
    status, output = tts(user_id, gpt_text)
    markup = menu_keyboard(['✍ Перевести на русский'])
    if status == 'SUCCESS':
        update_tts_tokens_in_limits(user_id, len(gpt_text))

        bot.send_voice(user_id, output)
        text = get_markdownv2_text(gpt_text)
        bot.send_message(user_id, f'"""||{text}||"""', parse_mode='MarkdownV2', reply_markup=markup)

    elif status in ['LIMITS', 'IEM_ERROR', 'TTS_ERROR']:
        bot.send_message(user_id, gpt_text)
        bot.send_message(user_id, output, reply_markup=markup)



if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename='logging.txt',
        filemode='w'
    )
    with open('tests.json', 'r', encoding='utf-8') as file:
        tests_dict = json.load(file)

    # Создаем три таблицы: одна для тестов, другая - для лимитов токенов и блоков пользователей, еще другая - для промптов.
    create_table_tests()
    create_table_limits()
    create_table_prompts()
    logging.info('Tables are created')

    # Создаем меню в телеграмме
    c1 = BotCommand(command='start', description='Начать взаимодействие с ботом')
    c2 = BotCommand(command='help', description='Помощь с ботом')
    c3 = BotCommand(command='menu', description='Открывает меню взаимодействия с ботом')
    c4 = BotCommand(command='stop_dialog', description='Останавливает диалог с ботом')
    bot.set_my_commands([c1, c2, c3, c4])

    bot.polling()