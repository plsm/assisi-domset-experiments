#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time

from assisipy import casu

if __name__ == '__main__':

    if len(sys.argv) < 2:
        sys.exit('Please provide .rtc file name!')

    c = casu.Casu(sys.argv[1],log=True)

    while True:
        time.sleep(10)
    
