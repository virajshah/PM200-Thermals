import u6
from datetime import datetime
import traceback
import threading
from time import sleep

#Initialize device
d = u6.U6()

#Stream configuration inputs
print "Configuring U6 stream..."
NumChannels = 10
ChannelNumbers = range(10)
ChannelOptions = [ 0 ] * 10 
SettlingFactor = 1
ResolutionIndex = 1
ScanFrequency = 15
d.streamConfig( NumChannels = NumChannels , ChannelNumbers = ChannelNumbers , ChannelOptions = ChannelOptions , SettlingFactor = SettlingFactor , ResolutionIndex = ResolutionIndex, ScanFrequency = ScanFrequency )

#Get threads up and running
class RawDataThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop = threading.Event()

    def run(self):
        while not self.stop.isSet():
            #Do computation
            pass

try:
    print "Starting stream..."
    d.streamStart()
    start = datetime.now()
    print "Test Start %s" %(start)

    #Initialize streaming variables needed to keep track
    missedSamples = 0
    requestCount = 0
    packetCount = 0

    for r in d.streamData():
        if r is not None:

            if r['errors'] != 0:
                print "Error: %s ; " % r['errors'], datetime.now()

            if r['numPackets'] != d.packetsPerRequest:
                print "----- UNDERFLOW : %s : " % r['numPackets'], datetime.now()

            if r['missed'] != 0:
                missedSamples += r['missed']
                print "+++ Missed ", r['missed']

            #Do some stuff with r such as export to file and eventually graph
            f = open('myfile.txt','a')
            f.write('%s \n' %(r))
            f.close()

            requestCount += 1
            packetCount += r['numPackets']

        else:
            # If no data is recieved. Occurs when stream period is
            # greater than USB read timeout (~1 second)
            print "No data", datetime.now()
except:
    print "".join(i for i in traceback.format_exc())
finally:
    stop = datetime.now()
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

    runTime = (stop-start).seconds + float((stop-start).microseconds)/1000000
    print "The experiment took %s seconds." % runTime
    print "Scan Rate : %s scans / %s seconds = %s Hz" % ( scanTotal, runTime, float(scanTotal)/runTime )
    print "Sample Rate : %s samples / %s seconds = %s Hz" % ( sampleTotal, runTime, float(sampleTotal)/runTime )