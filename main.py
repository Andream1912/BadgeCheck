import peripherals.lcdi2c as LCDI2C
import peripherals.rfid as RFID
import gpio
import i2c
import pwm
from networking import wifi
import credentials
from zdm import zdm
from stdlib import csv

#--------Inizializzazione Variabili--------------#
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
#-------------------JOB PER ZDM CLOUD--------------------#

# Funzione remota per resettare un badge passandogli un uid


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

# Funzione remota per assegnare un nuovo badge ad un nuovo dipendente


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
        if attempt < 1:  # Effettua 10 tentativi per l'aggiunta di un nuovo dipendente
            stopSystem = False
            lcd.putstr("Tempo Scaduto")
            lcd.clear()
            break
        else:
            attempt -= 1
            sleep(1000)

# Funzione remota per bloccare il sistema tramite lo zerynth cloud


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

#------------Funzioni-------------#

# Badge riconosciuto


def cardRecognize(diz, uid):
    global checkEntrance
    user = diz[uid]
    if uid in checkEntrance:
        checkEntrance.remove(uid)
        agent.publish(payload={
                      "uid": uid, "name": user[0], "surname": user[1], "Entrance": False}, tag="user")
        lcd.putstr("Arrivederci\n" + user[0])
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

# Badge non riconosciuto


def cardNotRecognize(id):
    lcd.putstr("Accesso\nNon Consentito")
    gpio.high(red_led)
    gpio.high(buzzer)
    sleep(1500)
    gpio.low(buzzer)
    gpio.low(red_led)
    print(id)
    lcd.clear()

# Funzione per far ruotare il servo motore di 90°


def rotate():
    global pulse
    pulse = 2500
    pwm.write(servo, period, pulse, MICROS)

# Funzione per far ruotare il servo motore di -90°


def rotateBack():
    global pulse
    pulse = 1500
    pwm.write(servo, period, pulse, MICROS)

# Funzione per far aprire il tornello senza badge


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
                    if card_id in diz:  # if card_id in rows: GESTIONE ENTRATA E USCITA
                        cardRecognize(diz, card_id)
                    else:
                        cardNotRecognize(card_id)
                    lcd.putstr("Counter:%d" % (len(checkEntrance)))
                    sleep(2000)
        else:
            print("Sistema fermo")
            sleep(2000)


#----------Inizializzazione Sensori---------------------------#
gpio.mode(green_led, OUTPUT)
gpio.mode(red_led, OUTPUT)
gpio.mode(buzzer, OUTPUT)
gpio.mode(servo, OUTPUT)
gpio.mode(button, INPUT_PULLDOWN)
gpio.on_fall(button, pressButton, pull=INPUT_PULLDOWN, debounce=1)
#----------Inizializzazione schermo LCD i2C----------------#
lcd = None
i2cObj = None
i2cObj = i2c.I2c(0x27, clock=400000)
lcd = LCDI2C.I2cLcd(i2cObj, 2, 16)
#----------Inizializzazione RFID SPI-----------------------#
###############################################
#               3.3 -> 3.3                    #
#               GND -> GND                    #
#               SDA -> D15                    #
#               SCK -> D14                    #
#               Mosi -> D13                   #
#               Miso -> D12                   #
###############################################
rdr = RFID.RFID(rfid_rst, rfid_cs)
#-------------Configurazione Wifi-------------#
try:
    lcd.putstr("Configurazione\nWifi...")
    wifi.configure(ssid=credentials.SSID, password=credentials.PASSWORD)
    wifi.start()
    sleep(3000)
    lcd.putstr("Connessione\nRiuscita")
    sleep(1000)
except WifiBadPassword:
    print("Bad Password")
    lcd.putstr("Password Wi-Fi\n Sbagliata")
except WifiBadSSID:
    print("Bad SSID")
    lcd.putstr("Non trovo il Wi-Fi")
except WifiException:
    print("Generic Wifi Exception")
    lcd.putstr("Errore Wi-Fi")
except Exception as e:
    raise e
#----------------zdm cloud-------------#
agent = zdm.Agent(
    jobs={"control": control, "addUser": addUser, "remove": removeUser})
agent.start()
#--------------Apertura file csv con Lettura UID----------------------#
file = csv.CSVReader("/zerynth/dipendenti.csv", has_header=True, quotechar="|")
for element in file:
    if element[0] != "uid":  # SALTO DELL'HEADER
        uid = "0" + element[0]
        # Inserisco nel dizionario tutti i dipendenti riconosciuti tramite uid
        diz[uid] = element[1], element[2]
file.close()
#-------------avvio thread-------------#
lcd.putstr("Counter:%d" % (len(checkEntrance)))
thread(start)
