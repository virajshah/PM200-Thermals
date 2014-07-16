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
"""

class Measurement():
    """
    Object to contain information of one measurement to LabJack.
    """
    def __init__(self, channelNum, resolutionIndex, gainIndex, settlingFactor, differential, thermocouple):
        self.channelNum = channelNum
        self.resolutionIndex = resolutionIndex
        self.gainIndex = gainIndex
        self.settlingFactor = settlingFactor
        self.differential = differential
        self.thermocouple = thermocouple

        self.getParams = {"channel": self.channelNum,
                            "resolution": self.resolutionIndex,
                            "gain": self.gainIndex,
                            "settlingFactor": self.settlingFactor,
                            "differential": self.differential}
    
    def GET(self, string):
        """Access variables in getParams hash."""
        return self.getParams[string]

    def isThermocouple(self):
        return self.thermocouple


class LabJackIO(threading.Thread):
    """
    LabJackIO establishes and communicates with LabJack in stream mode
    and puts the requests retrieved into a queue to be processed by another
    thread. 
    """
    def __init__(self, listOfMeasurements, scanFrequency):
        threading.Thread.__init__(self)
        self.stop = threading.Event()

        self.listOfMeasurements = listOfMeasurements
        self.scanFrequency = scanFrequency

    def run(self):
        #Initialize device
        d = u6.U6()

        numOfMeasurements = len(self.listOfMeasurements)
        feedbackArguments = [0]*numOfMeasurements
        latestAinValues = [0]*numOfMeasurements

        #Create Feedback Argument List
        for i in range(numOfMeasurements):
            ithMeasurement = self.listOfMeasurements[i]
            feedbackArguments[i] = ( u6.AIN24(ithMeasurement.GET("channel"), 
                                                ithMeasurement.GET("resolution"), 
                                                ithMeasurement.GET("gain"), 
                                                ithMeasurement.GET("settlingFactor"), 
                                                ithMeasurement.GET("differential")) )

        #Break up into chunks of 10 channels per feedback command sent (can only send max of 13 at a time to USB host)
        if numOfMeasurements > 10:
            chunks = [feedbackArguments[i:i+10] for i in range(0, numOfMeasurements, 10)]
        else:
            chunks = feedbackArguments

        #Gather data and return list of readings in order of channel list
        while True:
            startTime = time()
            if self.stop.is_set():
                break
            feedbackResult = []
            for i in chunks:
                feedbackResult.extend(d.getFeedback(i))

            #Convert binary values into analog voltages
            for i in range(numOfMeasurements):
                ithMeasurement = self.listOfMeasurements[i]
                latestAinValues[i] = d.binaryToCalibratedAnalogVoltage(ithMeasurement.GET("gain"), feedbackResult[i], resolutionIndex = ithMeasurement.GET("resolution"))

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
    def __init__(self, listOfMeasurements, scanFrequency, ljCJCTempOffset, ljCJCTempSlope):
        threading.Thread.__init__(self)
        self.stop = threading.Event()

        self.listOfMeasurements = listOfMeasurements
        self.scanFrequency = scanFrequency
        
        self.ljCJCTempOffset = ljCJCTempOffset
        self.ljCJCTempSlope = ljCJCTempSlope

        self.timeCounter = 0

    def run(self):
        global q

        while not self.stop.is_set():
            try:
                latestAinValues = q.get(False)
            except Queue.Empty:
                continue

            #Convert voltage array recieved from queue to converted array
            latestConvertedValues = self.convert(latestAinValues)
            
            #Running timestamp of data based on Scan Frequency and loop iteration
            timestamp = (1.0/self.scanFrequency)*self.timeCounter 

            #Log temperature data into a CSV file
            with open('test.csv','ab') as f:
                wr = csv.writer(f)
                wr.writerow([timestamp]+latestConvertedValues)

            self.timeCounter += 1
            q.task_done()

    def convert(self, latestAinValues):
        #Set up conversion variables on first iteration for faster run time. 
        if self.timeCounter == 0:
            self.numOfMeasurements = len(self.listOfMeasurements)
            self.convertedValues = [0]*self.numOfMeasurements #initialize converted values array
            #Find the index in the measurement list of AIN14 which is oboard Tsensor for CJC
            self.cjcExists = False
            for i in range(self.numOfMeasurements):
                if self.listOfMeasurements[i].GET("channel") == 14:
                    self.ljCJCchannelListIndex = i
                    self.cjcExists = True
                    break
        
        if self.cjcExists:
            ljCJCTempK = latestAinValues[self.ljCJCchannelListIndex]*self.ljCJCTempSlope + self.ljCJCTempOffset
            ljCJCTempC = ljCJCTempK + 2.5 - 273.15 #add 2.5 since screw terminals on CB37 are 2.5C above ambient with enclosure

        #If value is a thermocouple, send to T-type library to get converted to temperature, 
        #if CJC return value calculated above otherwise leave alone. 
        for i in range(self.numOfMeasurements):
            if self.listOfMeasurements[i].isThermocouple():
                self.convertedValues[i] = tTypeThermocouple.convertVoltsToTemp(ljCJCTempC, latestAinValues[i])
            elif i == self.ljCJCchannelListIndex:
                self.convertedValues[i] = ljCJCTempC
            else: 
                self.convertedValues[i] = latestAinValues[i]
        
        return self.convertedValues


def main():
    """==========User Input Begin=========="""
    #Define acquisition parameters
    channelList = range(30)
    resolutionIndexList = [1]*30
    gainIndexList = [2]*30; gainIndexList[14] = 0
    settlingFactor = 0
    differentialList = [False]*30
    thermocoupleList = [True]*30; thermocoupleList[14]=False
    
    scanFrequency = 10

    #Find calibration constants for LJ, will be used for CJC temperature calculation
    ljCJCTempOffset = 465.12900000000002 #d.calInfo.temperatureOffset
    ljCJCTempSlope = -92.379000000000005 #d.calInfo.temperatureSlope
    """==========User Input End=========="""

    assert len(channelList) == len(resolutionIndexList) == len(gainIndexList) == len(differentialList) == len(thermocoupleList), "Length of input lists are not all the same."

    #Build up list of measurements to be passed to worker threads.
    listOfMeasurements = [0]*len(channelList)
    for i in range(len(channelList)):
        listOfMeasurements[i] = Measurement(channelNum = channelList[i], 
                                            resolutionIndex = resolutionIndexList[i], 
                                            gainIndex = gainIndexList[i], 
                                            settlingFactor = settlingFactor, 
                                            differential = differentialList[i], 
                                            thermocouple = thermocoupleList[i])

    #Set up queue to be shared between threads
    global q
    q = Queue.Queue()

    #Start LabJackIO Thread
    LabJackIOThread = LabJackIO(listOfMeasurements, scanFrequency)
    LabJackIOThread.setDaemon(True)
    LabJackIOThread.start()
    
    #Start ConvertLogGraph Thread
    ConvertLogGraphThread = ConvertLogGraph(listOfMeasurements, scanFrequency, ljCJCTempOffset, ljCJCTempSlope)
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