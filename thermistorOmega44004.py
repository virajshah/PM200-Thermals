#Temperature calculation based on voltage measurement form DAQ. 
#Using datasheet: http://www.omega.com/Temperature/pdf/44000_THERMIS_ELEMENTS.pdf
#This is using a pullup resistor.

#Returns T in Celsius.

from math import log #imports natural log (a.k.a. ln)

def voltsToTemp(measuredV, supplyV, pullupR):
	#Steinhart-Hart Equation coefficients
	A = 1.468E-3
	B = 2.383E-4
	C = 1.007E-7

	thermistorR = 0 if measuredV == 0 or supplyV == 0 else pullupR/((float(supplyV)/measuredV) - 1) #Voltage divider formula
	try:
		inverseT = A + B*log(thermistorR) + C*(log(thermistorR)**3)
	except:
		inverseT = 1

	return (float(1)/inverseT)-273.15
