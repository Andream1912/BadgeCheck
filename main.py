from bsp import board
import peripherals.lcdi2c as LCDI2C
import peripherals.rfid as RFID
import gpio
import i2c
import pwm
from networking import wifi
import credentials
from zdm import zdm
from stdlib import csv
from protocols import mqtt

#--------Variable Initialization--------------#
green_led = D21
red_led = D18
rfid_rst = D27
rfid_cs = D15
buzzer = D22
servo = D23
button = D19
period = 20000
checkEntrance = []
diz = {}
stopSystem = False
#--------------------------------MQTT--------------------------------#
def run():
    try:
        client.loop()
    except Exception as e:
        sleep(6000)
#callback that controls if the message received from the exit is in the dictionary and then removes it
def callback(client,topic,message):
    global checkEntrance
    user = diz[message]
    if message in checkEntrance:
        checkEntrance.remove(message)
        agent.publish(payload={
                      "uid": message, "name": user[0], "surname": user[1], "Entrance": False}, tag="user")
        lcd.putstr("Arrivederci\n" + user[0])
        sleep(2000)
        lcd.clear()
        lcd.putstr("Counter:%d" % (len(checkEntrance)))

#-------------------JOB FOR ZDM CLOUD--------------------#

#Remote function to reset a badge by passing it a uid
def removeUser(agent, args):
    global diz, checkEntrance
    uid_remove = args["uid"]
    if uid_remove in diz:
        if uid_remove in checkEntrance:
            checkEntrance.remove(uid)
        user = diz[uid_remove]
        lcd.putstr(user[0] + "\nRimosso")
        diz.pop(uid_remove)
        #file = csv.CSVWrite("/zerynth/dipendenti.csv",as_dict=True)
        #header = ["uid","name","surname"]
        # file.write_header(header)
        # file.write(diz)
        # file.close()
        sleep(3000)
        lcd.putstr("Counter:%d" % (len(checkEntrance)))

# Remote function to assign a new badge to a new employee
def addUser(agent, args):
    global stopSystem, diz
    stopSystem = True
    attempt = 10
    nome = args["name"]
    cognome = args["surname"]
    while True:
        lcd.putstr("Appoggia la\nCarta")
        (stat, tag_type) = rdr.request(rdr.REQIDL)
        if stat == rdr.OK:
            (stat, raw_uid) = rdr.anticoll()
            if stat == rdr.OK:
                card_id = "0x%02x%02x%02x%02x" % (
                    raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3])
                if card_id not in diz:
                    diz[card_id] = [nome, cognome]
                    #file = csv.CSVWrite("/zerynth/dipendenti.csv",as_dict=True)
                    #header = ["uid","name","surname"]
                    # file.write_header(header)
                    # file.write(diz)
                    # file.close()
                    lcd.putstr("Aggiunto " + nome)
                    sleep(2000)
                    stopSystem = False
                    lcd.putstr("Counter:%d" % (len(checkEntrance)))
                    break
                else:
                    lcd.putstr("Carta già registrata\nnel sistema!")
                    stopSystem = False
                    break
        if attempt < 1:  # Make 10 attempts to add a new employee
            stopSystem = False
            lcd.putstr("Tempo Scaduto")
            lcd.clear()
            break
        else:
            attempt -= 1
            sleep(1000)

# Remote function to lock the system through the zerynth cloud
def control(agent, args):
    global stopSystem, checkEntrance
    command = args["control"]
    if command == "stop":
        stopSystem = True
        lcd.putstr("STOP SISTEMA")
        sleep(2000)
        lcd.putstr("Attendo il\nRiavvio")
        checkEntrance.clear()
    elif command == "restart":
        lcd.putstr("Riavvio Sistema")
        sleep(2000)
        stopSystem = False
        lcd.putstr("Counter:%d" % (len(checkEntrance)))
    else:
        lcd.putstr("Parametro passato dal JOB errato")

#------------Function-------------#

# Badge Recognized


def cardRecognize(diz, uid):
    global checkEntrance
    user = diz[uid]
    if uid in checkEntrance:
        lcd.putstr(user[0] +" gia'\nall'interno")
        gpio.high(red_led)
        gpio.high(buzzer)
        sleep(1500)
        gpio.low(buzzer)
        gpio.low(red_led)
        lcd.clear()
    else:
        checkEntrance.append(uid)
        agent.publish(payload={
                      "uid": uid, "name": user[0], "surname": user[1], "Entrance": True}, tag="user")
        lcd.putstr("Benvenuto\n" + user[0])
        gpio.high(green_led)
        rotate()
        sleep(2500)
        rotateBack()
        sleep(1000)
        gpio.low(green_led)
        lcd.clear()
    

# Badge not Recognized
def cardNotRecognize(id):
    lcd.putstr("Accesso\nNon Consentito")
    gpio.high(red_led)
    gpio.high(buzzer)
    sleep(1500)
    gpio.low(buzzer)
    gpio.low(red_led)
    lcd.clear()
    agent.publish(payload={"warning":True},tag="warning")

# Function to rotate the servo motor 90 °
def rotate():
    global pulse
    pulse = 2500
    pwm.write(servo, period, pulse, MICROS)

# Function to rotate the servo motor -90 °
def rotateBack():
    global pulse
    pulse = 1500
    pwm.write(servo, period, pulse, MICROS)

# Function to open the turnstile without a badge
def pressButton():
    rotate()
    sleep(2500)
    rotateBack()

# Thread Main Function
def start():
    global stopSystem, checkEntrance
    lcd.putstr("Counter:%d" % (len(checkEntrance)))
    while True:
        if stopSystem == False:
            (stat, tag_type) = rdr.request(rdr.REQIDL)
            if stat == rdr.OK:
                (stat, raw_uid) = rdr.anticoll()
                if stat == rdr.OK:
                    card_id = "0x%02x%02x%02x%02x" % (
                        raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3])
                    if card_id in diz:  # if card_id in rows: ENTRY AND EXIT MANAGEMENT
                        cardRecognize(diz, card_id)
                    else:
                        cardNotRecognize(card_id)
                    lcd.putstr("Counter:%d" % (len(checkEntrance)))
                    sleep(2000)
        else:
            sleep(2000)


#----------Sensors initialization---------------------------#
gpio.mode(green_led, OUTPUT)
gpio.mode(red_led, OUTPUT)
gpio.mode(buzzer, OUTPUT)
gpio.mode(servo, OUTPUT)
gpio.mode(button, INPUT_PULLDOWN)
gpio.on_fall(button, pressButton, pull=INPUT_PULLDOWN, debounce=1)
#----------I2C LCD screen initialization----------------#
lcd = None
i2cObj = None
i2cObj = i2c.I2c(0x27, clock=400000)
lcd = LCDI2C.I2cLcd(i2cObj, 2, 16)
#----------SPI RFID initialization-----------------------#
###############################################
#               3.3 -> 3.3                    #
#               GND -> GND                    #
#               SDA -> D15                    #
#               SCK -> D14                    #
#               Mosi -> D13                   #
#               Miso -> D12                   #
###############################################
rdr = RFID.RFID(rfid_rst, rfid_cs)
#-------------Wi-fi configuration-------------#
try:
    lcd.putstr("Configurazione\nWifi...")
    wifi.configure(ssid=credentials.SSID, password=credentials.PASSWORD)
    wifi.start()
    sleep(1500)
    lcd.putstr("Connessione\nRiuscita")
    sleep(1000)
except WifiBadPassword:
    lcd.putstr("Password Wi-Fi\n Sbagliata")
except WifiBadSSID:
    lcd.putstr("Non trovo il Wi-Fi")
except WifiException:
    lcd.putstr("Errore Wi-Fi")
except Exception as e:
    raise e
#----------------Zdm Cloud-------------#
agent = zdm.Agent(
    jobs={"control": control, "addUser": addUser, "remove": removeUser})
agent.start()
#--------------Opening csv file with UID reading----------------------#
file = csv.CSVReader("/zerynth/dipendenti.csv", has_header=True, quotechar="|")
for element in file:
    if element[0] != "uid":  # SKIP HEADER
        uid = "0" + element[0]
        # I put in the dictionary all employees recognized by uid
        diz[uid] = element[1], element[2]
file.close()
#-------------Start Thread-------------#
lcd.putstr("Counter:%d" % (len(checkEntrance)))
thread(start)
#-------------Mqtt's receiving end-----------------#
try:
    client=mqtt.MQTT("test.mosquitto.org","Entrance")
    client.on("/IoT2022/SmartAcces",callback,0)
    client.connect()
    thread(run)
    while True:
        sleep(2500)
        if client.is_connected():
            break
    while True:
        sleep(5000)
except Exception as e:
    raise e
