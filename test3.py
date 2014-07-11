"""import threading
from time import sleep

class myTimer(threading.Timer):
	def __init__(self):
        threading.Timer.__init__(self)
        self.stop = threading.Event()
    def run(self):
    	print 
    	t = myTimer()
    	t.setDaemon(True)
    	t.start()

def printit():
  threading.Timer(5.0, printit).start()
  print "Hello, World!"

t = myTimer()
t.setDaemon(True)
t.start()"""

"""import threading;

def do_every (interval, worker_func):
    threading.Timer(interval, do_every).start();
    worker_func();

def print_hw():
  print "hello world";

# call print_hw two times per second, forever
do_every(0.5, print_hw);"""
"""
import threading;

def work (): 		
  threading.Timer(0.25, work).start(); 
  print "stackoverflow";

work(); 
"""

import threading
import time

def func():
	global t
	t = threading.Timer(0.2, func)
	t.setDaemon(True)
	t.start()
	print "Hello World"

func()
time.sleep(1)
global t
time.sleep(1)
