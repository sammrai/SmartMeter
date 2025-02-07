from m5stack import *
import logging
import machine
import ujson
import utime
import ntptime
import wifiCfg
import charge
from BP35A1 import BP35A1

# Global variables
level = logging.DEBUG  # Log level
bp35a1 = None  # BPA35A1 object
config = {}  # Configuration
orient = lcd.LANDSCAPE_FLIP  # Display orientation
logger = None  # Logger object
logger_name = 'SMM'  # Logger name
influxdbconfig=None
max_retries = 30  # Maximum number of times to retry

# Colormap (tab10)
colormap = (
    0x1f77b4,  # tab:blue
    0xff7f0e,  # tab:orange
    0x2ca02c,  # tab:green
    0xd62728,  # tab:red
    0x9467bd,  # tab:purple
    0x8c564b,  # tab:brown
    0xe377c2,  # tab:pink
    0x7f7f7f,  # tab:gray
    0xbcbd22,  # tab:olive
    0x17becf,  # tab:cyan
)
bgcolor = 0x000000  # Background color
uncolor = 0xa9a9a9  # Unit color
color1 = colormap[0]  # Current value color
color2 = colormap[1]  # Total value color


def buttonA():
    """
    Aボタン：画面の上下反転
    """
    global orient
    if orient == lcd.LANDSCAPE:
        orient = lcd.LANDSCAPE_FLIP
    else:
        orient = lcd.LANDSCAPE
    logger.info('Set screen orient: %s', orient)
    lcd.orient(orient)
    lcd.clear()


def checkWiFi():
    """
    WiFi接続チェック
    """
    if not wifiCfg.isconnected():
        logger.warn('Reconnect to WiFi')
        if not wifiCfg.reconnect():
            machine.reset()


def status(message):
    """
    ステータスの表示
    """
    (x, y, w, h) = (3, 34, 154, 14)
    lcd.rect(x, y, w, h, bgcolor, bgcolor)

    logger.info(message)
    lcd.font(lcd.FONT_DefaultSmall)
    lcd.print(message, lcd.CENTER, lcd.CENTER, uncolor)


def progress(percent):
    """
    プログレスバーの表示
    """
    (w, h) = lcd.screensize()
    x = (w - 6) * percent // 100
    lcd.rect(3, h - 12, x, 12, bgcolor, color1)
    lcd.rect(3 + x, h - 12, w - 6, 12, bgcolor, bgcolor)
    lcd.font(lcd.FONT_DefaultSmall, transparent=True)
    lcd.text(lcd.CENTER, h - 10, '{}%'.format(percent), uncolor)


def instantaneous_amperage(amperage):
    """
    瞬時電流計測値の表示
    """
    (x, y, w, h) = (3, 3, 70, 25)
    lcd.rect(x, y, w, h, bgcolor, bgcolor)

    amperage = str(int(amperage))
    lcd.font(lcd.FONT_DejaVu24)
    lcd.print(amperage, x + 34 - lcd.textWidth(amperage), y, color1)
    lcd.font(lcd.FONT_DefaultSmall)
    lcd.print('A', lcd.LASTX, y + (25 - 10), uncolor)

    contract_amperage = str(int(config['contract_amperage']))
    lcd.font(lcd.FONT_Ubuntu)
    lcd.print(contract_amperage, x + 44, y + (25 - 16), uncolor)
    lcd.font(lcd.FONT_DefaultSmall)
    lcd.print('A', lcd.LASTX, y + (25 - 16) + (16 - 10), uncolor)


def instantaneous_power(power_kw):
    """
    瞬時電力計測値の表示
    """
    (x, y, w, h) = (73, 3, 84, 25)
    lcd.rect(x, y, w, h, bgcolor, bgcolor)

    power_kw = str(int(power_kw))
    lcd.font(lcd.FONT_DejaVu24)
    lcd.print(power_kw, x + w - 15 - lcd.textWidth(power_kw), y, color1)
    lcd.font(lcd.FONT_DefaultSmall)
    lcd.print('kW', lcd.LASTX, y + (25 - 10), uncolor)


def collect_range(collect, update):
    """
    今月（検針日を起点）の日付範囲を表示
    """
    (x, y, w, h) = (3, 33, 177, 12)
    lcd.rect(x, y, w, h, bgcolor, bgcolor)

    s = '{}~{}'.format(collect[5:10], update[5:10])
    lcd.font(lcd.FONT_DefaultSmall)
    lcd.print(s, int(x + (w - lcd.textWidth(s)) / 2), y, color2)


def monthly_power(power_kwh):
    """
    今月（検針日を起点）の電力量の表示
    """
    (x, y, w, h) = (3, 45, 70, 35)
    lcd.rect(x, y, w, h, bgcolor, bgcolor)

    power_kwh = str(int(power_kwh))
    lcd.font(lcd.FONT_DejaVu24)
    lcd.print(power_kwh, x + w - lcd.textWidth(power_kwh), y, color2)
    lcd.font(lcd.FONT_DefaultSmall)
    lcd.print('kWh', x + w - lcd.textWidth('kWh'), y + 25, uncolor)


def monthly_fee(fee):
    """
    今月（検針日を起点）の電気料金の表示
    """
    (x, y, w, h) = (73, 45, 84, 35)
    lcd.rect(x, y, w, h, bgcolor, bgcolor)

    fee = str(int(fee))
    lcd.font(lcd.FONT_DejaVu24)
    lcd.print(fee, x + w - lcd.textWidth(fee), y, colormap[1])
    lcd.font(lcd.FONT_DefaultSmall)
    lcd.print('Yen', x + w - lcd.textWidth('Yen'), y + 25, uncolor)

if __name__ == '__main__':
    try:
        # Initialize logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

        # Initialize lcd
        lcd.orient(orient)
        lcd.clear()

        # Start button thread
        btnA.wasPressed(buttonA)

        # Connecting Wi-Fi
        status('Connecting Wi-Fi')
        wifiCfg.autoConnect(lcdShow=False)
        if not wifiCfg.is_connected():
            raise Exception('Can not connect to WiFi.')

        # Start checking the WiFi connection
        machine.Timer(0).init(period=60 * 1000,
                              mode=machine.Timer.PERIODIC,
                              callback=checkWiFi)

        # Set Time
        status('Set Time')
        ntp = ntptime.client(host='jp.pool.ntp.org', timezone=9)

        # Load configuration
        status('Load configuration')
        config_file = '/flash/SmartMeter.json'
        with open(config_file) as f:
            config = ujson.load(f)

        # Create objects
        status('Create objects')
        bp35a1 = BP35A1(config['id'],
                        config['password'],
                        config['contract_amperage'],
                        config['collect_date'],
                        progress_func=progress,
                        logger_name=logger_name)
        logger.info('BP35A1 config: (%s, %s, %s, %s)', config['id'],
                    config['password'], config['contract_amperage'],
                    config['collect_date'])
        charge = eval('charge.{}'.format(config['charge_func']))
        logger.info('charge function: %s', charge.__name__)

        if "influxdb" in config:
            import influxdb
            influxdbconfig=config["influxdb"]

        # Connecting to Smart Meter
        status('Connecting SmartMeter')
        (channel, pan_id, mac_addr, lqi) = bp35a1.open()
        logger.info('Connected. BP35A1 info: (%s, %s, %s, %s)', channel,
                    pan_id, mac_addr, lqi)

        # Start monitoring
        status('Start monitoring')
        amperage = power_kw = power_kwh = amount = total_power_kwh = 0
        update = collect = 'YYYY-MM-DD hh:mm:ss'
        retries = 0
        t = 0
        while retries < max_retries:
            # Updated every 10 seconds
            if t % 10 == 0:
                try:
                    (_, amperage) = bp35a1.instantaneous_amperage()
                    (update, power_kw) = bp35a1.instantaneous_power()
                    instantaneous_amperage(amperage)
                    instantaneous_power(power_kw)
                    retries = 0
                except Exception as e:
                    logger.error(str(e))
                    retries += 1

            # Updated every 60 seconds
            if t % 60 == 0:
                try:
                    (collect, power_kwh) = bp35a1.monthly_power()
                    (_, total_power_kwh) = bp35a1.total_power()
                    amount = charge(config['contract_amperage'], power_kwh)
                    collect_range(collect, update)
                    monthly_power(power_kwh)
                    monthly_fee(amount)
                    retries = 0
                except Exception as e:
                    logger.error(str(e))
                    retries += 1

            # Send every 30 seconds
            if t % 30 == 0:
                try:
                    if influxdbconfig:
                        c=influxdb.InfluxDBClient(**influxdbconfig)
                        m = {
                            "amperage": amperage,
                            "power_kw": power_kw,
                            "power_kwh": power_kwh,
                            "amount": amount,
                            "total_power_kwh" : total_power_kwh
                        }
                        logger.info(str(m))
                        result=c.write(point="smartmeter",measurement=m,tag={"host":"home"})

                        if int(result.status_code) not in [200, 204]:
                            raise Exception(
                                'influxdb.write() failed. status: %s',
                                result.status_code)
                        retries = 0
                except Exception as e:
                    logger.error(str(e))
                    retries += 1

            # Ping every 1 hour
            if t % 3600 == 0:
                bp35a1.skPing()

            utime.sleep(1)
            t = utime.time()

    finally:
        machine.reset()
