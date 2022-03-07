#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
import urllib.request
import requests
import vk
import random
import json
import datetime
import os
from settings   import *
from variables  import *
from re       import fullmatch, IGNORECASE

# Global variables
member_ids  = []
loc         = os.path.dirname(os.path.abspath(__file__))
json_resp   = None
server      = None
session     = vk.Session(access_token=token)
v           = 5.103

# Методы ----------

def log(log_message):
    file_d = os.path.join(loc, 'log.txt')
    file = open(file_d, 'a')
    now = datetime.datetime.now()
    time = f"[{now.hour}:{now.minute}:{now.second}]"
    file.write(f'{time} {log_message}\n')
    file.close()
    print(f'{time} {log_message}')


def get_long_poll_server(group_id):
    response_ = api.__call__(
        'groups.getLongPollServer', oauth='1', group_id=group_id, v=v)
    return response_


def upload_photo(file):
    """Загружает фото на сервер вк"""
    # Получаем данные для загрузки
    upload_url = api.__call__('photos.getMessagesUploadServer',
                              peer_id=0,
                              v=v)['upload_url']

    # Берём фото для загрузки
    files = {'photo': file}

    # Загружаем фото на сервер
    response = requests.post(upload_url, files=files)
    response_data = response.json()

    # Сохраняем фото в альбом
    photo_info = api.__call__('photos.saveMessagesPhoto',
                              server=response_data['server'],
                              photo=response_data['photo'],
                              hash=response_data['hash'],
                              v=v)
    return photo_info


def atts_to_string(attachments_):
    """Создаёт строку вложения"""
    atts = ''
    if attachments_.__len__ == 0:
        return ''
    else:
        for att in attachments_:

            att_type = att['type']
            if att_type == 'wall':
                owner_id = att[att_type]['from_id']
            else:
                owner_id = att[att_type]['owner_id']

            atts += f"{att_type}{owner_id}_{att[att_type]['id']}_{att[att_type]['access_key']},"
        return atts


def send_message(user_id_, message_text_, atts=''):
    """Отправляет сообщение пользователю"""
    # print(f'atts = {atts}')
    # отправка сообщений
    api.__call__(
        'messages.send',
        user_id=user_id_,
        message=message_text_,
        attachment=atts,
        random_id=random.randint(0, 2000000),
        keyboard=json.dumps(main_keyboard),
        v=v)

# Методы ----------


# Тело

try:
    # Авторизация
    api = vk.API(session)
    print('Аутентификация успешна')

    # Получаем данные для запросов лонгполу
    server = get_long_poll_server(group_id)
    # Получаем подпищеков
    if DEBUG:
        member_ids = [admin_id]
    else:
        member_ids = api.__call__('groups.getMembers', group_id=group_id, v=v)['items']

except ValueError:
    send_message(admin_id, '⚠️Пора апдейтнуть куки!!!⚠️')

except BaseException as error_msg:
    log(error_msg)
    print(error_msg)

# Главный цикл -----
while True:
    try:
        # Делаем запрос на лонгпол сервер
        request = f"{server['server']}?act=a_check&key={server['key']}&ts={server['ts']}&wait=25"
        response = urllib.request.urlopen(request)

        # Десериализуем json ответ в переменную
        json_resp = json.loads(response.read())

    except BaseException as ex:
        log(ex)
        print(ex)

    # Если вернулась ошибка
    if 'failed' in json_resp:
        server = get_long_poll_server(group_id)
        continue

    # Обновляем ts
    server['ts'] = json_resp['ts']

    # Перебор событий
    for update in json_resp['updates']:
        # Объект сообщения в переменную
        message = update['object']['message']
        # Айди челика
        user_id = message['from_id']
        
        ## Прогоняем текст сообщения через регексы чтоб узнать какую команду прислал пользователь
        add_hw       = fullmatch(set_hw_pattern,       message['text'])              # записывает дз
        ask_hw       = fullmatch(ask_hw_pattern,       message['text'], IGNORECASE)  # спрашивает дз
        ask_schedule = fullmatch(ask_schedule_pattern, message['text'], IGNORECASE)  # спрашивает расписание
        ban_user     = fullmatch(ban_user_pattern,     message['text'], IGNORECASE)  # банит
        unban_user   = fullmatch(unban_user_pattern,   message['text'], IGNORECASE)  # Анбанит
        ask_user     = fullmatch(ask_user_pattern,     message['text'], IGNORECASE)  # Спрашивает кто написал дз
        broadcast    = fullmatch(broadcast_pattern,    message['text'], IGNORECASE)  # Делает рассылку

        try:
            ## В зависимости от команды делаем действия
            # Просит команды
            if message['text'].lower() in ('помощь', 'команды', 'help', 'хелп'):
                send_message(user_id, help_message)

            # Челик записывает дз и его нет в чёрном списке
            elif add_hw:
                file_d = os.path.join(loc, 'blacklist.json')
                bl = json.load(open(file_d, encoding='utf-8'))
                if bl.__contains__(str(user_id)):
                    send_message(user_id, '❌ Вам запрещено изменять дз, причина - ' + bl[str(user_id)])
                else:
                    day_num = 0

                    # Экранируем кавычки
                    message['text'] = str.replace(message['text'], "'", "\\'")
                    message['text'] = str.replace(message['text'], '"', '\\"')

                    # Получаем номер дня недели
                    if not days_of_week.__contains__(str.lower(message['text'])[0:2]):
                        send_message(message_text_=funny_replies[random.randint(0, 5)],
                                     user_id_=user_id,
                                     atts=funny_replies_photo[random.randint(0, 4)])
                        continue

                    # Предмет, дз и вложения, которое записывает челик
                    subject = add_hw.group(1).lower()
                    homeTask = add_hw.group(2)
                    atts = []
                    for att in message['attachments']:
                        att_type = att['type']
                        if att_type == 'wall':
                            owner_id = att[att_type]['from_id']
                        else:
                            owner_id = att[att_type]['owner_id']
                        if att_type == 'photo':
                            max_size = 0
                            index = 0
                            i = 0
                            for size in att[att_type]['sizes']:
                                if size['height'] > max_size:
                                    index = i
                                    max_size = size['height']
                                i += 1
                            photo_url = att[att_type]['sizes'][index]['url']
                            urllib.request.urlretrieve(photo_url, 'att.jpg')
                            photo = upload_photo(open('att.jpg', 'rb'))[0]
                            atts.append(f'photo{photo["owner_id"]}_{photo["id"]}_{photo["access_key"]}')
                        else:
                            atts.append(f'{att_type}{owner_id}_{att[att_type]["id"]}_{att[att_type]["access_key"]}')
                    attachments = ','.join(atts)
                    
                    # Ищем дз на этот день
                    file_d = os.path.join(loc, 'homework.json')
                    day_hw = json.load(open(file_d, encoding='utf-8'))

                    # Этот предмет есть в дз на этот день
                    if day_hw[str.lower(message['text'])[0:2]].__contains__(subject):
                        # Если дз - 0
                        if homeTask == '0':
                            del day_hw[str.lower(message['text'])[0:2]][subject]
                            log(f'удаляю дз от {user_id} по {subject} на {days_of_week[day_num]}')
                            send_message(user_id, f'✔ Дз успешно удалено')
                        # Если дз есть то заменяем
                        else:
                            day_hw[str.lower(message['text'])[0:2]][subject]['text'] = homeTask
                            if attachments:
                                day_hw[str.lower(message['text'])[0:2]][subject]['attachments'] = attachments
                            day_hw[str.lower(message['text'])[0:2]][subject]['edited_by'] = user_id
                            log(f'Заменяю дз от {user_id} по {subject} на {days_of_week[day_num]}')
                            send_message(user_id, f'✔ Дз успешно заменено')

                    else:
                        if homeTask == '0':
                            send_message(user_id, f'❌ На этот предмет и так нет дз')
                        else:
                            # Добавляем дз
                            day_hw[str.lower(message['text'])[0:2]][subject] = {
                                'text': homeTask,
                                'attachments': attachments,
                                'edited_by': user_id,
                                'weekday': datetime.datetime.today().weekday()
                            }
                            log(f'Добавляю дз от {user_id} по {subject} на {days_of_week[day_num]}')
                            send_message(user_id, f'✔ Дз успешно добавлено')

                    json.dump(day_hw, open(file_d, 'w', encoding='utf-8'))

            # Челик просит дз
            elif ask_hw:
                message_text = ''
                attachments = ''
                day_num = 0
                file_d = os.path.join(loc, 'homework.json')
                hw = json.load(open(file_d, encoding='utf-8'))
                if not ask_hw.group(5):
                    for day in hw:
                        message_text += f'{day}:\n'
                        if hw[day] == {}:
                            message_text += '&#8195;На этот день ещё нет дз\n'
                        else:
                            for subj in hw[day]:
                                message_text += f'&#8195;{subj} - {hw[day][subj]["text"]}\n'
                                attachments += hw[day][subj]['attachments']
                        message_text += '------------------------------\n'
                else:
                    # дз на конкретный день
                    if message['text'][-2:] in days_of_week:
                        if hw[message['text'][-2:]] == {}:
                            message_text = 'На этот день ещё нет дз'
                        else:
                            message_text = f'Дз на {message["text"][-2:]}:\n'
                            for subj in hw[message['text'][-2:]]:
                                message_text += '------------\n'
                                message_text += f'{subj.title()} - {hw[message["text"][-2:]][subj]["text"]}\n'
                                attachments += hw[message['text'][-2:]][subj]['attachments']
                    # дз на завтра
                    elif 'завтр' in message['text'].split()[-1]:
                        hwl = list(hw.values())
                        wd = cur_time.weekday() + 1
                        if cur_time.weekday() + 1 >= 6:
                            wd = 0
                        if hwl[wd] == {}:
                            message_text = 'На этот день ещё нет дз'
                        else:
                            message_text = f'Дз на {list(hw.keys())[wd]}:\n'
                            for subj in list(hw.values())[wd]:
                                message_text += '------------\n'
                                message_text += f'{subj.title()} - {hwl[wd][subj]["text"]}\n'
                                attachments += hwl[wd][subj]['attachments']
                    # такого дня недели нет
                    else:
                        message_text = funny_replies[random.randint(0, 5)]
                        attachments = funny_replies_photo[random.randint(0, 4)]
                try:
                    send_message(user_id, message_text, attachments)
                except vk.api.VkAPIError as vk_ex:
                    send_message(user_id, f'❌ Ошибка с вк апи: {vk_ex}')
                    log(f'Ошибка с вк апи: {vk_ex}\nПопробуйте спросить дз на конкретный день')

            # Спрашивает расписание
            elif fullmatch(ask_time_table_pattern, message['text'], IGNORECASE):
                send_message(user_id, time_table)

            # Спрашивает расписание на какой то день
            elif ask_schedule:
                # Получаем номер дня недели
                if ask_schedule.group(5):
                    if days_of_week.__contains__(message['text'][-2:]):
                        send_message(user_id, schedule[message['text'][-2:]])
                    elif 'завтр' in message['text'].split()[-1]:
                        wd = cur_time.weekday() + 1
                        if cur_time.weekday() + 1 >= 6:
                            wd = 0
                        send_message(user_id, f'Расписание на {list(schedule.keys())[wd]}:\n' + list(schedule.values())[wd])
                    else:
                        send_message(message_text_=funny_replies[random.randint(0, 5)], user_id_=user_id,
                                     atts=funny_replies_photo[random.randint(0, 4)])
                else:
                    msg = ''
                    for day in schedule.keys():
                        msg += f'{day}:\n{schedule[day]}\n'
                    send_message(user_id, msg)

            # Админ банит
            elif user_id == admin_id and ban_user:
                file_d = os.path.join(loc, 'blacklist.json')
                blacklist = json.load(open(file_d, 'r', encoding='utf-8'))
                blacklist[str(ban_user.group(2))] = ban_user.group(3)
                json.dump(blacklist, open(file_d, 'w', encoding='utf-8'))
                send_message(user_id, f'✔ [id{ban_user.group(2)}|Пользователь] успешно заблокирован')

            # Админ анбанит
            elif user_id == admin_id and unban_user:
                file_d = os.path.join(loc, 'blacklist.json')
                blacklist = json.load(open(file_d, 'r', encoding='utf-8'))
                del blacklist[str(unban_user.group(2))]
                json.dump(blacklist, open(file_d, 'w', encoding='utf-8'))
                send_message(user_id, f'✔ [id{unban_user.group(2)}|Пользователь] успешно разблокирован')

            # Кто автор дз
            elif ask_user:
                if ask_user.group(2) and ask_user.group(4):
                    file_d = os.path.join(loc, 'homework.json')
                    hw = json.load(open(file_d, 'r'))
                    send_message(user_id, f'дз на {ask_user.group(2)} по {ask_user.group(4)} добавил '
                                          f'[id{hw[ask_user.group(2)][ask_user.group(4)]["edited_by"]}|он(а)]')
                else:
                    send_message(user_id, '❌ Эта функция ещё не проработана')

            # Разошли
            elif broadcast:
                file_d = os.path.join(loc, 'blacklist.json')
                bl = json.load(open(file_d, encoding='utf-8'))
                if bl.__contains__(str(user_id)):
                    send_message(user_id, '❌ Вам запрещено запускать рассылку, причина - ' + bl[str(user_id)])
                else:
                    fwd_message = ''
                    text = ''
                    atts = []
                    if message['fwd_messages']:
                        fwd_message = message['id']
                    else:
                        for att in message['attachments']:
                            att_type = att['type']
                            if att_type == 'wall':
                                owner_id = att[att_type]['from_id']
                            else:
                                owner_id = att[att_type]['owner_id']
                            if att_type == 'photo':
                                max_size = 0
                                index = 0
                                i = 0
                                for size in att[att_type]['sizes']:
                                    if size['height'] > max_size:
                                        index = i
                                        max_size = size['height']
                                    i += 1
                                photo_url = att[att_type]['sizes'][index]['url']
                                urllib.request.urlretrieve(photo_url, 'att.jpg')
                                photo = upload_photo(open('att.jpg', 'rb'))[0]
                                atts.append(f'photo{photo["owner_id"]}_{photo["id"]}_{photo["access_key"]}')
                            else:
                                atts.append(f'{att_type}{owner_id}_{att[att_type]["id"]}_{att[att_type]["access_key"]}')
                        text = broadcast.group(1)

                    broadcaster = api.__call__('users.get', user_ids=message['from_id'], v=v)[0]
                    fullname = broadcaster['first_name'] + ' ' + broadcaster['last_name']
                    ids = api.__call__('groups.getMembers', group_id=group_id, v=v)['items']
                    if not DEBUG:
                        ids.remove(message['from_id'])

                    response = api.__call__(
                        'messages.send',
                        user_ids=ids,
                        message=fullname + ': ' + text,
                        attachment=','.join(atts),
                        random_id=random.randint(0, 2000000),
                        forward_messages=fwd_message,
                        v=v)
                    try:
                        if len(response) > 0 and type(response[0]) == type({}):
                            send_message(user_id, '✔ Рассылка успешно запущена')
                        else:
                            send_message(user_id, f'❌ Рассылка успешно не была запущена. Ошибка\n{ response }')
                    except Exception as e:
                        send_message(user_id, f'❌ Произошла ошибка\n{e}')

            # Админ вырубил бота
            elif message['text'].lower() == "вырубай шарманку" and user_id == admin_id:
                send_message(user_id, '✔ ок')
                raise SystemExit(0)

        except BaseException as ex:
            print(ex)
            send_message(user_id, ex)
            log(ex)
