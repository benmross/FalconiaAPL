import logging
from time import strftime, localtime, time
logname = 'logs/{}.txt'.format(strftime("%d-%b-%Y_%H:%M:%S", localtime(time())))
logging.basicConfig(filename=logname,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

def log(data):
	logging.info(data)
