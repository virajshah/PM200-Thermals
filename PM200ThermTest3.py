import u6
from datetime import datetime
import threading
import traceback
from time import sleep, time
import Queue
import csv
import tTypeThermocouple

"""
Notes for future improvements, things needed, etc. 
- LabJackIO and ConvertLogGraph threads have very similar structures.
Create a base class with a general constructor with variables and just 
have LabJackIO and ConvertLogGraph subclass. 
- Figure out a better way to have CJC calibratoin constants passed to
consumer thread.
- Clean up comments for each class and function so that it matches
docstring format. 
- Add in a logging feature. 
- Add in a way to change the type of thermocouple. Right now this
has T type hardcoded. 
- Create an object to contain information about a measurement instead
of have lists
"""

class LabJackIO(threading.Thread):
    """
    LabJackIO establishes and communicates with LabJack in stream mode
    and puts the requests retrieved into a queue to be processed by another
    thread. 
    """
    def __init__(self, resolutionIndexList, gainIndexList, settlingFactor, differentialList, channelList, scanFrequency):
        threading.Thread.__init__(self)
        self.stop = threading.Event()

        #Define acquisition parameters
        self.resolutionIndexList = resolutionIndexList
        self.gainIndexList = gainIndexList
        self.settlingFactor = settlingFactor
        self.differentialList = differentialList
        self.channelList = channelList
        self.scanFrequency = scanFrequency

    def run(self):
        #Initialize device
        d = u6.U6()

        feedbackArguments = [0]*len(self.channelList)
        latestAinValues = [0]*len(self.channelList)

        #Create Feedback Argument List
        for i in range(len(self.channelList)):
            feedbackArguments[i] = ( u6.AIN24(self.channelList[i], self.resolutionIndexList[i], self.gainIndexList[i], self.settlingFactor, self.differentialList[i]) )

        #Break up into chunks of 10 channels per feedback command sent if 
        if len(feedbackArguments) > 10:
            chunks = [feedbackArguments[i:i+10] for i in range(0, len(feedbackArguments), 10)]
        else:
            chunks = feedbackArguments

        #Gather data and return list of readings in order of channel list
        while True:
            startTime = time()
            if self.stop.is_set():
                break
            result = []
            for i in chunks:
                result.extend(d.getFeedback(i))

            for i in range(len(self.channelList)):
                latestAinValues[i] = d.binaryToCalibratedAnalogVoltage(self.gainIndexList[i], result[i], resolutionIndex = self.resolutionIndexList[i])

            #Put in queue for other thread to process. 
            global q
            q.put(latestAinValues)
            timeElapsed = time()-startTime
            sleep(max(0, 1.0/self.scanFrequency - timeElapsed)) #Use max to ensure it's not a negative number


class ConvertLogGraph(threading.Thread):
    """
    ConvertLogGraph takes the request data from the queue and processes,
    converts, logs, and graphs the data. 
    """
    def __init__(self, resolutionIndexList, gainIndexList, settlingFactor, differentialList, channelList, scanFrequency, ljCJCTempOffset, ljCJCTempSlope):
        threading.Thread.__init__(self)
        self.stop = threading.Event()

        #Define acquisition parameters
        self.resolutionIndexList = resolutionIndexList
        self.gainIndexList = gainIndexList
        self.settlingFactor = settlingFactor
        self.differentialList = differentialList
        self.channelList = channelList
        self.scanFrequency = scanFrequency
        
        self.ljCJCTempOffset = ljCJCTempOffset
        self.ljCJCTempSlope = ljCJCTempSlope

        self.timeCounter = 0

    def run(self):
        global q

        #Find index in channel list of AIN14 which is onboard T sensor for CJC
        ljCJCchannelListIndex = self.channelList.index(14)

        while not self.stop.is_set():
            try:
                latestAinValues = q.get(False)
            except Queue.Empty:
                continue

            #Convert voltage array recieved from queue to temperature array
            ljCJCTempK = latestAinValues[ljCJCchannelListIndex]*self.ljCJCTempSlope + self.ljCJCTempOffset
            ljCJCTempC = ljCJCTempK + 2.5 - 273.15 #add 2.5 since screw terminals on CB37 are 2.5C above ambient with enclosure
            latestAinValues[ljCJCchannelListIndex] = 0 #This is a bullshit fix that needs work.            
            latestTempValues = tTypeThermocouple.convertVoltsArrayToTempsArray(ljCJCTempC, latestAinValues)
            latestTempValues[ljCJCchannelListIndex] = ljCJCTempC #Go back and replace AIN14 with the CJC temp calcuated using slope and offset parameters above
            
            #Running timestamp of data based on Scan Frequency and loop iteration
            timestamp = (1.0/self.scanFrequency)*self.timeCounter 

            #Log temperature data into a CSV file
            with open('test.csv','ab') as f:
                wr = csv.writer(f, quoting=csv.QUOTE_ALL)
                wr.writerow([timestamp]+latestTempValues)

            self.timeCounter += 1
            q.task_done()


def main():
    """-----User Input Begin-----"""
    #Define acquisition parameters
    resolutionIndexList = [1]*30
    gainIndexList = [3]*30; gainIndexList[14] = 0
    settlingFactor = 0
    differentialList = [False]*30
    channelList = range(30)
    scanFrequency = 10

    #Find calibration constants for LJ, will be used for CJC temperature calculation
    ljCJCTempOffset = 465.12900000000002
    ljCJCTempSlope = -92.379000000000005
    """-----User Input End-----"""

    #Set up queue to be shared between threads
    global q
    q = Queue.Queue()

    #Start LabJackIO Thread
    LabJackIOThread = LabJackIO(resolutionIndexList, gainIndexList, settlingFactor, differentialList, channelList, scanFrequency)
    LabJackIOThread.setDaemon(True)
    LabJackIOThread.start()
    
    #Start ConvertLogGraph Thread
    ConvertLogGraphThread = ConvertLogGraph(resolutionIndexList, gainIndexList, settlingFactor, differentialList, channelList, scanFrequency, ljCJCTempOffset, ljCJCTempSlope)
    ConvertLogGraphThread.setDaemon(True)
    ConvertLogGraphThread.start()

    sleep(0.2) # wait for threads to start up
    # User input to set stop condition to stop streaming
    while True:
        user_stop_keyinput = raw_input("To stop streaming, type in 'endstream': ")
        if user_stop_keyinput == 'endstream':
            LabJackIOThread.stop.set()
            LabJackIOThread.join()
            print "Please wait for all processing to finish."
            q.join() #Wait till all the remaining requests are processed
            ConvertLogGraphThread.stop.set()
            ConvertLogGraphThread.join()
            print "Test is complete."
            break

if __name__ == '__main__':
    main()