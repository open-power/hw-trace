#!/usr/bin/python

import struct
import sys
import match_trace


f_in = open(sys.argv[1])
filename_out=sys.argv[1]+".matched"
f_out = open(filename_out, "w")
trace =  match_trace.match_trace()

trace.parse(f_in,f_out)

f_in.close()
f_out.close()
