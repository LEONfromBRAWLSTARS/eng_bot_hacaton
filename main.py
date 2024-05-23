from telebot import TeleBot
from telebot.types import Message, CallbackQuery, BotCommand
from config import BOT_TOKEN, SYSTEM_PROMPT, SYSTEM_PROMPT_TRANSLATION

from validation import (is_user_amount_limit, is_gpt_tokens_limit_per_message)
from database import (create_table_tests, add_user_to_tests_table, get_tests_info, is_user_in_tests, add_level_info, create_table_prompts, create_table_limits, user_in_table,
                      insert_row_into_limits, update_tts_tokens_in_limits, insert_row_into_prompts,
                      update_stt_blocks_in_limits, update_gpt_tokens_in_limits, get_last_session,
                      update_session_id, get_start_dialog, get_theme_dialog, update_start_dialog, update_theme_dialog,
                      update_message_translation, get_last_message_and_translation, is_user_in_words, get_words, add_word, add_user_to_words_table, create_table_words,
                      create_table_user_words, is_user_in_user_words, get_user_words_info, add_user_to_user_words, add_level_user_words_info,
                      create_table_all_words, is_user_in_all_words_table, add_user_to_all_words_table, get_info_all_words, add_info_all_words, update_location_all_words, add_bound_for_repeating_words, update_info_all_words)
import logging
from math import ceil
from keyboards import menu_keyboard, inline_menu_keyboard
from info import topics
from utils import get_markdownv2_text, get_word, deque_manipulation, deleting_tildas
from dialog_pipeline import stt, ttt, tts
import random
import json
from vocab import get_info_of_word, get_translation
from vocab_func import translate
import time
bot = TeleBot(token=BOT_TOKEN)


@bot.message_handler(commands=['vocab'])
def vocab(message: Message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'введите слово для его перевода')
    bot.register_next_step_handler(message=message, callback=translate)


def translate(message: Message, state='show_word'):

    #if not is_user_in_words(user_id):
        #add_user_to_words_table(user_id)

    translation, error = get_translation(message)
    definition, example, audio, error = get_info_of_word(message)
    resp = ''
    if state=='show_word':
        resp = f'📌 Слово {message} 📌\n'
    if error != None or (translation == None and definition == None and example == None and audio == None):

        return False, False

    #add_word(user_id, message)
    #print(get_words(user_id))

    if translation:
        trans = ", ".join(translation)
        resp += f'*Meaning*: {trans}\n'

    if definition:
        resp += f'*Definition*: {definition}\n'

    if example:
        resp += f'*Example*: {example}\n'

    if audio:
        return resp, audio
    return resp, False


# Сюда отправляется пользователь, когда он хочет добавить свое слово в словарь для повторения.
def translate_user_message(message: Message):
    user_id = message.from_user.id
    # Так как мы храним слова пользователя в виде строки, отделенные друг от друга ~, то мы должны прописать исключение
    user_word = deleting_tildas(message.text)
    if not user_word:
        bot.send_message(user_id, 'Введите фразу или слово')
        return
    # Если пользователь вводит что-то слишком большое
    if len(user_word) > 100:
        markup = inline_menu_keyboard([['Выход', 'exit_adding_word']], rows=1)
        bot.send_message(user_id, 'Слишком большое выражение, введите поменьше', reply_markup=markup)
        bot.register_next_step_handler(message, callback=translate_user_message)
        return

    text, audio = translate(user_word)
    update_info_all_words(user_id, 'user_words', user_word)
    # Если нет слова
    if not text:
        update_location_all_words(user_id, 'adding_translation')
        bot.send_message(user_id, 'Не получилось перевести ваше слово или фразу, добавьте свой перевод')
        bot.register_next_step_handler(message, callback=user_translation)
        return
    # Если получилось перевести слово или фразу, то даем возможность написать свой перевод или же оставить из словаря
    markup = inline_menu_keyboard([['Оставить перевод', 'leave_api_translation'],
                                   ['Добавить свой перевод', 'adding_own_translation']], rows=2)
    bot.send_message(user_id, text, reply_markup=markup)


# Здесь пользователь оказывается, когда он вводит свой перевод слова или выражения
def user_translation(message: Message):
    user_id = message.from_user.id
    # Избавляемся от тильд
    user_word = deleting_tildas(message.text)
    if not user_word:
        bot.send_message(user_id, 'Введите перевод')
        return
    update_location_all_words(user_id, 'None')
    # Если слишком длинный перевод слова или фразы
    if len(user_word) > 150:
        bot.send_message(user_id, 'Слишком длинный перевод, введите покороче')
        bot.register_next_step_handler(message, callback=user_translation)
    # Добавляем слово и его перевод
    add_info_all_words(user_id, 'translation', user_word)
    # в "user_word" мы записываем слова, которые пользователь сам пожелал добавить(изначальная функция - буффер для
    # пользовательского ввода для того, чтобы избежать всевозможных баггов.
    word = get_info_all_words(user_id, 'user_words').split('~')[-1]
    add_info_all_words(user_id, 'words_to_learn', word)
    bot.send_message(user_id, 'Новое слово добавлено')


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

    # Я искренне прошу прощения перед всеми, кто решит заглянуть в следующие 150-200 строк кода.
    # Начинается ветвь вокабуляра
    elif call.data == 'vocabulary':
        markup = inline_menu_keyboard([['Учить слова и выражения', 'learn_new_words'],
                                       ['Добавить свои слова', 'add_new_words'],
                                       ['Повторить изученные', 'repeat_words'],
                                       ['Вывести изученные слова', 'all_words']], rows=2)
        bot.send_message(user_id, 'Опции представлены ниже', reply_markup=markup)
    # Пользователь нажимает "учить новые слова" из json файла
    elif call.data == 'learn_new_words':
        markup = inline_menu_keyboard([['A1', 'A1_words'], ['A2', 'A2_words'], ['B1', 'B1_words'],
                                       ['B2', 'B2_words'], ['C1', 'C1_words'], ['C2', 'C2_words']], rows=2)
        bot.send_message(user_id, 'Выберите уровень, слова которого вы хотите изучить', reply_markup=markup)
    # Пользователь выбирает уровень слов
    elif call.data in ['A1_words', 'A2_words', 'B1_words', 'B2_words', 'C1_words', 'C2_words']:
        if call.data in ['B1_words', 'B2_words', 'C1_words', 'C2_words']:
            bot.send_message(user_id, 'temporary not available')
            return
        if not is_user_in_user_words(user_id):
            add_user_to_user_words(user_id)
        level = call.data[:2]
        # Извлекаем всю необходимую информацию о пользователе на этом этапе
        status, num_of_word, amount_of_learned, *message_id = get_user_words_info(user_id, level).split(', ')
        # Если пользователь уже начал учить слова, но потом еще раз нажал эту кнопку, то мы просто удаляем старый блок
        # сообщения, чтобы избежать всевозможных ошибок
        if status == 'Start':
            bot.delete_messages(chat_id=user_id, message_ids=message_id)
        # Извлекаем слово, которое надо показать пользователю
        word_to_show = words_dict[level][int(num_of_word)]
        # Обращаемя к АПИ для перевода, описания, произношения слова
        text, audio = translate(word_to_show)
        markup = inline_menu_keyboard([['Знаю', f'{level}_known_word'], ['Не знаю', f'{level}_unknown_word'],
                                       ['Выход', f'{level}_exit']], rows=2)
        text = get_markdownv2_text(text)
        # Если мы получили перевод и произношение
        if text and audio:
            message1 = bot.send_message(user_id, text, reply_markup=markup, parse_mode='MarkdownV2')
            message2 = bot.send_voice(user_id, audio)
            add_level_user_words_info(user_id, level, f'Start, {num_of_word}, {amount_of_learned}, {message1.message_id}, {message2.message_id}')
        # Если мы получили только перевод
        elif text:
            message = bot.send_message(user_id, text, reply_markup=markup, parse_mode='MarkdownV2')
            add_level_user_words_info(user_id, level, f'Start, {num_of_word}, {amount_of_learned}, {message.message_id}')
        # Если мы не получили ни перевода, ни произношения
        else:
            bot.send_message(user_id, 'Возникла ошибка')
            return

    elif call.data in ['A1_known_word', 'A1_unknown_word', 'A2_known_word', 'A2_unknown_word',
                       'B1_known_word', 'B1_unknown_word', 'B2_known_word', 'B2_unknown_word',
                       'C1_known_word', 'C1_unknown_word', 'C2_known_word', 'C2_unknown_word',
                       'A1_exit', 'A2_exit', 'B1_exit', 'B2_exit', 'C1_exit', 'C2_exit']:
        if not is_user_in_all_words_table(user_id):
            add_user_to_all_words_table(user_id)
        # Извлекаем вот таким вот варварским способом уровень, значение и слово
        level = call.data[:2]
        state = call.data[3:]
        word = get_word(call.message.text)
        # Получаем всю необходимую инфу
        status, num_of_word, amount_of_learned, *message_id = get_user_words_info(user_id, level).split(', ')
        # Получаем количество слово в уровне
        amount_of_level_words = len(words_dict[level])
        # Если количество слов, которые пользователь прошел сравнялось с количеством слов в уровне, то завершаем
        if num_of_word == amount_of_level_words:
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text='Слова закончились в уровне')
            add_level_user_words_info(user_id, level, f'Finished, {num_of_word}, {amount_of_learned}, {message_id}')
            return
        # Если пользователь нажал выход из режима изучения новых слов
        if state == 'exit':
            add_level_user_words_info(user_id, level, f'None, {num_of_word}, {amount_of_learned}, None')
            bot.delete_messages(chat_id=user_id, message_ids=message_id)
            return
        # Если пользователь нажал кнопку, что он уже знает это слово
        elif state == 'known_word':
            amount_of_learned = int(amount_of_learned) + 1
            # Добавляем слово в колонку слов, которые он уже знает
            add_info_all_words(user_id, 'learned_words', word)
            add_info_all_words(user_id, 'time', time.time())
        # Если пользователь нажал кнопку, что он не знает этого слова
        elif state == 'unknown_word':
            add_info_all_words(user_id, 'words_to_learn', word)
            add_info_all_words(user_id, 'translation', 'None')
            add_info_all_words(user_id, 'time', time.time())

        num_of_word = int(num_of_word) + 1

        word_to_show = words_dict[level][int(num_of_word)]
        text, audio = translate(word_to_show)

        markup = inline_menu_keyboard([['Знаю', f'{level}_known_word'], ['Не знаю', f'{level}_unknown_word'],
                                       ['Выход', f'{level}_exit']], rows=2)
        if text and audio:
            # Тут короче манипуляция с кнопками.
            if len(message_id) == 2:
                bot.delete_message(chat_id=user_id, message_id=message_id[1])

            message1 = bot.edit_message_text(chat_id=user_id, message_id=message_id[0], text=text,
                                             reply_markup=markup, parse_mode='HTML')
            message2 = bot.send_voice(user_id, audio)
            add_level_user_words_info(user_id, level, f'Start, {num_of_word}, {amount_of_learned}, {message1.message_id}, {message2.message_id}')
        elif text:
            # Тут тоже манипуляция с кнопками
            if len(message_id) == 2:
                bot.delete_message(chat_id=user_id, message_id=message_id[1])
            message1 = bot.edit_message_text(chat_id=user_id, message_id=message_id[0], text=text,
                                             reply_markup=markup, parse_mode='HTML')
            add_level_user_words_info(user_id, level, f'Start, {num_of_word}, {amount_of_learned}, {message1.message_id}')
        else:
            bot.send_message(user_id, 'Возникла ошибка')
            return
    # Режим, если пользователь захочет добавить свои слова
    elif call.data == 'add_new_words':
        if not is_user_in_all_words_table(user_id):
            add_user_to_all_words_table(user_id)
        user_location = get_info_all_words(user_id, 'user_location')
        # Обработка ошибок, если пользователь вдруг уже нажимал эту кнопку, ввел слово, но не добавил его перевод.
        if user_location == 'adding_translation':
            bot.send_message(user_id, 'Добавьте перевод вашего слова')
            return
        # Даем пользователю возможность выйти из режима, если он случайно сюда зашел
        markup = inline_menu_keyboard([['Выход', 'exit_adding_word']], rows=1)
        bot.send_message(user_id, 'Отправьте слово для добавления', reply_markup=markup)
        bot.register_next_step_handler(call.message, callback=translate_user_message)
    # Если пользователь не захотел добавлять свое слово для изучения
    elif call.data == 'exit_adding_word':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        update_location_all_words(user_id, 'None')
        bot.clear_step_handler_by_chat_id(user_id)
    # Тут пользователь решает, оставить ли ему перевод, который получился из API, либо же добавить свой перевод
    elif call.data in ['leave_api_translation', 'adding_own_translation']:
        # Блокируем кнопки, для избежания ошибок
        markup = inline_menu_keyboard([['Оставить перевод', 'Null'],
                                       ['Добавить свой перевод', 'Null']], rows=2)
        bot.edit_message_reply_markup(chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)
        # Оставляет перевод API
        if call.data == 'leave_api_translation':
            update_location_all_words(user_id, 'None')
            word = get_info_all_words(user_id, 'user_words').split('~')[-1]
            add_info_all_words(user_id, 'words_to_learn', word)
            add_info_all_words(user_id, 'translation', call.message.text)
            bot.send_message(user_id, 'Перевод добавлен')
        # Добавляет свой перевод
        elif call.data == 'adding_own_translation':
            bot.send_message(user_id, 'Введите перевод')
            bot.register_next_step_handler(call.message, callback=user_translation)
    # Если пользователь выбирает повторять слова
    elif call.data == 'repeat_words':
        # Если пользователя нет в таблице слов, значит у него нет слов
        if not is_user_in_all_words_table(user_id):
            add_user_to_all_words_table(user_id)
            bot.send_message(user_id, 'У вас еще нет слов для повторения')
            return
        # Извлекаем слово
        word = get_info_all_words(user_id, 'words_to_learn').split('~')[0]
        if not word:
            bot.send_message(user_id, 'У вас еще нет слов для повторения')
            return
        # Извлекаем перевод, если он есть
        translation = get_info_all_words(user_id, 'translation').split('~')[0]
        # Если у нас нет перевода(это слово добавил пользователь,так как для слов пользователя мы сохраняем его перевод,
        # а для слов из словаря - нет
        if translation.strip() == 'None':
            translation, audio = translate(word, state='not_showing_word')
        translation = get_markdownv2_text(translation)
        # Это специальный, так скажем, флаг, для того, чтобы определять, когда пользователю нужно закончить повторять
        # слова из списка слов для повторений. В следующем блоке описано более подробно
        add_bound_for_repeating_words(user_id, word)
        # maybe need to clear addition words
        markup = inline_menu_keyboard([['Еще повторить', 'not_learned_word_yet'],
                                       ['Теперь знаю это слово', 'learned_word']], rows=2)
        bot.send_message(user_id, f'{word}\n||{translation}||', reply_markup=markup, parse_mode='MarkdownV2')
    # Если пользователь еще не выучил слово и хочет в будущем его повторить, или же пользователь выучил его и не надо
    # это слово больше показывать.
    elif call.data in ['not_learned_word_yet', 'learned_word']:
        # Извлекаем все слова для повторения и их переводы
        words = get_info_all_words(user_id, 'words_to_learn').split('~')[:-1]
        translations = get_info_all_words(user_id, 'translation').split('~')[:-1]
        bound_word = get_info_all_words(user_id, 'bound_for_repeating_words')
        if call.data == 'not_learned_word_yet':
            # Тут самый прикол начинается, короче, переходите по функции в модуль utils, там описано
            updated_words = deque_manipulation(words, 'stay')
            updated_translations = deque_manipulation(translations, 'stay')
        elif call.data == 'learned_word':
            updated_words = deque_manipulation(words, 'remove')
            updated_translations = deque_manipulation(translations, 'remove')
            add_info_all_words(user_id, 'learned_words', words[0])
        if updated_words and updated_translations:
            update_info_all_words(user_id, 'words_to_learn', '~'.join(updated_words)+'~')
            update_info_all_words(user_id, 'translation', '~'.join(updated_translations)+'~')
        else:
            update_info_all_words(user_id, 'words_to_learn', '')
            update_info_all_words(user_id, 'translation', '')
        # Условие, если мы повторили все слова, если нарвались на
        if len(words) < 2 or words[1] == bound_word:
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text='Вы повторили все слова')
            add_info_all_words(user_id, 'bound_for_repeating_words', '')
            return
        # Берем следующее слово и перевод.
        word = words[1]
        translation = translations[1]
        # Если нет перевода.
        if translation.strip() == 'None':
            translation, audio = translate(word, state='not_showing_word')
        translation = get_markdownv2_text(translation)
        markup = inline_menu_keyboard([['Еще повторить', 'not_learned_word_yet'],
                                       ['Теперь знаю это слово', 'learned_word']], rows=2)
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                              text=f'{word}\n||{translation}||', reply_markup=markup, parse_mode='MarkdownV2')

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

    with open('words.json', 'r', encoding='utf-8') as file:
        words_dict = json.load(file)
    # Создаем три таблицы: одна для тестов, другая - для лимитов токенов и блоков пользователей, еще другая - для промптов.
    create_table_tests()
    create_table_limits()
    create_table_prompts()
    create_table_words()
    create_table_user_words()
    create_table_all_words()
    logging.info('Tables are created')

    # Создаем меню в телеграмме
    c1 = BotCommand(command='start', description='Начать взаимодействие с ботом')
    c2 = BotCommand(command='help', description='Помощь с ботом')
    c3 = BotCommand(command='menu', description='Открывает меню взаимодействия с ботом')
    c4 = BotCommand(command='stop_dialog', description='Останавливает диалог с ботом')
    bot.set_my_commands([c1, c2, c3, c4])

    bot.polling()