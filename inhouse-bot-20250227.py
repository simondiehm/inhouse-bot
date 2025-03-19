#!/usr/bin/python3

import asyncio
#import datetime
import discord
import json
import os
#import random
#import re
#import socket
#import urllib.request
#import requests
import subprocess
#new
#from bs4 import BeautifulSoup

from collections import deque
#from dotenv import load_dotenv
from discord.ext import commands
from discord.ext import tasks

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix = ["!", "+", "-"], help_command=None, case_insensitive=True, intents=intents)

#load_dotenv()
DISCORD_TOKEN="removed"
TOKEN = DISCORD_TOKEN
TOKEN = os.getenv('DISCORD_TOKEN')
#CHANNEL_NAME = os.getenv('DISCORD_CHANNEL')
CHANNEL_NAME = "general" 
SERVER_IP = os.getenv('SERVER_IP')
SERVER_PORT = os.getenv('SERVER_PORT') # port to communicate with server plugin
SERVER_PASSWORD = os.getenv('SERVER_PASSWORD')
CLIENT_PORT = os.getenv('CLIENT_PORT') # port to communicate with client plugin listener (serverComms.py)

log_directory = "/home/steam/Steam/steamapps/common/Half-Life/tfc/logs/"
previous_files = set()

def find_recent_large_logs(log_directory, num_logs=2, min_size_kb=50):
    log_files = [os.path.join(log_directory, file) for file in os.listdir(log_directory) if file.endswith('.log')]
    log_files = [file for file in log_files if os.path.getsize(file) > min_size_kb * 1024]
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return log_files[:num_logs]

@client.command(pass_context=True)
async def logs(ctx):
    global previous_files

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
    await ctx.send("!entomb")

@client.command(pass_context=True)
async def entomb(ctx):
    await ctx.send("https://youtu.be/v3VqaATiNm0?si=3vdafgy5PxVcNu6C")

@client.event
async def on_ready():
    print(f'{client.user} is aliiiiiive!')

@client.command(pass_context=True)
async def mvp(ctx):
    await ctx.send("https://tenor.com/view/mvp-montel-vontavious-porter-entrance-wwe-smack-down-gif-18167076")

@client.command(pass_context=True)
async def boysouttonight(ctx):
    await ctx.send("https://tenor.com/view/boys-outtinigh-gif-19208350")

client.run(TOKEN)
