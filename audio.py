import sys
import json
#from datetime import datetime

from ctypes import Structure, windll, c_uint, sizeof, byref

class LASTINPUTINFO(Structure):
    _fields_ = [
        ('cbSize', c_uint),
        ('dwTime', c_uint),
    ]

def get_idle_duration():
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = sizeof(lastInputInfo)
    windll.user32.GetLastInputInfo(byref(lastInputInfo))
    millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
    return millis / 1000.0

if not sys.platform.startswith("linux"):
    from pycaw.pycaw import AudioUtilities
else:
    import pulsectl

import paho.mqtt.client as mqtt
from multiprocessing import Process
import time

ignoreList = ["Battle.net.exe", "AudioRelay.exe", "Steam.exe", "RAVCpl64.exe", "ShellExperienceHost.exe",
              "cef_browser_process.exe",
              "taskhostw.exe", "AMDRSServ.exe", "RadeonSoftware.exe", "explorer.exe", "Telegram.exe",
              "PeopleApp.exe", "steamwebhelper.exe", "obs64.exe", "steam.exe"]
lastPublishedState = False;
idleTimeLimit = 120
count = 0

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
    disconnected = True
    while disconnected:
        try:
            client.reconnect()
            disconnected = False
            publish_last_state()
        except:
            print("Reconnect failed")
            time.sleep(5)

def publish_last_state():
    if lastPublishedState:
        client.publish("pc/active", "ON")
    else:
        client.publish("pc/active", "OFF")

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
        if msg.topic[0:2] == "pc":
            try:
                message = str(msg.payload)[3:]
                message = message[:-1]
                if msg.topic == "pc/audio/set/1":
                    setVolumeProcess(sessions[0].Process.name(), float(message))
                elif msg.topic == "pc/audio/set/2":
                    setVolumeProcess(sessions[1].Process.name(), float(message))
                elif msg.topic == "pc/audio/set/3":
                    setVolumeProcess(sessions[2].Process.name(), float(message))
            except:
                print("Not found")


client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.username_pw_set("username", password="")
client.will_set("topic", "OFF", qos=0, retain=False)
client.connect_async("", 1883, 60)


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


if __name__ == "__main__":
    client.loop_start()
    time.sleep(2)
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

    while True:
        publishProcess()
        print(get_idle_duration())
        if (get_idle_duration() > idleTimeLimit):
            if lastPublishedState:
                client.publish("pc/active", "OFF")
                lastPublishedState = False
        else:
            if not lastPublishedState:
                client.publish("pc/active", "ON")
                lastPublishedState = True
            
        count = count + 1
        if count > 6:
            #client.publish("pc/time", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            publish_last_state()

            count = 0
        
        time.sleep(8)
    # client.loop_forever(timeout=1.0, max_packets=1, retry_first_connection=True)
