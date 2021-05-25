import urequests

class InfluxDBClient():
    def __init__(self,url, token, org, bucket):
        self.url=url
        self.token=token
        self.org=org
        self.params={"bucket":bucket ,"org":org}
        self.headers={"Authorization":"Token {}".format(token)}
        self.conveq=lambda x: ["{}={}".format(k,v) for k,v in x.items()]
    
    def write(self,point,measurement,tag=None):
        if not tag: tag = {}
        data=[str(point)]+self.conveq(tag)
        data=",".join(data)
        
        data=data+" "+",".join(self.conveq(measurement))
        params="&".join(self.conveq(self.params))
        response = urequests.post(
            self.url+'/api/v2/write?'+params,data=data,
            headers=self.headers)
        return response
