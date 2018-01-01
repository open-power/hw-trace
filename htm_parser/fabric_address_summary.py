#!/usr/bin/python

import sys
import fabric_trace

f_in = open(sys.argv[1])
trace = fabric_trace.fabric_trace()

while True:
	buf = f_in.read(1024 * 1024)
	if buf == '':
		break
	trace.parse(buf, len(buf))

addrs = {}
for entry in trace.entries:
	if entry.type == fabric_trace.type_rcmd:
		if entry.addr not in addrs:
			addrs[entry.addr] = 1
		else:
			addrs[entry.addr] += 1

print "Address               Count"
for key in sorted(addrs, key=addrs.__getitem__, reverse=True):
	print "0x%016x %8d" % (key, addrs[key])
