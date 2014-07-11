import u6
from datetime import datetime
import threading
import traceback
from time import sleep
import Queue


class LabJackIO(threading.Thread):
    """
    LabJackIO establishes and communicates with LabJack in stream mode
    and puts the requests retrieved into a queue to be processed by another
    thread. 
    """
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop = threading.Event()

    def run(self):
        #Initialize device
        d = u6.U6()

        #Stream configuration inputs
        print "Configuring U6 stream..."
        NumChannels = 28
        ChannelNumbers = range(14) + range(16,30)
        ChannelOptions = [ 0 ] * 28 
        SettlingFactor = 1
        ResolutionIndex = 1
        ScanFrequency = 10
        d.streamConfig( NumChannels = NumChannels , ChannelNumbers = ChannelNumbers , ChannelOptions = ChannelOptions , SettlingFactor = SettlingFactor , ResolutionIndex = ResolutionIndex, ScanFrequency = ScanFrequency )
    
        #Start stream and take data from USB --> Queue
        try:
            print "Starting stream..."
            d.streamStart()
            begin = datetime.now()
            print "Test Start %s" %(begin)

            #Initialize streaming variables needed to keep track
            missedSamples = 0
            requestCount = 0
            packetCount = 0

            for r in d.streamData():
                if self.stop.is_set():
                    break

                if r is not None:
                    if r['errors'] != 0:
                        print "Error: %s ; " % r['errors'], datetime.now()

                    if r['numPackets'] != d.packetsPerRequest:
                        print "----- UNDERFLOW : %s : " % r['numPackets'], datetime.now()

                    if r['missed'] != 0:
                        missedSamples += r['missed']
                        print "+++ Missed ", r['missed']

                    #Put the request into the queue to be accessed for use by another thread. 
                    global q
                    q.put(r)

                    requestCount += 1
                    packetCount += r['numPackets']    
                else:
                    # If no data is recieved. Occurs when stream period is
                    # greater than USB read timeout (~1 second)
                    print "No data", datetime.now()
        except:
            print "".join(i for i in traceback.format_exc())
        
        #End Stream by stop condition or error
        end = datetime.now()
        d.streamStop()
        print "Ending stream..."
        d.close()
        print "Device connection closed..."

        sampleTotal = packetCount * d.streamSamplesPerPacket
        scanTotal = sampleTotal / NumChannels

        print "%s requests with %s packets per request with %s samples per packet = %s samples total." %(requestCount, float(packetCount) / requestCount, d.streamSamplesPerPacket, sampleTotal )
        print "%s samples were lost due to errors." % missedSamples
        sampleTotal -= missedSamples
        print "Adjusted number of samples = %s" % sampleTotal

        runTime = (end-begin).seconds + float((end-begin).microseconds)/1000000
        print "The experiment took %s seconds." % runTime
        print "Scan Rate : %s scans / %s seconds = %s Hz" % ( scanTotal, runTime, float(scanTotal)/runTime )
        print "Sample Rate : %s samples / %s seconds = %s Hz" % ( sampleTotal, runTime, float(sampleTotal)/runTime )

class ConvertLogGraph(threading.Thread):
    """
    ConvertLogGraph takes the request data from the queue and processes,
    converts, logs, and graphs the data. 
    """
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop = threading.Event()

    def run(self):
        global q

        while not self.stop.is_set():
            try:
                r = q.get(False)
            except Queue.Empty:
                continue

            with open('myfile.txt','a') as f:
                f.write('%s \n' %(r))

            q.task_done()

def main():
    #Set up queue to be shared between threads
    global q
    q = Queue.Queue()

    #Start LabJackIO Thread
    LabJackIOThread = LabJackIO()
    LabJackIOThread.setDaemon(True)
    LabJackIOThread.start()
    
    #Start ConvertLogGraph Thread
    ConvertLogGraphThread = ConvertLogGraph()
    ConvertLogGraphThread.setDaemon(True)
    ConvertLogGraphThread.start()

    sleep(1) # wait for threads to start up
    # User input to set stop condition to stop streaming
    while True:
        user_stop_keyinput = raw_input("To stop streaming, type in 'endstream': ")
        if user_stop_keyinput == 'endstream':
            LabJackIOThread.stop.set()
            LabJackIOThread.join()
            q.join() #Wait till all the remaining requests are processed
            ConvertLogGraphThread.stop.set()
            ConvertLogGraphThread.join()
            break

if __name__ == '__main__':
    main()