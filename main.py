# import peripherals.lcd as LCDI2C //import vecchio
import peripherals.lcdi2c as LCDI2C
import peripherals.mfrc522 as MFRC522
import gpio
import i2c
from networking import wifi
import credentials
from zdm import zdm
from stdlib import csv
#--------Inizializzazione Variabili globali--------------#
green_led = D21
red_led = D18
rfid_rst = D27
rfid_cs = D15
buzzer = D22
#-------------JOB PER AGGIUNGERE UN NUOVO DIPENDENTE--------------#
def addUser(agent,args):
    global rows
    uid = args['uid']
    nome = args['nome']
    cognome = args['cognome']
    # with open("./resources/dipendenti.csv","a",newline="") as fobject:
    #     writerobject = writer(fobject)
    #     writerobject.writerow(uid,nome,cognome)
    #     rows[uid] = [nome,cognome]  
    #     print(uid + "Aggiunto: ",nome + cognome)
    #     lcd.putstr("Benvenuto ", nome)
    #     fobject.close()
#-------------------JOB PER STOPPARE IL SISTEMA--------------------#
def control(agent, args):
    global stopSystem
    command = args["control"]
    print(command)
    if command == "stop":
        stopSystem = True
        lcd.putstr("STOP SISTEMA")
        sleep(2000)
        lcd.putstr("Attendo il\nRiavvio")
    elif command == "restart":
        lcd.putstr("Riavvio Sistema")
        sleep(2000)
        stopSystem = False
        lcd.putstr("Counter:%d" % (count))
    else:
        lcd.putstr("Parametro passato dal JOB errato")
        
#------------Funzioni-------------#

def cardRecognize(id):
    global count
    count += 1
    agent.publish(payload={"uid": id}, tag="uid")
    lcd.putstr("Accesso\nConsentito")
    gpio.high(green_led)
    print(id)
    gpio.low(green_led)
    sleep(2000)
    lcd.clear()
    return count


def cardNotRecognize(id):
    lcd.putstr("Accesso\nNon Consentito")
    gpio.high(red_led)
    gpio.high(buzzer)
    sleep(1500)
    gpio.low(buzzer)
    gpio.low(red_led)


def start(lcd):
    global count,stopSystem,rows
    lcd.putstr("Counter:%d" % (count))
    while True:
        if stopSystem == False:
            (stat, tag_type) = rdr.request(rdr.REQIDL)
            if stat == rdr.OK:
                (stat, raw_uid) = rdr.anticoll()
                if stat == rdr.OK:
                    card_id = "0x%02x%02x%02x%02x" % (
                        raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3])
                    if card_id == "0x9987afb1": # if card_id in rows: GESTIONE ENTRATA E USCITA
                        count = cardRecognize(card_id)
                    else:
                        cardNotRecognize(card_id)
                    lcd.putstr("Counter:%d" % (count))
                    sleep(3000)
        else:
            sleep(2000)


#----------Inizializzazione Digital Sensor---------------------------#
gpio.mode(green_led, OUTPUT)
gpio.mode(red_led, OUTPUT)
gpio.mode(buzzer, OUTPUT)
#----------Inizializzazione schermo LCD i2C----------------#
lcd = None
i2cObj = None
i2cObj = i2c.I2c(0x27, clock=400000)
lcd = LCDI2C.I2cLcd(i2cObj, 2, 16)
#----------Inizializzazione RFID SPI-----------------------#
###############################################
#               3.3 -> 3.3                    #
#               GNG -> GNG                    #
#               SDA -> D15                    #
#               SCK -> D14                    #
#               Mosi -> D13                   #
#               Miso -> D12                   #
###############################################
rdr = MFRC522.MFRC522(D27, D15)               
#-------------Configurazione Wifi-------------#
try:
    lcd.putstr("Configurazione\nWifi...")
    wifi.configure(ssid=credentials.SSID, password=credentials.PASSWORD)
    wifi.start()
    sleep(7000)
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
agent = zdm.Agent(jobs={"control": control})
agent.start()
#--------------Apertura file csv con Lettura UID----------------------#

#-------------avvio thread-------------#
count = 0
stopSystem = False
lcd.putstr("Counter:%d" % (count))
#thread(target=start(lcd))
# header = next(file) #Ci sarà l'header del file csv
# rows = {}
# for row in csvreader:
#     uid = row[0]
#     nome = row[1]
#     cognome = row[2]
#     rows[uid] = [nome,cognome]
# file.close()
