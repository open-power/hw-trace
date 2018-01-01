#!/usr/bin/python

import struct
import ttypes
import ttypes_P9
import ports
import ports_P9
import subprocess
import logging
import os

processor_version = "P8"
htm_id = -1

adjust_cycle_count = 0
adjust_nhtm0 = False
adjust_nhtm1 = False

nhtm0_stamp_complete_found = False
nhtm1_stamp_complete_found = False

cycle_adjust_complete = False # This flag ensures the cycle count is adjusted just once.

# identify which htm to fetch data for
HTM0=0
HTM1=1

counter0 = 0 # nhtm0
counter1 = 0 # nhtm1

log = logging.getLogger(__name__)

class proc_version():
	def __init__(self):
		global processor_version
		log.info('processor_version is %s', processor_version)

#		processor_version="POWER9" # Testing manually for POWER9
		log.info('processor_version set to : %s', processor_version)
		self.set_processor_version()

	def set_processor_version(self):
		global processor_version

		cmd = 'cat /proc/cpuinfo  | grep cpu | awk -F\" \"  \'{print $3}\'| head -n1'
		p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
		processor_version = p.stdout.read().strip()


class statistics():
	def __init__(self):
		self.group_pump = 0
		self.node_pump = 0
		self.system_pump = 0
		self.ttype_dict = {}

	def addTtype(self,ttype, tsize):
		ttype_key = str(ttype)+str(tsize)
		#print ttype_key + "<-- key"
		if self.ttype_dict.has_key(ttype_key):
			self.ttype_dict[ttype_key]+=1
		else:
			self.ttype_dict[ttype_key] = 1

	def addCount(self,pump):
		if pump == 0:
			self.node_pump+=1
		elif pump == 1:
			self.group_pump+=1
		elif pump == 2:
			self.system_pump+=1
	def dump(self):
		log.info(str(self.node_pump) + " NP")
		log.info(str(self.group_pump) + " GP")
		log.info(str(self.system_pump) + " SP")
		#for k, v in self.ttype_dict:
		#	print str(v) + "  " + k
	def write(self,fname):
		f_out = open(fname,'w')
		f_out.write("GP %d " % self.group_pump)

#statList = []
#statList.append(statistics())
#statList.append(statistics())

class bits128:
	def __init__(self, dw1, dw2):
		self.dw1 = dw1
		self.dw2 = dw2

	def bit(self, bit):
		if bit >= 64:
			bit -= 64
			w = self.dw2
		else:
			w = self.dw1

		shift = 63 - bit

		return (w >> shift) & 1

	def bits(self, start, end):
		if (start & 0x40) != (end & 0x40):
			log.warning('bitmask cant cross 64 bit boundary')
			raise ValueError("bitmask cant cross 64 bit boundary")

		if start >= 64:
			start -= 64
			end -= 64
			w = self.dw2
		else:
			w = self.dw1

		start = (63 - start)
		end = (63 - end)

		mask = (1 << (start - end)) - 1 | (1 << (start - end))
		shift = end

		return (w >> shift) & mask


class fabric_entry(bits128):
	def __init__(self, dw1, dw2):
		bits128.__init__(self, dw1, dw2)

		# The trace type identification is identical on P8 / P9
		self.type = self.bits(0, 1)
		if self.type == 0x3:
			self.type = 0x2
                
	def format_scope(self, val):
                if (processor_version == "POWER9"):
                    if val == 0:
                            return 'Ln' # Local node
#                    elif val == 1: # '1' is not defined
#                            return 'GP'
                    elif val == 2:
                            return 'Nn' # Near node
                    elif val == 3:
                            return 'G'  # Group
                    elif val == 4:
                            return 'Rn' # Remote node
                    elif val == 5:
                            return 'Vg' # Vectored group
                    else:
                            return 'U'  # Unknown
                else:
                    if val == 0:
                            return 'NP'
                    elif val == 1:
                            return 'GP'
                    elif val == 2:
                            return 'SP'
                    elif val == 3:
                            return 'RP'
                    else:
                            return 'FP'


class cresp(fabric_entry):

	def search_key(self):
		return str(self.scope) + str(self.ticket) + str(self.ttag) + str(self.port)
	def format_ttag(self, ttag):
                if (processor_version == "POWER9"):
		   return "g%x:p%x" % ((ttag >> 3) & 0xf, ttag & 0x7) # printing 4-bit group id instead of node id
                else:
		   return "n%x:p%x" % ((ttag >> 3) & 0x7, ttag & 0x7)

	def __init__(self, cresp1, cresp2, timestamp):
                global counter0, counter1

		fabric_entry.__init__(self, cresp1, cresp2)
		if processor_version == "POWER9":

#                        The following bit settings will work for all cresps (1 through 4) since we pass in the actual bits
#                        per the cresp number, but they are always at the same position here.
                        self.port = self.bits(118,118)
                        self.cresp =	self.bits(99, 103)
                        self.ttag =	self.bits(104, 110)
                        self.ticket =	self.bits(111, 117)
                        self.scope =	self.bits(119, 121) 
                        self.target_ds =self.bits(122, 127) # Open: where / how will this get consumed?

                        self.addr =     0 # place holder. Required in case of rcmd
#			self.port =	self.bits(118, 118) # Combine this with bit 56 of trace data mem addr to 
							    # get snoop bus port #
 
                        if (htm_id == 0):
                         self.counter =  counter0 # Save the global counter in the cresp as well.
                        else: 
                         self.counter =  counter1 # Save the global counter in the cresp as well.
		else: # POWER8
			self.cresp =	self.bits(107, 111)
			self.ttag =	self.bits(112, 117)
			self.ticket =	self.bits(118, 123)
			self.port =	self.bits(124, 124)
			self.scope =	self.bits(125, 127)

		scope = self.scope
		self.timestamp = timestamp
		self.type = 1


		if (processor_version == "POWER9"): # Need to identify the port # in combination with bit 56
	        	p = ports_P9.ports()
                        self.port=p.port_P9(htm_id, self.port, type_cresp, self.addr)
                        if (htm_id == 0):
                         self.counter = counter0
                        else:
                         self.counter = counter1

	def format(self, statList):
#		return "%016d : C%d:%s                      cresp=%02x #X ticket=%02x ttag=%s\n" % (self.timestamp, self.port, self.format_scope(self.scope), self.cresp, self.ticket, self.format_ttag(self.ttag))

#               print the running counter instead of the timestamp
		return "%016d : C%d:%s                      cresp=%02x #X ticket=%02x ttag=%s\n" % (self.counter, self.port, self.format_scope(self.scope), self.cresp, self.ticket, self.format_ttag(self.ttag))

class rcmd(fabric_entry):

	def search_key(self):
                if (processor_version == "POWER9"):
                    ttag_raw=self.ttag>>16
                else:
		    ttag_raw=self.ttag>>13
		return str(self.scope) + str(self.ticket) + str(ttag_raw) + str(self.port)

	def add_cresp(self, cresp):
#		print "setting "+ str(cresp)
		self.cresp = cresp

	def format_ttag(self, ttag):
                if (processor_version == "POWER9"):
                    group = (ttag >> 18) & 0xf # Bits 0:3. Get the last 4 bits only (& 0xf). group id
                    chip = (ttag >> 15) & 0x7 # Bits 4:6. Get the last 3 bits only
                    unit = (ttag >> 5) & 0x3ff # Bits 7:16. Get the last 10 bits only
#                    transaction0 = ttag & 0x1 # Bit 18 is the first bit (0) for transaction. Get the last bit only
#                    transaction = transaction0 << 4 | self.bits(23,26) # Prepare the 5 bit transaction id using flex mux bits
                    transaction = ttag & 0x1f # Bits 17:21.
                else:
                    node = (ttag >> 16) & 0x7 # bits 0:2
                    chip = (ttag >> 13) & 0x7 # bits 3:5
                    unit = (ttag >> 5) & 0xff # bits 7:14
                    transaction = ttag & 0x1f # bits 15:19

                if (processor_version == "POWER9"):
#		 if (unit & 0x70) == 0x60 or
#                     (unit & 0x70) == 0x40: # L2/L3/NCU
                 if (unit & 0x50) == 0x40: # L2/L3/NCU
                        b13_17 = (ttag >> 4) & 0x1f
                        b18_19 = (ttag >> 2) & 0x3
                        b18    = (ttag >> 3) & 0x1
                        if (b13_17 == 0x1) or\
                                (b13_17 == 0x3) or\
                                (b13_17 == 0x6 and b18_19 == 0x2) or\
                                (b13_17 >> 1 == 0xc):
                                    chiplet_type = "l3"
                        elif (b13_17 == 0x2) or\
                                (b13_17 >> 3 == 0x1) or\
                                (b13_17 >> 3 == 0x2):
                                    chiplet_type = "l2"
                        elif (b13_17 == 0x4) or\
                                (b13_17 == 0x1c and  b18 == 0x0):
                                    chiplet_type = "ncu"

                        eq = (unit >> 7) & 0x7
                        chiplet = (unit >> 5) & 0x1
			thread = (transaction >> 0) & 0x7 # last 3 bits are thread id
                        name = "eq%d:ex%d:%s:t%d" % (eq, chiplet, chiplet_type, thread)
                 elif (unit & 0x178) == 0x8: # MCS
                        chiplet = (((unit >> 9) & 0x1) << 1) | ((unit >> 7) & 0x1)
                        sub_chiplet = (unit >> 2) & 0x1
                        mcs_value = chiplet << 1 | sub_chiplet
#			name = "mcs%x:s%x" % (chiplet, sub_chiplet)
                        name = "mcs%x" % (mcs_value)
                 elif (unit & 0x3f8) == 0x10: # nMMU
                        name = "nmmu"
                 elif (unit & 0x3fc) == 0x90: # INT
                        name = "int"
                 elif (unit & 0x3f8) == 0x120: # TP
                        sub_unit_bits = unit & 0x7
                        if sub_unit_bits == 0x0: # HCA
                            sub_unit = "hca"
                        elif sub_unit_bits == 0x1: # PBA
                            sub_unit = "pba"
                        elif sub_unit_bits == 0x2: # ADU
                            sub_unit = "adu"
                        elif sub_unit_bits == 0x3: # PSI
                            sub_unit = "psi"
                        elif (unit >> 1) & 0x2 == 0x2: # NHTM
                            sub_unit_id = unit & 0x1
                            sub_unit = "nhtm%x" %(sub_unit_id)
                        name = "tp:%s" %(sub_unit)
                 elif ((unit & 0x340) == 0x100) and ((unit & 0xa0) != 0x2) : # NPU and ss = b01 is not valid
                        unit_id = (((unit >> 7) & 0x1) << 1) | ((unit >> 5) & 0x1)
                        if (unit_id > 0):
                            unit_id = unit_id - 1 # 00: NPU0, 10: NPU1, 11: NPU2
                        name = "npu%x" % (unit_id)
                 elif (unit & 0x3fe) == 0x210: # MCD
                        unit_id = unit & 0x1
                        name = "mcd%x" % (unit_id)
                 elif (unit & 0x3f8) == 0x290: # VAS
                        name = "vas"
                 elif (unit & 0x3fc) == 0x308: # NX
                        name = "nx"
                 elif (unit & 0x37c) == 0x300: # CAPP
                        unit_id = (unit >> 7) & 0x1
                        name = "capp%x" %(unit_id)
                 elif (unit & 0x3ff) == 0x3bf: # PB Master
                        name = "pbmaster"
                 elif (unit & 0x3e0) == 0x3a0: # PCI
                        unit_id = (unit >> 3) & 0x3
                        name = "pci%x" %(unit_id)
                 else:
                        name = "unknown"
                else: # POWER8
		 if (unit & 0x80) == 0x0:
			chiplet = (unit >> 3) & 0xf
			thread = (transaction >> 0) & 0x7
			name = "ex%d:t%d" % (chiplet, thread)
		 elif (unit & 0xE) == 0x80:
			chiplet = (unit >> 5) & 0x3
			sub_chiplet = (unit >> 4) & 0x1
			name = "mcs%x:s%x" % (chiplet, sub_chiplet)
		 elif (unit & 0xF8) == 0xA0:
			name = "pci%x" % (unit & 0x6)
		 elif (unit & 0xF8) == 0xB0:
			name = "TP"
		 elif (unit & 0xF8) == 0xB8:
			name = "NX"
		 elif (unit & 0xF8) == 0xF8:
			sub_chiplet = (unit >> 3) & 0x1
			if sub_chiplet:
				name = "MCD"
			else:
				name = "PBmaster"
		 else:
			name = "unknown"

                if (processor_version == "POWER9"):
		   return "g%x:p%x:%s" % (group, chip, name)
                else:
		   return "n%x:p%x:%s" % (node, chip, name)

	def __init__(self, rcmd1, rcmd2, timestamp):
                global counter0,counter1

		fabric_entry.__init__(self, rcmd1, rcmd2)
		if (processor_version == "POWER9"):
			self.ttag =	self.bits(1, 18) << (26 - 22) # bit0..bit17
			self.ttag |=	self.bits(23, 26) # bit0..bit17:bit18..bit21

#			self.addr =	self.bits(27, 42) << (63 - 42) # bit16..bit31
#			self.addr |= 	self.bits(43, 63) # bit16..bit31:bit32..bit52 # split upto bit 63
							  # 64 bit boundary required for bits routine
#			self.addr =	self.addr << (68 - 63)
#			self.addr |=    self.bits(64, 68) # bit16..bit31:bit32..bit52:bit53..bit57

#			self.addr =	self.addr << (22 - 18)
#			self.addr |=	self.bits(19,22)  # bit16..bit31:bit32..bit57:bit58..bit61

			addr1     =	self.bits(27, 42) << (63 - 31) # bit16..bit31
                        addr2     =     ((self.bits(43,63) << (68 - 63)) | self.bits(64,68)) << (63 - 57)
                        addr3     =     self.bits(19,22) << (63 - 61)
                        self.addr =     addr1 | addr2 | addr3

			self.scope =	self.bits(69, 71)
			self.ticket =	self.bits(72, 78)
			self.ttype =	self.bits(79, 85)
			self.tsize =	self.bits(86, 93)
			self.cresp = ""
                        self.port =     self.bits(118,118) # port bit to decide with port#
                        self.counter =  0
		else:
			self.ttag =	self.bits(1, 19)
			self.addr =	self.bits(20, 63)
			self.ticket =	self.bits(64, 69)
			self.ttype =	self.bits(70, 75)
			self.tsize =	self.bits(76, 82)
			self.scope =	self.bits(83, 85)
			self.addr |=	self.bits(86, 91) << (63 - 19) # bit 14:::...:bit19:bit20:..:bit63
			self.source =	self.bits(92, 93)
			self.priority =	self.bits(94, 95)
			self.cresp = ""
                        self.counter =  0

		if (processor_version == "POWER9"): 
	        	p = ports_P9.ports()
                        self.port=p.port_P9(htm_id, self.port, type_rcmd, self.addr)
                        if (htm_id == 0):
                         self.counter = counter0
                        else:
                         self.counter = counter1
                         print('set self.counter for new rcmd to: %d'%(self.counter))
                else:
	        	p = ports.ports()
                        self.port=p.port(self.ttype, self.tsize, self.addr)

		self.timestamp=timestamp
		self.matched = False

	def format(self, statList):
                if processor_version == "POWER9":
                        t = ttypes_P9.ttypes()
                else:
                        t = ttypes.ttypes()
                ttype_decoded = t.lookup(self.ttype, self.tsize)

		if self.port == 0:
			statList[0].addCount(self.scope)
			statList[0].addTtype(self.ttype, self.tsize)
		elif self.port == 1:
			statList[1].addCount(self.scope)
			statList[1].addTtype(self.ttype, self.tsize)
		elif self.port == 2:
			statList[2].addCount(self.scope)
			statList[2].addTtype(self.ttype, self.tsize)
                elif self.port == 3: 
			statList[3].addCount(self.scope)
			statList[3].addTtype(self.ttype, self.tsize)

#		return "%016d : R%d:%s %-15s      tsize=%02x ticket=%02x addr=%013x ttag=%s %s\n" % (self.timestamp, self.port, self.format_scope(self.scope), ttype_decoded, self.tsize, self.ticket, self.addr, self.format_ttag(self.ttag), self.cresp)
#               print self.counter instead of self.timestamp
		return "%016d : R%d:%s %-15s      tsize=%02x ticket=%02x addr=%013x ttag=%s %s\n" % (self.counter, self.port, self.format_scope(self.scope), ttype_decoded, self.tsize, self.ticket, self.addr, self.format_ttag(self.ttag), self.cresp)


class stamp(fabric_entry):
	stamp_record = 0
	stamp_mark = 1
	stamp_complete = 2
	stamp_pause = 3
	stamp_timestamp = 4

	stamp_synchronization = 5 # P9

# POWER8
#record         ACEFF0 yy00000000
#complete       ACEFF1 0000000000
#pause          ACEFF2 0000000000
#mark           ACEFF3 yyyyyyyyyy
#time stamp     ACEFF8 xyyzzzzzzz

# POWER9		CHTM		NHTM
#record         ACEFF0 yy00000000 3FFE tttt tttt t000
#				  ACEF F0yy 0000 0000

#complete       ACEFF1 000zzzzzzz 3FFE tttt tttt t000
#				  ACEF F100 0zzz zzzz

#pause          ACEFF2 000zzzzzzz 3FFE tttt tttt t000
#				  ACEF F200 0zzz zzzz

#mark           ACEFF3 yyyyyyyyyy 3FFE tttt tttt t000
#				  ACEF F3yy yyyy yyyy

#time stamp     ACEFF8 xyyzzzzzzz 3FFE tttt tttt tccc
#				  ACEF F8xy yzzz zzzz

#synchronization
#		ACEFF4 0000000000 3FFE tttt tttt t000
#				  ACEF F400 0000 0000

	def __init__(self, stamp1, stamp2, timestamp):
                global counter0, counter1

		fabric_entry.__init__(self, stamp1, stamp2)

		self.timestamp = timestamp
		log.debug('timestamp before get_sync_time: %d', timestamp)
		if (processor_version=="POWER9"):
			self.timestamp = self.get_sync_time()
		log.debug('timestamp after: %d', self.timestamp)

#		'stamp' type bits are the same on P9.
		tt = self.bits(64, 64+23)
		if tt == 0xACEFF0:
			self.stamp_type = self.stamp_record
		elif tt == 0xACEFF1:
			self.stamp_type = self.stamp_complete
		elif tt == 0xACEFF2:
			self.stamp_type = self.stamp_pause
		elif tt == 0xACEFF3:
			self.stamp_type = self.stamp_mark
		elif tt == 0xACEFF8:
			self.stamp_type = self.stamp_timestamp
			# elapsed instead of imbedded timestamp
			#self.timestamp = self.bits(88, 127)
		elif tt == 0xACEFF4: # In P9
			self.stamp_type = self.stamp_synchronization
		else:
			log.warning('Unknown stamp type 0x%x', tt)
			raise ValueError("Unknown stamp type 0x%x" % tt)
               
                self.elapsed_time = self.bits(100,127)
                log.debug('elapsed time: %d', self.elapsed_time)
#                self.counter = counter

	def get_stamp_type(self):
	 return self.stamp_type

	def print_stamp_type(self):
	 log.info('Stamp type: ')
         if (self.stamp_type == self.stamp_record):
		log.info('Record')
         elif (self.stamp_type == self.stamp_mark):
		log.info('Mark')
	 elif (self.stamp_type == self.stamp_complete):
		log.info('Complete')
	 elif (self.stamp_type == self.stamp_pause):
		log.info('Pause')
	 elif (self.stamp_type == self.stamp_timestamp):
		log.info('Timestamp')
	 elif (self.stamp_type == self.stamp_synchronization):
			log.info('Synchronization')

	def get_sync_time(self):
		# read synchronization timer information if on POWER9
		# sync time info available in all stamp types
		if (processor_version=="POWER9"):
			synctimer_mask = self.bits(16,51)<<12 # LSH by 12 to cancel the lower 12 bits
                        log.debug('sync_time mask: %x', synctimer_mask)
			sync_time = (self.bits(0,63) & synctimer_mask)>>12
                        log.debug('sync_time: %x',sync_time)
			return sync_time

	def format(self, statList):
		if self.stamp_type == self.stamp_record:
			return "%016d : RECORD\n" % (self.timestamp)
		elif self.stamp_type == self.stamp_mark:
			chip_id = self.bits(88,88+2)
			node_id = self.bits(91,91+2)
			unit_id = self.bits(94,94+7)
			marker_info = self.bits(102, 102+11)
			return "%016d : MARK %-21s user_info=0x%x(%d) n%x:p%x %x\n" % (self.timestamp,"", marker_info, marker_info, node_id, chip_id, unit_id)
		elif self.stamp_type == self.stamp_complete:
			log.debug('format stamp_complete. timestamp: %ld', self.timestamp)
			return "%016d : COMPLETE\n" % (self.timestamp)
		elif self.stamp_type == self.stamp_pause:
			return "%016d : PAUSE\n" % (self.timestamp)
		elif self.stamp_type == self.stamp_timestamp:
			return ""
		else:
			log.warning('Unknown stamp type!')
			raise ValueError("Unknown stamp type!")

class fabric_trace:
#	global processor_version

	def __init__(self):
		self.entries = []
		self.missed = 0
		self.missed_list = []
		proc_version()
		if (processor_version == "POWER9"):
#		For additional nhtm
			self.entries2 = []
			self.missed2 = 0
			self.missed_list2 = []

			self.agg_entries = [] # aggregated
			self.agg_missed = 0
			self.agg_missed_list = []
#		self.set_processor_version()
#		processor_version="POWER9" # manual setting to validate for P9
#		print 'processor_version: {}'.format(processor_version)
		        self.stamp_complete_offset = -1 # offset of stamp_complete
		        self.stamp_complete_timestamp = -1 # timestamp of stamp_complete
                        self.run_number = -1 # Entries is appended to only if run_number == 2
                        self.current_offset = 0 # Used to identify stamp_complete offset
                        self.timedelta = 0 # Used to save cresp/ rcmd delta between iterations
                        self.stamp_elapsed_time = 0 # Used to save stamp_elapsed_time between iterations
                        self.current_timestamp = 0 # Used to save cur_ts between iterations

                        self.stamp_complete_offset0 = 0 # nhtm0 stamp_complete_offset
                        self.stamp_complete_time0   = 0 # nhtm0 stamp_complete time
                        self.stamp_complete_offset1 = 0 # nhtm1 stamp_complete_offset
                        self.stamp_complete_time1   = 0 # nhtm1 stamp_complete time

                        self.current_timestamp0 = 0 # cur_ts of nhtm0
                        self.current_timestamp1 = 0 # cur_ts of nhtm1
                        self.nhtm0_stamp_elapsed_time = 0
                        self.nhtm1_stamp_elapsed_time = 0
                        self.nhtm0_cresp_rcmd_delta = 0
                        self.nhtm1_cresp_rcmd_delta = 0
#                       self.counter = 0 # count cycles per JH approach. Currently handling it as a global variable
                        self.ref_timestamp0 = 0
                        self.ref_timestamp1 = 0
                        self.ref_timestamp_offset0 = 0
                        self.ref_timestamp_offset1 = 0

	def get_missed(self):
		return self.missed

	def get_missed2(self):
		if (processor_version == "POWER9"):
			return self.missed2
		else:
			log.warning('unsupported processor version')

	def get_missed_list(self):
		return self.missed_list

	def get_missed2_list(self):
		if (processor_version == "POWER9"):
			return self.missed2_list
		else:
			log.warning('unsupported processor version')

	def get_agg_missed_list(self):
		if (processor_version == "POWER9"):
			return self.agg_missed_list
		else:
			log.warning('unsupported processor version')

	def get_agg_missed(self):
		if (processor_version == "POWER9"):
			return self.agg_missed
		else:
			log.warning('unsupported processor version')

#       Identify if the trace record belongs to nhtm0 or nhtm1
        def find_nhtm(self, offset):
            nhtm_mask = 0x80 # bit 56
            if (offset & nhtm_mask)==0x80:
                return 1 # nhtm1
            else:
                return 0

#	Changing match_trace signature so that it can be used to run through entries, entries2 and agg_entries
	def match_trace(self, record, entries, missed, missed_list):
		maxlen = -500
		found = False
		if len(entries) < 500:
			maxlen = len(entries) * -1
		for x in range(-1, maxlen, -1):
			if entries[x].type == type_rcmd:
				if record.search_key() == entries[x].search_key() and not entries[x].matched:
					if found:
						log.warning('>>>>>>>ERROR: we already found one')
					statlist=[]
					statlist.append(statistics())
					statlist.append(statistics())
					if (processor_version=="POWER9"):
						statlist.append(statistics())
						statlist.append(statistics())

			#		print self.entries[x].format(statlist)
			#		print record.format(statlist)
					entries[x].matched = True
					if (processor_version == "POWER9"):
						t = ttypes_P9.ttypes()
					else:
						t = ttypes.ttypes()
					ttype_decoded = t.lookup(entries[x].ttype, entries[x].tsize)
			                cresp_ttype_decoded = t.cresp_lookup(entries[x].ttype, entries[x].tsize, record.cresp)
                                        
                                        # The cresp for the rcmd (entries[x]) is set to the cresp that was matched.
 					entries[x].add_cresp(cresp_ttype_decoded)
					
					found = True
					
				#	print "MATCH FOUND" + record.search_key() + " " + self.entries[x].search_key()
					break
		if not found:
			garbage_var=0
			missed_list.append(record.format(garbage_var))
			missed += 1

        # This routine is used to set timestamps using the adjust cycle count obtained from stamp_complete
        # of nhtm0 and nhtm1.
	def process_stamp1(self, f, dw1, dw2, entries, cur_timestamp, use_matched): 
		s = stamp(dw1, dw2, cur_timestamp)
                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                  if (htm_id == 0 and adjust_nhtm0 == True) or\
                          (htm_id == 1 and adjust_nhtm1 == True):
                              s.timestamp = s.timestamp + adjust_cycle_count
		  cur_timestamp = s.timestamp
		  log.debug('s.timestamp: %d', s.timestamp)
                  entries.insert(0,s) # Add at the beginning of the list.
#		entries.append(s)
                
		return (s, cur_timestamp)

	def process_stamp(self, f, dw1, dw2, entries, cur_timestamp, use_matched): 
                global counter0, counter1, cycle_adjust_complete

		s = stamp(dw1, dw2, cur_timestamp)
                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                  if (s.stamp_type == s.stamp_complete):
                      return (s, cur_timestamp) # do not insert the stamp_complete
                  if ((htm_id == 0 and adjust_nhtm0 == True) or\
                          (htm_id == 1 and adjust_nhtm1 == True)) and cycle_adjust_complete == False: # cycle adjust just the first time
#                             s.timestamp = s.timestamp + adjust_cycle_count # We do not care about updating the timestamp
                              if (htm_id == 0):
                               counter0 = counter0 + adjust_cycle_count + s.elapsed_time
                              else:
                               counter1 = counter1 + adjust_cycle_count + s.elapsed_time
                              cycle_adjust_complete = True
                  else:                              # If adjust_nhtm0 is True and current record is from nhtm1, or vice versa
                                                     # also if adjust_nhtm0/1 is True, and current record is from nhtm0/1, but cycle 
                                                     # adjustment is done.
                              if (htm_id == 0):
                               counter0 = counter0 + s.elapsed_time
                              else:
                               counter1 = counter1 + s.elapsed_time

#		  cur_timestamp = s.timestamp # do not update timestamp since we will only use the counter value
		  log.debug('s.timestamp: %d', s.timestamp)
                  print('stamp. current timestamp: %ld' %(s.timestamp))
                  if (htm_id == 0):
                   s.counter = counter0 # save the current global counter in the stamp record also.
                  else:
                   s.counter = counter1 # save the current global counter in the stamp record also.

                  entries.insert(0,s) # Add at the beginning of the list.
                
		return (s, cur_timestamp)

	def process_cresp(self, f, dw1, dw2, entries, cur_timestamp, use_matched, missed_list, missed, stamp_elapsed_time, timedelta_prev):
                global counter0, counter1, cycle_adjust_complete

		cresps = []
		timedelta = f.bits(self.timestamp_bit_start, self.timestamp_bit_end)
		log.debug('timedelta of cresp: %ld', timedelta)

                cresp_info_valid = 0

#               cur_timestamp -= timedelta
                if ((htm_id == 0 and adjust_nhtm0 == True) or\
                        (htm_id == 1 and adjust_nhtm1 == True)) and cycle_adjust_complete == False:
                        if (htm_id == 0):
                         counter0 = counter0 + adjust_cycle_count + timedelta;
                        else: 
                         counter1 = counter1 + adjust_cycle_count + timedelta;
                        cycle_adjust_complete = True;
                else:
                        if (htm_id == 0):
                         counter0 = counter0 + timedelta;
                        else:
                         counter1 = counter1 + timedelta;

#		cur_timestamp += timedelta # must use the previous 'time type stamp' to add the delta
		# up to 4 combined responses in a record
		if f.bit(self.cresp_bit_start_1):
			cresp_info_valid = 1

		if cresp_info_valid == 1:
			if (use_matched):
				self.match_trace(cresp(0, f.bits(self.cresp_bit_start_1, self.cresp_bit_end_1), cur_timestamp), entries, missed, missed_list)
			else:
                                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                      entries.insert(0,cresp(0, f.bits(self.cresp_bit_start_1, self.cresp_bit_end_1), cur_timestamp)) # Add at the beginning of the list.

                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                            cresps.insert(0,cresp(0, f.bits(self.cresp_bit_start_1, self.cresp_bit_end_1), cur_timestamp))

		if f.bit(self.cresp_bit_start_2):
			if (use_matched):
				self.match_trace(cresp(0, f.bits(self.cresp_bit_start_2, self.cresp_bit_end_2), cur_timestamp), entries, missed, missed_list)
			else:
                                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                      entries.insert(0,cresp(0, f.bits(self.cresp_bit_start_2, self.cresp_bit_end_2), cur_timestamp)) # Add at the beginning of the list.

                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                            cresps.insert(0,cresp(0, f.bits(self.cresp_bit_start_2, self.cresp_bit_end_2), cur_timestamp))

		if f.bit(self.cresp_bit_start_3):
			if (use_matched):
				self.match_trace(cresp(0, f.bits(self.cresp_bit_start_3, self.cresp_bit_end_3), cur_timestamp), entries, missed, missed_list)
			else:
                                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                      entries.insert(0,cresp(0, f.bits(self.cresp_bit_start_3, self.cresp_bit_end_3), cur_timestamp)) # Add at the beginning of the list.

                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                            cresps.insert(0,cresp(0, f.bits(self.cresp_bit_start_3, self.cresp_bit_end_3), cur_timestamp))

		if f.bit(self.cresp_bit_start_4):
			if (use_matched):
				self.match_trace(cresp(0, f.bits(self.cresp_bit_start_4, self.cresp_bit_end_4), cur_timestamp), entries, missed, missed_list)
			else:
                                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                      entries.insert(0,cresp(0, f.bits(self.cresp_bit_start_4, self.cresp_bit_end_4), cur_timestamp)) # Add at the beginning of the list.


                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                            cresps.insert(0,cresp(0, f.bits(self.cresp_bit_start_4, self.cresp_bit_end_4), cur_timestamp))

		return (cur_timestamp, entries, cresps, timedelta)

#       set the current timestamp based on the timedelta of the previous command (if it was a cresp/rcmd) or the elapsed time of the
#       previous stamp.
	def process_cresp1(self, f, dw1, dw2, entries, cur_timestamp, use_matched, missed_list, missed, stamp_elapsed_time, timedelta_prev):
		cresps = []
		timedelta = f.bits(self.timestamp_bit_start, self.timestamp_bit_end)
		log.debug('timedelta of cresp: %ld', timedelta)

                cresp_info_valid = 0

                if (stamp_elapsed_time == -1) and (timedelta_prev > -1):
                    cur_timestamp -= timedelta_prev # If the previous processed entry was a rcmd/ cresp
                elif (stamp_elapsed_time > -1) and (timedelta_prev == -1):
                    cur_timestamp -= stamp_elapsed_time # If the previous processed entry was a stamp
                else:
                    if (stamp_elapsed_time > -1) and (timedelta_prev > -1):
                        log.info('Error: Both stamp_elapsed_time and timedelta_rcmd_cresp are set.. Skipping cresp record')
                        exit(-1)
                    if (stamp_elapsed_time == -1) and (timedelta_prev == -1):
                        log.info('Error: Neither stamp_elapsed_time nor timedelta_rcmd_cresp is set.. Skipping cresp record')
                        exit(-1)

#		cur_timestamp += timedelta # must use the previous 'time type stamp' to add the delta
		# up to 4 combined responses in a record
		if f.bit(self.cresp_bit_start_1):
			cresp_info_valid = 1

		if cresp_info_valid == 1:
			if (use_matched):
				self.match_trace(cresp(0, f.bits(self.cresp_bit_start_1, self.cresp_bit_end_1), cur_timestamp), entries, missed, missed_list)
			else:
                                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                      entries.insert(0,cresp(0, f.bits(self.cresp_bit_start_1, self.cresp_bit_end_1), cur_timestamp)) # Add at the beginning of the list.

                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                            cresps.insert(0,cresp(0, f.bits(self.cresp_bit_start_1, self.cresp_bit_end_1), cur_timestamp))

		if f.bit(self.cresp_bit_start_2):
			if (use_matched):
				self.match_trace(cresp(0, f.bits(self.cresp_bit_start_2, self.cresp_bit_end_2), cur_timestamp), entries, missed, missed_list)
			else:
                                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                      entries.insert(0,cresp(0, f.bits(self.cresp_bit_start_2, self.cresp_bit_end_2), cur_timestamp)) # Add at the beginning of the list.

                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                            cresps.insert(0,cresp(0, f.bits(self.cresp_bit_start_2, self.cresp_bit_end_2), cur_timestamp))

		if f.bit(self.cresp_bit_start_3):
			if (use_matched):
				self.match_trace(cresp(0, f.bits(self.cresp_bit_start_3, self.cresp_bit_end_3), cur_timestamp), entries, missed, missed_list)
			else:
                                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                      entries.insert(0,cresp(0, f.bits(self.cresp_bit_start_3, self.cresp_bit_end_3), cur_timestamp)) # Add at the beginning of the list.

                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                            cresps.insert(0,cresp(0, f.bits(self.cresp_bit_start_3, self.cresp_bit_end_3), cur_timestamp))

		if f.bit(self.cresp_bit_start_4):
			if (use_matched):
				self.match_trace(cresp(0, f.bits(self.cresp_bit_start_4, self.cresp_bit_end_4), cur_timestamp), entries, missed, missed_list)
			else:
                                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                      entries.insert(0,cresp(0, f.bits(self.cresp_bit_start_4, self.cresp_bit_end_4), cur_timestamp)) # Add at the beginning of the list.

                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                            cresps.insert(0,cresp(0, f.bits(self.cresp_bit_start_4, self.cresp_bit_end_4), cur_timestamp))

		return (cur_timestamp, entries, cresps, timedelta)

        def set_special_ports(self, rcmd):
                if processor_version == "POWER9":
                        t = ttypes_P9.ttypes()
                else:
                        t = ttypes.ttypes()
                log.debug('ttype: %x, tsize: %x',rcmd.ttype, rcmd.tsize)
#                print('Matching ttype: %x, tsize: %x' %(self.ttype, self.tsize))
                ttype_decoded = t.lookup(rcmd.ttype, rcmd.tsize)
            
#               Set the port# based on the specific mnemonics
                special_0 = ['pMisc', 'hca_req.ref_updt', 'link_chk.data_chk'\
                        ,'link_chk.abort_op', 'asb_notify', 'msgsnd'\
                        ,'chgrate', 'rpt_hang.check', 'rpt_hang.poll'\
                        ,'rpt_hang.data', 'pbop'];

                special_2 = ['tlbi_t', 'slbi_t'];
            
                special_01 = ['tlbi_set'\
                             ,'slbi_set'\
                             ,'cop_req', 'sync'\
                             ,'eieio'];
            
                # mnemonics in special_tsize determine ports by tsize
                special_tsize = ['tlbi_op1', 'tlbi_op2', 'slbi_op1'\
                                ,'slbi_op2'];
            
                # The following mnemonics have their port#
                # decided by the thread id. Remove them from
                # special_01 above.
                special_thrd_id = ['tlbi_chk', 'ptesync'];
  
                special_3 = ['intrp'];
            
                special_match = False
                if (special_match == False):
                 for  i in range(0,len(special_0)):
                        if special_0[i] in ttype_decoded:
                          rcmd.port = 0
                          special_match = True
                          break
                if (special_match == False):
                 for  i in range(0,len(special_2)):
                        if special_2[i] in ttype_decoded:
                          rcmd.port = 2
                          special_match = True
                          break
                if (special_match == False):
                 for  i in range(0,len(special_3)):
                        if special_3[i] in ttype_decoded:
                          rcmd.port = 3
                          special_match = True
                          break
                if (special_match == False):
                 for i in range(0,len(special_thrd_id)):
                       if special_thrd_id[i] in ttype_decoded:
                           if rcmd.ttag & 0x1 == 0x1: # last bit is the thread id
                              rcmd.port = 1 # thread id is odd
                           else:
                              rcmd.port = 0
                           special_match = True
                           break
                if (special_match == False):
                 for i in range(0,len(special_tsize)):
                       if special_tsize[i] in ttype_decoded:
                           if ((rcmd.tsize >> 1) & 0x1) == 0x1: # self.tsize = 01pS SSSx. Check the last 'S'
                               rcmd.port = 1;
                           else:
                               rcmd.port = 0;
                           special_match = True
                           break
                if (special_match == False):
                 for  i in range(0,len(special_01)):
                        if special_01[i] in ttype_decoded:
                          if rcmd.port == 2:
                            rcmd.port = 0
                          elif rcmd.port == 3:
                            rcmd.port = 1
                          special_match = True
                          break

	def process_rcmd(self, f, dw1, dw2, entries, cur_timestamp, use_matched, stamp_elapsed_time, timedelta_prev):
                global counter0, counter1, cycle_adjust_complete

		cresps = []
		timedelta = f.bits(self.timestamp_bit_start, self.timestamp_bit_end)
		log.debug('timedelta of rcmd: %ld', timedelta)

		log.debug('timestamp parsed in rcmd: %ld', cur_timestamp)

                if ((htm_id == 0 and adjust_nhtm0 == True) or\
                        (htm_id == 1 and adjust_nhtm1 == True)) and cycle_adjust_complete == False:
                        if (htm_id == 0):
                         counter0 = counter0 + adjust_cycle_count + timedelta;
                        else:
                         counter1 = counter1 + adjust_cycle_count + timedelta;
                        cycle_adjust_complete = True;
                else:
                        if (htm_id == 0):
                         counter0 = counter0 + timedelta;
                        else:
                         counter1 = counter1 + timedelta;

		rcmds = rcmd(dw1, dw2, cur_timestamp)
                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                    entries.insert(0, rcmds)
		if f.bit(self.cresp_in_rcmd_bit_start):
			log.debug('cresp found in rcmd')
			timedelta = f.bits(self.timestamp_bit_start, self.timestamp_bit_end)
			if (use_matched):
				self.match_trace(cresp(4, f.bits(self.cresp_in_rcmd_bit_start, 127), cur_timestamp), self.entries, self.missed, self.missed_list)
			else:
                            if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                entries.insert(0,cresp(4, f.bits(self.cresp_in_rcmd_bit_start, 127), cur_timestamp))

                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                            cresps.insert(0,cresp(4, f.bits(self.cresp_in_rcmd_bit_start, 127), cur_timestamp))
		
		return (cur_timestamp, entries, cresps, rcmds, timedelta)

#       Routine used to set the timestamp within the rcmd based on the elapsed time of the previous stamp processed, or
#       the timedelta in case the previous command was a rcmd/cresp.
	def process_rcmd1(self, f, dw1, dw2, entries, cur_timestamp, use_matched, stamp_elapsed_time, timedelta_prev):
		cresps = []
		timedelta = f.bits(self.timestamp_bit_start, self.timestamp_bit_end)
		log.debug('timedelta of rcmd: %ld', timedelta)
                if (stamp_elapsed_time == -1) and (timedelta_prev > -1):
                    cur_timestamp -= timedelta_prev # If the previous processed entry was a rcmd/ cresp
                elif (stamp_elapsed_time > -1) and (timedelta_prev == -1):
                    cur_timestamp -= stamp_elapsed_time # If the previous processed entry was a stamp
                else:
                    if (stamp_elapsed_time > -1) and (timedelta_prev > -1):
                        log.info('Error: Both stamp_elapsed_time and timedelta_rcmd_cresp are set.. Skipping rcmd record')
                        exit(-1)
                    if (stamp_elapsed_time == -1) and (timedelta_prev == -1):
                        log.info('Error: Neither stamp_elapsed_time nor timedelta_rcmd_cresp is set.. Skipping rcmd record')
                        exit(-1)

		log.debug('timestamp parsed in rcmd: %ld', cur_timestamp)

		rcmds = rcmd(dw1, dw2, cur_timestamp)
                if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                    print('current timedelta of rcmd: %ld, timestamp parsed: %ld' %(timedelta, cur_timestamp))
                    entries.insert(0, rcmds)
		if f.bit(self.cresp_in_rcmd_bit_start):
			log.debug('cresp found in rcmd')
			timedelta = f.bits(self.timestamp_bit_start, self.timestamp_bit_end)
			if (use_matched):
				self.match_trace(cresp(4, f.bits(self.cresp_in_rcmd_bit_start, 127), cur_timestamp), self.entries, self.missed, self.missed_list)
			else:
#			entries.append(cresp(0, f.bits(cresp_in_rcmd_bit_start, 127), cur_timestamp))
                            if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
                                entries.insert(0,cresp(4, f.bits(self.cresp_in_rcmd_bit_start, 127), cur_timestamp))

#			cresps.append(cresp(0, f2.bits(cresp_in_rcmd_bit_start, 127), cur_timestamp2), self.entries, self.missed_list, self.missed)
                        if (self.run_number == 2): # Only if we have a stamp_complete, an entry makes sense
#                           cresps.insert(0,cresp(0, f2.bits(cresp_in_rcmd_bit_start, 127), cur_timestamp2))
                            cresps.insert(0,cresp(4, f.bits(self.cresp_in_rcmd_bit_start, 127), cur_timestamp))
		
#		return (cur_timestamp, entries, cresps, rcmds)
		return (cur_timestamp, entries, cresps, rcmds, timedelta)

        def parse_and_fill(self, buf, length, use_matched, htm_id, iteration):
         cresp_info_valid = 0

         format = '>QQ'
         size = struct.calcsize(format)

         if not self.entries:
                cur_timestamp=0
         else:
                cur_timestamp=self.entries[-1].timestamp
	

         if (processor_version == "POWER9"):
                if not self.entries2:
                        cur_timestamp2 = 0
                else:
                        cur_timestamp2=self.entries2[-1].timestamp

	 log.debug('At entry: size: %d, cur_timestamp: %ld, cur_timestamp2: %ld', size, cur_timestamp, cur_timestamp2)
	 
         if (processor_version == "POWER9"):
                self.cresp_bit_start_1 = 2 # cresp_info_valid set in bit 2
                self.cresp_bit_snoop_1 = 22
                self.cresp_bit_end_1   = 31
                self.cresp_bit_start_2 = 32
                self.cresp_bit_snoop_2 = 52
                self.cresp_bit_end_2   = 61
                self.cresp_bit_start_3 = 64
                self.cresp_bit_snoop_3 = 84
                self.cresp_bit_end_3   = 93
                self.cresp_bit_start_4 = 98
                self.cresp_bit_snoop_4 = 118
                self.cresp_bit_end_4   = 127
                self.cresp_in_rcmd_bit_start = 98
                self.timestamp_bit_start = 94
                self.timestamp_bit_end = 97
         else:
                self.cresp_bit_start_1 = 8
                self.cresp_bit_end_1   = 31
                self.cresp_bit_start_2 = 40
                self.cresp_bit_end_2   = 63
                self.cresp_bit_start_3 = 72
                self.cresp_bit_end_3   = 95
                self.cresp_bit_start_4 = 104
                self.cresp_bit_end_4   = 127
                self.cresp_in_rcmd_bit_start = 104
                self.timestamp_bit_start = 96
                self.timestamp_bit_end = 103

	 previous_type = notype
	 current_type  = notype

	 if htm_id == HTM0:
		entries = self.entries
                cur_ts = cur_timestamp
	 else:
		entries = self.entries2
                cur_ts = cur_timestamp2

         print('parse_and_fill: starting cur_ts: %d' % cur_ts)

         if (iteration >= 1): # Realign the values from the previous iteration
            cur_ts = self.cur_timestamp
            stamp_elapsed_time = self.stamp_elapsed_time
            timedelta_in = self.timedelta

	# Now that the complete stamp is found, iterate again from the beginning until the complete stamp
     #    while (length > offset):
         bytes_left = length
        
         print('length: {}'.format(length))
         curr_offset = length - size
#         curr_offset = length # For the stamp_complete record
         print('curr_offset: {}, size: {}'.format(curr_offset, size))

         timedelta_in = -1 
         stamp_complete_processed = False

         while(bytes_left > 0): # We need to always unroll the trace backwards
#          print('range to unpack: curr_offset: {}, curr_offset+size: {}'.format(curr_offset, curr_offset+size))
          (dw1, dw2) = struct.unpack(format, buf[curr_offset:curr_offset+size])
          f = fabric_entry(dw1, dw2)

          print('bytes_left %d, curr_offset %d' % (bytes_left, curr_offset))
	  try:
               if f.type == type_stamp:
                  log.debug('stamp found')
		 # how to identify whether we are sending to entries or entries2?
                  (s, cur_ts) = self.process_stamp(f, dw1, dw2, entries, cur_ts, use_matched)
                  print('stamp type: %d' % s.stamp_type)
                  if s.stamp_type == s.stamp_complete:
		       log.debug('stamp_complete found')
	#	       self.stamp_complete_offset = offset # Where did we find stamp_complete?
#		       self.stamp_complete_timestamp = cur_ts # Stamp complete was set in parse_single
                       stamp_complete_processed = True
	#	       log.debug('stamp_complete offset: %ld', self.stamp_complete_offset)
                       print('stamp_complete found')

                  print('stamp found')
		  ref_time  = cur_ts
                  stamp_elapsed_time = s.elapsed_time
                  timedelta_in = -1 # This is to ensure that the stamp_elapsed_time is used to calculate the new time for the rcmd/cresp
		  log.debug('stamp 1: %ld', cur_ts)
		  stamp_processed = True

	       elif f.type == type_cresp:
                log.debug('cresp found')
		if iteration == 0 and stamp_complete_processed == False: # Stamp_complete must be the first record to be processed
								# For subsequent iterations, we may have a starting cresp / rcmd
			log.info('A stamp_complete is required before processing cresps.. Skipping cresp.')
#			offset += size
                        bytes_left -= size
                        curr_offset -= size
			continue 
		# use the prev_ref_time until it is again replaced
		# For subsequent (after the first) iterations, if stamp isn't the first record (prev_ref_time=0), we must use the
		# cur_timestamp from the previous iteration (last entry in the entries array)
                if (iteration == 0 and stamp_complete_processed == True) or\
                        (iteration > 0 and ref_time != 0):
		 cur_ts = ref_time

		 log.debug('cresp in: %ld', cur_ts)
#		(cur_ts, entries, cresps) = self.process_cresp(f, dw1, dw2, entries, cur_ts, use_matched, missed_list, missed)
		 (cur_ts, entries, cresps, timedelta) = self.process_cresp(f, dw1, dw2, entries, cur_ts, use_matched, missed_list, missed, stamp_elapsed_time, timedelta_in)
		 log.debug('cresp out: %ld', cur_timestamp)
                 stamp_elapsed_time = -1 # This is to ensure that the next cresp/rcmd is not offset again with the same stamp elapsed time
                 timedelta_in = timedelta # for the next cresp/rcmd
                 print('cresp found')

	       else:  # rcmd
                log.debug('rcmd found')
		if iteration == 0 and stamp_processed == False: # At least one stamp record must be processed, just the first time
			log.debug('First record is rcmd. Expected stamp.. skipping')
			offset += size
			continue 
		# use the prev_ref_time until it is again replaced
		# For subsequent (after the first) iterations, if stamp isn't the first record (prev_ref_time=0), we must use the
		# cur_timestamp from the previous iteration (last entry in the entries array)
		if (iteration == 0 and stamp_complete_processed == True) or\
                        (iteration > 0 and ref_time != 0):
		 cur_ts = ref_time

		 log.debug('rcmd in: %ld', cur_ts)
#		(cur_ts, entries, cresps, rcmds) = self.process_rcmd(f, dw1, dw2, entries, cur_ts, use_matched)
		 (cur_ts, entries, cresps, rcmds, timedelta) = self.process_rcmd(f, dw1, dw2, entries, cur_ts, use_matched, stamp_elapsed_time, timedelta_in)
		 log.debug('rcmd out: %ld', cur_ts)
                 stamp_elapsed_time = -1 # This is to ensure that the next cresp/rcmd is not offset again with the same stamp elapsed time
                 timedelta_in = timedelta # for the next cresp/rcmd
#                print('rcmd found')
		
          except ValueError:
               #need to put back out there
	       log.warning('BAD RECORD 0x%016x 0x%016x', dw1, dw2)
               #return False
	  log.debug('curr_offset: %ld', curr_offset)
          curr_offset -= size
          bytes_left -= size

#        Save the latest values to be used in the next iteration
         self.cur_timestamp = cur_ts
         self.timedelta = timedelta
         self.stamp_elapsed_time = stamp_elapsed_time

	 return True

        def set_bits(self): # P8
                self.cresp_bit_start_1 = 8
                self.cresp_bit_end_1   = 31
                self.cresp_bit_start_2 = 40
                self.cresp_bit_end_2   = 63
                self.cresp_bit_start_3 = 72
                self.cresp_bit_end_3   = 95
                self.cresp_bit_start_4 = 104
                self.cresp_bit_end_4   = 127
                self.cresp_in_rcmd_bit_start = 104
                self.timestamp_bit_start = 96
                self.timestamp_bit_end = 103

        def set_bits_P9(self):
                self.cresp_bit_start_1 = 2 # cresp_info_valid set in bit 2
                self.cresp_bit_snoop_1 = 22
                self.cresp_bit_end_1   = 31
                self.cresp_bit_start_2 = 32
                self.cresp_bit_snoop_2 = 52
                self.cresp_bit_end_2   = 61
                self.cresp_bit_start_3 = 64
                self.cresp_bit_snoop_3 = 84
                self.cresp_bit_end_3   = 93
                self.cresp_bit_start_4 = 98
                self.cresp_bit_snoop_4 = 118
                self.cresp_bit_end_4   = 127
                self.cresp_in_rcmd_bit_start = 98
                self.timestamp_bit_start = 94
                self.timestamp_bit_end = 97

#       Fill trace entries per nhtm separately.
        def fill_trace(self, buf, length, use_matched, iteration, htm_ind):
         cresp_info_valid = 0
         format = '>QQ'
         size = struct.calcsize(format)

         if (processor_version == "POWER9"):
                self.set_bits_P9()
         else:
                self.set_bits()

         if (iteration >= 1): # Realign the values from the previous iteration
            if (htm_ind == 0): # nhtm0
              cur_ts0 = self.current_timestamp0
              nhtm0_stamp_elapsed_time = self.nhtm0_stamp_elapsed_time
              cresp_rcmd_delta0 = self.nhtm0_cresp_rcmd_delta
            else:  # nhtm1
              cur_ts1 = self.current_timestamp1
              nhtm1_stamp_elapsed_time = self.nhtm1_stamp_elapsed_time
              cresp_rcmd_delta1 = self.nhtm1_cresp_rcmd_delta
         else:
            if (htm_ind == 0): # nhtm0
             cur_ts0 = 0
             nhtm0_stamp_elapsed_time = 0
             cresp_rcmd_delta0 = 0
            else: 
             cur_ts1 = 0
             nhtm1_stamp_elapsed_time = 0
             cresp_rcmd_delta1 = 0

         bytes_left = length
         curr_offset = length - size

         if (htm_ind == 0 or htm_ind == -1): # either nhtm0 (for separate parse case) or aggregate trace parsing 
             entries = self.entries
         else: # htm_ind = 1. nhtm 
             entries = self.entries2

         while(bytes_left > 0): # We need to always unroll the trace backwards
          (dw1, dw2) = struct.unpack(format, buf[curr_offset:curr_offset+size])
          f = fabric_entry(dw1, dw2)

	  try:
               if (htm_ind == 0):
                   nhtm0 = True
                   nhtm1 = False
                   if ((self.current_offset+curr_offset) > self.stamp_complete_offset0): # current record is 'after' stamp_complete of nhtm0
                      curr_offset -= size
                      bytes_left -= size
                      continue
               else:
                   nhtm1 = True
                   nhtm0 = False
                   if ((self.current_offset+curr_offset) > self.stamp_complete_offset1): # current record is 'after' stamp_complete of nhtm1
                      curr_offset -= size
                      bytes_left -= size
                      continue

               if f.type == type_stamp:
                  log.debug('stamp found')
                  if nhtm0:
                      cur_ts = cur_ts0
                  else:
                      cur_ts = cur_ts1

                  (s, cur_ts) = self.process_stamp(f, dw1, dw2, entries, cur_ts, use_matched)
                  if s.stamp_type == s.stamp_complete:
		       log.debug('stamp_complete found')

                  if nhtm0:
		    nhtm0_ref_time  = cur_ts
                    cur_ts0 = cur_ts
                    nhtm0_stamp_elapsed_time = s.elapsed_time
                    cresp_rcmd_delta0 = -1 # This is to ensure that the stamp_elapsed_time is used to calculate the new time for the rcmd/cresp
                  else:
		    nhtm1_ref_time  = cur_ts
                    cur_ts1 = cur_ts
                    nhtm1_stamp_elapsed_time = s.elapsed_time
                    cresp_rcmd_delta1 = -1 # This is to ensure that the stamp_elapsed_time is used to calculate the new time for the rcmd/cresp
		  log.debug('stamp 1: %ld', cur_ts)
		  stamp_processed = True # whats the use?


	       elif f.type == type_cresp:
                log.debug('cresp found')
                
                if nhtm0:
                    stamp_elapsed_time = nhtm0_stamp_elapsed_time
                    cur_ts = cur_ts0
                    if nhtm0_stamp_elapsed_time > -1: # previous entry was a stamp
                      timedelta_in = -1 
                    else: # previous entry was a  rcmd/cresp
                      timedelta_in = cresp_rcmd_delta0
                else:
                    stamp_elapsed_time = nhtm1_stamp_elapsed_time
                    cur_ts = cur_ts1
                    if nhtm1_stamp_elapsed_time > -1: # previous entry was a stamp
                      timedelta_in = -1 
                    else: # previous entry was a  rcmd/cresp
                      timedelta_in = cresp_rcmd_delta1

		log.debug('cresp in: %ld', cur_ts)
		(cur_ts, entries, cresps, timedelta) = self.process_cresp(f, dw1, dw2, entries, cur_ts, use_matched, missed_list, missed, stamp_elapsed_time, timedelta_in)
		log.debug('cresp out: %ld', cur_timestamp)
                if nhtm0:
                    cur_ts0 = cur_ts
                    nhtm0_stamp_elapsed_time = -1 # This is to ensure that the next cresp/rcmd is not offset again with the same stamp elapsed time
                    cresp_rcmd_delta0 = timedelta # for the next cresp/rcmd
                else:
                    cur_ts1 = cur_ts
                    nhtm1_stamp_elapsed_time = -1 # This is to ensure that the next cresp/rcmd is not offset again with the same stamp elapsed time
                    cresp_rcmd_delta1 = timedelta # for the next cresp/rcmd

	       else:  # rcmd
                log.debug('rcmd found')
                if nhtm0:
                    stamp_elapsed_time = nhtm0_stamp_elapsed_time
                    cur_ts = cur_ts0
                    if nhtm0_stamp_elapsed_time > -1: # previous entry was a stamp
                      timedelta_in = -1 
                    else: # previous entry was a  rcmd/cresp
                      timedelta_in = cresp_rcmd_delta0
                else:
                    stamp_elapsed_time = nhtm1_stamp_elapsed_time
                    cur_ts = cur_ts1
                    if nhtm1_stamp_elapsed_time > -1: # previous entry was a stamp
                      timedelta_in = -1 
                    else: # previous entry was a  rcmd/cresp
                      timedelta_in = cresp_rcmd_delta1

		log.debug('rcmd in: %ld', cur_ts)
		(cur_ts, entries, cresps, rcmds, timedelta) = self.process_rcmd(f, dw1, dw2, entries, cur_ts, use_matched, stamp_elapsed_time, timedelta_in)
		log.debug('rcmd out: %ld', cur_ts)
                if nhtm0:
                    cur_ts0 = cur_ts
                    nhtm0_stamp_elapsed_time = -1 # This is to ensure that the next cresp/rcmd is not offset again with the same stamp elapsed time
                    cresp_rcmd_delta0 = timedelta # for the next cresp/rcmd
                else:
                    cur_ts1 = cur_ts
                    nhtm1_stamp_elapsed_time = -1 # This is to ensure that the next cresp/rcmd is not offset again with the same stamp elapsed time
                    cresp_rcmd_delta1 = timedelta # for the next cresp/rcmd
		
          except ValueError:
               #need to put back out there
	       log.warning('BAD RECORD 0x%016x 0x%016x', dw1, dw2)
               #return False
	  log.debug('curr_offset: %ld', curr_offset)
          curr_offset -= size
          bytes_left -= size

#        Save the latest values to be used in the next iteration
         if htm_ind == 0:
           self.current_timestamp0 = cur_ts0
           self.nhtm0_stamp_elapsed_time = nhtm0_stamp_elapsed_time
           self.nhtm0_cresp_rcmd_delta = cresp_rcmd_delta0
         else:
           self.current_timestamp1 = cur_ts1
           self.nhtm1_stamp_elapsed_time = nhtm1_stamp_elapsed_time
           self.nhtm1_cresp_rcmd_delta = cresp_rcmd_delta1

	 return True
#       Fill complete trace
        def fill_trace_all(self, buf, length, use_matched, iteration):
         cresp_info_valid = 0
         format = '>QQ'
         size = struct.calcsize(format)

         if (processor_version == "POWER9"):
                self.set_bits_P9()
         else:
                self.set_bits()

         global adjust_cycle_count, adjust_nhtm0, adjust_nhtm1, counter0, counter1

         # cycle adjustments in case nhtm0 and nhtm1 do not have the same 'stamp_complete' time
        # if self.stamp_complete_time0 > self.stamp_complete_time1:
        #     adjust_cycle_count = self.stamp_complete_time0 - self.stamp_complete_time1
        #     adjust_nhtm1 = True
        # elif self.stamp_complete_time1 > self.stamp_complete_time0:
        #     adjust_cycle_count = self.stamp_complete_time1 - self.stamp_complete_time0
        #     adjust_nhtm0 = True
        # Commented the above section since we want to do cycle adjustments based on the last found stamp (before stamp_complete)
         if self.ref_timestamp0 > self.ref_timestamp1:
              adjust_cycle_count = self.ref_timestamp0 - self.ref_timestamp1
              adjust_nhtm1 = True
              log.debug('debug: adjust_nhtm1 is True. adjust_cycle_count: %d'%(adjust_cycle_count))
         elif self.ref_timestamp1 > self.ref_timestamp0:
              adjust_cycle_count = self.ref_timestamp1 - self.ref_timestamp0
              adjust_nhtm0 = True
              log.debug('debug: adjust_nhtm0 is True. adjust_cycle_count: %d'%(adjust_cycle_count))

         if (iteration >= 1): # Realign the values from the previous iteration
            cur_ts0 = self.current_timestamp0
            cur_ts1 = self.current_timestamp1
            nhtm0_stamp_elapsed_time = self.nhtm0_stamp_elapsed_time
            nhtm1_stamp_elapsed_time = self.nhtm1_stamp_elapsed_time
            cresp_rcmd_delta0 = self.nhtm0_cresp_rcmd_delta
            cresp_rcmd_delta1 = self.nhtm1_cresp_rcmd_delta
            rcmd_0_previous_port = self.rcmd_0_previous_port
            rcmd_1_previous_port = self.rcmd_1_previous_port
         else:
            cur_ts0 = 0
            cur_ts1 = 0
            nhtm0_stamp_elapsed_time = 0
            nhtm1_stamp_elapsed_time = 0
            cresp_rcmd_delta0 = 0
            cresp_rcmd_delta1 = 0
            rcmd_0_previous_port = -1
            rcmd_1_previous_port = -1

         bytes_left = length
         curr_offset = length - size

         entries = self.entries
         
         global htm_id # declaring it here since we set it in this routine

         while(bytes_left > 0): # We need to always unroll the trace backwards
          (dw1, dw2) = struct.unpack(format, buf[curr_offset:curr_offset+size])
          f = fabric_entry(dw1, dw2)

	  try:
               if (self.find_nhtm(self.current_offset+curr_offset)==0): # self.current_offset points to the start of the 1M chunk
                   nhtm0 = True
                   nhtm1 = False
                   htm_id = 0
                   log.debug('debug: set htm_id to 0')
                   if ((self.current_offset+curr_offset) > self.stamp_complete_offset0): # current record is 'after' stamp_complete of nhtm0
                      curr_offset -= size
                      bytes_left -= size
                      continue
               else:
                   nhtm1 = True
                   nhtm0 = False
                   htm_id = 1
                   log.debug('debug: set htm_id to 1')
                   if ((self.current_offset+curr_offset) > self.stamp_complete_offset1): # current record is 'after' stamp_complete of nhtm1
                      curr_offset -= size
                      bytes_left -= size
                      continue

               log.debug('current offset: %d'%(self.current_offset+curr_offset))

               if f.type == type_stamp:
                  log.debug('stamp found')
                  if nhtm0:
                      cur_ts = cur_ts0
                  else:
                      cur_ts = cur_ts1

                  (s, cur_ts) = self.process_stamp(f, dw1, dw2, entries, cur_ts, use_matched)
                  if s.stamp_type == s.stamp_complete:
		       log.debug('stamp_complete found')

                  if nhtm0:
		    nhtm0_ref_time  = cur_ts
                    cur_ts0 = cur_ts
#                    nhtm0_stamp_elapsed_time = s.elapsed_time
#                    cresp_rcmd_delta0 = -1 # This is to ensure that the stamp_elapsed_time is used to calculate the new time for the rcmd/cresp
                  else:
		    nhtm1_ref_time  = cur_ts
                    cur_ts1 = cur_ts
#                    nhtm1_stamp_elapsed_time = s.elapsed_time
#                    cresp_rcmd_delta1 = -1 # This is to ensure that the stamp_elapsed_time is used to calculate the new time for the rcmd/cresp
		  log.debug('stamp 1: %ld', cur_ts)
		  stamp_processed = True # whats the use?

	       elif f.type == type_cresp:
                log.debug('cresp found')
                if nhtm0:
                    cur_ts = cur_ts0
                else:
                    cur_ts = cur_ts1
		log.debug('cresp in: %ld', cur_ts)
		(cur_ts, entries, cresps, timedelta) = self.process_cresp(f, dw1, dw2, entries, cur_ts, use_matched, self.missed_list, self.missed, 0, 0)
		log.debug('cresp out: %ld', cur_ts)
                if nhtm0:
                    cur_ts0 = cur_ts
                    cresp_0 = True                # cresp in nhtm0 trace
                else:
                    cur_ts1 = cur_ts
                    cresp_1 = True                # cresp in nhtm1 trace

	       else:  # rcmd
                log.debug('rcmd found')
                if nhtm0:
                    cur_ts = cur_ts0
                else:
                    cur_ts = cur_ts1

		log.debug('rcmd in: %ld', cur_ts)
		(cur_ts, entries, cresps, rcmds, timedelta) = self.process_rcmd(f, dw1, dw2, entries, cur_ts, use_matched, 0, 0)

                self.set_special_ports(rcmds) # this should set the special ports. Setting it here, so that the cycle adjustment below
                # can happen based on the modified special port if applicable.

                rcmd_current_port = rcmds.port
                log.debug('rcmd: current_port: %d'%(rcmds.port))
                if (htm_id == 0):
                 log.debug('rcmd: previous_htm0_port: %d'%(rcmd_0_previous_port))
                else:
                 log.debug('rcmd: previous_htm1_port : %d'%(rcmd_1_previous_port))
                if nhtm0: # current rcmd from nhtm0
                    if rcmd_current_port != rcmd_0_previous_port: # There is a transition
                        if rcmd_0_previous_port == 0: # Transition from 0 to 2
                         # modify timestamp for previous rcmd. Add +1
                           log.debug('adjusted counter0 for transition from port 0 to 2')
                         # cur_ts = cur_ts + 1
                           entries[0].counter = entries[0].counter + 1
                        elif rcmd_0_previous_port == 2: # from 2 to 0. Add -1. Explicit check since, the first time, previous_port is -1.
                           log.debug('adjusted counter0 for transition from port 2 to 0')
                         # cur_ts = cur_ts - 1
                           entries[0].counter = entries[0].counter - 1

                        counter0 = entries[0].counter # update the global counter
                else:
                    if rcmd_current_port != rcmd_1_previous_port: # There is a transition
                        if rcmd_1_previous_port == 1: # Transition from 1 to 3
                         # modify timestamp for previous rcmd. Add +1
                           log.debug('adjusted counter1 for transition from port 1 to 3')
                         # cur_ts = cur_ts + 1
                           log.debug('rcmd: 1-3 previous counter: %d'%(entries[0].counter))
                           entries[0].counter = entries[0].counter + 1
                           log.debug('rcmd: 1-3 modified counter: %d'%(entries[0].counter))
                        elif rcmd_1_previous_port == 3: # from 3 to 1. Add -1. First time, previous_port is -1.
                           log.debug('adjusted counter1 for transition from port 3 to 1')
                         # cur_ts = cur_ts - 1 
                           log.debug('rcmd: 3-1 previous counter: %d'%(entries[0].counter))
                           entries[0].counter = entries[0].counter - 1
                           log.debug('rcmd: 3-1 modified counter: %d'%(entries[0].counter))

                        counter1 = entries[0].counter # update the global counter

		log.debug('rcmd out: %ld', cur_ts)
                if nhtm0:
                    cur_ts0 = cur_ts
#                    nhtm0_stamp_elapsed_time = -1 # This is to ensure that the next cresp/rcmd is not offset again with the same stamp elapsed time
#                    cresp_rcmd_delta0 = timedelta # for the next cresp/rcmd
                    rcmd_0 = True                 # rcmd in nhtm0 trace
                    rcmd_0_previous_port = rcmds.port      # save the rcmd port# for comparison on next rcmd
                else:
                    cur_ts1 = cur_ts
#                    nhtm1_stamp_elapsed_time = -1 # This is to ensure that the next cresp/rcmd is not offset again with the same stamp elapsed time
#                    cresp_rcmd_delta1 = timedelta # for the next cresp/rcmd
                    rcmd_1 = True                 # rcmd in nhtm1 trace
                    rcmd_1_previous_port = rcmds.port      # save the rcmd port# for comparison on next rcmd
		
          except ValueError:
               #need to put back out there
	       log.warning('BAD RECORD 0x%016x 0x%016x', dw1, dw2)
               #return False
	  log.debug('curr_offset: %ld', curr_offset)
          curr_offset -= size
          bytes_left -= size

#        Save the latest values to be used in the next iteration
         self.current_timestamp0 = cur_ts0
         self.current_timestamp1 = cur_ts1
         self.nhtm0_stamp_elapsed_time = nhtm0_stamp_elapsed_time
         self.nhtm1_stamp_elapsed_time = nhtm1_stamp_elapsed_time
         self.nhtm0_cresp_rcmd_delta = cresp_rcmd_delta0
         self.nhtm1_cresp_rcmd_delta = cresp_rcmd_delta1
         self.rcmd_0_previous_port = rcmd_0_previous_port
         self.rcmd_1_previous_port = rcmd_1_previous_port

	 return True

        def find_stamp_complete(self, buf, length, iteration, htm_ind):
         cresp_info_valid = 0

         format = '>QQ'
         size = struct.calcsize(format)

         if (iteration == 0):
             self.current_offset = 0

         running_offset = self.current_offset
         offset = 0

         if (processor_version == "POWER9"):
                self.set_bits_P9()
         else:
                self.set_bits()

         entries = [] # dummy
         cur_ts = 0
         use_matched = False

         while (length > offset):
          (dw1, dw2) = struct.unpack(format, buf[offset:offset+size])
          f = fabric_entry(dw1, dw2)
	  try:
               if f.type == type_stamp:
                  (s, cur_ts) = self.process_stamp(f, dw1, dw2, entries, cur_ts, use_matched)
                  log.debug('stamp. dw1: %x, dw2: %x, offset: %d',dw1, dw2, running_offset+offset)
                  if s.stamp_type == s.stamp_complete:
                      if (htm_ind == -1): # neither htm0 nor htm1 is specified. Single consolidated input dump file
                          if (self.find_nhtm(running_offset+offset)==0): # nhtm0
                           if (self.stamp_complete_offset0 == 0):
                             self.stamp_complete_offset0 = running_offset+offset # just get to the start of the stamp_complete record
                          else:
                           if (self.stamp_complete_offset1 == 0):
                             self.stamp_complete_offset1 = running_offset+offset
                      else:
                          if (htm_ind == 0): # specified as nhtm0 
                             self.stamp_complete_offset0 = running_offset + offset
                          else: # nhtm1
                             self.stamp_complete_offset1 = running_offset + offset

		      log.debug('stamp_complete found')
               elif f.type == type_rcmd:
                   log.debug('rcmd')
               elif f.type == type_cresp:
                   log.debug('cresp')
               else:
                   if (self.find_nhtm(offset) == 0):
                       nhtm_index = 0
                   else:
                       nhtm_index = 1
                   print('unknown nhtm%d record at offset: %d' % (nhtm_index, offset))
          except ValueError:
	       log.warning('BAD RECORD 0x%016x 0x%016x', dw1, dw2)
               print('BAD RECORD 0x%016x 0x%016x', dw1, dw2)

          offset += size

#       Single consolidated input dump file
          if (htm_ind == -1) and ((self.stamp_complete_offset0 != 0) and\
                  (self.stamp_complete_offset1 != 0)):
                      return False

#       One input dump file for nhtm0 and nhtm1 each
          if ((htm_ind == 0) and (self.stamp_complete_offset0 != 0)) or\
                  ((htm_ind == 1) and (self.stamp_complete_offset1 != 0)):
                      return False

         self.current_offset += offset
         return True

#       Find both stamp_complete for nhtm0 and nhtm1
        def find_stamp_complete_all(self, buf, length, iteration):
         cresp_info_valid = 0

         format = '>QQ'
         size = struct.calcsize(format)

         if (iteration == 0):
             self.current_offset = 0

         running_offset = self.current_offset
         offset = 0

         if (processor_version == "POWER9"):
                self.set_bits_P9()
         else:
                self.set_bits()

         entries = [] # dummy
         cur_ts = 0
         use_matched = False

         while (length > offset):
          (dw1, dw2) = struct.unpack(format, buf[offset:offset+size])
          f = fabric_entry(dw1, dw2)
	  try:
               if f.type == type_stamp:
                  (s, cur_ts) = self.process_stamp(f, dw1, dw2, entries, cur_ts, use_matched)
                  log.debug('stamp. dw1: %x, dw2: %x, offset: %d',dw1, dw2, running_offset+offset)
                  if s.stamp_type == s.stamp_complete:
                        if (self.find_nhtm(running_offset+offset)==0): # nhtm0
                           if (self.stamp_complete_time0 == 0):
                             self.stamp_complete_time0 = s.timestamp # save the stamp_complete
                           if (self.stamp_complete_offset0 == 0):
                             self.stamp_complete_offset0 = running_offset+offset # just get to the start of the stamp_complete record
                        else:
                           if (self.stamp_complete_time1 == 0):
                             self.stamp_complete_time1 = s.timestamp # save the stamp_complete
                           if (self.stamp_complete_offset1 == 0):
                             self.stamp_complete_offset1 = running_offset+offset

		        log.debug('stamp_complete found')
                        stamp_complete_processed = True
                  elif s.stamp_type == s.stamp_timestamp: # FF8. Save and replace the FF8 stamps. The 
                                                    # last one before stamp_complete is required
                        if (self.find_nhtm(running_offset+offset)==0): # nhtm0
                             if (self.stamp_complete_offset0 == 0): # Keep updating the ref stamp for nhtm0 only until we reach stamp_complete.
                                 # The ref_ts0 should not be updated further once we have reached and crossed stamp_complete. This might be a 
                                 # case if stamp_complete for nhtm1 is much beyond nhtm0.
                              self.ref_timestamp0 = s.timestamp # save the reference timestamp
                              self.ref_timestamp_offset0 = running_offset+offset
                        else: # nhtm1
                             if (self.stamp_complete_offset1 == 0):
                              self.ref_timestamp1 = s.timestamp # save the reference timestamp
                              self.ref_timestamp_offset1 = running_offset+offset

               elif f.type == type_rcmd:
                   log.debug('rcmd')
               elif f.type == type_cresp:
                   log.debug('cresp')
               else:
                   if (self.find_nhtm(offset) == 0):
                       nhtm_index = 0
                   else:
                       nhtm_index = 1
                   print('unknown nhtm%d record at offset: %d' % (nhtm_index, offset))
          except ValueError:
	       log.warning('BAD RECORD 0x%016x 0x%016x', dw1, dw2)
               print('BAD RECORD 0x%016x 0x%016x', dw1, dw2)

          offset += size
#       We need to ensure that the ref_timestamp0/1 are both set. However, we should set this
#       just prior to setting the stamp_complete offsets. Therefore, run the loop (and set the
#       ref_timestamp_offset* values) until we get to the stamp_complete.
          if (self.stamp_complete_offset0 != 0) and\
                  (self.stamp_complete_offset1 != 0):
                      return False
#          if (self.ref_timestamp_offset0 != 0) and\
#                  (self.ref_timestamp_offset1 != 0):
#                      return False

         self.current_offset += offset
         return True

	def parse_single(self, buf, length, use_matched, htm_id, iteration):
         cresp_info_valid = 0

         format = '>QQ'
         size = struct.calcsize(format)

         if not self.entries:
                cur_timestamp=0
         else:
                cur_timestamp=self.entries[-1].timestamp
	

         if (processor_version == "POWER9"):
                if not self.entries2:
                        cur_timestamp2 = 0
                else:
                        cur_timestamp2=self.entries2[-1].timestamp

	 log.debug('At entry: size: %d, cur_timestamp: %ld, cur_timestamp2: %ld', size, cur_timestamp, cur_timestamp2)
	 
         offset = 0
         offset2 = 0

         if (processor_version == "POWER9"):
                self.cresp_bit_start_1 = 2 # cresp_info_valid set in bit 2
                self.cresp_bit_end_1   = 31
                self.cresp_bit_start_2 = 32
                self.cresp_bit_end_2   = 61
                self.cresp_bit_start_3 = 64
                self.cresp_bit_end_3   = 93
                self.cresp_bit_start_4 = 98
                self.cresp_bit_end_4   = 127
                self.cresp_in_rcmd_bit_start = 98
                self.timestamp_bit_start = 94
                self.timestamp_bit_end = 97
         else:
                self.cresp_bit_start_1 = 8
                self.cresp_bit_end_1   = 31
                self.cresp_bit_start_2 = 40
                self.cresp_bit_end_2   = 63
                self.cresp_bit_start_3 = 72
                self.cresp_bit_end_3   = 95
                self.cresp_bit_start_4 = 104
                self.cresp_bit_end_4   = 127
                self.cresp_in_rcmd_bit_start = 104
                self.timestamp_bit_start = 96
                self.timestamp_bit_end = 103

	 previous_type = notype
	 current_type  = notype
	 prev_ref_time = 0

	 if htm_id == HTM0:
		entries = self.entries
                cur_ts = cur_timestamp
	 else:
		entries = self.entries2
                cur_ts = cur_timestamp2

	 stamp_processed = False

	# Now that the complete stamp is found, iterate again from the beginning until the complete stamp
         while (length > offset):
          (dw1, dw2) = struct.unpack(format, buf[offset:offset+size])
          f = fabric_entry(dw1, dw2)

	  try:
               if f.type == type_stamp:
		 # how to identify whether we are sending to entries or entries2?
                  (s, cur_ts) = self.process_stamp(f, dw1, dw2, entries, cur_ts, use_matched)
                  if s.stamp_type == s.stamp_complete:
		       log.debug('stamp_complete found')
                       offset += size # Add 'size' to mark the end of 'stamp_complete'
		       self.stamp_complete_offset = self.current_offset + offset # Where did we find stamp_complete?
#		       self.stamp_complete_timestamp = cur_timestamp
		       log.debug('stamp_complete offset: %ld', self.stamp_complete_offset)
                       print('stamp complete offset: %d' % self.stamp_complete_offset)
                       return False
#		  ref_time  = cur_ts
#                  stamp_elapsed_time = s.elapsed_time
#                  timedelta_in = -1 # Unused in parse_single. Useful in parse_and_fill() routine.
#		  log.debug('stamp 1: %ld', cur_ts)
		  stamp_processed = True
		  print('stamp: %d' % offset) 
	       elif f.type == type_cresp:
		if iteration == 0 and stamp_processed == False: # At least one stamp record must be processed, just the first time
								# For subsequent iterations, we may have a starting cresp / rcmd
			log.debug('First record is cresp. Expected stamp.. skipping')
			offset += size
		        print('cresp skip: %d' % offset) 
			continue 
		# use the prev_ref_time until it is again replaced
		# For subsequent (after the first) iterations, if stamp isn't the first record (prev_ref_time=0), we must use the
		# cur_timestamp from the previous iteration (last entry in the entries array)
#		if iteration > 0 and prev_ref_time != 0:
#		 cur_ts = ref_time

#		log.debug('cresp in: %ld', cur_ts)
#		(cur_ts, entries, cresps) = self.process_cresp(f, dw1, dw2, entries, cur_ts, use_matched, missed_list, missed, stamp_elapsed_time, timedelta_in)
#		log.debug('cresp out: %ld', cur_timestamp)
#	        timedelta_in = timedelta	
		print('cresp: %d' % offset) 
	       else:  # rcmd
		if iteration == 0 and stamp_processed == False: # At least one stamp record must be processed, just the first time
			log.debug('First record is rcmd. Expected stamp.. skipping')
			offset += size
		        print('rcmd skip: %d' % offset) 
			continue 
		# use the prev_ref_time until it is again replaced
		# For subsequent (after the first) iterations, if stamp isn't the first record (prev_ref_time=0), we must use the
		# cur_timestamp from the previous iteration (last entry in the entries array)
#		if iteration > 0 and prev_ref_time != 0:
#		 cur_ts = ref_time

#		log.debug('rcmd in: %ld', cur_ts)
##		(cur_ts, entries, cresps, rcmds) = self.process_rcmd(f, dw1, dw2, entries, cur_ts, use_matched)
#		(cur_ts, entries, cresps, rcmds, timedelta) = self.process_rcmd(f, dw1, dw2, entries, cur_ts, use_matched, stamp_elapsed_time, timedelta_in)
#		log.debug('rcmd out: %ld', cur_ts)
#	        timedelta_in = timedelta	
                print('rcmd: %d' % offset)
          except ValueError:
               #need to put back out there
	       log.warning('BAD RECORD 0x%016x 0x%016x', dw1, dw2)
               #return False
	  log.debug('offset: %ld', offset)
          offset += size

         self.current_offset += offset

	 return True

#        def parse(self, buf, length): Need to bring in the def parse routine from the original source
#	def parse(self, buf, length, use_matched):
	def parse2(self, buf, length, buf2, length2, use_matched):
	# Records are 128 bit, big endian
	 cresp_info_valid = 0

	 format = '>QQ'
	 size = struct.calcsize(format)
	 if (processor_version == "POWER9"):
		size2 = size

	 if not self.entries:
		cur_timestamp=0
	 else:
		cur_timestamp=self.entries[-1].timestamp

	 if (processor_version == "POWER9"):
		if not self.entries2:
			cur_timestamp2 = 0
		else:
			cur_timestamp2=self.entries2[-1].timestamp2

	 offset = 0
 	 offset2 = 0
 
	 if (processor_version == "POWER9"):
	 	self.cresp_bit_start_1 = 2 # cresp_info_valid set in bit 2
		self.cresp_bit_end_1   = 31
		self.cresp_bit_start_2 = 32		
		self.cresp_bit_end_2   = 61
		self.cresp_bit_start_3 = 64		
		self.cresp_bit_end_3   = 93
		self.cresp_bit_start_4 = 98		
		self.cresp_bit_end_4   = 127
		self.cresp_in_rcmd_bit_start = 98
		self.timestamp_bit_start = 94
		self.timestamp_bit_end = 97
	 else:
		self.cresp_bit_start_1 = 8
		self.cresp_bit_end_1   = 31
		self.cresp_bit_start_2 = 40		
		self.cresp_bit_end_2   = 63
		self.cresp_bit_start_3 = 72		
		self.cresp_bit_end_3   = 95
		self.cresp_bit_start_4 = 104		
		self.cresp_bit_end_4   = 127
		self.cresp_in_rcmd_bit_start = 104
		self.timestamp_bit_start = 96
		self.timestamp_bit_end = 103

	 nhtm0_complete = False
	 nhtm1_complete = False

	 while (length > offset) or (length2 > offset2):
		if (length > offset):
		 (dw1, dw2) = struct.unpack(format, buf[offset:offset+size])
		 f = fabric_entry(dw1, dw2)
		else:
		 print 'reached the end of the current 4k chunk: nhtm0 (1)'
		 nhtm0_complete = True

		if (processor_version == "POWER9"):
		 if (length2 > offset2):
		  (dw3, dw4) = struct.unpack(format, buf2[offset2:offset2+size2])
		  f2 = fabric_entry(dw3, dw4)
		 else:
		  print 'reached the end of the current 4k chunk: nhtm1 (1)'
		  nhtm1_complete = True

		try:
			if not nhtm0_complete:
			 if f.type == type_stamp:
				(s, cur_timestamp) = self.process_stamp(f, dw1, dw2, self.entries, cur_timestamp, use_matched)
				s.get_stamp_type()
				if (processor_version != "POWER9"):
						if s.stamp_type == s.stamp_complete:
							print 'nhtm trace complete'	
							return False
				print 'stamp/ nhtm0 1, {}'.format(cur_timestamp)

			 elif f.type == type_cresp:
				(cur_timestamp, self.entries, cresps) = self.process_cresp(f, dw1, dw2, self.entries, cur_timestamp, use_matched, missed_list, missed, stamp_elapsed_time)
				print 'cresp/ nhtm0 1, {}'.format(cur_timestamp)

			 else:
				(cur_timestamp, self.entries, cresps, rcmds) = self.process_rcmd(f, dw1, dw2, self.entries, cur_timestamp, use_matched)
				print 'process_rcmd: rcmd/ nhtm0 1, {}'.format(cur_timestamp)

			if (processor_version=="POWER9"):
				if not nhtm1_complete:
				 if f2.type == type_stamp:
					(s2, cur_timestamp2) = self.process_stamp(f2, dw3, dw4, self.entries2, cur_timestamp2, use_matched)
					s2.get_stamp_type()
					print 'stamp/ nhtm1 1, {}'.format(cur_timestamp2)

				 elif f2.type == type_cresp:
					(cur_timestamp2, self.entries2, cresps2) = self.process_cresp(f2, dw3, dw4, self.entries2, cur_timestamp2, use_matched, missed_list2, missed2, stamp_elapsed_time)
					cur_timestamp2 += cresp_time
					print 'cresp/ nhtm1 1, {}'.format(cur_timestamp2)
				 else:
					(cur_timestamp2, self.entries2, cresps2, rcmds2) = self.process_rcmd(f2, dw3, dw4, self.entries2, cur_timestamp2, use_matched)
					print 'process_rcmd: rcmd/ nhtm1 1, {}'.format(cur_timestamp2)

				# Aggregate now

				if ((not nhtm0_complete) or (not nhtm1_complete)):
				 if (cur_timestamp == cur_timestamp2):
#				Update nhtm0 record first, and then nhtm1 
					if f.type == type_stamp:
						self.agg_entries.append(s)
						if s.stamp_type == s.stamp_complete:
							print 'nhtm0 trace complete (1)'	
					elif f.type == type_cresp:
						for i in range(0,len(cresps)):
							if (use_matched):
								self.match_trace(cresps[i], self.agg_entries, self.agg_missed_list, self.agg_missed)
							else:
								self.agg_entries.append(cresps[i])
					else: #f.type = rcmd
						self.agg_entries.append(rcmds)	
						print 'append rcmd/ nhtm0 1'
						if (len(cresps)>0):
							if (use_matched):
								self.match_trace(cresps[0], self.agg_entries, self.agg_missed_list, self.agg_missed)
							else:
								self.agg_entries.append(cresps[0])	
							print 'append rcmd:cresp/ nhtm0 1'

                                        if f2.type == type_stamp:
                                                self.agg_entries.append(s2)
						if s2.stamp_type == s2.stamp_complete:
							print 'nhtm1 trace complete (1)'	
						print 'append stamp/ nhtm1 1'

                                        elif f2.type == type_cresp:
                                                for i in range(0,len(cresps2)):
                                                        if (use_matched):
                                                                self.match_trace(cresps2[i], self.agg_entries, self.agg_missed_list, self.agg_missed)
                                                        else:
                                                                self.agg_entries.append(cresps2[i])
						print 'append cresp/ nhtm1 1'

                                        else: #f.type = rcmd
                                                self.agg_entries.append(rcmds2)
						print 'append rcmd/ nhtm1 1'
                                                if (len(cresps2)>0):
                                                        if (use_matched):
                                                                self.match_trace(cresps2[0], self.agg_entries, self.agg_missed_list, self.agg_missed)
                                                        else:
                                                                self.agg_entries.append(cresps2[0])
							print 'append rcmd:cresp/ nhtm1 1'
					offset += size
					offset2 += size2
				 else:	
				  while (cur_timestamp < cur_timestamp2):
					if f.type == type_stamp:
						self.agg_entries.append(s)
						if s.stamp_type == s.stamp_complete:
							print 'nhtm0 trace complete (2)'	
						print 'append stamp/ nhtm0 2'

					elif f.type == type_cresp:
						for i in range(0,len(cresps)):
							if (use_matched):
								self.match_trace(cresps[i], self.agg_entries, self.agg_missed_list, self.agg_missed)
							else:
								self.agg_entries.append(cresps[i])
						print 'append cresp/ nhtm0 2'

					else: #f.type = rcmd
						self.agg_entries.append(rcmds)	
						print 'append rcmd/ nhtm0 2'
						if (len(cresps)>0):
							if (use_matched):
								self.match_trace(cresps[0], self.agg_entries, self.agg_missed_list, self.agg_missed)
							else:
								self.agg_entries.append(cresps[0])	
							print 'append rcmd:cresp/ nhtm0 2'

					offset += size
					if (length > offset):
					 (dw1, dw2) = struct.unpack(format, buf[offset:offset+size])
					 f = fabric_entry(dw1, dw2)
					 if f.type == type_stamp:
						(s, cur_timestamp) = self.process_stamp(f, dw1, dw2, self.entries, cur_timestamp, use_matched)
						s.get_stamp_type()
						print 'stamp/ nhtm0 2'

					 elif f.type == type_cresp:
						(cur_timestamp, self.entries, cresps) = self.process_cresp(f, dw1, dw2, self.entries, cur_timestamp, use_matched, missed_list, missed)
						cur_timestamp += cresp_time
						print 'cresp/ nhtm0 2'

					 else:
						(cur_timestamp, self.entries, cresps, rcmds) = self.process_rcmd(f, dw1, dw2, self.entries, cur_timestamp, use_matched)
						print 'rcmd/ nhtm0 2'

					else:
						print 'reached the end of the current 4k chunk: nhtm0 (2)'
						nhtm0_complete = True
						if (nhtm1_complete == False):
							print 'bumping up cur_timestamp to write out pending record'
							cur_timestamp = cur_timestamp2 + 1
						break # no more nhtm0 records in current chunk

				# Now cur_timestamp2 < cur_timestamp
				  while (cur_timestamp2 < cur_timestamp):
					print 't2<t: t2: {}, t: {}'.format(cur_timestamp2, cur_timestamp)
                                        if f2.type == type_stamp:
                                                self.agg_entries.append(s2)
						if s2.stamp_type == s2.stamp_complete:
							print 'nhtm1 trace complete (2)'
						print 'append stamp/ nhtm1 2'
                                        elif f2.type == type_cresp:
                                                for i in range(0,len(cresps2)):
                                                        if (use_matched):
                                                                self.match_trace(cresps2[i], self.agg_entries, self.agg_missed_list, self.agg_missed)
                                                        else:
                                                                self.agg_entries.append(cresps2[i])
						print 'append cresp/ nhtm1 2'
                                        else: #f.type = rcmd
                                                self.agg_entries.append(rcmds2)
						print 'append rcmd/ nhtm1 2'
                                                if (len(cresps2)>0):
                                                        if (use_matched):
                                                                self.match_trace(cresps2[0], self.agg_entries, self.agg_missed_list, self.agg_missed)
                                                        else:
                                                                self.agg_entries.append(cresps2[0])
							print 'append rcmd:cresp/ nhtm1 2'
                                        offset2 += size2
					if (length2 > offset2):
					 (dw3, dw4) = struct.unpack(format, buf2[offset2:offset2+size2])
					 f2 = fabric_entry(dw3, dw4)
					 if f2.type == type_stamp:
						(s2, cur_timestamp2) = self.process_stamp(f2, dw3, dw4, self.entries2, cur_timestamp2, use_matched)
						s2.get_stamp_type()
						print 'stamp/ nhtm1 2: cur_timestamp2: {}'.format(cur_timestamp2)
						print 'stamp/ nhtm1 2'

					 elif f2.type == type_cresp:
						(cur_timestamp2, self.entries2, cresps2) = self.process_cresp(f2, dw3, dw4, self.entries2, cur_timestamp2, use_matched, missed_list, missed)
						print 'cresp/ nhtm1 2'

					 else:
						(cur_timestamp2, self.entries2, cresps2, rcmds2) = self.process_rcmd(f2, dw3, dw4, self.entries2, cur_timestamp2, use_matched)
						print 'rcmd/ nhtm1 2'

					else:
						print 'reached the end of the current 4k chunk: nhtm1 (1)'
						nhtm1_complete = True
						if (nhtm0_complete == False):
							cur_timestamp2 = cur_timestamp + 1
						break # no more nhtm1 records

		except ValueError:
			#need to put back out there
			print "BAD RECORD 0x%016x 0x%016x" % (dw1, dw2)
			#return False
		offset += size
		if (processor_version=="POWER9"):
			offset2 += size2
	#statList[1].dump()
	 return True

type_stamp = 0
type_cresp = 1
type_rcmd = 2
notype = 3
