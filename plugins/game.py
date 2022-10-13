from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums.chat_type import ChatType
from pyromod.helpers import ikb
from random import randint
import time
import datetime

NEIGHBORS = [
    lambda x, y: (x - 1, y - 1), # top left
    lambda x, y: (x - 1, y),     # top
    lambda x, y: (x - 1, y + 1), # top right
    lambda x, y: (x,     y - 1), # left
    lambda x, y: (x,     y + 1), # right
    lambda x, y: (x + 1, y - 1), # bottom left
    lambda x, y: (x + 1, y),     # bottom
    lambda x, y: (x + 1, y + 1)  # bottom right
]

class Game:
    def __init__(self):
        self.mines = []
        self.matrix = [[0 for row in range(6)] for column in range(12)]
        self.played = []
        self.game = [['⬛️' for row in range(6)] for column in range(12)]

    def create_game(self):
        while len(self.mines) != 10:
            minePosition = [randint(0, 11), randint(0, 5)]
            if minePosition not in self.mines:
                self.mines.append(minePosition)
                self.matrix[minePosition[0]][minePosition[1]] = 'M'
        for x, y in self.mines:
            for func in NEIGHBORS:
                try:
                    xN, yN = func(x, y)
                    if xN < 0 or yN < 0:
                        raise IndexError
                    if self.matrix[xN][yN] != 'M':
                        self.matrix[xN][yN] += 1
                except IndexError:
                    pass

    def delete_blank(self, x, y):
        for func in NEIGHBORS:
            try:
                xN, yN = func(x, y)
                if xN < 0 or yN < 0:
                    raise IndexError
                if self.matrix[xN][yN] != 'M':
                    if not [xN, yN] in self.played:
                        self.click(xN, yN, blank=False)
                        if self.matrix[xN][yN] == 0:
                            self.delete_blank(xN, yN)
            except IndexError:
                pass

    def click(self, x, y, blank=True):
        self.played.append([x, y])
        self.game[x][y] = self.matrix[x][y]
        if blank and self.matrix[x][y] == 0:
            self.delete_blank(x, y)
    
    def show_game(self):
        for i in self.played:
            self.matrix[i[0]][i[1]] = f'<strike>{self.matrix[i[0]][i[1]]}</strike>'
        ret = ''
        for row in self.matrix:
            ret += " ".join(str(cell) for cell in row)
            ret += '\n'
        return ret
games = {}
battles = {}

@Client.on_message(filters.command("leave"))
async def leave(c:Client, m:Message):
    del games[str(m.from_user.id)]
    await m.reply('Ok, você saiu da partida que você estava')

@Client.on_message(filters.command("start"), group=2)
async def start(c:Client, m:Message):
    cid = m.text.split('_')[1]
    if not cid in battles:
        await m.reply('essa partida não existe, talvez já tenha acabado')
    elif battles[str(cid)]['is_started']:
        await m.reply('essa partida já foi iniciada')
    elif str(m.from_user.id) in games:
        await m.reply('Você já está em uma partida')
    else:
        create_game(m)
        battles[cid]['players'].append(m.from_user.id)
        await m.reply('Entrado com sucesso.')
        text = 'Jogadores:\n\n'
        for i in battles[str(cid)]['players']:
            text += f'{(await c.get_chat(i)).first_name} ❤️\n'
        text += '\nEntre no botão abaixo:'
        keyb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                "Entrar na partida",
                url=f"https://t.me/{(await c.get_me()).username}?start=game_{cid}")],
            [InlineKeyboardButton(
                "Começar partida",
                callback_data=f"game_start")]
            ])
        await battles[str(cid)]['message'].edit_message_text(text, reply_markup=keyb)

@Client.on_message(filters.command(["minesweeper", "start_ms", "campo"]))
async def new_game(c, m):
    keyb = [
        [('Solo', 'create_solo'), ('PVP', f'create_battle')],
    ]
    await m.reply('Escolha um modo de jogo abaixo:', reply_markup=ikb(keyb))

@Client.on_callback_query(filters.regex("^(create_battle)"))
async def cr_battle(c:Client, m:CallbackQuery):
    if not m.message.chat.id in battles and m.message.chat.type != ChatType.PRIVATE and m.message.reply_to_message.from_user.id == m.from_user.id:
        await m.edit_message_text('Criando partida')
        battles.update({str(m.message.chat.id):{'players':[m.from_user.id], 'losed':[], 'message':m, "is_started":False}})
        create_game(m)
        keyb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                "Entrar na partida",
                url=f"https://t.me/{(await c.get_me()).username}?start=game_{str(m.message.chat.id)}")]
            ])
        await m.edit_message_text('Partida criada e você já foi adicionada nela\nPara outos jogadores entrar ultilize o botão abaixo:', reply_markup=keyb)

@Client.on_callback_query(filters.regex("^(game_start)"))
async def start_battle(c:Client, m:CallbackQuery):
    if m.message.reply_to_message.from_user.id == m.from_user.id:
        cid = m.message.chat.id
        battles[str(cid)]['is_started'] = True
        for i in battles[str(cid)]['players']:
            sent = await c.send_message(i,'Começando o jogo')
            g = games[str(i)]['game']
            games[str(i)]['message'] = sent
            games[str(i)]['battle'] = cid
            player_map = [[[replaces(g.game[column][row]), f'_mw|{column}x{row}x{i}'] for row in range(6)] for column in range(12)]
            await sent.edit("Let's go", reply_markup=ikb(player_map))
        text = 'Jogo iniciado\nJogadores:\n\n'
        for i in battles[str(cid)]['players']:
            text += f'{(await c.get_chat(i)).first_name} ❤️\n'
        text += '\n'
        await c.send_message(cid, 'Partida iniciada!!!')
        await battles[str(cid)]['message'].edit_message_text(text)

@Client.on_callback_query(filters.regex("^(create_solo)"))
async def start_game(c, m:CallbackQuery):
    print(m.message.chat)
    if m.message.chat.type == ChatType.PRIVATE or m.message.reply_to_message.from_user.id == m.from_user.id:
        player_map = create_game(m)
        await m.edit_message_text("Let's go", reply_markup=ikb(player_map))

def create_game(m):
    g = Game()
    games.update({str(m.from_user.id):{'game':g, 'message':m, 'battle':'', 'time':''}})
    g.create_game()
    print(g.show_game())
    player_map = [[[g.game[column][row], f'_mw|{column}x{row}x{m.from_user.id}'] for row in range(6)] for column in range(12)]
    return player_map

@Client.on_callback_query(filters.regex("^(_mw)"))
async def played(c: Client, m:CallbackQuery):
    x, y, user = (m.data.split('|')[1]).split('x')
    if user == str(m.from_user.id):
        x, y = int(x), int(y)
        g:Game = games[str(m.from_user.id)]['game']
        if not games[str(m.from_user.id)]['time']:
            print(time.time())
            games[str(m.from_user.id)]['time'] = time.time()
        if g.matrix[x][y] == 'M':
            await m.edit_message_text('Fim de jogo, voce durou: {}\n\n{}'.format(get_time(games[str(m.from_user.id)]['time'], time.time()), replaces(g.show_game())))
            if games[str(m.from_user.id)]['battle']:
                cid = games[str(m.from_user.id)]['battle']
                battles[str(cid)]['players'].remove(m.from_user.id)
                battles[str(cid)]['losed'].append(m.from_user.id)
                text = 'Game:\n\n'
                for i in battles[str(cid)]['players']:
                    hour = ''
                    if games[str(i)]['time']:
                        hour = get_time(games[str(i)]['time'], time.time())
                    text += f'{(await c.get_chat(i)).first_name} ❤️ {hour}\n'
                text += '\n'
                for i in battles[str(cid)]['losed']:
                    if games[str(i)]['time']:
                        hour = get_time(games[str(i)]['time'], time.time())
                    text += f'{(await c.get_chat(i)).first_name} 💀 {hour}\n'
                if len(battles[str(cid)]['players']) == 1:
                    i = battles[str(cid)]['players'][0]
                    g = games[str(i)]['game']
                    if len(g.played) >= 3:
                        texts = [
                            f'Partida encerrada pois quase todos perderam.\nEntão {(await c.get_chat(i)).first_name} ganhou pq foi o que não perdeu.\n\n{text}',
                            'You Win\n\n{}'.format(replaces(g.show_game()))
                        ]
                    else:
                        texts = [
                            f'Partida encerrada pois todos perderam.\nSobou o {(await c.get_chat(i)).first_name} porém ele não jogou nenhum.\n\n{text}',
                            'You NOT Win\n\n{}'.format(replaces(g.show_game()))
                        ]
                    await battles[str(cid)]['message'].edit_message_text(texts[0])
                    await games[str(i)]['message'].edit(texts[1])
                    for i in battles[str(cid)]['players']:
                        del games[str(i)]
                    del battles[str(cid)]

                else:
                    await battles[str(cid)]['message'].edit_message_text(text)
            else:
                del games[str(m.from_user.id)]
            return
        if [x, y] in g.played:
            return
        g.click(x, y)
        if len(g.played) >= 62:
            await m.edit_message_text('Você veneu, e demorou {}\n\n{}'.format(get_time(games[str(m.from_user.id)]['time'], time.time()), replaces(g.show_game())))
            if games[str(m.from_user.id)]['battle']:
                cid = games[str(m.from_user.id)]['battle']
                await battles[str(cid)]['message'].edit_message_text(f'Partida encerrada, {m.from_user.first_name} ganhou\n\n{replaces(g.show_game())}')
                del games[str(m.from_user.id)]
                for i in battles[str(cid)]['players']:
                    if i != m.from_user.id and str(i) in games:
                        g = games[str(i)]['game']
                        await games[str(i)]['message'].edit(f'Desculpe, o {m.from_user.first_name} ganhou\n\n{replaces(g.show_game())}')
                        del games[str(i)]
                del battles[str(cid)]
            return
        player_map = [[[replaces(g.game[column][row]), f'_mw|{column}x{row}x{m.from_user.id}'] for row in range(6)] for column in range(12)]
        await m.edit_message_text("Let's go", reply_markup=ikb(player_map))

def get_time(time1, time2):
    return datetime.datetime.utcfromtimestamp(time2-time1).strftime('%M:%S')

def replaces(text):
    text = str(text)
    text = text.replace('0','⬜️')
    text = text.replace('1','1⃣')
    text = text.replace('2','2⃣')
    text = text.replace('3','3⃣')
    text = text.replace('4','4⃣')
    text = text.replace('5','5⃣')
    text = text.replace('6','6⃣')
    text = text.replace('7','7⃣')
    text = text.replace('M','💣')
    return text
