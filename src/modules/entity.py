import time
import traceback
import discord
import modules.database as db
from random import randint, choice

mutes = []


class CommandError(Exception):
    pass


class command():
    commands = []
    categories = []
    def __init__(self, name, func, category, desc='Este comando faz algo!', args=[], cost=0, perm=0):
        self.name = name
        self.func = func
        self.category = category
        self.desc = desc
        self.args = args
        self.cost = cost
        self.perm = perm

        command.commands.append(self)


    async def execute(self, message, param, connection, bot):
        await self.func(message, param, connection, bot)


    @classmethod
    async def trycommand(cls, message, content, connection, masterid, bot):
        contlist = content.split()
        contcommand = str(contlist[0]).lower()

        if len(contlist) > 1:
            commandpar = ' '.join(contlist[1:])
        else:
            commandpar = None


        cmd = cls.getcommand(message.guild.id, contcommand,connection)
        if cmd == None:
            return

        if cmd['active'] == 0:
            return

        if cmd['permission'] == 2:
            if message.author.id != masterid:
                await message.channel.send('Voce não possui permissão para isto! :sob:')
                return

        if cmd['permission'] >= 1:
            if not message.author.guild_permissions.administrator:
                await message.channel.send('Voce não possui permissão para isto! :sob:')
                return

        if cmd['price'] > 0:
            points = db.getpoints(message.author.id, message.guild.id, connection)
            if points < cmd['price']:
                await message.channel.send(f'{message.author.mention}, Voce não possui coins suficiente, custo do comando é de `{cmd["price"]}c`')
                return
            else:
                await message.channel.send(f'{message.author.mention} comprou {cmd["name"]} por `{cmd["price"]}c`')
                db.subpoints(message.author.id, message.guild.id, cmd['price'], connection)

        if cmd['overwritten'] == 0:
            try:
                _cmd = [x for x in cls.commands if x.name == cmd['name']][0]
                await _cmd.execute(message, commandpar, connection, bot)
            except CommandError as e:
                await message.channel.send(e)
                if cmd['price'] > 0:
                    db.addpoints(message.author.id, message.guild.id, cmd['price'], connection)
            except Exception:
                traceback.print_exc()
        else:
            await message.channel.send(cmd['message'])


    @classmethod
    def getcommand(cls, guildid, name, connection):
        _command = db.getservercommand(guildid, name, connection)
        if _command == None:
            for cmd in cls.commands:
                if cmd.name == name:
                    _cmd = ['', cmd.name, '', cmd.desc, cmd.args, cmd.perm, cmd.cost, cmd.category, 1, 0]
                    leg = ['serverid', 'name', 'message', 'description', 'args', 'permission', 'price', 'category', 'active', 'overwritten']
                    result = dict(zip(leg, _cmd))
                    return result
        else:
            return _command


    @classmethod
    def getallcommands(cls, guildid, connection):
        _commands = db.getallserverscommands(guildid, connection)

        for cmd in cls.commands:
            c = 0
            for i in _commands:
                if i['name'] == cmd.name:
                    c = 1

            if c == 1:
                continue

            _cmd = ['', cmd.name, '', cmd.desc, cmd.args, cmd.perm, cmd.cost, cmd.category, 1, 0]
            leg = ['serverid', 'name', 'message', 'description', 'args', 'permission', 'price', 'category', 'active', 'overwritten']
            _commands.append(dict(zip(leg, _cmd)))

        return _commands


    @classmethod
    def newcategory(cls, category, visual_name, is_visible=True):
        cls.categories.append([category, visual_name, is_visible])


    @classmethod
    def getcommandsbycategory(cls, category, guildid, connection):
        cmds = []
        for cmd in cls.getallcommands(guildid, connection):
            if category == cmd['category']:
                cmds.append(cmd)
        
        return cmds
            


    @classmethod
    def getcategories(cls):
        return cls.categories


class event():
    events = []
    def __init__(self, name:str, createfunc, executefunc, trigger='react', desc='Nothing', command_create=True, loop_event_create=True):
        self.name = name
        self.createfunc = createfunc
        self.exec = executefunc
        self.desc = desc
        self.trigger = trigger
        self.command_create = command_create
        self.loop_event_create = loop_event_create
        self.cache = dict()
        event.events.append(self)

    async def create(self, par, ind:str):
        cache = self.getcache(ind)

        if cache == None:
            cache = await self.createfunc(par)
            self.cache[ind] = cache


    async def execute(self, par, ind:str):
        cache = self.getcache(ind)

        if cache == None:
            return
        
        if cache == True:
            self.clear(ind)
            return

        cache = await self.exec(par, cache)
        self.cache[ind] = cache


    def msgvalidation(self, msg, ind:str):
        cache = self.getcache(ind)
        if cache == None:
            return False
        
        if cache == True:
            return False

        if cache[0] == msg:
            return True
        else:
            return False


    def getcache(self, ind):
        ind = str(ind)
        try:
            cache = self.cache[ind]
        except:
            cache = None

        return cache


    def clear(self, ind:str):
        if self.getcache(ind) != None:
            self.cache.pop(ind)


class timer():
    timers = []

    @classmethod
    def timer(cls, ind, segs, recreate=False):
        timenow = time.time()

        check = 0
        for i in cls.timers:
            if i[0] == ind:
                check = 1
                if (timenow - i[1]) >= i[2]:
                    cls.timers.remove(i)
                    if recreate:
                        cls.timers.append([ind,timenow,segs])

                    return True
                else:
                    return False
        
        if check == 0:
            if segs > 0:
                cls.timers.append([ind,timenow,segs])
            return False


class Client(discord.Client):
    def __init__(self, db_connection, master_id, **kwargs):
        super().__init__(**kwargs)
        self.db_connection = db_connection
        self.master_id = master_id

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(f'{len(self.guilds)} servers!'))
        
        for guild in self.guilds:
            if db.getserver(guild.id, self.db_connection) == None:
                db.addserver(guild.id, self.db_connection)

        command.newcategory('personalizado', ':paintbrush:Personalizados.')

        print(f'{self.user} esta logado em {len(self.guilds)} grupos!')
        print('Pronto!')


    async def on_message(self, message):
        if message.author == self.user:
            return

        server = db.getserver(message.guild.id, self.db_connection)

        #add (pointsqt) points every (pointstime) seconds
        pointstime = 300
        pointsqt = 100

        if timer.timer('point_time_'+str(message.guild.id), pointstime, recreate=1):
            for member in message.guild.members:
                if member.status == 'offline' or (member.bot == True and member.id != self.user.id):
                    continue
                
                db.addpoints(member.id,message.guild.id,pointsqt, self.db_connection)


        if str(message.author.id)+str(message.channel.id) in mutes:
            if timer.timer(str(message.author.id)+str(message.channel.id),0):
                mutes.remove(str(message.author.id)+str(message.channel.id))
            else:
                await message.delete()
                return
        
        auto_events = server['auto_events']
        if auto_events:
            if timer.timer('event_time_'+str(message.guild.id), randint(1000,10000), recreate=1) == True:
                
                eventchannel = server['eventchannel']

                try:
                    eventchannel = self.get_channel(int(eventchannel))
                    if eventchannel == None:
                        eventchannel = message.channel
                except:
                    db.editserver(message.guild.id, self.db_connection, 'eventchannel', None)
                    eventchannel = message.channel
                
                
                eve = choice([i for i in event.events if i.loop_event_create])
                eve.clear(str(message.guild.id))
                
            
                await eve.create([eventchannel], str(message.guild.id))
                        

        try:
            print(f'{message.guild} #{message.channel} //{message.author} : {message.content}')

            
            prefix = server['prefix']
            cmdchannel = server['commandchannel']


            if cmdchannel == None:
                pass
            elif self.get_channel(int(cmdchannel)) == None:
                db.editserver(message.guild.id, self.db_connection, 'commandchannel', None)
                cmdchannel = None

            if message.content == f'<@!{self.user.id}>':
                helpstr = f'{prefix}help para lista de comandos.'
                

                if cmdchannel != None:
                    helpstr += f'\nCanal de comandos: <#{cmdchannel}>'

                await message.channel.send(helpstr)
                return


            if message.content[0:len(prefix)] == prefix:
                if cmdchannel == None:
                    pass
                elif int(cmdchannel) != message.channel.id:
                    return

                content = message.content[len(prefix):]
                await command.trycommand(message, content, self.db_connection, self.master_id, self)
 

            for eve in event.events:
                if eve.trigger == 'message':
                    await eve.execute([message, self.db_connection], str(message.guild.id))

        except Exception as e:
            print(e)
            traceback.print_exc()
        

    async def on_reaction_add(self, reaction, user):
        if user == self.user:
            return

        for eve in event.events:
            if eve.msgvalidation(reaction.message, str(reaction.message.guild.id)) and eve.trigger == 'react':
                await eve.execute([user,reaction.emoji, self.db_connection], str(reaction.message.guild.id))

    async def on_guild_join(self, guild):
        if db.getserver(guild.id, self.db_connection) == None:
                db.addserver(guild.id, self.db_connection)

