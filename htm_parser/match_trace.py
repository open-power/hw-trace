#!/usr/bin/python

import struct
import ttypes
import ports
import re
import tagg
class match_trace:
	def __init__(self):
		self.entries = {}

        def parse_line(self, trace_line):
		ret_string = ""
                mymatch=re.match('(\d+) : R(\d):(\w+) \w+ .+ ttype=(\w+) tsize=(\d+) ticket=(\w+) .* ttag=(\w\d:\w\d)[^\s]+ (\d+)',trace_line)
                if mymatch:
                        cycle = mymatch.group(1)
                        port=mymatch.group(2)
                        scope=mymatch.group(3)
                        ttype=mymatch.group(4)
                        ticket=mymatch.group(6)
			ttag=mymatch.group(7)
			ttag_raw=bin(mymatch.group(8))>>13
			searchkey=port+scope+ticket+str(ttag_raw)
			new_line = re.sub('ticket=\w+','',trace_line)
			if ttag_raw in tagg.ttag_str.keys():
				new_line = re.sub('ttag=([^\s]+)',tagg.ttag_str[ttag_raw],new_line)
			else:
				new_line = re.sub('ttag=','',new_line)
                        self.entries[searchkey] = new_line.rstrip()
		else 

			mymatch=re.match('(\d+) : C(\d):(\w+) .+ cresp=(\d+) #X ticket=(\w+) ttag=(\w\d:\w\d)[^\s]+ (\d+)',trace_line)
			if mymatch:
				cycle = mymatch.group(1)
				port=mymatch.group(2)
				scope=mymatch.group(3)
				cresp=mymatch.group(4)
				ticket=mymatch.group(5)
				ttag=mymatch.group(6)
				ttag_raw=mymatch.group(7)
				searchkey=port+scope+ticket+ttag_raw
				if searchkey in self.entries.keys():
					addrmatch = re.match('(\d+) : .+', self.entries[searchkey])
					ret_string= self.entries[searchkey] + " cresp="+cresp + "  delta=" + str(int(cycle)-int(addrmatch.group(1)))+"\n"
					del self.entries[searchkey]
				else:
					ret_string= "WARNING cresp not found! cresp="+cresp + " scope="+scope+" ticket="+ticket+"\n"

		return ret_string


	def parse(self, f_in, f_out):
		for line in f_in:
			f_out.write(self.parse_line(line))
		print "Unmatched Entries"
		for k, v in self.entries.iteritems():
			print k, v
