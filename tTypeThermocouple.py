"""
This module will define the functions needed to convert voltages
to temperatures and vice versa for T-type thermocouples. 
The the coefficients for the polynomials are obtained from
NIST.
http://srdata.nist.gov/its90/type_t/tcoefficients.html
http://srdata.nist.gov/its90/type_t/tcoefficients_inverse.html
"""

#Define coefficients
"""
Volts (mV) --> Temp (C)
-200C to OC
-5.603mV to 0mV
"""
voltsToTempCoefficients1 = (0.0E0,
                            2.5949192E1,
                            -2.1316967E-1,
                            7.9018692E-1,
                            4.2527777E-1,
                            1.3304473E-1,
                            2.0241446E-2,
                            1.2668171E-3)

"""
Volts (mV) --> Temp (C)
0C to 400C
0mV to 20.872mV
"""
voltsToTempCoefficients2 = (0.0E0,
                            2.592800E1,
                            -7.602961E-1,
                            4.637791E-2,
                            -2.165394E-3,
                            6.048144E-5,
                            -7.293422E-7)

"""
Temp (C) --> Volts (mV)
-270C to 0C
"""
tempToVoltsCoefficients1 = (0.0E0,
                            0.387481063640E-1,
                            0.441944343470E-4,
                            0.118443231050E-6,
                            0.200329735540E-7,
                            0.901380195590E-9,
                            0.226511565930E-10,
                            0.360711542050E-12,
                            0.384939398830E-14,
                            0.282135219250E-16,
                            0.142515947790E-18,
                            0.487686622860E-21,
                            0.107955392700E-23,
                            0.139450270620E-26,
                            0.797951539270E-30)

"""
Temp (C) --> Volts (mV)
OC to 400C
"""
tempToVoltsCoefficients2 = (0.0E0,
                            0.387481063640E-1,
                            0.332922278800E-4,
                            0.206182434040E-6,
                            -0.218822568460E-8,
                            0.109968809280E-10,
                            -0.308157587720E-13,
                            0.454791352900E-16,
                            -0.275129016730E-19)

def voltsToTempCoeffs(mVolts):
    """
    Takes in a voltage in millivolts and returns
    set of coefficients that will be used for conversion
    into temperature in Celsius.
    """
    if mVolts < -5.603 or mVolts > 20.872:
        print "Voltage outside range."
    if mVolts < 0:
        return voltsToTempCoefficients1 
    else: 
        return voltsToTempCoefficients2

def tempToVoltsCoeffs(tempC):
    """
    Takes in temperature in Celsius and returns
    set of coefficients that will be used for conversion
    into voltage in millivolts.
    """
    if tempC < -270 or tempC > 400:
        print "Temperature outside range."
    if tempC < 0:
        return tempToVoltsCoefficients1
    else:
        return tempToVoltsCoefficients2

def computePolynomial(coeffs, x):
    """
    coeffs = Set of coefficients used in polynomials
    conversion.
    x = value to be converted. 
    """
    runningSum = 0
    x_nththerm = 1 #nth order term (i.e. x^n), we start with x^0=1
    for coefficient in coeffs:
        runningSum += coefficient*x_nththerm
        x_nththerm *= x
    return runningSum

def mVoltstoTempC(mVolts):
    coeffs = voltsToTempCoeffs(mVolts)
    return computePolynomial(coeffs, mVolts)

def tempCtoMVolts(tempC):
    coeffs = tempToVoltsCoeffs(tempC)
    return computePolynomial(coeffs, tempC)

def convertVoltsToTemp(cjcTempC, voltsMeasured):
    """
    cjcTempC = cold junction temperature in Celsius
    voltsMeasured = voltage measured in Volts
    """
    cjcMVolts = tempCtoMVolts(cjcTempC) #Convert cold junction temp to mV
    return mVoltstoTempC(voltsMeasured*1000 + cjcMVolts) #multiply by 1000 to convert to mV