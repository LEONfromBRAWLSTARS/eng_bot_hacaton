from database import is_user_in_words, add_user_to_words_table, add_word, get_words
from vocab import get_info_of_word, get_translation


def translate(message):
    user_id = message
    #if not is_user_in_words(user_id):
        #add_user_to_words_table(user_id)

    translation, error = get_translation(message)
    definition, example, audio, error = get_info_of_word(message)
    resp = f'📌 Слово {message} 📌\n'
    if error != None or (translation == None and definition == None and example == None and audio == None):

        return False, False

    #add_word(user_id, message)
    #print(get_words(user_id))

    if translation:
        trans = ", ".join(translation)
        resp += f'<b>Meaning</b>: {trans}\n'

    if definition:
        resp += f'<b>Definition</b>: {definition}\n'

    if example:
        resp += f'<b>Example</b>: {example}\n'

    if audio:
        return resp, audio
    return resp, False

