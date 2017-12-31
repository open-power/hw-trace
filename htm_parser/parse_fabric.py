#!/usr/bin/python

from operator import attrgetter
import struct
import sys
import time
import argparse
import fabric_trace
from fabric_trace import statistics
from fabric_trace import type_stamp
import logging
import os

#Use for filtering out different records with a common timestamp
stamp_complete=2

#Size of htm records.
RECORD_SIZE=128

SINGLE_REC_SIZE=16

#how big of a buffer to read in each time.
BUFFER_SIZE=1024*1024

#How many entries to print before stopping, allowing for more cresp matching
PRINT_NUM=BUFFER_SIZE/RECORD_SIZE/2

#Identify which htm to fetch for
HTM0=0
HTM1=1

parser = argparse.ArgumentParser(description='Parse HTM Dump File')
parser.add_argument('filename', metavar='FILE', action="store", # nhtm (nhtm0 in case POWER9)
			help='dump filename to parse')

trace = fabric_trace.fabric_trace() # moved up since we add_argument based on processor version

if fabric_trace.processor_version=="POWER9":
 nhtm0_1_same_file = False
 parser.add_argument('--filename2', metavar='FILE2', action="store",\
			help='dump second filename to parse (applicable in POWER9)', default=None) # nhtm1

parser.add_argument('--match', action="store_true",  default=False, 
			help='Perform cresp matching on trace')

parser.add_argument('--logfile', '-f', type=str, help='Save all logging and debug information to this file')
parser.add_argument('--debug', '-d', action='store_true', help='Print debug information')

args = parser.parse_args()

if not args.filename: # redundant?
  print('A dump file has to be specified for processing.')
  parser.print_help()
  exit(-1)

if fabric_trace.processor_version=="POWER9" and not args.filename2:
    nhtm0_1_same_file = True # single dump file with both nhtm0 and 1 records

if fabric_trace.processor_version=="POWER9":
 if '0' in args.filename:
  out_file_prefix = args.filename.replace('nhtm0','nhtm') + ('_agg')
 else:
  out_file_prefix = args.filename + ('_agg')
else:
 out_file_prefix = args.filename

print('out_file_prefix: {}'.format(out_file_prefix))

if args.logfile:
   logfile = args.logfile[0]
else:
   logfile = out_file_prefix + ".log"

if args.match:
	out_file = out_file_prefix + ".matched"
 	if fabric_trace.processor_version=="POWER9":
 	 out_single_file = args.filename + ".matched.sorted"
         if args.filename2:
	  out_single_file2 = args.filename2 + ".matched.sorted"
else:
	out_file = out_file_prefix + ".formatted"
 	if fabric_trace.processor_version=="POWER9":
	 out_single_file = args.filename + ".formatted.sorted"
         if args.filename2:
	  out_single_file2 = args.filename2 + ".formatted.sorted"

log_level = logging.INFO

if args.debug:
 log_level = logging.DEBUG

logformat = '%(asctime)s %(levelname)s: %(message)s'

logging.basicConfig(level=log_level,
		    filename=logfile,
		    format=logformat)

sh = logging.StreamHandler(sys.stderr)
sh.setLevel(log_level)
sh.setFormatter(logging.Formatter(logformat))
logging.getLogger('').addHandler(sh)

logging.info("proc_version: %s\n", fabric_trace.processor_version)

#out_file_missed = sys.argv[1] + ".missed"
#out_file_stats = sys.argv[1] + ".stats"

#f_in = open(sys.argv[1])
f_in = open(args.filename, "r")

if fabric_trace.processor_version=="POWER9":
# f_in2 = open(sys.argv[2])
 f_out_single = open(out_single_file, "w")
 if args.filename2:
  f_in2 = open(args.filename2, "r")
  f_out_single2 = open(out_single_file2, "w")

f_out_format = open(out_file, "w")
#f_out_missed = open(out_file_missed, "w")
#f_out_stats = open(out_file_stats, "w")

statList = []
statList.append(statistics())
statList.append(statistics())

if fabric_trace.processor_version=="POWER9": # 4 statLists one per port
	statList.append(statistics())
	statList.append(statistics())

timestamp = long(0)
start_time=time.mktime(time.gmtime())

# write to single files if POWER9
if fabric_trace.processor_version=="POWER9":
# Now, get the entries
 iteration = 0
 reverse = True

 if reverse == True:
  trace.run_number = 1 # iteration to fetch stamp_complete
  if nhtm0_1_same_file == True:
   while True: # First get the stamp_complete offset.
    buf = f_in.read(BUFFER_SIZE)
    logging.debug('len of buf: %d', len(buf))

    if buf == '':
	break;
       # find stamp_complete for both nhtm0 and nhtm1
    if not trace.find_stamp_complete_all(buf, len(buf), iteration):
          break
    iteration = iteration + 1

  iteration = 0
  if nhtm0_1_same_file == False:
   while True: # First get the stamp_complete offset.
    buf = f_in.read(BUFFER_SIZE)
    logging.debug('len of buf: %d', len(buf))

    if buf == '':
	break;
       # find stamp_complete for both nhtm0 and nhtm1
    if not trace.find_stamp_complete(buf, len(buf), iteration, HTM0):
	break # trace.stamp_complete_offset is set
   
    iteration = iteration + 1
 
   iteration = 0
   while True: # First get the stamp_complete offset.
    buf = f_in2.read(BUFFER_SIZE)
    logging.debug('len of buf: %d', len(buf))

    if buf == '':
	break;
       # find stamp_complete for both nhtm0 and nhtm1
    if not trace.find_stamp_complete(buf, len(buf), iteration, HTM1):
	break # trace.stamp_complete_offset is set
   
    iteration = iteration + 1
  
  if nhtm0_1_same_file == True:
      logging.debug('stamp_complete_offsets: nhtm0: %d, nhtm1: %d', trace.stamp_complete_offset0, trace.stamp_complete_offset1)
  else:
      logging.debug('stamp_complete offset: %d', trace.stamp_complete_offset)

#  trace.stamp_complete_offset = 522944 # manual setting of nhtm1 stamp_complete, for faster debug

  size = os.stat(args.filename).st_size
  logging.debug('size of file: %ld', size)
  if nhtm0_1_same_file == True:
      if trace.stamp_complete_offset1 > trace.stamp_complete_offset0:
          trace.stamp_complete_offset = trace.stamp_complete_offset1
      else:
          trace.stamp_complete_offset = trace.stamp_complete_offset0

      trace.current_offset = trace.stamp_complete_offset + SINGLE_REC_SIZE # this is how far we'll go into the file

# In case of parsing individual trace files per nhtm, retain offset0 and offset1 as is.
  trace.run_number = 2 # Iteration to add entries

  iteration = 0

  if nhtm0_1_same_file == True:
   while (trace.current_offset > 0):
    if (trace.current_offset < BUFFER_SIZE):
     f_in.seek(0, os.SEEK_SET)
     buf = f_in.read(trace.current_offset)
     trace.current_offset = 0 # complete
    else: # trace.stamp_complete_offset > BUFFER_SIZE
     trace.current_offset -= BUFFER_SIZE
     f_in.seek(trace.current_offset, os.SEEK_SET) # Move (SINGLE_REC_SIZE) 16 bytes ahead to cover the last record
     buf = f_in.read(BUFFER_SIZE)
 
    trace.fill_trace_all(buf, len(buf), args.match, iteration) # All of nhtm0 and nhtm1 together
    iteration = iteration + 1
  else: # separate trace input files for nhtm0/1
   iteration = 0

   trace.current_offset = trace.stamp_complete_offset0 + SINGLE_REC_SIZE # nhtm0
   while (trace.current_offset > 0):
    if (trace.current_offset < BUFFER_SIZE):
     f_in.seek(0, os.SEEK_SET)
     buf = f_in.read(trace.current_offset)
     trace.current_offset = 0 # complete
    else: # trace.stamp_complete_offset > BUFFER_SIZE
     trace.current_offset -= BUFFER_SIZE
     f_in.seek(trace.current_offset, os.SEEK_SET) # Move (SINGLE_REC_SIZE) 16 bytes ahead to cover the last record
     buf = f_in.read(BUFFER_SIZE)
    trace.fill_trace(buf, len(buf), args.match, iteration, HTM0) # All of nhtm0 and nhtm1 together
#      trace.parse_and_fill(buf, len(buf), args.match, HTM0, iteration)
    iteration = iteration + 1

   iteration = 0
   trace.current_offset = trace.stamp_complete_offset1 + SINGLE_REC_SIZE # nhtm1
   while (trace.current_offset > 0):
    if (trace.current_offset < BUFFER_SIZE):
     f_in2.seek(0, os.SEEK_SET)
     buf = f_in2.read(trace.current_offset)
     trace.current_offset = 0 # complete
    else: # trace.stamp_complete_offset > BUFFER_SIZE
     trace.current_offset -= BUFFER_SIZE
     f_in2.seek(trace.current_offset, os.SEEK_SET) # Move (SINGLE_REC_SIZE) 16 bytes ahead to cover the last record
     buf = f_in2.read(BUFFER_SIZE)
    trace.fill_trace(buf, len(buf), args.match, iteration, HTM1) # All of nhtm0 and nhtm1 together
#      trace.parse_and_fill(buf, len(buf), args.match, HTM0, iteration)
    iteration = iteration + 1
 else:    # P9. reverse != True
  while True:
	buf = f_in.read(BUFFER_SIZE)
	logging.debug('len of buf: %d', len(buf))

	if buf == '':
		break;
	if not trace.parse_single(buf, len(buf), args.match, HTM0, iteration):
		break
	iteration = iteration + 1

  if trace.stamp_complete_offset == -1:# Finished the full trace but, could not find trace_complete
   logging.warning('Could not find trace completion stamp in nhtm0 trace. Parsing complete data\n')

   # Data has been fetched. Now sort and merge as required

 logging.debug('entries count: %d', len(trace.entries))

 if reverse != True: # separately per nhtm

     entries_sorted = sorted(trace.entries, key=attrgetter('timestamp'))
    # for entry in entries_sorted:
    #	logging.debug('entry timestamp sorted: %ld', entry.timestamp)

     timestamp = 0
     # now write the sorted entries
    # for entry in trace.entries:
     entries_sorted_new = []
     for entry in entries_sorted:
    #                timestamp += long(entry.timestamp) # Already added in process_* routines
                    timestamp = long(entry.timestamp)
                    logging.debug('writing.. timestamp: %ld',timestamp)
                    f_out_single.write(entry.format(statList))
                    entries_sorted_new.append(entry)
    #		Only write upto the stamp_complete record
    #		However, there could be different record types with
    #		the same timestamp
                    if timestamp == trace.stamp_complete_timestamp and\
                            entry.type == type_stamp and\
                            entry.stamp_type == stamp_complete:
                             break

     end_time = time.mktime(time.gmtime())

     iteration = 0
     trace.stamp_complete_offset = -1 # rest for nhtm1
     trace.stamp_complete_timestamp = -1

     while True:
            buf2 = f_in2.read(BUFFER_SIZE)
            if buf2 == '':
                    break;
            if not trace.parse_single(buf2, len(buf2), args.match, HTM1, iteration):
                    break
            iteration = iteration + 1

     if trace.stamp_complete_offset == -1: # Finished the full trace but, could not find trace_complete
       logging.warning('Could not find trace completion stamp in nhtm1 trace. Parsing complete data\n')

     logging.debug('entries2 count: %d', len(trace.entries2))

     for entry in trace.entries2:
            logging.debug('entry2 timestamp: %ld', entry.timestamp)

     # sort by ascending timestamp
    # if trace.stamp_complete_offset > -1: # Should we specify this condition?
     entries_sorted2 = sorted(trace.entries2, key=attrgetter('timestamp'))
     for entry in entries_sorted2:
            logging.debug('entry timestamp sorted: %ld', entry.timestamp)

     timestamp = 0
    # for entry in trace.entries2:
     entries_sorted2_new = []

     for entry in entries_sorted2:
    #                timestamp += long(entry.timestamp) # Already added in process_* routines
                    timestamp = long(entry.timestamp)
                    logging.debug('writing.. timestamp: %ld',timestamp)
                    f_out_single2.write(entry.format(statList))
                    entries_sorted2_new.append(entry)
    # 		write upto the stamp_complete record
    #		However, there could be different record types with
    #		the same timestamp
                    if timestamp == trace.stamp_complete_timestamp and\
                            entry.type == type_stamp and\
                            entry.stamp_type == stamp_complete:
                             break

     # merge sorted and sorted2 by ascending timestamp
     entries_all = entries_sorted_new + entries_sorted2_new
     
     entries_all_sorted = sorted(entries_all, key=attrgetter('timestamp')) 

     timestamp = 0
     for entry in entries_all_sorted:
                    timestamp += long(entry.timestamp)
                    f_out_format.write(entry.format(statList))
 else: # P9, reverse = True
     if nhtm0_1_same_file == True:
      entries_sorted = []

#     entries_sorted = sorted(trace.entries, key=attrgetter('timestamp'))
      entries_sorted = sorted(trace.entries, key=attrgetter('counter')) # Sort based on running counter
      for entry in entries_sorted:
         timestamp = long(entry.timestamp)
         f_out_single.write(entry.format(statList))
   
      entries_all = entries_sorted
     else: #  separate files for each nhtm and aggregation file as well
      entries_sorted = sorted(trace.entries, key=attrgetter('timestamp'))

      timestamp = 0
      entries_sorted_new = []
      for entry in entries_sorted:
                    timestamp = long(entry.timestamp)
                    logging.debug('writing.. timestamp: %ld',timestamp)
                    f_out_single.write(entry.format(statList))
                    entries_sorted_new.append(entry)

      entries2_sorted = sorted(trace.entries2, key=attrgetter('timestamp'))

      timestamp = 0
      entries2_sorted_new = []
      for entry in entries2_sorted:
                    timestamp = long(entry.timestamp)
                    logging.debug('writing.. timestamp: %ld',timestamp)
                    f_out_single2.write(entry.format(statList))
                    entries2_sorted_new.append(entry)

     # merge sorted and sorted2 by ascending timestamp
      entries_all = entries_sorted_new + entries2_sorted_new
     
     entries_all_sorted = sorted(entries_all, key=attrgetter('timestamp')) 

     timestamp = 0
     for entry in entries_all_sorted:
                    timestamp = long(entry.timestamp)
                    f_out_format.write(entry.format(statList))
 end_time = time.mktime(time.gmtime())

else: # P8
 while True:
	buf = f_in.read(BUFFER_SIZE)
	if buf == '':
		break;

	if not trace.parse(buf, len(buf), args.match):
		break

#print out the rest of the records
 mid_time = time.mktime(time.gmtime())
 logging.debug('initial reqd completed in ' + str(mid_time - start_time) + ' seconds')

 for entry in fabric_trace.entries:
	timestamp += long(entry.timestamp)
	f_out_format.write(entry.format(statList))
 end_time = time.mktime(time.gmtime())

logging.debug ('Elapsed time: ' + str(end_time - start_time) + ' seconds')

if fabric_trace.processor_version=="POWER9":
     if reverse != True:
	logging.info ('missed (agg): %d ', trace.get_agg_missed())
     else:
	logging.info ('missed: %d ', trace.get_missed()) 
else:
	logging.info ('missed: %d ', trace.get_missed()) 

logging.info ('Port 0 Scopes')
statList[0].dump()
logging.info ('Port 1 Scopes')
statList[1].dump()
if fabric_trace.processor_version=="POWER9":
	logging.info ('Port 2 Scopes')
	statList[2].dump()
	logging.info ('Port 3 Scopes')
	statList[3].dump()

print "File " + out_file + " created"
logging.info ('File ' + out_file + ' created')

logging.shutdown()
