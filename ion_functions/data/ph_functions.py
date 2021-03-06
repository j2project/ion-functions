#!/usr/bin/env python

"""
@package ion_functions.data.ph_functions
@file ion_functions/data/ph_functions.py
@author Christopher Wingard
@brief Module containing pH family instrument related functions
"""

# imports
import numpy as np
from ion_functions.utils import isscalar


# wrapper functions to extract L0 parameters from SAMI-II pH instruments (PHSEN)
def ph_434_intensity(light):
    """
    Wrapper function to extract the signal intensity at 434 nm (PH434SI_L0)
    from the pH instrument light measurements. Coded to accept either a
    single record or an array of records.
    """
    light = light.astype(np.float)
    if light.ndim == 1:
        new = np.reshape(light, (23, 4))
        si434 = new[:, 3]
    else:
        tmp = np.zeros(23, dtype=np.float)
        for iRec in light:
            new = np.reshape(iRec, (23, 4))
            tmp = np.vstack((tmp, new[:, 1]))

        si434 = tmp[1:, :]

    return si434  # signal intensity, 434 nm (PH578SI_L0)


def ph_578_intensity(light):
    """
    Wrapper function to extract the signal intensity at 578 nm (PH578SI_L0)
    from the pH instrument light measurements. Coded to accept either a
    single record or an array of records.
    """
    light = light.astype(np.float)
    if light.ndim == 1:
        new = np.reshape(light, (23, 4))
        si578 = new[:, 3]
    else:
        tmp = np.zeros(23, dtype=np.float)
        for iRec in light:
            new = np.reshape(iRec, (23, 4))
            tmp = np.vstack((tmp, new[:, 3]))

        si578 = tmp[1:, :]

    return si578  # signal intensity, 578 nm (PH578SI_L0)


def ph_thermistor(traw):
    """
    Wrapper function to convert the thermistor data (ABSTHRM_L0) from counts to
    degrees Centigrade from the pH instrument.
    """
    # convert raw thermistor readings from counts to degrees Centigrade
    Rt = (traw / (4096.0 - traw)) * 17400.0
    InvT = 0.0010183 + 0.000241 * np.log(Rt) + 0.00000015 * np.log(Rt)**3
    TempK = 1.0 / InvT
    therm = TempK - 273.15

    return therm


def ph_calc_phwater(ref, light, therm, ea434, eb434, ea578, eb578, psal=35.0):
    """
    Wrapper function to vectorize the Sea Water pH calculation defined
    below in ph_phwater. Coded to accept either a single record or an array of
    records.
    """
    if ref.ndim == 1:
        # only one record is being presented to the function
        pH = ph_phwater(ref, light, therm, ea434, eb434, ea578, eb578, psal)
    else:
        # multiple records are being passed in, determine how many and create
        # an empty pH array to hold the final outputs.
        nRec = ref.shape[0]
        pH = np.zeros(nRec, dtype=np.float)

        # Salinity can either be a default value of 35 or from a co-located
        # CTD. Need to replicate it to the same size as nRec if it is just the
        # default scalar.
        if np.isscalar(psal) is True:
            psal = np.tile(psal, (nRec, 1))

        # Iterate through the records
        for iRec in range(nRec):
            pH[iRec] = ph_phwater(ref[iRec, :], light[iRec, :], therm[iRec],
                                  ea434[iRec], eb434[iRec], ea578[iRec],
                                  eb578[iRec], psal[iRec])

    return pH


def ph_phwater(ref, light, therm, ea434, eb434, ea578, eb578, psal=35.0):
    """
    Description:

        OOI Level 1 pH of seawater core data product, which is calculated using
        data from the Sunburst SAMI-II pH instrument (PHSEN). This document is
        intended to be used by OOI programmers to construct appropriate
        processes to create the L1 pH of seawater core data product.

    Implemented by:

        2013-04-19: Christopher Wingard. Initial code.

    Usage:

        ph = ph_phwater(ref, light, therm, ea434, eb434, ea578, eb578, psal=35)

            where

        ph = measured pH of seawater [unitless]
        ref = raw signal and reference measurements during blank cycle [counts]
        light = raw signal and reference measurements during measurement cycle
            [counts]
        therm = thermistor reading at end of measurement cycle [deg_C]
        ea434 = mCP molar absorptivities provided by vendor, specific to a
            reagent bag with a defined shelflife.
        eb434 = mCP molar absorptivities as above
        ea578 = mCP molar absorptivities as above
        eb578 = mCP molar absorptivities as above
        psal = practical salinity estimate used in calculcations, default is
            35.0 [unitless]

    References:

        OOI (2012). Data Product Specification for pH of Seawater. Document
            Control Number 1341-00510. https://alfresco.oceanobservatories.org/
            (See: Company Home >> OOI >> Controlled >> 1000 System Level >>
            1341-00510_Data_Product_SPEC_PHWATER_OOI.pdf)
    """
    # Calculate blanks from the 16 sets of reference light measurements
    ref = ref.astype(np.float)  # convert to float array

    arr434 = np.array([
        (ref[1] / ref[0]),
        (ref[5] / ref[4]),
        (ref[9] / ref[8]),
        (ref[13] / ref[12]),
    ])
    blank434 = np.mean(arr434)

    arr578 = np.array([
        (ref[3] / ref[2]),
        (ref[7] / ref[6]),
        (ref[11] / ref[10]),
        (ref[15] / ref[14]),
    ])
    blank578 = np.mean(arr578)

    # Extract 23 sets of 4 light measurements into arrays corresponding to the
    # raw reference and signal measurements at 434 and 578 nm. Input is an
    # array of length 92 (23 sets * 4 measurements per set). Can reshape and
    # slice to extract the parameters.
    light = light.astype(np.float)
    new = np.reshape(light, (23, 4))
    ref434 = new[:, 0]   # reference signal, 434 nm
    int434 = new[:, 1]   # signal intensity, 434 nm (PH434SI_L0)
    ref578 = new[:, 2]   # reference signal, 578 nm
    int578 = new[:, 3]   # signal intensity, 578 nm (PH578SI_L0)

    # Absorbance
    A434 = -np.log10(int434 / ref434)
    A434blank = -np.log10(blank434)
    abs434 = A434 - A434blank

    A578 = -np.log10(int578 / ref578)
    A578blank = -np.log10(blank578)
    abs578 = A578 - A578blank

    # pka from Clayton and Byrne, 1993
    pKa = (1245.69 / (therm + 273.15)) + 3.8275 + (0.0021 * (35. - psal))
    R = (A578 - A578blank) / (A434 - A434blank)

    # Molar absorptivities
    ea434 = ea434 - (26. * (therm - 24.788))
    ea578 = ea578 + (therm - 24.788)
    eb434 = eb434 + (12. * (therm - 24.788))
    eb578 = eb578 - (71. * (therm - 24.788))
    e1 = ea578 / ea434
    e2 = eb578 / ea434
    e3 = eb434 / ea434

    V1 = R - e1
    V2 = e2 - R * e3

    # indicator concentration calculations
    HI = (abs434 * eb578 - abs578 * eb434) / (ea434 * eb578 - eb434 * ea578)
    I = (abs578 * ea434 - abs434 * ea578) / (ea434 * eb578 - eb434 * ea578)
    IndConc = HI + I
    pointph = np.real(pKa + np.lib.scimath.log10(V1 / V2))

    # ************************ Initial pH Calcs ************************
    # determine the most linear region of points for pH of seawater
    # calculation, skipping the first 5 points.
    IndConca = IndConc[5:]
    Y = pointph[5:]
    X = np.linspace(1, 18, 18)

    # [TODO: The next sequence of steps could likely be optimized by using the
    # built-in numpy linear interpolation algorithm, rather than the hand-coded
    # implementation provided in the vendor code. However, coordination with
    # the DPS author will be required as the calculated pH values do differ
    # slightly when using the different methods.]

    step = 7  # number of points to use
    count = step + 1
    npts = np.size(X) - step
    r2 = np.zeros(npts)
    for i in range(npts):
        sumx = np.sum(X[i:i+count])
        sumy = np.sum(Y[i:i+count])
        sumxy = np.sum(X[i:i+count] * Y[i:i+count])
        sumx2 = np.sum(X[i:i+count]**2)
        sumy2 = np.sum(Y[i:i+count]**2)
        avgx = np.mean(X[i:i+count])
        avgy = np.mean(Y[i:i+count])
        sumxx = sumx * sumx
        sumyy = sumy * sumy
        ssxy = sumxy - (sumx * sumy) / count
        ssx = sumx2 - (sumxx / count)
        ssy = sumy2 - (sumyy / count)
        r2[i] = ssxy**2 / (ssx * ssy)

    # Range of seawater points to use
    cutoff1 = np.argmax(r2)  # Find the first, best R-squared value
    cutoff2 = cutoff1 + count

    # Indicator and pH range limited to best points
    IndConcS = IndConca[cutoff1:cutoff2]
    pointphS = Y[cutoff1:cutoff2]

    # ************************* Final pH Calcs *************************
    sumx = np.sum(IndConcS)
    sumy = np.sum(pointphS)
    sumxy = np.sum(pointphS * IndConcS)
    sumx2 = np.sum(IndConcS**2)
    sumy2 = np.sum(pointphS**2)
    xbar = np.mean(IndConcS)
    ybar = np.mean(pointphS)
    sumxx = sumx * sumx
    sumyy = sumy * sumy
    ssxy = sumxy - (sumx * sumy) / count
    ssx = sumx2 - (sumxx / count)
    ssy = sumy2 - (sumyy / count)
    slope = ssxy / ssx
    ph = ybar - slope * xbar

    return ph
