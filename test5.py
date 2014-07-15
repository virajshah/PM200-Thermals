import u6
import time
d = u6.U6()

start = time.time()
d.configIO( NumberTimersEnabled = 1 )
d.configTimerClock( TimerClockBase = 2) #48 MHz
d.getFeedback( u6.Timer0Config(TimerMode = 2, Value = 0) ) #Set the Timer mode to 2. 32-bit rising edge Timer. 
while True:
	d.setDOState(1, state = 1)
	timerFeedbackArg = u6.Timer(timer = 0, UpdateReset = True, Value = 0, Mode = 2)
	print d.getFeedback(timerFeedbackArg)
	print time.time() - start
	d.setDOState(1, state = 0)
	time.sleep(0.5)