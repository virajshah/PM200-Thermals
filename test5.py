import u6
import time
d = u6.U6()

start = time.time()
d.configIO( NumberTimersEnabled = 1 )
d.configTimerClock( TimerClockBase = 1, TimerClockDivisor = 255) #Clock freq 1 Mhz/ 256 ~ 4 kHz
d.getFeedback( u6.Timer0Config(TimerMode = 2, Value = 0) )
while True:
	d.setDOState(1, state = 1)
	timerFeedbackArg = u6.Timer(timer = 0, UpdateReset = True, Value = 0, Mode = 2)
	print d.getFeedback(timerFeedbackArg)
	print time.time() - start
	d.setDOState(1, state = 0)
	time.sleep(0.5)