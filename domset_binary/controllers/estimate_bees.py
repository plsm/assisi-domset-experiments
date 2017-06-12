#!/usr/bin/env python
# -*- coding: utf-8 -*-

from assisipy import casu
import numpy as np

def estimate_numbees(ir_raw, ir_threshold):
    """
    Bee density estimator.
    """
    numbees = 0
    for i in range(6):
        if ir_raw[i] > ir_threshold[i]:
            numbees += 1

    return numbees


if __name__ == '__main__':

    """ IR sensors threshold - [F, FR, BR, B, BL, FL] """
    ir_threshold = [1000, 2000, 3000, 4000, 5000, 6000] 

    """ IR sensors readings - [F, FR, BR, B, BL, FL] """
    ir_raw = [[0, 1000, 1000, 1000, 1000, 1000],
             [0, 1000, 1000, 1000, 1000, 1000],
             [2000, 1000, 1000, 1000, 1000, 1000],
             [2000, 1000, 1000, 1000, 1000, 1000],
             [2000, 1000, 1000, 1000, 1000, 1000],
             [2000, 3000, 1000, 1000, 1000, 1000],
             [2000, 3000, 1000, 1000, 1000, 1000],
             [2000, 3000, 1000, 1000, 1000, 1000],
             [2000, 3000, 4000, 1000, 1000, 1000],
             [2000, 3000, 4000, 1000, 1000, 1000]]
    
    """ Number of bees average calculation """
    Tavr = 4   #Time in which average is calculated
    t_old = 0
    casu_numbees_sum = 0
    n_data = 0
    numbees_avr = 0
    
    """ Main loop """
    t = 0
    Texp = 10
    k = 0
    while t<Texp:
        casu_numbees = estimate_numbees(ir_raw[k], ir_threshold)
        print "numbees = ", casu_numbees
        k += 1

        dt = t - t_old   
        casu_numbees_sum += casu_numbees
        n_data += 1.0     
        if dt >= Tavr:
            t_old = t
            numbees_avr = casu_numbees_sum/n_data
            n_data = 0
            num_bees_sum = 0
        
        print "numbees_avr = ", numbees_avr
        t += 1
  
    """ Debug print """

    print "numbees_avr = ", numbees_avr
    print "numbees = ", casu_numbees


