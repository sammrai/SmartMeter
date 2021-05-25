from m5stack import lcd

class logging():
    def __init__(self,logger_name=None,lcd=False):
        if logger_name==None:
            self.logger_name=""
        self.logger_name=logger_name
        self.lcd=lcd
        self.counter=0
        pass
    def setLevel(self,level):
        pass
    def emit(self,message,*val):
        if val:
            message = (message%val)
        else:
            message = (message)
        
        if self.lcd:
            lcd.print(message, 0, self.counter*5, lcd.WHITE)
            self.counter+=1
        print(self.logger_name+": "+message)

    def info(self,message,*val):
        self.emit(message,*val)
    def warn(self,message,*val):
        self.emit(message,*val)
    def error(self,message,*val):
        self.emit(message,*val)
    def debug(self,message,*val):
        self.emit(message,*val)

def getLogger(name):
    return logging(name)

DEBUG=None
INFO=None
WARN=None
ERROR=None