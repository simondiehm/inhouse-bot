#!/usr/bin/python3

import asyncio
import datetime
import discord
import json
import os
import random
import re
import socket
import urllib.request
import requests
import subprocess
import aiohttp

from collections import deque
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext import tasks

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix = ["!", "+", "-"], help_command=None, case_insensitive=True, intents=intents)

load_dotenv()
DISCORD_TOKEN=""
TOKEN = DISCORD_TOKEN
#TOKEN = os.getenv('DISCORD_TOKEN')
#CHANNEL_NAME = os.getenv('DISCORD_CHANNEL')
CHANNEL_NAME = 'pugs'
#SERVER_IP = os.getenv('SERVER_IP')
SERVER_IP = "45.77.239.85"
#SERVER_PORT = os.getenv('SERVER_PORT') # port to communicate with server plugin
SERVER_PORT = "27015"
#SERVER_PASSWORD = os.getenv('SERVER_PASSWORD')
SERVER_PASSWORD = "4v4"
CLIENT_PORT = os.getenv('CLIENT_PORT') # port to communicate with client plugin listener (serverComms.py)

# on load, load previous teams + map from the prev* files
if os.path.exists('prevmaps.json'):
    with open('prevmaps.json', 'r') as f:
        previousMaps = deque(json.load(f), maxlen=5)
else:
    previousMaps = []

if os.path.exists('prevteams.json'):
    with open('prevteams.json', 'r') as f:
        previousTeam = json.load(f)
else:
    previousTeam = []

emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
mapList = []

playerList = {}
pickupStarted = False
pickupActive = False
playerNumber = 8
lastAdd = datetime.datetime.utcnow()
lastAddCtx = None

mapChoices = []

recentlyPlayedMapsMsg = None
mapVote = False
mapVoteMessage = None
mapVoteMessageView = None
nextCancelConfirms = False

class MapChoice:
    def __init__(self, mapName, decoration=None):
        self.mapName = mapName
        self.decoration = decoration
        self.votes = []

    ## maybe other voting methods here?

async def HandleMapButtonCallback(self, interaction: discord.Interaction, button: discord.ui.Button):
    global mapVoteMessage
    if self is mapVoteMessageView:
        processVote(interaction.user, int(button.custom_id))
        await interaction.response.edit_message(embed=GenerateMapVoteEmbed())

class MapChoiceView(discord.ui.View):
    def __init__(self, mapChoices):
        super().__init__()
        self.addButtons()

    def addButtons(self):
        default_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
        emoji_symbols = default_emojis[:len(mapChoices)]
    
        for idx, mapChoice in enumerate(mapChoices):
            self.add_item(self.createButton(label=f"{emoji_symbols[idx]} {mapChoice.mapName}", custom_id=f"{idx + 1}"))

    def createButton(self, label, custom_id):
        button = discord.ui.Button(label=label, custom_id=custom_id)

        async def mapButtonCallback(interaction: discord.Interaction):
            await HandleMapButtonCallback(self, interaction, button)

        button.callback = mapButtonCallback
        return button



# @debounce(2)
async def printPlayerList(ctx):
    global playerList
    global playerNumber

    msg =  ", ".join([s for s in playerList.values()])
    counter = str(len(playerList)) + "/" + str(playerNumber)

    await ctx.send("```\nPlayers (" + counter + ")\n" + msg + "```")
    await updateNick(ctx, counter)

async def DePopulatePickup(ctx):
    global pickupStarted
    global pickupActive
    global playerNumber
    global mapVote
    global playerList

    mapVote = False
    pickupStarted = False
    pickupActive = False
    playerNumber = 8
    playerList = {}

    if idlecancel.is_running():
        idlecancel.stop()

    if ctx:
        await updateNick(ctx)


def PickMaps(initial=False):
    global mapList
    global mapChoices

    mapChoices = []
    if initial:
        for i in range(3):
            if i == 0:
                mapname = random.choice(mapList["tier1"] + mapList["tier2"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname, "⭐"))
            elif i == 1:
                mapname = random.choice(mapList["tier2"] + mapList["tier3"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname))
            elif i == 2:
                mapname = random.choice(mapList["tier3"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname))
    else:
        for i in range(3):
            if i == 0:
                mapname = random.choice(mapList["tier1"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname, "✨"))
            elif i == 1:
                mapname = random.choice(mapList["tier1"] + mapList["tier2"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname, "⭐"))
            elif i == 2:
                mapname = random.choice(mapList["tier2"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname))

def RemoveMap(givenMap):
    global mapList

    if givenMap in mapList['tier1']:
        mapList['tier1'].remove(givenMap)
    elif givenMap in mapList['tier2']:
        mapList['tier2'].remove(givenMap)
    elif givenMap in mapList['tier3']:
        mapList['tier3'].remove(givenMap)

def RecordMapAndTeams(winningMap):
    global previousMaps
    global playerList
    global previousTeam

    previousMaps.append(winningMap)
    with open('prevmaps.json', 'w') as f:
        json.dump(list(previousMaps), f)

    previousTeam = list(playerList.values())
    with open('prevteams.json', 'w') as f:
        json.dump(previousTeam, f)

async def updateNick(ctx, status=None):
    if status == "" or status is None:
        status = None
    else:
        status = "inhouse-bot (" + status + ")"

    await ctx.message.guild.me.edit(nick=status)

@client.command(pass_context=True)
async def pickup(ctx):
    global pickupStarted
    global pickupActive
    global mapVote
    global mapList
    global playerNumber
    global previousMaps
    global recentlyPlayedMapsMsg
    global nextCancelConfirms

    if pickupStarted == False and pickupActive == False and mapVote == False:
        with open('maplist.json') as f:
            mapList = json.load(f)
            for prevMap in previousMaps:
                for tier in mapList.values():
                    if prevMap in tier:
                        tier.remove(prevMap)

        DePopulatePickup

        pickupStarted = True
        nextCancelConfirms = False
        recentlyPlayedMapsMsg = "Maps %s were recently played and are removed from voting." % ", ".join(previousMaps)

        await ctx.send("Pickup started. !add in 3 seconds")
        await updateNick(ctx, "starting...")
        await asyncio.sleep(3)

        if pickupStarted == True:
            pickupActive = True
            await ctx.send("!add enabled")
            await printPlayerList(ctx)
        else:
            await ctx.send("Pickup was canceled before countdown finished 🤨")

@client.command(pass_context=True)
async def cancel(ctx):
    global pickupStarted
    global pickupActive
    global mapVote
    global mapVoteMessage
    global nextCancelConfirms

    if mapVote != False and not nextCancelConfirms:
        await ctx.send("You're still picking maps, still wanna cancel?")
        nextCancelConfirms = True
        return
    if pickupStarted == True or pickupActive == True:
        pickupStarted = False
        pickupActive = False
        if mapVoteMessage is not None:
            await mapVoteMessage.edit(view=None)
            mapVoteMessage = None
        await ctx.send("Pickup canceled.")
        await DePopulatePickup(ctx)
    else:
        await ctx.send("No pickup active.")

@client.command(pass_context=True)
async def playernumber(ctx, numPlayers: int):
    global playerNumber

    try:
        players = int(numPlayers)
    except:
        await ctx.send("Given value isn't a number you doofus.")
        return

    if players % 2 == 0 and players <= 20 and players >= 2:
        playerNumber = players
        await ctx.send("Set pickup to fill at %d players" % playerNumber)
        await updateNick(ctx, str(len(playerList)) + "/" + str(playerNumber))
    else:
        await ctx.send("Can't set pickup to an odd number, too few, or too many players")

def GenerateMapVoteEmbed():
    global emoji
    global mapChoices
    global recentlyPlayedMapsMsg

    if len(emoji) < len(mapChoices):
        print(f"[WARNING] emoji list too short: {len(emoji)} < {len(mapChoices)}")

    default_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    emoji_symbols = default_emojis[:len(mapChoices)]

    embed = discord.Embed(
        title="Vote for your map!",
        description=f"When vote is stable, !lockmap",
        color=0x00FFFF
    )

    for i in range(len(mapChoices)):
        mapChoice = mapChoices[i]
        mapName = mapChoice.mapName
        decoration = mapChoice.decoration or ""

        votes = mapChoice.votes
        numVotes = len(votes)
        whoVoted = ", ".join([playerList[playerId] for playerId in votes])
        whoVotedString = whoVoted
        if len(whoVoted) > 0:
            whoVotedString = "_" + whoVotedString + "_"

        if numVotes == 1:
            voteCountString = "1 vote"
        else:
            voteCountString = "%d votes" % (numVotes)

        emoji_symbol = emoji_symbols[i]
        embed.add_field(
        name="",
        value=emoji_symbol + " `" + mapName + " " + decoration + 
          (" " * (25 - len(mapName) - 2 * len(decoration))) + voteCountString + "`\n\u200B" + whoVotedString,
        inline=False
        )

    if recentlyPlayedMapsMsg != None:
        embed.add_field(name="", value=recentlyPlayedMapsMsg, inline=False)

    playersVoted = [playerId for mapChoice in mapChoices for playerId in mapChoice.votes]
    playersAbstained = [playerList[playerId] for playerId in playerList.keys() if playerId not in playersVoted]
    if len(playersAbstained) != 0 and len(playersAbstained) != len(playerList):
        embed.add_field(name="", value="```💩 " + ", ".join(playersAbstained) +  " need" + ("s" if len(playersAbstained) == 1 else "") + " to vote 💩```", inline=False)

    return embed

@client.command(pass_context=True, name="+")
async def plusPlus(ctx):
    if ctx.prefix == "+":
        await add(ctx)

@client.command(pass_context=True, name="-")
async def minusMinus(ctx):
    if ctx.prefix == "-":
        await remove(ctx)

@client.command(pass_context=True)
async def add(ctx):
    global playerNumber
    global playerList
    global pickupActive
    global mapVote
    global mapVoteMessage
    global mapVoteMessageView
    global previousMaps
    global lastAdd
    global lastAddCtx

    global mapChoices

    player = ctx.author

    if pickupActive == True:
        playerId = player.id
        playerName = player.display_name
        if playerId not in playerList:
            playerList[playerId] = playerName
            lastAdd = datetime.datetime.utcnow()

            if not idlecancel.is_running():
                idlecancel.start()
                lastAddCtx = ctx

            if len(playerList) < playerNumber:
                await printPlayerList(ctx)
            else:
                pickupActive = False
                if idlecancel.is_running():
                    idlecancel.stop()

                await printPlayerList(ctx)
                await updateNick(ctx, "voting...")

                # ensure that playerlist is first n people added
                playerList = dict(list(playerList.items())[:playerNumber])

                PickMaps(True)
                mapChoices.append(MapChoice("New Maps"))

                mapVote = True

                embed = GenerateMapVoteEmbed()
                mapVoteMessageView = MapChoiceView(mapChoices)
                mapVoteMessage = await ctx.send(embed=embed, view=mapVoteMessageView)

                mentionString = ""
                for playerId in playerList.keys():
                    mentionString = mentionString + ("<@%s> " % playerId)
                await ctx.send(mentionString)

@tasks.loop(minutes=30)
async def idlecancel():
    global lastAdd
    global lastAddCtx
    global pickupActive
    global mapVote

    if pickupActive == True and pickupStarted == True and mapVote == False:
        # check if 3 hours since last add
        lastAddDiff = (datetime.datetime.utcnow() - lastAdd).total_seconds()
        print("last add was %d minutes ago" % (lastAddDiff / 60))

        if lastAddDiff > (3 * 60 * 60):
            print("stopping pickup")

            await lastAddCtx.send("Pickup idle for more than three hours, canceling.")
            await DePopulatePickup(lastAddCtx)

@client.command(pass_context=True)
async def remove(ctx):
    global playerList
    global pickupActive

    if pickupActive == True :
        if ctx.author.id in playerList:
            del playerList[ctx.author.id]
            await printPlayerList(ctx)

@client.command(pass_context=True)
@commands.has_role('badmin')
async def kick(ctx, player: discord.User):
    global playerList

    if player is not None and player.id in playerList:
        del playerList[player.id]
        await ctx.send("Kicked %s from the pickup." % player.mention)
        await printPlayerList(ctx)

@client.command(pass_context=True)
async def teams(ctx):
    if pickupStarted == False:
        await ctx.send("No pickup active.")
    else:
        await printPlayerList(ctx)


def processVote(player: discord.Member=None, vote=None):
    global mapVote
    global playerList

    global mapChoices

    if player.id in playerList:
        # remove any existing votes
        for mapChoice in mapChoices:
            if(player.id in mapChoice.votes):
                mapChoice.votes.remove(player.id)

        mapChoices[vote - 1].votes.append(player.id)

@client.command(pass_context=True, aliases=["fv"])
async def lockmap(ctx):
    global mapVote
    global mapVoteMessage
    global mapVoteMessageView

    global mapChoices

    global mapList
    global previousMaps
    global recentlyPlayedMapsMsg
    global nextCancelConfirms

    rankedVotes = []
    highestVote = 0
    winningMap = " "

    if(mapVote == True):
        nextCancelConfirms = False

        # get top maps
        mapTally = [(mapChoice.mapName, len(mapChoice.votes)) for mapChoice in mapChoices]
        rankedVotes = sorted(mapTally, key=lambda e: e[1], reverse=True)

        highestVote = rankedVotes[0][1]

        # don't allow lockmap if no votes were cast
        if highestVote == 0:
            await ctx.send("!lockmap denied; no votes were cast.")
            return

        # Hide voting buttons now that the vote is complete.
        mapVoteMessageView = None
        await mapVoteMessage.edit(view=None)

        winningMaps = [pickedMap for (pickedMap, votes) in rankedVotes if votes == highestVote]

        # don't allow "New Maps" to win
        if len(winningMaps) > 1 and "New Maps" in winningMaps:
            winningMap = "New Maps"
        else:
            winningMap = random.choice(winningMaps)

        if(winningMap == "New Maps"):
            PickMaps()
            carryOverMap = random.choice([pickedMap for (pickedMap, votes) in rankedVotes if votes == rankedVotes[1][1] and pickedMap != "New Maps"])
            mapChoices.append(MapChoice(carryOverMap, "🔁"))

            recentlyPlayedMapsMsg = None
            embed = GenerateMapVoteEmbed()
            mapVoteMessageView = MapChoiceView(mapChoices)

            mapVoteMessage = await ctx.send(embed=embed, view=mapVoteMessageView)
        else:
            mapVoteMessage = None
            mapVoteMessageView = None

            mapVote = False
            RecordMapAndTeams(winningMap)

            await ctx.send("The winning map is: " + winningMap)
            await ctx.send("steam://connect/" + SERVER_IP + ":27015/" + SERVER_PASSWORD)
            await DePopulatePickup(ctx)

@client.command(pass_context=True)
async def vote(ctx):
    global mapVote
    global playerList
    global mapChoices

    if mapVote == True:
        playersVoted = [playerId for mapChoice in mapChoices for playerId in mapChoice.votes]
        playersAbstained = [playerId for playerId in playerList.keys() if playerId not in playersVoted]

        mentionString = "🗳️🗳️ vote maps or kick: "
        for playerId in playersAbstained:
            mentionString = mentionString + ("<@%s> " % playerId)
        await ctx.send(mentionString + " 🗳️🗳️")

@client.command(pass_context=True)
async def lockset(ctx, mapToLockset):
    global previousMaps
    global pickupActive
    global mapVote

    if ctx.channel.name != CHANNEL_NAME:
        return

    if pickupActive != False and mapVote != False:
        await ctx.send("Error: can only !lockset during map voting or if no pickup is active (changes the map for the last pickup)")
        return

    previousMaps.pop()
    previousMaps.append(mapToLockset)

    with open('prevmaps.json', 'w') as f:
        json.dump(list(previousMaps), f)

    await ctx.send("Set pickup map to %s" % mapToLockset)

@client.command(pass_context=True)
async def timeleft(ctx):
    # construct a UDP packet and send it to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto("BOT_MSG@TIMELEFT@".encode(), (SERVER_IP, int(SERVER_PORT)))

    await asyncio.sleep(3)
    if os.path.exists('timeleft.json'):
        with open('timeleft.json', 'r') as f:
            try:
                timeleft = json.load(f)
                if timeleft is not None and timeleft['timeleft']:
                    await ctx.send("Timeleft: %s" % timeleft['timeleft'])
                    return
            except:
                await ctx.send("Server did not respond.")
    else:
        await ctx.send("Server did not respond")

@client.command(pass_context=True)
async def stats(ctx):
    with open('prevlog.json', 'r') as f:
        prevlog = json.load(f)
        await ctx.send('Stats: %s' % prevlog['site'])

@client.command(pass_context=True)
@commands.has_role('admin')
async def forcestats(ctx):
    print("forcestats -- channel name" + ctx.channel.name)
    if ctx.channel.name == 'moderator-only':
        await ctx.send("force-parsing stats; wait 5 sec...")

        with open('prevlog.json', 'w') as f:
            f.write("[]")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto("BOT_MSG@END".encode(), ('0.0.0.0', int(CLIENT_PORT)))

        await asyncio.sleep(5)

        with open('prevlog.json', 'r') as f:
            prevlog = json.load(f)
            await ctx.send('Stats: %s' % prevlog['site'])

log_directory = "/home/steam/Steam/steamapps/common/Half-Life/tfc/logs/"
previous_files = set()

def find_recent_large_logs(log_directory, num_logs=2, min_size_kb=50):
    log_files = [os.path.join(log_directory, file) for file in os.listdir(log_directory) if file.endswith('.log')]
    log_files = [file for file in log_files if os.path.getsize(file) > min_size_kb * 1024]
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return log_files[:num_logs]

@client.command(pass_context=True)
async def oldlogs(ctx):
    global previous_files

    await ctx.send("Fetching logs, please wait...")
    recent_logs = find_recent_large_logs(log_directory)

    current_files = set(os.listdir(log_directory))
    previous_files = current_files

    if len(recent_logs) >= 2:
        logToParse1 = recent_logs[0]
        logToParse2 = recent_logs[1]

        # First API call (Hampalyzer)
        hampalyzer_command = [
            'curl', '-X', 'POST',
            '-F', 'force=on',
            '-F', f'logs[]=@{logToParse1}',
            '-F', f'logs[]=@{logToParse2}',
            'http://app.hampalyzer.com/api/parseGame'
        ]

        # Second API call (TFCStats)
        tfcstats_command = [
            'curl', '-X', 'POST',
            '-F', f'logs[]=@{logToParse1}',
            '-F', f'logs[]=@{logToParse2}',
            'https://www.tfcstats.com/api/parsePickup'
        ]

        try:
            # Run first API call
            hampalyzer_result = subprocess.run(hampalyzer_command, capture_output=True, text=True, check=True)
            hampalyzer_response = json.loads(hampalyzer_result.stdout.strip())

            # Run second API call
            tfcstats_result = subprocess.run(tfcstats_command, capture_output=True, text=True, check=True)
            tfcstats_response = json.loads(tfcstats_result.stdout.strip())

            # Extract URLs from responses
            hampalyzer_url = f"http://app.hampalyzer.com{hampalyzer_response['success']['path']}" if 'success' in hampalyzer_response and 'path' in hampalyzer_response['success'] else None
            tfcstats_url = tfcstats_response['success']['path'] if 'success' in tfcstats_response and 'path' in tfcstats_response['success'] else None
            # Send the links in Discord
            message = "Parsed Logs:\n"
            if hampalyzer_url:
                message += f"📌 Hampalyzer: {hampalyzer_url}\n"
            else:
                message += "❌ Hampalyzer API failed.\n"

            if tfcstats_url:
                message += f"📌 TFCStats: {tfcstats_url}\n"
            else:
                message += "❌ TFCStats API failed.\n"

            await ctx.send(message)

        except subprocess.CalledProcessError as e:
            await ctx.send(f"❌ Error while calling APIs: {e}")
    else:
        await ctx.send("⚠️ Not enough recent large log files found.")

@client.command(pass_context=True)
async def server(ctx):
    await ctx.send("connect " + SERVER_IP + "; password " + SERVER_PASSWORD)

@client.command(pass_context=True)
async def help(ctx):
    await ctx.send("tfc server info: !listmaps !mapsearch <name>")
    await ctx.send("!logs")
    await ctx.send("!entomb !schtop")
    await ctx.send("!boysouttonight")
    await ctx.send("!pickup !playernumber !add !remove !lockmap")

@client.command(pass_context=True)
async def entomb(ctx):
    await ctx.send("https://youtu.be/v3VqaATiNm0?si=3vdafgy5PxVcNu6C")

@client.command(pass_context=True)
async def schtop(ctx):
    await ctx.send("https://cdn.discordapp.com/attachments/1121809844916203520/1145367851914514492/image.png?ex=67da2f2f&is=67d8ddaf&hm=469da226878d3d8dd0300cc314938b63778b3ca0264637bce1f75e7955933aad&")

@client.event
async def on_ready():
    print(f'{client.user} is aliiiiiive!')


@client.command(pass_context=True)
async def max(ctx):
    await ctx.send("https://tenor.com/view/crash-verstappen-verstappen-crash-gif-24527805")

@client.command(pass_context=True)
async def mvp(ctx):
    await ctx.send("https://tenor.com/view/mvp-montel-vontavious-porter-entrance-wwe-smack-down-gif-18167076")

@client.command(pass_context=True)
async def boysouttonight(ctx):
    await ctx.send("https://tenor.com/view/boys-outtinigh-gif-19208350")

@client.command(pass_context=True)
async def fulllogs(ctx):
    global previous_files

    # Find recent log files
    recent_logs = find_recent_large_logs(log_directory)

    if len(recent_logs) < 2:
        await ctx.send("Not enough recent large log files found.")
        return

    logToParse1, logToParse2 = recent_logs[:2]

    # Construct the cURL command for TFCStats
    curl_command = [
        'curl',
        '-X', 'POST',
        '-F', f'logs[]=@{logToParse1}',
        '-F', f'logs[]=@{logToParse2}',
        'https://www.tfcstats.com/api/parsePickup'
    ]

    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
        response_data = result.stdout.strip()

        # Attempt to parse JSON
        parsed_response = json.loads(response_data)

        # Send the full JSON response (formatted)
        response_text = json.dumps(parsed_response, indent=4)  # Pretty print JSON
        if len(response_text) > 2000:  # Discord message character limit
            await ctx.send("Response too long, sending as a file.")
            with open("response.json", "w") as f:
                f.write(response_text)
            await ctx.send(file=discord.File("response.json"))
        else:
            await ctx.send(f"```json\n{response_text}\n```")

    except subprocess.CalledProcessError as e:
        await ctx.send(f"Error: {e}")
    except json.JSONDecodeError:
        await ctx.send(f"Invalid JSON response:\n{response_data}")

@client.command(pass_context=True)
async def tfcstatslogs(ctx):
    global previous_files

    await ctx.send("Fetching logs, please wait...")

    # Find recent log files
    recent_logs = find_recent_large_logs(log_directory)

    if len(recent_logs) < 2:
        await ctx.send("Not enough recent large log files found.")
        return

    logToParse1, logToParse2 = recent_logs[:2]

    # API URL
    api_url = "https://www.tfcstats.com/api/parsePickup"

    # Send logs to API
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("logs[]", open(logToParse1, "rb"))
        data.add_field("logs[]", open(logToParse2, "rb"))

        async with session.post(api_url, data=data) as response:
            if response.status != 200:
                await ctx.send(f"API Error: {response.status}")
                return

            response_data = await response.json()

    success = response_data.get("success", {})
    map_name = success.get("map", {}).get("name", "Unknown Map")
    score = success.get("score", ["?", "?"])
    match_link = success.get("path", "No link available")

    # Extracting top 3 players
    top3 = success.get("awards", {}).get("top3", [])
    medals = ["🥇", "🥈", "🥉"]
    top_players_text = " ".join(f"{medals[i]} {p['playerName']}" for i, p in enumerate(top3) if i < 3)

    # Extracting notable stats
    stats_fields = {
        "airshots": "Airshots",
        "concKills": "Conc'd Kills",
        "damage": "Damage",
        "flagCarrierKills": "Flag Carrier Kills",
        "flagTouches": "Flag Touches",
        "sgKills": "SG Kills",
        "coastToCoast": "Coast to Coast"
    }

    notable_text = "\n".join(
        f"🎖️ {stat['playerName']} | {stat['value']} {label}"
        for key, label in stats_fields.items()
        if (stat := success.get("awards", {}).get(key))
    )

    # Construct the summary message
    summary_message = f"""
**{map_name}**
🟢 {score[0]} - {score[1]} 🟣

{top_players_text}

{notable_text}
🔗 {match_link}
"""

    await ctx.send(summary_message)

@client.command(pass_context=True)
async def logs(ctx):
    global previous_files

    await ctx.send("Fetching logs, please wait...")

    # Find recent log files
    recent_logs = find_recent_large_logs(log_directory)

    if len(recent_logs) < 2:
        await ctx.send("Not enough recent large log files found.")
        return

    logToParse1, logToParse2 = recent_logs[:2]

    tfcstats_api_url = "https://www.tfcstats.com/api/parsePickup"
    hampalyzer_api_url = "http://app.hampalyzer.com/api/parseGame"

    async with aiohttp.ClientSession() as session:
        # Sending logs to **Hampalyzer**
        hampalyzer_data = aiohttp.FormData()
        hampalyzer_data.add_field("force", "on")
        hampalyzer_data.add_field("logs[]", open(logToParse1, "rb"))
        hampalyzer_data.add_field("logs[]", open(logToParse2, "rb"))

        async with session.post(hampalyzer_api_url, data=hampalyzer_data) as hampalyzer_response:
            if hampalyzer_response.status == 200:
                hampalyzer_data = await hampalyzer_response.json()
                hampalyzer_url = f"http://app.hampalyzer.com{hampalyzer_data['success']['path']}" if 'success' in hampalyzer_data and 'path' in hampalyzer_data['success'] else None
            else:
                hampalyzer_url = None

        # Sending logs to **TFCStats**
        tfcstats_data = aiohttp.FormData()
        tfcstats_data.add_field("logs[]", open(logToParse1, "rb"))
        tfcstats_data.add_field("logs[]", open(logToParse2, "rb"))

        async with session.post(tfcstats_api_url, data=tfcstats_data) as response:
            if response.status != 200:
                await ctx.send(f"API Error: {response.status}")
                return

            response_data = await response.json()

    success = response_data.get("success", {})
    map_name = success.get("map", {}).get("name", "Unknown Map")
    score = success.get("score", ["?", "?"])
    match_link = success.get("path", "No link available")

    # Extracting top 3 players
    top3 = success.get("awards", {}).get("top3", [])
    medals = ["🥇", "🥈", "🥉"]
    top_players_text = " ".join(f"{medals[i]} {p['playerName']}" for i, p in enumerate(top3) if i < 3)

    # Extracting notable stats
    stats_fields = {
        "airshots": "Airshots",
        "concKills": "Conc'd Kills",
        "damage": "Damage",
        "flagCarrierKills": "Flag Carrier Kills",
        "flagTouches": "Flag Touches",
        "sgKills": "SG Kills",
        "coastToCoast": "Coast to Coast"
    }

    notable_text = "\n".join(
        f"🎖️  {stat['playerName']} | {stat['value']} {label}"
        for key, label in stats_fields.items()
        if (stat := success.get("awards", {}).get(key))
    )

    # Construct the summary message
    summary_message = f"""
**{map_name}**
🟢 {score[0]} - {score[1]} 🟣

{top_players_text}

{notable_text}

🔗 TFCStats: {match_link}
"""

    # Add Hampalyzer link if available
    if hampalyzer_url:
        summary_message += f"\n📌 Hampalyzer: {hampalyzer_url}"

    await ctx.send(summary_message)

client.run(TOKEN)
