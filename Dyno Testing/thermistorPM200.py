#Using the lookup table generated from \\valentino\engineering\Test Plans and Reports\TPR00156 - PM200 Thermal Characterization\11 Experimental setup\AL03006-17.53-98-G2.xlsx

#Returns T in Celsius.

Resistance_LookUp_Ohms = (965530,700033,512947,379641,283651,213839,162585,124616,96248,75197,59173,46882,37387,30000,24216,19657,16043,13162,10851,8990,7486,6265,5268,4450,3776,3217,2751,2362,2036,1758,1523,1324,1155,1010,886.9,780.8,689.4,610.3,541.8,482.1,430.1,384.7,344.9,309.9,279.1,251.9,227.8,206.5,187.5,170.6,155.4)

Temperature_LookUp_C = (-40,-35,-30,-25,-20,-15,-10,-5,0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175,180,185,190,195,200,205,210) 

def voltsToTemp(measuredV, supplyV, pullupR):
	try:
		thermistorR = 0 if (measuredV == 0 or supplyV == 0 or measuredV == supplyV) else pullupR/((float(supplyV)/measuredV) - 1) #Voltage divider formula
		indexForInterp = 0
		for i in range(len(Resistance_LookUp_Ohms)):
			if thermistorR >= Resistance_LookUp_Ohms[i]:
				r_pt1 = Resistance_LookUp_Ohms[i-1]
				r_pt2 = Resistance_LookUp_Ohms[i]
				temp_pt1 = Temperature_LookUp_C[i-1]
				temp_pt2 = Temperature_LookUp_C[i]
				m = (temp_pt2 - temp_pt1)/float((r_pt2 - r_pt1))
				b = temp_pt1 - (m*r_pt1)
				return (m*thermistorR) + b

	except:
		return 0