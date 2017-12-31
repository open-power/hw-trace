#!/usr/bin/python

import re

class ports:
	__ax_axd_str = [
		"01000001pSSSL" ,
		"0100001000000" ,
		"01000011pSSS0" ,
		"0100010100IGL" ,
		"0100011000000" ,
		"0100100100000" ,
		"0100101000000" ,
		"0100110100000" ,
		"0100111000000" ,
		"101010i000000" ,
		"1100000000000" ,
		"1100010000000" ,
		"110001xxxxxx1" ,
		"110001xxxxx1x" ,
		"110001xxxx1xx" ,
		"1100010001xxx" ,
		"1100010010xxx" ,
		"1100010100000" ,
		"1100010100xxx" ,
		"1100011000xxx" ,
		"1100100000000" ,
		"1100101000000" ,
		"1110000000001" ,
		"1110000000010" ,
		"111001xxxxxxx" ,
		"11101000HPccc" ,
		"111100xxxxx00" ,
		"111100xxxxx01" ,
		"111100xxxxx10" ,
		"111100xxxxx11" ,
		"1111010000001" ,
		"111101R000010" ,
		"111101R000100" ,
		"1111011000001" ,
		"1111100000000" ,
		"1111100000001" ,
		"1111100000010" ,
		"111110000100u" ,
		"111111000xxxx" ,
		"111111100xxxx" ,
		"1111111111111" ,
	]
		
	__ax_axd = []
	for val in __ax_axd_str:
		match = int(re.sub(r'[^01]', '0', val), 2)
		mask = re.sub(r'[01]', '1', val)
		mask = int(re.sub(r'[^01]', '0', mask), 2)
		__ax_axd.append((match, mask))


	def is_ax_axd(self, ttype, tsize):
		val = (ttype << 7) | tsize

		matches = 0
		for (match, mask) in self.__ax_axd:
			if (val & mask) == match:
				matches += 1

		if matches > 1:
			matches = 1
			#This is okay, the pMisc codes   "1100010100000" and  "1100010100xxx" match 
			#the same entry.  Either way if it matches we confirm it's at least an ax/axd command 
			#raise ValueError("Invalid ttype %x tsize %x (matched %d)" % ttype, tsize, matches)

		# Match 101000iwHPwww
		if (val & 0x1f80) == 0x1400:
			return -1

		return matches

	def port(self, ttype, tsize, addr):
		ax_axd = self.is_ax_axd(ttype, tsize)

		if ax_axd == 1:
			return 0

		if ax_axd == -1:
			return -1

		if (addr >> 7) & 1:
			return 1

		return 0


if __name__ == '__main__':
	p = ports()
	print p.port(0x22, 0x0, 0)
