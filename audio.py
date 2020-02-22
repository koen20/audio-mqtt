from pycaw.pycaw import AudioUtilities
import paho.mqtt.client as mqtt
from multiprocessing import Process
import time


def getSessions():
    sessions = AudioUtilities.GetAllSessions()
    for session1 in sessions:
        if session1.Process:
            if session1.Process.name() == "Steam.exe" or session1.Process.name() == "RAVCpl64.exe" or session1.Process.name() == "Discord.exe":
                sessions.remove(session1)
        else:
            sessions.remove(session1)

    for session1 in sessions:
        if session1.Process:
            if session1.Process.name() == "Steam.exe" or session1.Process.name() == "RAVCpl64.exe" or session1.Process.name() == "Discord.exe":
                sessions.remove(session1)
        else:
            sessions.remove(session1)

    return sessions


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("pc/audio/set/#")


def on_message(client, userdata, msg):
    sessions = getSessions()
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


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set("woonkamer-pc", password="ijflmtSktpftqwn6R7UI")
client.connect("mqtt.koenhabets.nl", 1883, 60)


def setVolumeProcess(process, vol):
    print(process, vol)
    sessions2 = AudioUtilities.GetAllSessions()
    for session2 in sessions2:
        volume = session2.SimpleAudioVolume
        if session2.Process and session2.Process.name() == process:
            volume.SetMasterVolume(vol, None)


def publishProcess():
    while True:
        processList = []
        sessions = getSessions()
        for session in sessions:
            if session.Process:
                processList.append(session.Process.name())

        publishString = ""
        for i in range(0, len(processList)):
            processName = processList[i][0:3]
            publishString = publishString + processName + "/"

        publishString = publishString[:-1]
        client.publish("pc/audio/display", publishString)

        time.sleep(10)


if __name__ == "__main__":
    sessions = getSessions()
    for session in sessions:
        if session.Process:
            print(session.Process.name())

    p1 = Process(target=publishProcess)
    p1.start()
    client.loop_forever()
