import u3, u6, ue9
from time import sleep
from datetime import datetime
import struct
import traceback

# MAX_REQUESTS is the number of packets to be read.
MAX_REQUESTS = 75


## At high frequencies ( >5 kHz), the number of samples will be MAX_REQUESTS times 48 (packets per request) times 25 (samples per packet).
d = u6.U6()

## For applying the proper calibration to readings.
#d.getCalibrationData()

print "configuring U6 stream"

d.streamConfig( NumChannels = 2, ChannelNumbers = [ 0, 1 ], ChannelOptions = [ 0, 0 ], SettlingFactor = 1, ResolutionIndex = 1, ScanFrequency = 5000 )


try:
    print "start stream",
    d.streamStart()
    start = datetime.now()
    print start
    
    missed = 0
    dataCount = 0
    packetCount = 0

    for r in d.streamData():
        if r is not None:
            # Our stop condition
            if dataCount >= MAX_REQUESTS:
                break
            
            if r['errors'] != 0:
                print "Error: %s ; " % r['errors'], datetime.now()

            if r['numPackets'] != d.packetsPerRequest:
                print "----- UNDERFLOW : %s : " % r['numPackets'], datetime.now()

            if r['missed'] != 0:
                missed += r['missed']
                print "+++ Missed ", r['missed']

            # Comment out these prints and do something with r
            print "Average of" , len(r['AIN0']), "AIN0," , len(r['AIN1']) , "AIN1 reading(s):", 
            print sum(r['AIN0'])/len(r['AIN0']) , "," , sum(r['AIN1'])/len(r['AIN1'])

            dataCount += 1
            packetCount += r['numPackets']
        else:
            # Got no data back from our read.
            # This only happens if your stream isn't faster than the 
            # the USB read timeout, ~1 sec.
            print "No data", datetime.now()
except:
    print "".join(i for i in traceback.format_exc())
finally:
    stop = datetime.now()
    d.streamStop()
    print "stream stopped."
    d.close()

    sampleTotal = packetCount * d.streamSamplesPerPacket

    scanTotal = sampleTotal / 2 #sampleTotal / NumChannels
    print "%s requests with %s packets per request with %s samples per packet = %s samples total." % ( dataCount, (float(packetCount) / dataCount), d.streamSamplesPerPacket, sampleTotal )
    print "%s samples were lost due to errors." % missed
    sampleTotal -= missed
    print "Adjusted number of samples = %s" % sampleTotal

    runTime = (stop-start).seconds + float((stop-start).microseconds)/1000000
    print "The experiment took %s seconds." % runTime
    print "Scan Rate : %s scans / %s seconds = %s Hz" % ( scanTotal, runTime, float(scanTotal)/runTime )
    print "Sample Rate : %s samples / %s seconds = %s Hz" % ( sampleTotal, runTime, float(sampleTotal)/runTime )
