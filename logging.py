from m5stack import lcd
import utime


def localtime():
    offset = 9 * 3600  # JST
    return utime.localtime(utime.mktime(utime.localtime()) + offset)

def strftime(tm, *, fmt='[{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}] '):
    (year, month, mday, hour, minute, second) = tm[:6]
    return fmt.format(year, month, mday, hour, minute, second)

class logging():
    def __init__(self, logger_name=None, lcd=False, file_path=None):
        self.logger_name = logger_name if logger_name is not None else ""
        self.lcd = lcd
        self.file_path = file_path
        self.counter = 0
        self.log_file = open(self.file_path, 'a') if self.file_path else None

    def setLevel(self,level):
        pass
    def emit(self,level, message,*val):
        if val:
            message = (message%val)
        else:
            message = (message)
        
        timestr = strftime(utime.localtime(utime.mktime(utime.localtime())))
        
        if self.lcd:
            lcd.print(message, 0, self.counter*5, lcd.WHITE)
            self.counter+=1
        if self.log_file:
            self.log_file.write(timestr+self.logger_name+"/"+level+": "+message + '\n')
            self.log_file.flush()

        print(timestr+self.logger_name+"/"+level+": "+message)

    def info(self,message,*val):
        self.emit("info ", message,*val)
    def warn(self,message,*val):
        self.emit("warn ", message,*val)
    def error(self,message,*val):
        self.emit("error", message,*val)
    def debug(self,message,*val):
        self.emit("debug", message,*val)

def getLogger(name, file_path='test_log.txt'):
    return logging(logger_name=name, file_path=file_path)

DEBUG=None
INFO=None
WARN=None
ERROR=None