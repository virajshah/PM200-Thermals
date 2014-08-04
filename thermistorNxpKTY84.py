#Using the lookup table generated from \\valentino\engineering\Dyno\Dyno 2013\OEM Components\Sensors\Temperature\Thermistor Table - Updated.xlsx

#Returns T in Celsius.

Resistance_LookUp_Ohms = (359,391,424,460,498,538,581,626,672,722,773,826,882,940,1000,1062,1127,1194,1262,1334,1407,1482,1560,1640,1722)

Temperature_LookUp_C = (-40,-30,-20,-10,0,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200) 

def voltsToTemp(measuredV, supplyV, pullupR):
	thermistorR = 0 if supplyV == 0 or measuredV == 0 else pullupR/((float(supplyV)/measuredV) - 1) #Voltage divider formula
	indexForInterp = 0
	for i in range(len(Resistance_LookUp_Ohms)):
		if thermistorR <= Resistance_LookUp_Ohms[i]:
			indexForInterp = i -1
			r_pt1 = Resistance_LookUp_Ohms[indexForInterp]
			r_pt2 = Resistance_LookUp_Ohms[indexForInterp+1]
			temp_pt1 = Temperature_LookUp_C[indexForInterp]
			temp_pt2 = Temperature_LookUp_C[indexForInterp + 1]
			m = (temp_pt2 - temp_pt1)/float((r_pt2 - r_pt1))
			b = temp_pt1 - (m*r_pt1)
			return (m*thermistorR) + b