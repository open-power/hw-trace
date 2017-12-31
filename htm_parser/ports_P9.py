#!/usr/bin/python

import re
import logging

log = logging.getLogger(__name__)

class ports:
	__ax_axd_P9_str = [
		"0001111000000ss",
		"0001111000001ss",
		"0001111000010ss",
		"001000000000000",
		"001000001pSSSSF",
		"001000010pSSSS1",
		"001000011pSSSS0",
		"001000100000000",
		"001000101pSSSSF",
		"001000110pSSSS1",
		"001000111pSSSS0",
		"010110100000000",
		"010110100000100",
		"010111000000000",
		"010111000000001",
		"010111000000010",
		"011000100000000", # pMisc
		"0110001xxxxxx1x",
		"01100010xxxx1x0",
		"01100010xxx1xx0",
		"01100010001xxx0",
		"011000101000000",
		"01100010100xxx0",
		"01100010010xxx0",
		"011000110000000",
		"011000100000001", # pMisc end
		"011001000000000",
		"011001010000000",
		"0110011xxxxxxxx",
		"011100000000000",
		"011100000000010",
		"011100000000100",
		"0111001xxxxxxxx",
		"0111010xxxxxxxx",
		"011110100000010",
		"0111101R0000100",
		"0111101R0001000",
		"011110110000010",
		"011111000000000",
		"011111000000010",
		"011111000000100",
		"01111110000f000",
		"01111110000f001",
		"01111110000f010",
		"01111110000f011",
		"011111111111111", # Ax ends here
		"010011100000000", # AxD start
		"01001111000000L",
		"0101000xwHPwww0",
		"011000000000000",
		"01101010ttt1000", # AxD end
	]
			
		
	__ax_axd_P9 = []
	for val in __ax_axd_P9_str:
		match = int(re.sub(r'[^01]', '0', val), 2)
		mask = re.sub(r'[01]', '1', val)
		mask = int(re.sub(r'[^01]', '0', mask), 2)
		__ax_axd_P9.append((match, mask))


	def is_ax_axd(self, ttype, tsize):
#		val = (ttype << 7) | tsize 
		val = (ttype << 8) | tsize # in P9, ttype:tsize is set as 7:8 as opposed to a 6:7 arrangement in P8

		matches = 0
		for (match, mask) in self.__ax_axd_P9:
			if (val & mask) == match:
				matches += 1

		if matches > 1:
			matches = 1
			#This is okay, the pMisc codes   "1100010100000" and  "1100010100xxx" match 
			#the same entry.  Either way if it matches we confirm it's at least an ax/axd command 
			#raise ValueError("Invalid ttype %x tsize %x (matched %d)" % ttype, tsize, matches)

		# Match 101000iwHPwww. This is a AxD class mnemonic: cop_req. Wasn't included in the list hence checked.
#		if (val & 0x1f80) == 0x1400: # Match any val that is 101000xxxxxxx. But what does returning -1 mean?
#			return -1
#		for P9, this doesn't apply since we include the cop_req mnemonic in the list above.

		return matches

	def port(self, ttype, tsize, addr):
		ax_axd = self.is_ax_axd(ttype, tsize)
		
		# In P8, we assume that the port identified is '0' if the command is of class Ax / AxD
		if ax_axd == 1: 
			return 0

		if ax_axd == -1:
			return -1

		# What does this check mean on P8? How did we identify port #1?
		if (addr >> 7) & 1: # check if bit 56 is 1. If bit 56 is 1, then use port 1!
			return 1

		return 0

        def port_P9_old(self, addr, snoop_id_bit, cmd_type):
               if (cmd_type == 1) or (cmd_type == 2): # cresp or rcmd
                if snoop_id_bit == 0:
                  if (addr >> 7) & 1: # nhtm1
                        return 1 # If bit 118 was set to 0 (port 0/2), return 2 (if nhtm1)
                  else: 
                        return 0  # nhtm0
                else: 
                  if (addr >> 7) & 1: # nhtm1
                        return 3 # If bit 118 was set to 1 (port 1/3), return 3 (if nhtm1)
                  else: 
                        return 2  # nhtm0
               else:
                   print 'unsupported command type for port number'
                   log.debug('unsupported command type for port number')

        def port_P9(self, htm_id, snoop_id_bit, cmdtype, addr):
               log.debug('snoop_id_bit: %d' %(snoop_id_bit))
               if (cmdtype == 1): # cresp
                if snoop_id_bit == 0:
                  if htm_id == 1: # nhtm1
                        return 1 # If bit 118 was set to 0 (port 0/2), return 2 (if nhtm1)
                  else: 
                        return 0  # nhtm0
                else: 
                  if htm_id == 1: # nhtm1
                        return 3 # If bit 118 was set to 1 (port 1/3), return 3 (if nhtm1)
                  else: 
                        return 2  # nhtm0
               elif (cmdtype == 2): # rcmd
                   log.debug('addr: %x' %(addr))
                   portid = (addr >> 7) & 0x3 # Bits 55:56. port id is set to the exact value
                   return portid
               else: # unsupported type
                   print('port_P9: unsupported type')
                   log.debug('port_P9: unsupported type')

if __name__ == '__main__':
	if (processor_version == "POWER9"):
		p = ports_P9()
	else:
		p = ports()

	print p.port(0x22, 0x0, 0)
