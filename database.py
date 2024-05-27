import sqlite3

DB_DAME = 'database.db'

TESTS_TABLE = 'tests'
PROMPTS_TABLE = 'prompts'
LIMITS_TABLE = 'limits'
USER_WORDS_TABLE = 'user_words'
ALL_USER_WORDS_TABLE = 'all_user_words'


# Функция выполнения запроса к БД.
def execute_query(query, data=None):
    cursor, connection = get_cursor()
    if data:
        result = cursor.execute(query, data).fetchall()
    else:
        result = cursor.execute(query).fetchall()
    connection.commit()
    connection.close()
    return result


# Создаем курсор.
def get_cursor():
    connection = sqlite3.connect(DB_DAME)
    return connection.cursor(), connection


# Создаем таблицу с пользователем и тестами
# В колонки тестов мы передаем строку с ключевыми параметрами, разделенными запятой. Параметры по порядку: state,
# num_of_question, amount_of_correct_answers, message_id.
# state - в каком состоянии находится пользователь по тесту(None - не начинал тест вообще, Start - начал его и проходит,
# Finished - завершил тест), num_of_question - номер вопроса, который проходит пользователь,
# amount_of_correct_answers - количество правильных ответов в тесте, message_id - id сообщения с тестом, остальные
# значение - все вопросы через запятую, на которые пользователь ответил неверно.
# Выставляем значения по умолчанию для уровней тестов.
def create_table_tests():
    query = f'''
    CREATE TABLE IF NOT EXISTS {TESTS_TABLE}
    (id INTEGER PRIMARY KEY,
    user_id INTEGER,
    A1 TEXT DEFAULT 'None, 1, 0, None, None',
    A2 TEXT DEFAULT 'None, 1, 0, None, None',
    B1 TEXT DEFAULT 'None, 1, 0, None, None',
    B2 TEXT DEFAULT 'None, 1, 0, None, None',
    C1 TEXT DEFAULT 'None, 1, 0, None, None',
    C2 TEXT DEFAULT 'None, 1, 0, None, None');
    '''

    execute_query(query)


# Проверяем, есть ли пользователь в таблице тестов
def is_user_in_tests(user_id):
    query = f'''
        SELECT EXISTS(SELECT 1 FROM {TESTS_TABLE} WHERE user_id = {user_id});
        '''
    result = execute_query(query)

    return result[0][0]


# Извлекаем информацию о тесте
def get_tests_info(user_id, level):
    query = f'''
    SELECT {level} FROM {TESTS_TABLE}
    WHERE user_id = {user_id}'''
    result = execute_query(query)
    return result[0][0]


# Добавляем просто айди пользователя в таблицу тестов. По дефолту там уже стоят значения на уровнях теста
def add_user_to_tests_table(user_id):
    query = f'''
    INSERT INTO {TESTS_TABLE}
    (user_id)
    VALUES(?);
    '''
    execute_query(query, (user_id, ))


# Получаем всю информацию о пользователе из тест таблицы
def get_all_tests_info(user_id):
    query = f'''
    SELECT A1, A2, B1, B2, C1, C2 FROM {TESTS_TABLE}
    WHERE user_id = {user_id}'''
    result = execute_query(query)
    return result[0]


# Добавляем инфу по определенному тесту, на котором сейчас пользователь
def add_level_info(user_id, level, info):
    query = f'''
    UPDATE {TESTS_TABLE}
    SET {level} = '{info}'
    WHERE user_id = {user_id};
    '''
    execute_query(query)


# Создание таблицы промптов.
def create_table_prompts():
    query = f'''
    CREATE TABLE IF NOT EXISTS {PROMPTS_TABLE}
    (id INTEGER PRIMARY KEY,
    user_id INTEGER,
    role TEXT,
    message TEXT,
    translation TEXT,
    session_id INTEGER);
    '''
    execute_query(query)


# Создание таблицы лимитов пользователей.
def create_table_limits():
    query = f'''
    CREATE TABLE IF NOT EXISTS {LIMITS_TABLE}
    (id INTEGER PRIMARY KEY,
    user_id INTEGER,
    total_gpt_tokens INTEGER DEFAULT 0,
    total_tts_tokens INTEGER DEFAULT 0,
    total_stt_blocks INTEGER DEFAULT 0,
    session_id INTEGER DEFAULT 0,
    amount_of_secs INTEGER DEFAULT 0,
    start TEXT DEFAULT 'False',
    theme TEXT DEFAULT 'False');
    '''

    execute_query(query)


# Добавление строки в таблицу промптов.
def insert_row_into_prompts(values):
    query = f'''
    INSERT INTO {PROMPTS_TABLE}
    (user_id, role, message, session_id)
    VALUES(?, ?, ?, ?);
    '''
    execute_query(query, values)


def is_user_in_limits(user_id):
    query = f'''
            SELECT EXISTS(SELECT 1 FROM {LIMITS_TABLE} WHERE user_id = {user_id});
            '''
    result = execute_query(query)

    return result[0][0]


# Добавление строки в таблицу лимитов пользователей.
def insert_row_into_limits(user_id):
    query = f'''
    INSERT INTO {LIMITS_TABLE}
    (user_id)
    VALUES({user_id});
    '''
    execute_query(query)


# Обновление ттс токенов в таблице лимитов пользователей.
def update_tts_tokens_in_limits(user_id, value):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET total_tts_tokens = total_tts_tokens + {value}
    WHERE user_id = {user_id};
    '''

    execute_query(query)


# Обновление стт блоков в таблице лимитов пользователей.
def update_stt_blocks_in_limits(user_id, value):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET total_stt_blocks = total_stt_blocks + {value}
    WHERE user_id = {user_id};
    '''

    execute_query(query)


# Обновление гпт токенов в таблице лимитов пользователей.
def update_gpt_tokens_in_limits(user_id, value):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET total_gpt_tokens = total_gpt_tokens + {value}
    WHERE user_id = {user_id};
    '''
    execute_query(query)


# Получение ттс токенов из таблицы лимитов пользователей.
def get_tts_tokens(user_id):
    query = f'''
    SELECT total_tts_tokens FROM {LIMITS_TABLE} WHERE user_id = {user_id};
    '''
    result = execute_query(query)

    return result[0][0]


# Получение стт блоков из таблицы лимитов пользователей.
def get_stt_blocks(user_id):
    query = f'''
    SELECT total_stt_blocks FROM {LIMITS_TABLE} WHERE user_id = {user_id};
    '''
    result = execute_query(query)

    return result[0][0]


# Получение гпт токенов из таблицы лимитов пользователей.
def get_gpt_tokens(user_id):
    query = f'''
    SELECT total_gpt_tokens FROM {LIMITS_TABLE} WHERE user_id = {user_id};
    '''

    result = execute_query(query)

    return result[0][0]


def get_amount_of_secs_limits(user_id):
    query = f'''
        SELECT amount_of_secs FROM {LIMITS_TABLE} WHERE user_id = {user_id};
        '''
    result = execute_query(query)

    return result[0][0]


# Получение всех промптов пользователя.
def get_user_prompts(user_id, session_id):
    query = f'''
    SELECT message, role FROM {PROMPTS_TABLE} WHERE user_id = {user_id} and session_id = {session_id};
    '''
    result = execute_query(query)

    return list(map(lambda x: {"role": x[1], "text": x[0]}, result))


# Получение всех различных id пользователей.


def all_users():
    query = f'''
    SELECT COUNT(DISTINCT user_id) AS unique_count_users FROM {LIMITS_TABLE};
    '''
    result = execute_query(query)

    return result[0][0]


# Проверяем есть ли пользователь в таблице
def user_in_table(user_id):
    query = f'''
    SELECT EXISTS(SELECT 1 FROM {LIMITS_TABLE} WHERE user_id = {user_id});
    '''

    result = execute_query(query)

    return result[0][0]


# Получаем номер последней сессию общения в диалоге
def get_last_session(user_id):
    query = f'''
    SELECT session_id FROM {LIMITS_TABLE} WHERE user_id = {user_id};'''
    result = execute_query(query)
    return 0 if not result else result[0][0]


# Обновляем сессию в диалоге
def update_session_id(user_id, value):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET session_id = {value}
    WHERE user_id = {user_id};
    '''
    execute_query(query)


# Увеличиваем количество секунд, которые пользователь проводит в диалоге с ботом
def update_amount_of_secs(user_id, value):
    query = f'''
        UPDATE {LIMITS_TABLE}
        SET amount_of_secs = amount_of_secs + {value}
        WHERE user_id = {user_id};
        '''
    execute_query(query)


# Проверяем, начал ли пользователь диалог
def get_start_dialog(user_id):
    query = f'''
    SELECT start FROM {LIMITS_TABLE} WHERE user_id = {user_id};
    '''
    result = execute_query(query)

    return result[0][0]


# Получаем тему диалога
def get_theme_dialog(user_id):
    query = f'''
    SELECT theme FROM {LIMITS_TABLE} WHERE user_id = {user_id};
    '''
    result = execute_query(query)
    return result[0][0]


# Устанавливаем в каком состоянии находится пользователь в диалоге(общается ли он с ботом или нет)
def update_start_dialog(user_id, value):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET start = '{value}'
    WHERE user_id = {user_id};
    '''
    execute_query(query)


# Обновляем тему диалога
def update_theme_dialog(user_id, value):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET theme = '{value}'
    WHERE user_id = {user_id};
    '''
    execute_query(query)


# Записываем перевод сообщения в диалоге
def update_message_translation(user_id, translation):
    query = f'''
    UPDATE {PROMPTS_TABLE}
    SET translation = '{translation}'
    WHERE id IN (SELECT id FROM {PROMPTS_TABLE}
                 WHERE user_id = {user_id} AND role = 'assistant'
                 ORDER BY id DESC
                 LIMIT 1);
    '''
    execute_query(query)


# Получаем последнее сообщение из диалога и его перевод(если он есть)
def get_last_message_and_translation(user_id):
    query = f'''
    SELECT message, translation FROM {PROMPTS_TABLE}
    WHERE user_id = {user_id} AND role = 'assistant'
    ORDER BY id DESC
    LIMIT 1;
    '''
    result = execute_query(query)
    return result[0]


# Создаем таблицу слов, параметры: состояние, какое слово по счету, количество выученных, message_id
def create_table_user_words():
    query = f'''
        CREATE TABLE IF NOT EXISTS {USER_WORDS_TABLE}
        (id INTEGER PRIMARY KEY,
        user_id INTEGER,
        A1 TEXT DEFAULT 'None, 0, 0, None',
        A2 TEXT DEFAULT 'None, 0, 0, None',
        B1 TEXT DEFAULT 'None, 0, 0, None',
        B2 TEXT DEFAULT 'None, 0, 0, None',
        C1 TEXT DEFAULT 'None, 0, 0, None',
        C2 TEXT DEFAULT 'None, 0, 0, None');
        '''

    execute_query(query)


# Проверяем, есть ли пользователь в таблице слов пользователя
def is_user_in_user_words(user_id):
    query = f'''
        SELECT EXISTS(SELECT 1 FROM {USER_WORDS_TABLE} WHERE user_id = {user_id});
        '''
    result = execute_query(query)

    return result[0][0]


# Извлекаем информацию о словах на определенном уровне
def get_user_words_info(user_id, level):
    query = f'''
    SELECT {level} FROM {USER_WORDS_TABLE}
    WHERE user_id = {user_id}'''
    result = execute_query(query)
    return result[0][0]


# Добавляем просто айди пользователя в таблицу слов пользователя. По дефолту там уже стоят значения на уровнях теста
def add_user_to_user_words(user_id):
    query = f'''
    INSERT INTO {USER_WORDS_TABLE}
    (user_id)
    VALUES(?);
    '''
    execute_query(query, (user_id, ))


# Добавляем инфу по определенной категории слов(А1, А2..), на котором сейчас пользователь
def add_level_user_words_info(user_id, level, info):
    query = f'''
    UPDATE {USER_WORDS_TABLE}
    SET {level} = '{info}'
    WHERE user_id = {user_id};
    '''
    execute_query(query)


# Вся инфа о словах пользователя, time - на будущее, если бот будет доделываться, для schedule
def create_table_all_words():
    query = f'''
    CREATE TABLE IF NOT EXISTS {ALL_USER_WORDS_TABLE}
    (id INTEGER PRIMARY KEY,
     user_id INTEGER,
     user_location TEXT DEFAULT 'None',
     learned_words TEXT DEFAULT '',
     words_to_learn TEXT DEFAULT '',
     user_words TEXT DEFAULT '',
     translation TEXT DEFAULT '',
     time TEXT DEFAULT '',
     bound_for_repeating_words TEXT DEFAULT '',
     repeat_words TEXT DEFAULT 'None');
     '''
    execute_query(query)


def is_user_in_all_words_table(user_id):
    query = f'''
            SELECT EXISTS(SELECT 1 FROM {ALL_USER_WORDS_TABLE} WHERE user_id = {user_id});
            '''
    result = execute_query(query)

    return result[0][0]


def add_user_to_all_words_table(user_id):
    query = f'''
        INSERT INTO {ALL_USER_WORDS_TABLE}
        (user_id)
        VALUES(?);
        '''
    execute_query(query, (user_id,))


def get_info_all_words(user_id, column):
    query = f'''
    SELECT {column} FROM {ALL_USER_WORDS_TABLE}
    WHERE user_id = {user_id};
    '''
    result = execute_query(query)
    return result[0][0]


def add_info_all_words(user_id, column, word):
    query = f'''
    UPDATE {ALL_USER_WORDS_TABLE}
    SET {column} = {column} || (?) || '~'
    WHERE user_id = {user_id};
    '''
    execute_query(query, (word, ))


def update_location_all_words(user_id, location):
    query = f'''
    UPDATE {ALL_USER_WORDS_TABLE}
    SET user_location = '{location}'
    WHERE user_id = {user_id};
    '''
    execute_query(query)


def update_repeat_words_id(user_id, value):
    query = f'''
        UPDATE {ALL_USER_WORDS_TABLE}
        SET repeat_words = '{value}'
        WHERE user_id = {user_id};
        '''
    execute_query(query)


def limit_reset_db(user_id):
    query = f'''
    UPDATE {LIMITS_TABLE}
    SET total_gpt_tokens = 0, total_tts_tokens = 0, total_stt_blocks = 0
    WHERE user_id = {user_id};
    '''
    execute_query(query)

    
# Добавляет границу, где мы закончим повторять слова
def add_bound_for_repeating_words(user_id, word):
    print(word)
    query = f'''
    UPDATE {ALL_USER_WORDS_TABLE}
    SET bound_for_repeating_words = (?)
    WHERE user_id = {user_id};
    '''
    execute_query(query, (word, ))


def update_info_all_words(user_id, column, info):
    query = f'''
        UPDATE {ALL_USER_WORDS_TABLE}
        SET {column} = (?)
        WHERE user_id = {user_id};
        '''
    execute_query(query, (info, ))


# Вся инфа по пользователю для вывода статистики
def get_all_user_info(user_id):
    if not is_user_in_limits(user_id):
        insert_row_into_limits(user_id)
    if not is_user_in_tests(user_id):
        add_user_to_tests_table(user_id)
    if not is_user_in_all_words_table(user_id):
        add_user_to_all_words_table(user_id)
    amount_of_secs = get_amount_of_secs_limits(user_id)
    unknown_words = len(get_info_all_words(user_id, 'words_to_learn').split('~')[:-1])
    known_words = len(get_info_all_words(user_id, 'learned_words').split('~')[:-1])
    tests_info = get_all_tests_info(user_id)
    updated_tests_info = []
    for level in tests_info:
        needed_info = level.split(', ')[:3]
        updated_tests_info.append(needed_info)
    return amount_of_secs, known_words, unknown_words, updated_tests_info


# Это все для тестов. В продакшн это не идет
con = sqlite3.connect(DB_DAME)
cur = con.cursor()
cur.execute('DROP TABLE IF EXISTS prompts;')
cur.execute('DROP TABLE IF EXISTS limits;')
cur.execute('DROP TABLE IF EXISTS tests;')
cur.execute('DROP TABLE IF EXISTS words;')
cur.execute('DROP TABLE IF EXISTS user_words;')
cur.execute('DROP TABLE IF EXISTS all_user_words;')
con.commit()
con.close()
