
import numpy

def moving_average (data, window_size):
    ''' from http://stackoverflow.com/a/11352216'''
    window = numpy.ones (int (window_size)) / float (window_size)
    return numpy.convolve (data, window, 'same')

import numpy as np
def find_nearest(array, value):
    idx = (np.abs(array - value)).argmin()
    return array[idx]

def find_nearest_index (array, value):
    return (np.abs(array - value)).argmin()
