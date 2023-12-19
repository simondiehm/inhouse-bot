#!/usr/bin/python3

import asyncio
import json
import os

from datetime import datetime
from dotenv import load_dotenv
from ftplib import FTP

async def start_udp_listener():
    loop = asyncio.get_event_loop()
    return await loop.create_datagram_endpoint(lambda: InhouseServerProtocol(), local_addr=('0.0.0.0', 16353))

def main_watcher():
    loop = asyncio.get_event_loop()
    coro = start_udp_listener()
    transport, _ = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
        loop.close()

def main():
    global FTP_USER
    global FTP_PASSWD
    global FTP_SERVER

    load_dotenv()
    FTP_USER = os.getenv('FTP_USER')
    FTP_PASSWD = os.getenv('FTP_PASSWD')
    FTP_SERVER = os.getenv('FTP_SERVER')

    main_watcher()

def getLastGameLogs():
    logs_directory = '/home/steam/Steam/steamapps/common/Half-Life/tfc/logs/' # Set the path to your local logs directory

    if os.path.exists('prevlog.json'):
        with open('prevlog.json', 'r') as f:
            prevlog = json.load(f)
    else:
        prevlog = []

    # Get list of log files sorted by modification time in descending order
    logFiles = sorted(
        [f for f in os.listdir(logs_directory) if f.endswith('.log')],
        key=lambda x: os.path.getmtime(os.path.join(logs_directory, x)),
        reverse=True
    )

    firstLog = None
    secondLog = None
    for logFile in logFiles:
        logFilePath = os.path.join(logs_directory, logFile)
        if 'logFiles' in prevlog and logFile in prevlog['logFiles']:
            print("already parsed the latest log")
            return

        # Check the size, should be >100kB
        if os.path.getsize(logFilePath) > 100000:
            logModified = datetime.fromtimestamp(os.path.getmtime(logFilePath))
            if firstLog is None:
                firstLog = (logFile, logModified)
                continue

            # Verify that there was another round played at least <60 minutes within the last found log
            if (firstLog[1] - logModified).total_seconds() < 3600:
                secondLog = (logFile, logModified)
            break

    # Abort if we didn't find a log
    if firstLog is None or secondLog is None:
        return

    # Assuming hampalyze API still needs the files to be sent
    hampalyze = 'curl -X POST -F logs[]=@%s -F logs[]=@%s http://app.hampalyzer.com/api/parseGame' % (os.path.join(logs_directory, secondLog[0]), os.path.join(logs_directory, firstLog[0]))
    output = os.popen(hampalyze).read()
    print(output)

    status = json.loads(output)
    if 'success' in status:
        site = "http://app.hampalyzer.com" + status['success']['path']
        print("Parsed logs available: %s" % site)

        with open('prevlog.json', 'w') as f:
            prevlog = { 'site': site, 'logFiles': [ firstLog[0], secondLog[0] ] }
            json.dump(prevlog, f)
    else:
        print('error parsing logs: %s' % output)

class InhouseServerProtocol:
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode()
        print('received %r from %s' % (message, addr))

        message_parts = message.split("@")
        if message_parts[0] != "BOT_MSG":
            return

        if message_parts[1] == "IRC":
            print("message inhouse! {}" % message)

        if message_parts[1] == "MAP":
            with open('prevmaps.json', 'r') as f:
                prevmaps = json.load(f)
                curmap = prevmaps[-1]

                self.send_message("MAP", curmap, addr)

        if message_parts[1] == "RS":
            with open('prevmaps.json', 'r') as f:
                prevmaps = json.load(f)
                curmap = prevmaps[-1]

                self.send_message("RS", curmap, addr)

        if message_parts[1] == "TEAMS":
            with open('prevteams.json', 'r') as f:
                prevteams = json.load(f)

                self.send_message("TEAMS", ', '.join(prevteams[:4]), addr)
                self.send_message("TEAMS", ', '.join(prevteams[4:]), addr)

        if message_parts[1] == "END":
            getLastGameLogs()

        if message_parts[1] == "TIMELEFT":
            with open('timeleft.json', 'w') as f:
                json.dump({ 'timeleft': message_parts[-1] }, f)


    def send_message(self, msg_type, message, addr):
        data = ("BOT_MSG@%s@%s" % (msg_type, message)).encode()
        self.transport.sendto(data, (addr[0], 16354))  # bot only listens on this port

if __name__ == "__main__":
    main()

