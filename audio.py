import sys

if not sys.platform.startswith("linux"):
    from pycaw.pycaw import AudioUtilities
else:
    import pulsectl

import paho.mqtt.client as mqtt
from multiprocessing import Process
import time

ignoreList = ["Battle.net.exe", "AudioRelay.exe", "Steam.exe", "RAVCpl64.exe", "ShellExperienceHost.exe",
              "cef_browser_process.exe",
              "taskhostw.exe", "AMDRSServ.exe", "RadeonSoftware.exe", "explorer.exe", "Telegram.exe", "PeopleApp.exe"]

client = mqtt.Client()

if sys.platform.startswith("linux"):
    pulse = pulsectl.Pulse('audio')


def getSessionsWindows():
    sessionsAll = AudioUtilities.GetAllSessions()
    sessions = []
    for session1 in sessionsAll:
        if session1.Process:
            if session1.Process.name() not in ignoreList:
                exists = False
                for session2 in sessions:
                    if session2.Process.name() == session1.Process.name():
                        exists = True
                if not exists:
                    sessions.append(session1)

    return sessions


def getSessionsLinux():
    sessions = pulse.sink_input_list()
    return sessions


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("pc/audio/set/#")


def on_disconnect(client, userdate, rc):
    print("Disconnected")
    client.reconnect()


def on_message(client, userdata, msg):
    if sys.platform.startswith("linux"):
        sessions = getSessionsLinux()
        # print(msg.topic + " " + str(msg.payload))
        message = str(msg.payload)[3:]
        message = message[:-1]
        print(message)
        if msg.topic == "pc/audio/set/1":
            setVolumeProcess(sessions[0].proplist["application.name"], float(message))
        elif msg.topic == "pc/audio/set/2":
            setVolumeProcess(sessions[1].proplist["application.name"], float(message))
        elif msg.topic == "pc/audio/set/3":
            setVolumeProcess(sessions[2].proplist["application.name"], float(message))
    else:
        sessions = getSessionsWindows()
        # print(msg.topic + " " + str(msg.payload))
        message = str(msg.payload)[3:]
        message = message[:-1]
        print(message)
        if msg.topic == "pc/audio/set/1":
            setVolumeProcess(sessions[0].Process.name(), float(message))
        elif msg.topic == "pc/audio/set/2":
            setVolumeProcess(sessions[1].Process.name(), float(message))
        elif msg.topic == "pc/audio/set/3":
            setVolumeProcess(sessions[2].Process.name(), float(message))


client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.username_pw_set("woonkamer-pc", password="ijflmtSktpftqwn6R7UI")
client.will_set("pc/audio/display", "", qos=0, retain=False)
client.connect("mqtt.koenhabets.nl", 1883, 60)


def setVolumeProcess(process, vol):
    print(process, vol)
    if sys.platform.startswith("linux"):
        sessions2 = getSessionsLinux()
        for session2 in sessions2:
            if session2.proplist["application.name"] == process:
                pulse.volume_set_all_chans(session2, vol)
    else:
        sessions2 = AudioUtilities.GetAllSessions()
        for session2 in sessions2:
            volume = session2.SimpleAudioVolume
            if session2.Process and session2.Process.name() == process:
                volume.SetMasterVolume(vol, None)


def publishProcess():
    while True:
        processList = []
        if not sys.platform.startswith("linux"):
            sessions = getSessionsWindows()
            for session in sessions:
                if session.Process:
                    processList.append(session.Process.name())
        else:
            sessions = getSessionsLinux()
            for session in sessions:
                processList.append(session.proplist["application.name"])

        publishString = ""
        processCount = len(processList)
        if processCount >= 3:
            processCount = 3

        for i in range(0, processCount):
            processName = processList[i][0:3]
            publishString = publishString + processName + "/"

        publishString = publishString[:-1]
        client.publish("pc/audio/display", publishString)
        time.sleep(10)


if __name__ == "__main__":
    client.loop_start()
    if not sys.platform.startswith("linux"):
        sessions = getSessionsWindows()
        for session in sessions:
            if session.Process:
                print(session.Process.name())
    else:
        print(pulse.sink_input_list())
        sessions = pulse.sink_input_list()
        for session in sessions:
            print(session.proplist["application.name"])

    publishProcess()
    # client.loop_forever(timeout=1.0, max_packets=1, retry_first_connection=True)
