import requests
from bs4 import BeautifulSoup
import telebot
from telebot import types
import re
import pickle

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
gauth.LoadCredentialsFile('mycreds.txt')

drive = GoogleDrive(gauth)

file = drive.CreateFile({'id':'17m5TyTaaPXKJCcrYqP1zTBWSez5kr0--'})
content = file.GetContentFile('usuarios.pkl')


class Usuario:
    def __init__(self, chat_id, first_name,plataforma=None):
        self.chat_id = chat_id
        self.name = first_name
        self.plataforma = plataforma
        self.lista_jogos = []
        self.lista = []

    def mudar_plataforma(self,plataforma):
        self.plataforma = plataforma


def carregar_lista():
    try:
        with open('usuarios.pkl', 'rb') as inp:
            users = pickle.load(inp)
    except:
        users = {}
    return users

def salvar_usuarios(lista_users):
    with open('usuarios.pkl', 'wb') as outp:
        pickle.dump(lista_users, outp, pickle.HIGHEST_PROTOCOL)
    file = drive.CreateFile({'id': '17m5TyTaaPXKJCcrYqP1zTBWSez5kr0--'})
    file.SetContentFile('usuarios.pkl')
    file.Upload()


def get_user_step(uid):
    global check
    if check == 1:
        return 1
    if check == 0:
        return 0


def informacoes_jogo(text,id,users):
    global lista_jogos, lista

    print(text)
    for cont, game in enumerate(users[id].lista_jogos):
        if game == text:
            return cont


TOKEN = my_token

users = {}

lista = []
lista_jogos = []

check = 0

esconder_teclado = types.ReplyKeyboardRemove()
selecao_plataforma = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=3)
selecao_plataforma.add('Xbox', 'Playstation', 'Switch')


bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def comando_start(m):

    users = carregar_lista()

    cid = m.chat.id

    if cid in users.keys():
        bot.send_message(cid,
f'''SUA ATUAL PLATAFORMA JÁ ESTÁ REGISTRADA
ATUAL PLATAFORMA : {users[cid].plataforma}''')
    else:
        users[m.chat.id] = Usuario(m.chat.id, m.from_user.first_name)
        plataforma = bot.send_message(cid,
'''BEM VINDO AO RASTREADOR DE PREÇOS DA XBOX STORE
DIGITE /jogo [jogo que deseja] para começar a utilizar o bot''',
                         reply_markup=selecao_plataforma)
        print(users.keys())
        salvar_usuarios(users)

        bot.register_next_step_handler(plataforma,registro_plataforma)


@bot.message_handler(commands='plataforma')
def mudar_plataforma(m):
    users = carregar_lista()
    if m.chat.id in users.keys():
        texto = bot.send_message(m.chat.id, 'SELECIONE SUA PLATAFORMA:', reply_markup=selecao_plataforma)
        bot.register_next_step_handler(texto, registro_plataforma)
    else:
        print(m.chat.id, ':', users.keys())
        bot.send_message(m.chat.id, 'DIGITE /start')


def registro_plataforma(m):

    users = carregar_lista()

    if m.text.lower() not in ['xbox','playstation','switch']:
        bot.send_message(m.chat.id, f'PLATAFORMA NÃO ENCONTRADA, DIGITE /plataforma', reply_markup=types.ReplyKeyboardRemove())
    else:
        users[m.chat.id].mudar_plataforma(m.text)
        bot.send_message(m.chat.id, f'SUA PLATAFORMA ATUAL É : {users[m.chat.id].plataforma}', reply_markup=types.ReplyKeyboardRemove())
        salvar_usuarios(users)
        print(users[m.chat.id].plataforma)

@bot.message_handler(commands=['jogo'])
def jogo(m):
    global lista, lista_jogos

    users = carregar_lista()

    texto = m.text[6:]
    cid = m.chat.id


    if len(texto) < 2:
        bot.send_message(cid, "DIGITE O NOME DE ALGUM JOGO")
    elif cid not in users.keys():
        bot.send_message(cid,'DIGITE /start')
    elif users[cid].plataforma is None:
        bot.send_message(cid, "SUA PLATAFORMA NAO FOI REGISTRADA, DIGITE /plataforma")
    else:

        users[cid].lista_jogos.clear()
        users[cid].lista.clear()

        if users[cid].plataforma == 'Switch':
            site = 'nt'
        elif users[cid].plataforma == 'Playstation':
            site = 'ps'
        elif users[cid].plataforma == 'Xbox':
            site = 'xb'
        site_jogos = f'https://{site}deals.net/br-store/search?search_query={texto.replace(" ", "+")}'

        request_jogos = requests.get(site_jogos)

        print(site_jogos)

        html = BeautifulSoup(request_jogos.text, 'html.parser')

        jogos = html.find_all('a', attrs={'class': 'game-collection-item-link'}, href=True)

        if len(jogos) == 0:
            bot.send_message(cid, "JOGO NÃO ENCONTRADO")
        else:
            bot.send_chat_action(cid, 'typing')
            for contador, jogo in enumerate(jogos):
                users[cid].lista.append(jogo['href'])
                nome_jogos = jogo['href'].rfind('/')
                users[cid].lista_jogos.append(jogo['href'][nome_jogos + 1:].replace('-', ' ').upper())
                if contador == 5:
                    break

            selecao_jogo = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=6)
            for jogo in users[cid].lista_jogos:
                selecao_jogo.add(jogo)

            texto = bot.send_message(cid, "Qual versão do jogo deseja?", reply_markup=selecao_jogo)

            bot.register_next_step_handler(texto, enviar_jogo,users)


def enviar_jogo(m,users):
    global lista, lista_jogos

    cid = m.chat.id
    text = m.text
    bot.send_chat_action(cid, 'typing')

    numero = informacoes_jogo(text,cid,users)

    if users[cid].plataforma == 'Switch':
        site = 'nt'
    elif users[cid].plataforma == 'Playstation':
        site = 'ps'
    elif users[cid].plataforma == 'Xbox':
        site = 'xb'

    request_jogo = requests.get(f'https://{site}deals.net' + users[cid].lista[numero])
    print(f'https://{site}deals.net' + users[cid].lista[numero])
    html_jogo = BeautifulSoup(request_jogo.text, 'html.parser')

    nome_jogo = html_jogo.find('div', attrs={'class': 'game-title-info-name'})
    preco_jogo = html_jogo.find('span', attrs={'class': 'game-collection-item-regular-price'})
    menor_preco_jogo = html_jogo.find('span', attrs={'class': 'game-stats-col-number-big game-stats-col-number-green'})

    script = html_jogo.find_all('script')

    pattern = re.compile(r'"price":"\d*.\d*"')
    pattern_data = re.compile(r'"date":"\d{4}.\d{2}.\d{2}')

    todo_script = script[11].text

    script_preco = pattern.findall(script[11].text[todo_script.find('var chartBonusPrices'):])
    script_data = pattern_data.findall(script[11].text[todo_script.find('var chartBonusPrices'):])

    if len(script_preco) == 0:
        script_preco = pattern.findall(script[11].text[:todo_script.find('var chartBonusPrices')])
        script_data = pattern_data.findall(script[11].text[:todo_script.find('var chartBonusPrices')])

    if len(script_data) >= 2:
        bot.send_message(cid,
                         f'{nome_jogo.text}\n\nPREÇO : {preco_jogo.text}\n\nMENOR PREÇO : {menor_preco_jogo.text}\n\n'
                         f'REGISTROS DE PREÇOS RECENTES:\n\n{script_data[-1][8:]} : R${script_preco[-1][9:-2]}\n{script_data[-2][8:]} : R${script_preco[-2][9:-2]}\n\n\nTODAS INFORMAÇOES EM : https://{site}deals.net{users[cid].lista[numero]}',
                         reply_markup=esconder_teclado)
    else:
        bot.send_message(cid,
                         f'{nome_jogo.text}\n\nPREÇO : {preco_jogo.text}\n\nMENOR PREÇO : {menor_preco_jogo.text}\n\n'
                         f'REGISTROS DE PREÇOS RECENTES:\n\n{script_data[-1][8:]} : R${script_preco[-1][9:-2]}\n\n\nTODAS INFORMAÇOES EM : https://{site}deals.net{users[cid].lista[numero]}',
                         reply_markup=esconder_teclado)

    users[cid].lista_jogos.clear()
    users[cid].lista.clear()
    script_data.clear()
    script_preco.clear()

@bot.message_handler(commands=['link'])
def bypass(m):
    cid = m.chat.id
    url = m.text[5:]

    payload = {
        "url": url,
    }

    r = requests.post("https://api.bypass.vip/", data=payload)
    print(r.json())
    link = r.json()['destination']

    requestlink = requests.get(link)

    soup = BeautifulSoup(requestlink.text, 'html.parser')
    link_mega = soup.find('meta', attrs={'name': 'description'})
    bot.send_message(cid,link_mega['content'])

bot.infinity_polling()
