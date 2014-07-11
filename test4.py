from time import time, sleep
import u6
import Queue

d = u6.U6()
q = Queue.Queue()

#Define acquisition parameters
resolutionIndex = 2
gainIndex = 0
settlingFactor = 0
differential = False
channelList = range(30)

feedbackArguments = [0]*len(channelList)
latestAinValues = [0]*len(channelList)

#Create Feedback Argument List
for i in range(len(channelList)):
    feedbackArguments[i] = ( u6.AIN24(channelList[i], resolutionIndex, gainIndex, settlingFactor, differential) )

#Break up into chunks of 10 channels per feedback command sent
chunks = [feedbackArguments[i:i+10] for i in range(0, len(feedbackArguments), 10)]

#Gather data and return list of readings in order of channel list
time1 = time()
for k in range(1000):
    startTime = time()
    result = []
    for i in chunks:
        result.extend(d.getFeedback(i))
    """
    for i in range(len(channelList)):
        latestAinValues[i] = d.binaryToCalibratedAnalogVoltage(gainIndex, result[i], resolutionIndex = resolutionIndex)
    """
    #Put in queue for other thread to process. 
    q.put(latestAinValues)
    endTime = time() - startTime
    sleep(0.1-endTime)
time2 = time()
print time2-time1
print q.qsize()
