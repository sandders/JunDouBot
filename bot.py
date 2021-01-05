import telebot
import requests
import os
from bs4 import BeautifulSoup
from pymongo import MongoClient

API_TOKEN = str(os.environ.get('API_TOKEN'))

cluster = MongoClient(str(os.environ.get('MONGO_CLIENT')))
db = cluster['JunBot_database']
collection = db['user_data']

bot = telebot.TeleBot(API_TOKEN)

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
url = 'https://jobs.dou.ua/first-job/'

locations = []

def get_locations():
    html = requests.get(url, headers=headers).text
    soup = BeautifulSoup(html, 'lxml')
    div_locations = soup.find('div', {'class': 'first-job-cities'})
    all_locations = div_locations.find_all('a')
    return [location.text for location in all_locations]

def find_vacancies(location, keywords):
    html = requests.get(url, headers=headers).text
    soup = BeautifulSoup(html, 'lxml')
    all_vacancies = soup.find_all('div', {'class': 'vacancy'})
    loc_filtered_vac = [vac for vac in all_vacancies if f'{location}' in vac.text] if not location.lower() == "все" else all_vacancies
    keyword_filtered_vac = [vac for vac in loc_filtered_vac if any([kwrg in vac.find('a', {'class': 'vt'}).text.lower() for kwrg in keywords])]
    if 'java' in keywords:
        keyword_filtered_vac = [vac for vac in keyword_filtered_vac if not any([kwrg in vac.find('a', {'class': 'vt'}).text.lower() for kwrg in ['java script', 'javascript']])]
    return [{'title': vac.find('a', {'class': 'vt'}).text,
             'link': vac.find('a', {'class': 'vt'}, href=True)['href']} for vac in keyword_filtered_vac]
def main_keymap():
    keyboard = telebot.types.ReplyKeyboardMarkup()
    keyboard.row('Обновить')
    keyboard.row('Изменить город', 'Изменить ключевое слово')
    return keyboard

def location_keymap():
    global locations
    locations = get_locations()
    keyboard = telebot.types.ReplyKeyboardMarkup()
    for i, k in zip(locations[0::2], locations[1::2]):
        keyboard.row(i, k)
    if len(locations)%2 == 1:
        keyboard.row(locations[-1])
    return keyboard

@bot.message_handler(commands=['start'])
def start_message(message):
    global connection
    if collection.count_documents({'_id': message.chat.id}) == 0:
        collection.insert_one({'_id': message.chat.id, 'location':'', 'keywords':''})
    #bot.send_message(message.chat.id, 'Димон Гломозда смотрит гей порно')
    check_data(message)
    

def check_data(message):
    user_data = collection.find_one({'_id':message.chat.id})
    if user_data['location']=='':
        bot.send_message(message.chat.id, 'Введите город:', reply_markup=location_keymap())
        bot.register_next_step_handler(message, change_location)
        return
    if user_data['keywords']==[]:
        bot.send_message(message.chat.id, 'Введите ключевое слово для поиска (можно несколько, для разделения используйте запятую):', reply_markup=telebot.types.ReplyKeyboardRemove(selective=False))
        bot.register_next_step_handler(message, select_keyword)
        return
    show_vacancies(message)
    

def change_location(message):
    global collection, locations
    new_locatoin = message.text
    if new_locatoin in locations:
        collection.update_one({'_id':message.chat.id}, {'$set':{'location':new_locatoin}})
        check_data(message)
    else:
        bot.send_message(message.chat.id, 'К сожалению, город не найден или не поддерживаеться. Попробуйте ещё раз.')
        bot.send_message(message.chat.id, 'Введите город:', reply_markup=location_keymap())
        bot.register_next_step_handler(message, change_location)

def select_keyword(message):
    global collection
    new_keyword = message.text
    new_keywords = new_keyword.split(',')
    new_keywords = [word.strip().lower() for word in new_keywords]
    collection.update_one({'_id':message.chat.id}, {'$set':{'keywords':new_keywords}})
    check_data(message)

def show_vacancies(message):
    global collection
    user_data = collection.find_one({'_id':message.chat.id})
    if not len(vacancies:=find_vacancies(user_data['location'], user_data['keywords'])) == 0:
        bot.send_message(message.chat.id, 'Вот список вакансий:', reply_markup=main_keymap())
        for a in vacancies:
            bot.send_message(message.chat.id, f"{a['title']} {a['link']}")
        bot.send_message(message.chat.id, f'Всего найдено вакансий: {len(vacancies)}', reply_markup=main_keymap())
    else:
        bot.send_message(message.chat.id, f'По вашему запросу "{user_data["location"].title()} {", ".join(i.title() for i in user_data["keywords"])}" ваканисий не найдено. Попробуйте изменить параметры поиска.', reply_markup=main_keymap())
    bot.register_next_step_handler(message, main_handler)

@bot.message_handler(content_types=['text'])
def main_handler(message):
    if message.text.lower() == 'обновить':
        show_vacancies(message)
    elif message.text.lower() == 'изменить город':
        bot.send_message(message.chat.id, 'Введите город:', reply_markup=location_keymap())
        bot.register_next_step_handler(message, change_location)
    elif message.text.lower() == 'изменить ключевое слово':
        bot.send_message(message.chat.id, 'Введите ключевое слово для поиска (можно несколько, для разделения используйте запятую):', reply_markup=telebot.types.ReplyKeyboardRemove(selective=False))
        bot.register_next_step_handler(message, select_keyword)
    else:
        check_data(message)

    

if __name__ == '__main__':
    bot.polling(none_stop=True)
