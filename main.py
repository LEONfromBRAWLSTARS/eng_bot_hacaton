from telebot import TeleBot
from telebot.types import Message, CallbackQuery, BotCommand
from config import BOT_TOKEN, SYSTEM_PROMPT, SYSTEM_PROMPT_TRANSLATION

from validation import (is_user_amount_limit, is_gpt_tokens_limit_per_message)
from database import (create_table_tests, add_user_to_tests_table, get_tests_info, is_user_in_tests, add_level_info, create_table_prompts, create_table_limits, user_in_table,
                              insert_row_into_limits, update_tts_tokens_in_limits, insert_row_into_prompts,
                              update_stt_blocks_in_limits, update_gpt_tokens_in_limits, get_last_session,
                              update_session_id, get_start_dialog, get_theme_dialog, update_start_dialog, update_theme_dialog,
                              update_message_translation, get_last_message_and_translation, 
                              create_table_words, add_word, get_words, is_word_in_table, change_trans_in_db)
import logging
from math import ceil
from keyboards import menu_keyboard, inline_menu_keyboard
from info import topics
from utils import get_markdownv2_text
from dialog_pipeline import stt, ttt, tts
import random
import json
from vocab import get_info_of_word, get_translation
bot = TeleBot(token=BOT_TOKEN)


def translate(message: Message):
    user_id = message.from_user.id

    translation, error = get_translation(message.text)
    definition, example, audio, error = get_info_of_word(message.text)
    resp = f'📌 Слово {message.text} 📌\n'
    if error != None or (translation == None and definition == None and example == None and audio == None):
        bot.send_message(user_id, 'Не удалось ничего найти в словаре по этому слову(')
        return None

    if translation:
        trans = ", ".join(translation)
        resp += f'<b>Meaning</b>: {trans}\n'

    if definition != None:
        resp += f'<b>Definition</b>: {definition}\n'

    if example != None:
        resp += f'<b>Example</b>: {example}\n'
    bot.send_message(user_id, resp, parse_mode='HTML')

    if audio != None:
        bot.send_voice(user_id, audio)
    
    return translation


def add_new_word(user_id, word, translation):
    if is_word_in_table(user_id, word):
        bot.send_message(user_id, "Это слово уже есть в списке")
    else:
        add_word(user_id, word, translation, False)
        bot.send_message(user_id, "Слово добавлено в список")

def words_handler(message):
    user_id = message.chat.id
    if message.content_type != 'text':
        bot.send_message(user_id, "Нужно ввести слово")
        bot.register_next_step_handler(message, words_handler)
        
    translation = translate(message)
    markup = inline_menu_keyboard([['Изменить перевод', 'change_trans']], rows = 1)
    if translation != None:
        translation = ", ".join(translation)
        add_new_word(user_id, message.text.lower(), translation)
        bot.send_message(user_id, f"Если вы хотите изменить перевод, то можете сделать это нажав кнопку внизу.", reply_markup=markup)
    else:
        bot.send_message(user_id, "Но можете добавить перевод сами", reply_markup=markup)


def trans_handler(message):
    user_id = message.chat.id
    if message.content_type != 'text':
        bot.send_message(user_id, "Нужно ввести слово и его перевод")
        bot.register_next_step_handler(message, words_handler)
    parts = message.text.split("-", 1)
    if len(parts) == 1:
        bot.send_message(user_id, "Не получилось добавить перевод. В сообщении обязательно должно быть тире.")
        return
    word = parts[0].lstrip().rstrip().lower()
    trans = parts[1].lstrip().rstrip().lower()

    if is_word_in_table(user_id, word):
        change_trans_in_db(user_id, word, trans)
    else:
        add_word(user_id, word, trans)
    bot.send_message(user_id, f"Для слова {word} установлен такой перевод: {trans}")
    




@bot.message_handler(commands=['start'])
def start(message: Message):
    user_id = message.from_user.id

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
    markup = inline_menu_keyboard([['Тесты', 'tests'], ['Диалог', 'dialog'], ['Вокабуляр', 'vocabulary'], ['Список переведенных слов', 'all_words']], rows=3)
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
    # мы нажимаем кнопку Тесты
    if call.data == 'tests':
        if not is_user_in_tests(user_id):
            add_user_to_tests_table(user_id)
        # не обращайте внимание на 2 строки внизу
        # markup = inline_menu_keyboard([['Тесты', 'Null'], ['Диалог', 'Null'], ['Вокабуляр', 'Null']], rows=3)
        # bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=markup)
        markup = inline_menu_keyboard([['A1', 'A1'], ['A2', 'A2'], ['B1', 'B1'],
                                       ['B2', 'B2'], ['C1', 'C1'], ['C2', 'C2']], rows=2)
        bot.send_message(user_id, ('Внизу представлены тесты различных уровней, '
                                   'выберите подходящий и вперед!'), reply_markup=markup)
    # мы выбираем уровень тестов
    elif call.data in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
        # если айди пользователя еще не записалось в базу данных, то мы записываем
        if not is_user_in_tests(user_id):
            add_user_to_tests_table(user_id)
        if call.data in ['C1', 'C2']:
            bot.send_message(user_id, 'В разработке. Недоступны C1, C2')
            return

        chosen_level = call.data  # выбранный пользователем уровень (A1, A2, B1 ...)
        tests_of_level = tests_dict[chosen_level]  # мы извлекаем тесты из json файла для соответствующего уровня
        # мы берем инфу: state - в каком состоянии находится пользователь по тесту(None - не начинал тест вообще,
        # Start - начал его и проходит, Finished - завершил тест), num_of_question - номер вопроса,
        # который проходит пользователь, amount_of_correct_answers - количество правильных ответов в тесте, message_id -
        # нужен будет в будущем, чтобы избежать всевозможных багов, связанных с кнопками.
        state, num_of_question, amount_of_correct_answers, message_id = get_tests_info(user_id, chosen_level).split(', ')
        amount_of_questions = len(tests_of_level)  # количество вопросов в тесте

        # если пользователь тест уже прошел и нажал на него еще раз, то мы ему говорим об этом.
        if state == 'Finished':
            markup = inline_menu_keyboard([['Пройти еще раз', 'test_start_over'],
                                           ['Выйти', 'exit']], rows=1)
            bot.send_message(chat_id=user_id,
                             text=(f'{chosen_level} уровень. Вы уже прошли данное тестирование, '
                                   f'хотите пройти его еще раз?'), reply_markup=markup)
            return
        # если пользователь проходил тест, не завершил его и бросил, а потом нажал на него еще раз, то мы предлагаем ему
        # либо продолжить тест, либо начать заново
        if state == "Start":
            # мы удаляем старое сообщение с тестом для избежания багов и поддержания чистоты, как раз тут message_id
            # используется. Message_id - id старого сообщения с тестом, который мы удаляем
            bot.delete_message(chat_id=user_id, message_id=message_id)
            markup = inline_menu_keyboard([['Продолжить тестирование', 'test_continue'],
                                           ['Начать сначала', 'test_start_over']], rows=1)
            bot.send_message(user_id, (f'{chosen_level} уровень. У вас есть незавершенное тестирование\n'
                                       f'Хотите продолжить?'), reply_markup=markup)
        # если пользователь проходит тест в данный момент в штатном режиме
        else:
            # Получаем вопрос из нашего json
            question = tests_of_level[num_of_question]["question"]
            # Создаем клавиатуру с опциями для ответа
            markup = inline_menu_keyboard(tests_of_level[num_of_question]["options"].items(), rows=2)
            message = bot.send_message(user_id, (f'{call.data}. Вопрос {int(num_of_question)}/{amount_of_questions}\n\n'
                                       f'{question}'), reply_markup=markup)
            # Обновляем информацию о пользователе в таблице тестов.
            # Стоить заметить, что мы передаем строку в таблицу, ключевые элементы которой разделены через запятую.
            # Элементы (state, num_of_question, amount_of_correct_answers, message_id). Я их расписал вверху
            add_level_info(user_id, chosen_level,
                           f'Start, {num_of_question}, {amount_of_correct_answers}, {message.message_id}')

    # обработчик кнопок "Продолжить тестирование", "Начать сначала", "Выход"
    elif call.data in ['test_continue', 'test_start_over', 'exit']:
        # Получаем уровень теста, на котором сейчас пользователь(я сделал это не очень красиво, так как я беру уровень
        # из текста сообщения(первые два знака), в таком случае при изменении текста с кнопками
        # "Продолжить тестирование", "Начать сначала", "Выход" нам нужно будет всегда обязательно указывать в сообщении
        # уровень теста (А1, А2 ...) и также надо смотреть, где мы этот уровень написали, чтобы потом срезом строки
        # вынуть уровень)
        level = call.message.text[:2]
        # Если нажали кнопку "Выход". (Мы удаляем сообщение, чтобы глаза не маячило и, опять же, избежать багов)
        if call.data == 'exit':
            bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        # Если нажали кнопку "Продолжить тестирование". (Мы берем инфу из БД и продолжаем тест с того же места)
        if call.data == 'test_continue':
            # Информация по переменным указана в 'if call.data in ['A1', 'A2'...' вверху. (Можете через ctrl + F найти)
            tests_of_level = tests_dict[level]
            state, num_of_question, amount_of_correct_answers, message_id = get_tests_info(user_id, level).split(', ')
            amount_of_questions = len(tests_of_level)
            question = tests_of_level[num_of_question]["question"]

            add_level_info(user_id, level,
                           f'Start, {num_of_question}, {amount_of_correct_answers}, {call.message.id}')
            markup = inline_menu_keyboard(tests_of_level[num_of_question]["options"].items(), rows=2)
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                  text=(f'{level}. Вопрос {int(num_of_question)}/{amount_of_questions}\n\n'
                                        f'{question}'), reply_markup=markup)
        # Если пользователь нажал "Начать сначала". (Мы обновляем всю его информацию по этому тесту и начинаем сначала)
        elif call.data == 'test_start_over':
            # Обновляем всю информацию по тесту
            state = 'Start'
            num_of_question = '1'
            amount_of_correct_answers = 0
            message_id = call.message.message_id
            # Извлекаем вопрос из json
            tests_of_level = tests_dict[level]
            amount_of_questions = len(tests_of_level)
            question = tests_of_level[num_of_question]["question"]

            markup = inline_menu_keyboard(tests_of_level[num_of_question]["options"].items(), rows=2)
            bot.edit_message_text(chat_id=user_id, message_id=message_id,
                                  text=(f'{level}. Вопрос {num_of_question}/{amount_of_questions}\n\n'
                                        f'{question}'), reply_markup=markup)
            add_level_info(user_id, level, f'{state}, {num_of_question}, {amount_of_correct_answers}, {message_id}')
    # Используется, когда пользователь нажимает кнопки ответов на вопросы теста
    elif call.data in ['1', '2', '3', '4']:
        if not is_user_in_tests(user_id):
            bot.send_message(user_id, 'запустите тест заново')
            return
        # Опять берем уровень теста
        level = call.message.text[:2]

        tests_of_level = tests_dict[level]
        state, num_of_question, amount_of_correct_answers, message_id = get_tests_info(user_id, level).split(', ')
        amount_of_questions = len(tests_of_level)
        message_id = call.message.id  # maybe useless
        # Смотрим выбранный пользователем ответ и правильный ответ, а потом еще и сравниваем их
        chosen_answer = call.data
        correct_answer = tests_of_level[num_of_question]['correct_answer']

        if chosen_answer == correct_answer:
            amount_of_correct_answers = int(amount_of_correct_answers) + 1
        # Если номер отвеченного вопроса пользователя сравнялся с количеством вопросов в тесте, то мы его заканчиваем
        if int(num_of_question) == amount_of_questions:

            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                  text=(f'В тесте уровня {level} ваш результат {amount_of_correct_answers} '
                                        f'правильных ответов из {amount_of_questions}\n\n'
                                        f'СУПЕР ГУД, {call.from_user.first_name}.'))
            # Добавляем инфу о том, что тест завершен
            add_level_info(user_id, level, f'Finished, {int(num_of_question)+1}, {amount_of_correct_answers}, {"None"}')
            return
        # Иначе, если тест у нас идет в штатном режиме и пользователь только проходит его
        add_level_info(user_id, level, f'Start, {int(num_of_question)+1}, {amount_of_correct_answers}, {message_id}')
        question = tests_of_level[str(int(num_of_question) + 1)]["question"]
        markup = inline_menu_keyboard(tests_of_level[str(int(num_of_question) + 1)]["options"].items(), rows=2)
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                              text=(f'{level}. Вопрос {int(num_of_question) + 1}/{amount_of_questions}\n\n'
                                    f'{question}'), reply_markup=markup)
    # Дальше идет код для кнопочек диалога
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

    # Кнопки для того, чтобы решить, кто будет иницатором беседы
    elif call.data in ['dialog_bot', 'dialog_user']:
        markup = inline_menu_keyboard([['Задай ты', 'Null'], ['Я задам', 'Null']], rows=3)
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=markup)
        # Если бот начинает беседу, то мы берем рандомную тему из списка тем topics из модуля info
        if call.data == 'dialog_bot':
            update_theme_dialog(user_id, 'bot')
            initial_text = random.choice(topics)
        elif call.data == 'dialog_user':
            update_theme_dialog(user_id, 'user')
            initial_text = 'What do you want to talk about?'

        last_session_id = get_last_session(user_id)
        insert_row_into_prompts((user_id, 'assistant', initial_text, last_session_id + 1))

        status, output = tts(user_id, initial_text)

        # Если у нас все супер и мы можем дать пользователю ответ
        if status == 'SUCCESS':
            update_tts_tokens_in_limits(user_id, len(initial_text))

            markup = menu_keyboard(['✍ Перевести на русский'])

            bot.send_message(user_id, 'Here we go!!!\nВы сможете завершить диалог командой /stop_dialog')
            bot.send_voice(user_id, output)
            text = get_markdownv2_text(initial_text)
            bot.send_message(user_id, f'"""||{text}||"""', parse_mode='MarkdownV2', reply_markup=markup)
        # Если пользователь уперся в лимит токенов
        elif status == 'LIMITS':
            markup = menu_keyboard(['✍ Перевести на русский'])
            bot.send_message(output)
            bot.send_message(user_id, 'Here we go!!!\nВы сможете завершить диалог командой /stop_dialog')
            text = get_markdownv2_text(initial_text)
            bot.send_message(user_id, f'"""||{text}||"""', parse_mode='MarkdownV2', reply_markup=markup)
            return
        # Если мы получили ошибку с нейронкой
        elif status == 'IEM_ERROR':
            bot.send_message(output)
            return

        update_session_id(user_id, last_session_id+1)

    elif call.data == 'vocabulary':
        markup = inline_menu_keyboard([['Перевести слово', 'translate'], ['Пополнить словарный запас', 'random_word'], ['Повторить изученное', 'remind_words'], ['Добавить слово', 'input_word'], ['Изменить перевод', 'change_trans']], rows=1)
        bot.send_message(user_id, "Изучай и повторяй английские слова!", reply_markup=markup) 

    elif call.data == 'translate':
        bot.send_message(user_id, 'Введите слово для его перевода:')
        bot.register_next_step_handler(message=call.message, callback=translate)

    elif call.data == 'random_word':
        word = "essential"#как-то получаю слово
        translation, error = get_translation(word)

        bot.send_message(user_id, f'Can you translate this word: {word}?')
        text = get_markdownv2_text(', '.join(translation))
        bot.send_message(user_id, f'Right answer: """||{text}||"""', parse_mode='MarkdownV2')
        markup = inline_menu_keyboard([['Добавить слово', 'input_word']], rows = 1)
        bot.send_message(user_id, 'Если твой ответ правильный, то ты, конечно же, СУПЕР ГУД, а если нет, то можешь добавить его в слова для запоминания', reply_markup=markup)

    elif call.data == 'input_word':
        bot.send_message(user_id, "Отправьте следующем сообщением слово, которое хотите добавить в словарь")
        bot.register_next_step_handler(call.message, words_handler)

    elif call.data == 'change_trans':
        bot.send_message(user_id, "Отправьте следующем сообщением слово и черех тире его варианты перевода(через запятую, еслии их несколько), например: cup - чашка, стакан")
        bot.register_next_step_handler(call.message, trans_handler)

    elif call.data == "remind_words":
        know, dont_know = get_words(user_id)
        word = random.choice(list(know.keys()) + list(dont_know.keys()))
        if bot in know:
            translation = know[word]
        else:
            translation = dont_know[word]

        bot.send_message(user_id, f'Can you translate this word: {word}?')
        bot.send_message(user_id, f'Right answer: """||{translation}||"""', parse_mode='MarkdownV2')
        

    elif call.data == 'all_words':
        know, dont_know = get_words(user_id)
        cnt_unknown = 1
        unknown = ""
        resp = "<b>Новые слова</b>: \n"
        for pair in dont_know.items():
            unknown += f"{cnt_unknown}. {pair[0]}: {pair[1]}\n"
            cnt_unknown += 1
    
        if dont_know  == {}:
            resp += "Вы еще не переводили новые слова. \n"
        else:
            resp += unknown

        resp += "\n <b>Слова, которые уже знаешь</b>: \n"
        if know == {}:
            resp += "Вы еще не отметили выученным никакие слова"
        else:
            know = ', '.join(know.keys())
            resp += know
        
        bot.send_message(user_id, resp, parse_mode='HTML')



# Сюда отправляется весь текст и голосовые сообщения
@bot.message_handler(content_types=['voice', 'text'])
def chatting(message: Message):
    user_id = message.from_user.id

    if get_start_dialog(user_id) == 'False':
        bot.send_message(user_id, "Вы еще не начали диалог. Начните его через команду /menu")
        return

    if get_theme_dialog(user_id) == 'False':
        bot.send_message(user_id, 'Вы не выбрали тему диалог, пожалуйста, выберите.')
        return
    # Если пользователь ввел текст Перевести на русский
    if message.text == '✍ Перевести на русский':
        original_message, translated_message = get_last_message_and_translation(user_id)
        if translated_message:
            bot.send_message(user_id, 'Текст уже переведен.')
            return
        session_id = get_last_session(user_id)
        is_limit, tokens = is_gpt_tokens_limit_per_message(original_message, SYSTEM_PROMPT_TRANSLATION)
        status, translation = ttt(user_id, original_message, session_id, is_limit, 'translation')
        # Если все супер и мы получили сообщение от нейронки
        if status == 'SUCCESS':
            update_gpt_tokens_in_limits(user_id, tokens)
            session_id = get_last_session(user_id)
            bot.send_message(user_id, translation)
            update_message_translation(user_id, translation)
            return
        # Если выскочила ошибка какая либо
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
    # Обрабатываем голосовые
    if message.content_type == 'voice':

        file_id = message.voice.file_id  # получаем id голосового сообщения
        file_info = bot.get_file(file_id)  # получаем информацию о голосовом сообщении
        file = bot.download_file(file_info.file_path)  # скачиваем голосовое сообщение
        # Сначала мы пытаемся расшифровать голосовое с помощью английского расшифровщика
        status, output = stt(user_id, file, message.voice.duration, 'english')

        if status == 'SUCCESS':
            text = output
            update_stt_blocks_in_limits(user_id, ceil(message.voice.duration / 15))
        elif status in ['LIMIT', 'IEM_ERROR', 'STT_ERROR']:
            bot.send_message(user_id, output)
            return
        # Если у нас не получилось расшифровать голосовое с помощью английского расшифровщика, то это либо пользователь
        # начал говорить по русски и расшифровщик его не понял, либо пользователь ничего не сказал, либо сказал невнятно
        if not text:
            # Мы пытаемся расшифровать голосовое русским расшифровщиком
            status, output = stt(user_id, file, message.voice.duration, 'russian')

            if status == 'SUCCESS':
                text = output
                update_stt_blocks_in_limits(user_id, ceil(message.voice.duration / 15))
            elif status in ['LIMIT', 'IEM_ERROR', 'STT_ERROR']:
                bot.send_message(user_id, output)
                return
        # Если и русский расшифровщик ничего не понял, то мы выдаем сообщение пользователю
        if not text:
            bot.send_message(user_id, 'Не удалось распознать речь. Учтите, что бот понимает только английский и русский.')
            return
    # Это если пользователь воспользовался не голосовым вводом, а текстовым.
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
    create_table_words()
    logging.info('Tables are created')

    # Создаем меню в телеграмме
    c1 = BotCommand(command='start', description='Начать взаимодействие с ботом')
    c2 = BotCommand(command='help', description='Помощь с ботом')
    c3 = BotCommand(command='menu', description='Открывает меню взаимодействия с ботом')
    c4 = BotCommand(command='stop_dialog', description='Останавливает диалог с ботом')
    bot.set_my_commands([c1, c2, c3, c4])

    bot.polling()