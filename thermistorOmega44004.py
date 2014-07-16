#Temperature calculation based on voltage measurement form DAQ. 
#Using datasheet: http://www.omega.com/Temperature/pdf/44000_THERMIS_ELEMENTS.pdf
#This is using a pullup resistor.

from math import log #imports natural log (a.k.a. ln)

def voltsToTemp(measuredV, supplyV, pullupR):
	#Steinhart-Hart Equation coefficients
	A = 1.468E-3
	B = 2.383E-4
	C = 1.007E-7

	thermistorR = pullupR/((float(supplyV)/measuredV) - 1) #Voltage divider formula

	inverseT = A + B*log(thermistorR) + C*(log(thermistorR)**3)

	return 1/inverseT