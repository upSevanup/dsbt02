import discord
from discord.ext import commands, tasks
from discord import utils
import random, logging
from config import *
from functions import *
import datetime
import os

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = discord.Intents.all()
intents.members = True

async def open_acc(user):
    users = await get_bank()
    if user.bot is True:
        return
    if str(user.id) in users:
        return False
    else:
        users[str(user.id)] = {}
        users[str(user.id)]['wallet'] = 100
    write_json('jsons/bank', users)
    return True

async def get_bank():
    users = load_json('jsons/bank')
    return users


class KiBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @tasks.loop()
    async def check_mutes(self):
        current = datetime.datetime.now()
        mutes = load_json("jsons/mutes")
        users, times = list(mutes.keys()), list(mutes.values())
        for i in range(len(times)):
            time = times[i]
            unmute = datetime.datetime.strptime(str(time), "%c")
            if unmute < current:
                user_id = users[times.index(time)]
                try:
                    member = await self.guild.fetch_member(int(user_id))
                    await member.remove_roles(self.mutedrole)
                    mutes.pop(str(member.id))
                except discord.NotFound:
                    pass
                write_json("jsons/mutes", mutes)

    @commands.command(name='ban')
    @commands.has_permissions(administrator=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None, amount=1):
        await ctx.channel.purge(limit=int(amount))
        await member.ban(reason=reason)
        await ctx.send(f'{ member.mention } был забанен')

    @commands.command(name='unban')
    @commands.has_permissions(administrator=True)
    async def unban(self, ctx, *, member):
        await ctx.channel.purge(limit=1)
        banned_users = await ctx.guild.bans()
        for ban_entry in banned_users:
            user = ban_entry.user
            await ctx.guild.unban(user)
            await ctx.send(f'{ctx.author.name} разбанил {user.mention}')
            return

    @commands.command(name='roll')
    async def roll(self, ctx, min_int, max_int):
        num = random.randint(int(min_int), int(max_int))
        await ctx.send(num)

    @commands.command()
    @commands.has_any_role(ACCESS_ROLE)
    async def mute(self, ctx, member: discord.Member = None, time: str = None, *, reason="не указана"):
        if member is None:
            return await ctx.send("Укажите пользователя")
        if member.bot is True:
            return await ctx.send("Вы не можете замутить бота")
        if member == ctx.author:
            return await ctx.send("Вы не можете замутить себя")
        if len(reason) > 150:
            return await ctx.send("Причина слишком длинная")
        if member and member.top_role.position >= ctx.author.top_role.position:
            return await ctx.send("Вы не можете замутить человека с ролью выше вашей")
        if time is None:
            return await ctx.send("Вы не указали время")
        else:
            try:
                seconds = int(time[:-1])
                duration = time[-1]
                if duration == "s":
                    pass
                if duration == "m":
                    seconds *= 60
                if duration == "h":
                    seconds *= 3600
                if duration == "d":
                    seconds *= 86400
            except:
                return await ctx.send("Указана неправильная продолжительность")
            mute_expiration = (datetime.datetime.now() + datetime.timedelta(seconds=int(seconds))).strftime("%c")
            role = self.mutedrole
            if not role:
                return await ctx.send("Я не могу найти роль мута")
            mutes = load_json("jsons/mutes")
            try:
                member_mute = mutes[str(member.id)]
                return await ctx.send("Пользователь ужe в муте")
            except:
                mutes[str(member.id)] = str(mute_expiration)
                write_json("jsons/mutes", mutes)
                await member.add_roles(role)
                await member.move_to(channel=None)
                await ctx.send(f"{ctx.author.mention} замутил(а) {member.mention}"
                               f" до {mute_expiration} по причине: {reason}")

    @commands.command()
    @commands.has_any_role(ACCESS_ROLE)
    async def unmute(self, ctx, member: discord.Member):
        await member.remove_roles(self.mutedrole)
        await ctx.send(f"{ctx.author.mention} размутил(а) {member.mention}")
        mutes = load_json("jsons/mutes")
        mutes.pop(str(member.id))
        write_json("jsons/mutes", mutes)

    @commands.command(name='kick')
    @commands.has_permissions(administrator=True)
    async def kick(self, ctx, member: discord.Member, *, reason='Гнев Бога'):
        await ctx.channel.purge(limit=1)

        await member.kick(reason=reason)
        await ctx.send(f'{ctx.author.name} кикнул {member.mention}')

    @commands.command(name='clear')
    async def clear(self, ctx, amount: int):
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f'Удалено {amount} сообщений!', delete_after=3)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id == ROLE_POST_ID:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            member = await (await self.bot.fetch_guild(payload.guild_id)).fetch_member(payload.user_id)

            emoji = str(payload.emoji)
            role = utils.get(message.guild.roles, id=ROLES[emoji])

            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id == ROLE_POST_ID:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            member = await (await self.bot.fetch_guild(payload.guild_id)).fetch_member(payload.user_id)

            emoji = str(payload.emoji)
            role = utils.get(message.guild.roles, id=ROLES[emoji])

            await member.remove_roles(role)

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = await self.bot.fetch_guild(SERVER_ID)  # You server id
        self.mutedrole = utils.get(self.guild.roles, id=MUTE_ROLE)  # Mute role id
        self.check_mutes.start()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.bot.get_channel(GREETINGS_CHAT)
        await channel.send(f'''Привет, {member.mention}!
напиши //help_me если хочешь ознакомиться с командами сервера''')

    @commands.command(name='poker')
    async def poker(self, ctx, num: int, member: discord.Member = None):
        await open_acc(ctx.author)
        await open_acc(member)
        users = await get_bank()
        member_bank = users[str(member.id)]['wallet']
        author_bank = users[str(ctx.author.id)]['wallet']
        if author_bank < num:
            await ctx.send('У вас не достаточно денег')
            return
        elif member_bank < num:
            await ctx.send(f'У {member.mention} не достаточно денег')
            return

        combos = ['ничего', 'пара', 'две пары', 'сет', 'фулл хаус', 'каре', 'покер']
        edges = ['\u2680', '\u2681', '\u2682', '\u2683', '\u2684', '\u2685']

        player_1, pl_1_score, combo_1 = poker()
        player_2, pl_2_score, combo_2 = poker()

        winner = ''
        looser = ''
        if player_1 == player_2:
            if pl_1_score > pl_2_score:
                winner = ctx.author
                looser = member
            elif pl_1_score < pl_2_score:
                winner = member
                looser = ctx.author
        elif combos.index(player_1) > combos.index(player_2):
            winner = ctx.author
            looser = member
        else:
            winner = member
            looser = ctx.author

        await ctx.send(f'''{ctx.author.mention}: 
{edges[combo_1[0] - 1]} {edges[combo_1[1] - 1]} {edges[combo_1[2] - 1]} {edges[combo_1[3] - 1]} {edges[combo_1[4] - 1]} 
комбинация: {player_1} 
счёт: {pl_1_score} \n
{member.mention}: 
{edges[combo_2[0] - 1]} {edges[combo_2[1] - 1]} {edges[combo_2[2] - 1]} {edges[combo_2[3] - 1]} {edges[combo_2[4] - 1]} 
комбинация: {player_2} 
счёт: {pl_2_score} \n
Победил {winner.mention}!''')

        await open_acc(winner)
        users = await get_bank()
        users[str(winner.id)]['wallet'] += num
        write_json('jsons/bank', users)

        await open_acc(looser)
        users = await get_bank()
        users[str(looser.id)]['wallet'] += num * -1
        write_json('jsons/bank', users)

    @commands.command(name='poker_rules')
    async def poker_rules(self, ctx):
        await ctx.send(f'''Для каждого игрока бросается по 5 игральных кубиков,
игрок с большей комбиеацией побеждает и получает выйгрыш (у проигравшего MarciСoins забираются)
Комбинации (по возрастанию):
1 - ничего
2 - пара
3 - две пары
4 - сет
5 - фулл хаус
6 - каре
8 - покер
Если у игроков одинаковые комбинации то выигрывает тот, у кого больше счёт в комбинации''')

    @commands.command(name='help_me')
    async def help_me(self, ctx):
        await ctx.send(f'''Список команд и возможностей:
//ban member - бан выбранного пользователя
//mute member time s/m/h/d - мут пользователя на время
//kick member - кикнуть выбранного пользователя
//clear number - удалить определённое число сообщений
в чате greetings можно получить роль кликнув на реакцию
//balance - посмотреть свой баланс (Points)
//poker bet member - покер костями с другим участником
//roll mum_1 num_2 - случайное число от num_1 до num_2''')


class Eco(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def balance(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        await open_acc(member)
        users = await get_bank()
        member_bank = users[str(member.id)]['wallet']
        await ctx.send(f'Баланс {member.mention}: {member_bank} Points')

    @commands.command()
    async def pay(self, ctx, num: int, member: discord.Member = None):
        if member is None:
            return await ctx.send('Вы не указали пользователя!', delete_after=3)
        if num < 0:
            return await ctx.send('Перевод должен быть положительным', delete_after=3)
        await open_acc(ctx.author)
        await open_acc(member)
        users = await get_bank()
        member_bank = users[str(member.id)]['wallet']
        author_bank = users[str(ctx.author.id)]['wallet']
        if author_bank < num:
            return await ctx.send('У вас недостаточно средств', delete_after=3)
        users[str(member.id)]['wallet'] += num
        users[str(ctx.author.id)]['wallet'] -= num
        write_json('jsons/bank', users)
        await ctx.send(f'{ctx.author.mention} перевел(а) {member.mention}: {num} Points')

    @commands.command()
    @commands.has_any_role(ACCESS_ROLE)
    async def dupe(self, ctx, num: int):
        await open_acc(ctx.author)
        users = await get_bank()
        author_bank = users[str(ctx.author.id)]['wallet']
        if num < 0:
            users[str(ctx.author.id)]['wallet'] += num
            write_json('jsons/bank', users)
            await ctx.send(f'Вы забрали у себя: {num * -1} Points')
        else:
            users[str(ctx.author.id)]['wallet'] += num
            write_json('jsons/bank', users)
            await ctx.send(f'Вы выдали себе: {num} Points')


bot = commands.Bot(command_prefix='//', intents=intents)
bot.add_cog(KiBot(bot))
bot.add_cog(Eco(bot))

bot.run(TOKEN)
