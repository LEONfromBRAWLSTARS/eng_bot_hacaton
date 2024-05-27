import sqlite3

DB_DAME = 'database.db'

TESTS_TABLE = 'tests'
PROMPTS_TABLE = 'prompts'
WORDS_TABLE = 'words'
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
# amount_of_correct_answers - количество правильных ответов в тесте, message_id - id сообщения с тестом.
# Выставляем значения по умолчанию для уровней тестов.
def create_table_tests():
    query = f'''
    CREATE TABLE IF NOT EXISTS {TESTS_TABLE}
    (id INTEGER PRIMARY KEY,
    user_id INTEGER,
    A1 TEXT DEFAULT 'None, 1, 0, None',
    A2 TEXT DEFAULT 'None, 1, 0, None',
    B1 TEXT DEFAULT 'None, 1, 0, None',
    B2 TEXT DEFAULT 'None, 1, 0, None',
    C1 TEXT DEFAULT 'None, 1, 0, None',
    C2 TEXT DEFAULT 'None, 1, 0, None');
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


def create_table_words():
    query = f'''
    CREATE TABLE IF NOT EXISTS {WORDS_TABLE}
    (id INTEGER PRIMARY KEY,
    user_id INTEGER,
    words_list TEXT DEFAULT '', 
    learned_words TEXT DEFAULT '');
    '''
    execute_query(query)


def get_words(user_id):
    query = f'''
    SELECT words_list, learned_words FROM {WORDS_TABLE}
    WHERE user_id = {user_id};
    '''
    result = execute_query(query)
    return result[0][0], str(result[0][1])


def add_word(user_id, word):
    user_words, user_status = get_words(user_id)
    if user_words == '' or user_words == '0':
        user_words = word
        user_status = '0'
    else:
        user_words += ', ' + word
        user_status += '0'
    query = f'''
    UPDATE {WORDS_TABLE}
    SET words_list = '{user_words}', 
        learned_words = '{user_status}'
    WHERE user_id = {user_id};
    '''
    execute_query(query)


def is_user_in_words(user_id):
    query = f'''
        SELECT EXISTS(SELECT 1 FROM {WORDS_TABLE} WHERE user_id = {user_id});
        '''
    result = execute_query(query)

    return result[0][0]


def add_user_to_words_table(user_id):
    query = f'''
    INSERT INTO {WORDS_TABLE}
    (user_id)
    VALUES(?);
    '''
    execute_query(query, (user_id, ))






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

# Вся инфа о словах пользователя
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
     bound_for_repeating_words DEFAULT '');
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
    SET {column} = {column} || '{word}~'
    WHERE user_id = {user_id}
    '''
    execute_query(query)


def update_location_all_words(user_id, location):
    query = f'''
    UPDATE {ALL_USER_WORDS_TABLE}
    SET user_location = '{location}'
    WHERE user_id = {user_id}
    '''
    execute_query(query)


def add_bound_for_repeating_words(user_id, word):
    query = f'''
    UPDATE {ALL_USER_WORDS_TABLE}
    SET bound_for_repeating_words = '{word}'
    WHERE user_id = {user_id}
    '''
    execute_query(query)


def update_info_all_words(user_id, column, info):
    query = f'''
        UPDATE {ALL_USER_WORDS_TABLE}
        SET {column} = '{info}'
        WHERE user_id = {user_id}
        '''
    execute_query(query)


# Это все для тестов. В продакшн это не идет
#con = sqlite3.connect(DB_DAME)
#cur = con.cursor()
#cur.execute('DROP TABLE IF EXISTS prompts;')
#cur.execute('DROP TABLE IF EXISTS limits;')
#cur.execute('DROP TABLE IF EXISTS tests;')
#cur.execute('DROP TABLE IF EXISTS words;')
#cur.execute('DROP TABLE IF EXISTS user_words;')
#cur.execute('DROP TABLE IF EXISTS all_user_words;')
#con.commit()
#con.close()
