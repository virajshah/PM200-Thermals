import u6
from datetime import datetime
import threading
import traceback
from time import sleep, time
import Queue
import csv
import tTypeThermocouple
import thermistorNxpKTY84
import thermistorOmega44004

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
    def __init__(self, channelName, channelNum, resolutionIndex, gainIndex, settlingFactor, differential, thermocouple, digital):
        self.channelName = channelName
        self.channelNum = channelNum
        self.resolutionIndex = resolutionIndex
        self.gainIndex = gainIndex
        self.settlingFactor = settlingFactor
        self.differential = differential
        self.thermocouple = thermocouple
        self.digital = digital

        self.getParams = {"name": self.channelName,
                            "channel": self.channelNum,
                            "resolution": self.resolutionIndex,
                            "gain": self.gainIndex,
                            "settlingFactor": self.settlingFactor,
                            "differential": self.differential}
    
    def GET(self, string):
        """Access variables in getParams hash."""
        return self.getParams[string]

    def isThermocouple(self):
        return self.thermocouple

    def isDigital(self):
        return self.digital


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
        latestValues = [0]*numOfMeasurements

        for measurement in self.listOfMeasurements:
            if measurement.isDigital():
                d.configIO( NumberTimersEnabled = 1 )
                d.configTimerClock( TimerClockBase = 2) #48 MHz
                d.getFeedback(u6.Timer0Config(TimerMode = 2, Value = 0)) #Set the Timer mode to 2. 32-bit rising edge Timer. 

        #Create Feedback Argument List
        for i in range(numOfMeasurements):
            ithMeasurement = self.listOfMeasurements[i]
            if ithMeasurement.isDigital():
                feedbackArguments[i] = u6.Timer(timer = 0, UpdateReset = True, Value = 0, Mode = 2)
            else:    
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
                #If measurement is digital leave the value alone. If analog, convert binary to voltage. 
                if ithMeasurement.isDigital():
                    latestValues[i] = feedbackResult[i]
                else:
                    latestValues[i] = d.binaryToCalibratedAnalogVoltage(ithMeasurement.GET("gain"), feedbackResult[i], resolutionIndex = ithMeasurement.GET("resolution"))

            #Put in queue for other thread to process. 
            global q
            q.put(latestValues)
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

        #Write the header with all the measurement names at the top of the file
        channelNamesList = ["Timestamp"]
        for measurement in self.listOfMeasurements:
            channelNamesList.append(measurement.GET("name"))
        with open('test.csv','ab') as f:
                wr = csv.writer(f)
                wr.writerow(channelNamesList)

    def run(self):
        global q

        while not self.stop.is_set():
            try:
                latestValues = q.get(False)
            except Queue.Empty:
                continue

            #Convert voltage array recieved from queue to converted array
            latestConvertedValues = self.convert(latestValues)
            
            #Running timestamp of data based on Scan Frequency and loop iteration
            timestamp = (1.0/self.scanFrequency)*self.timeCounter 

            #Log temperature data into a CSV file
            with open('test.csv','ab') as f:
                wr = csv.writer(f)
                wr.writerow([timestamp]+latestConvertedValues)

            self.timeCounter += 1
            q.task_done()

    def convert(self, latestValues):
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

            self.ref_5V = 5 #Set thermistor reference voltage
        
        if self.cjcExists:
            ljCJCTempK = latestValues[self.ljCJCchannelListIndex]*self.ljCJCTempSlope + self.ljCJCTempOffset
            ljCJCTempC = ljCJCTempK + 2.5 - 273.15 #add 2.5 since screw terminals on CB37 are 2.5C above ambient with enclosure

        #If value is a thermocouple, send to T-type library to get converted to temperature, 
        #if CJC return value calculated above otherwise leave alone. 
        for i in range(self.numOfMeasurements):
            if self.listOfMeasurements[i].isThermocouple():
                #Returns T in Celsius
                self.convertedValues[i] = tTypeThermocouple.convertVoltsToTemp(ljCJCTempC, latestValues[i])
            elif i == self.ljCJCchannelListIndex:
                #Returns T in Celsius
                self.convertedValues[i] = ljCJCTempC
            elif i == 0 or i ==1:
                #Returns T in Celsius
                self.convertedValues[i] = thermistorNxpKTY84.voltsToTemp(latestValues[i], self.ref_5V, 1000) #measuredV, supplyV, pullupR
            elif i == 8 or i == 9:
                #Returns T in Celsius
                self.convertedValues[i] = thermistorOmega44004.voltsToTemp(latestValues[i], self.ref_5V, 1000) #measuredV, supplyV, pullupR
            elif i == 28:
                self.ref_5V = latestValues[i]
                self.convertedValues[i] = latestValues[i]
            elif self.listOfMeasurements[i].isDigital():
                self.convertedValues[i] = 0 if latestValues[i] == 0 else float(48e6)/latestValues[i] #returns Hz from flowmeter
            else: 
                self.convertedValues[i] = latestValues[i]
        
        return self.convertedValues


def main():
    """==========User Input Begin=========="""
    #Define acquisition parameters
    channelNameList = ["""T Motor 1""","""T Motor 2""","""T Surface 1""","""T Surface 2""","""T Surface 3""","""T Stator steel body 1""","""T Stator steel body 2""","""T Stator steel body 3""","""T coolant motor inlet""","""T coolant motor outlet""","""P coolant motor inlet""","""T coolant post U-jacket 1""","""T coolant post U-jacket 2""","""T ambient""","""T Stator copper end-turn 1""","""T Stator copper end-turn 2""","""T Stator copper end-turn 3""","""T Stator copper end-turn 4""","""T Stator copper end-turn 5""","""T Stator copper end-turn 6""","""T Stator copper mid-stack 1""","""T Stator copper mid-stack 2""","""T Stator copper mid-stack 3""","""T Stator copper mid-stack 4""","""T Stator steel weld line 1""","""T Stator steel weld line 2""","""T Stator steel weld line 3""","""Cold Junction Temp""","""5V Ref""","""Coolant flow rate"""]
    channelList = [48,120,49,50,51,52,53,54,121,122,123,55,80,81,82,83,84,85,86,87,96,97,98,99,100,101,102,14,124,None]
    resolutionIndexList = [1]*len(channelList)
    gainIndexList = [0,0,2,2,2,2,2,2,0,0,0,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,0,0,None]
    settlingFactor = 0
    differentialList = [True,False,True,True,True,True,True,True,False,False,False,True,True,True,True,True,True,True,True,True,True,True,True,True,True,True,True,False,False,False]
    thermocoupleList = [False,False,True,True,True,True,True,True,False,False,False,True,True,True,True,True,True,True,True,True,True,True,True,True,True,True,True,False,False,False]
    digitalList = [False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,True]
    scanFrequency = 10

    #Find calibration constants for LJ, will be used for CJC temperature calculation
    ljCJCTempOffset = 465.12900000000002 #d.calInfo.temperatureOffset
    ljCJCTempSlope = -92.379000000000005 #d.calInfo.temperatureSlope
    """==========User Input End=========="""

    assert len(channelNameList) == len(channelList) == len(resolutionIndexList) == len(gainIndexList) == len(differentialList) == len(thermocoupleList) == len(digitalList), "Length of input lists are not all the same."

    #Build up list of measurements to be passed to worker threads.
    listOfMeasurements = [0]*len(channelList)
    for i in range(len(channelList)):
        listOfMeasurements[i] = Measurement(channelName = channelNameList[i],
                                            channelNum = channelList[i], 
                                            resolutionIndex = resolutionIndexList[i], 
                                            gainIndex = gainIndexList[i], 
                                            settlingFactor = settlingFactor, 
                                            differential = differentialList[i], 
                                            thermocouple = thermocoupleList[i],
                                            digital = digitalList[i])

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