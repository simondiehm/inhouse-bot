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
    # Get list of files in the log directory
    log_files = [os.path.join(log_directory, file) for file in os.listdir(log_directory) if file.endswith('.log')]

    # Filter files by size
    log_files = [file for file in log_files if os.path.getsize(file) > min_size_kb * 1024]

    # Sort files by modification time (most recent first)
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    # Take the most recent 'num_logs' files
    recent_logs = log_files[:num_logs]

    return recent_logs

@client.command(pass_context=True)
async def logs(ctx):
    global previous_files

    # Assuming you have the function to find recent logs
    recent_logs = find_recent_large_logs(log_directory)

    # Update previous_files with current_files
    current_files = set(os.listdir(log_directory))
    previous_files = current_files

    if len(recent_logs) >= 2:
        logToParse1 = recent_logs[0]
        logToParse2 = recent_logs[1]

        # Construct the cURL command
        curl_command = [
            'curl',
            '-X', 'POST',
            '-F', 'force=on',
            '-F', f'logs[]=@{logToParse1}',
            '-F', f'logs[]=@{logToParse2}',
            'http://app.hampalyzer.com/api/parseGame'
        ]

        try:
            result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
            response_data = result.stdout.strip()
            parsed_response = json.loads(response_data)

            if 'success' in parsed_response and 'path' in parsed_response['success']:
                path = parsed_response['success']['path']
                url = f"http://app.hampalyzer.com{path}"

                # Send the parsed log URL in Discord
                await ctx.send(f"Parsed Log URL: {url}")
            else:
                await ctx.send("Unexpected response format from the parsing API.")
        
        except subprocess.CalledProcessError as e:
            await ctx.send(f"Error: {e}")
    else:
        await ctx.send("Not enough recent large log files found.")

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
