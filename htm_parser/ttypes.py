#!/usr/bin/python

import re

class ttypes:

	__ttype_Read_str = {
	0b00000 : 'addr_error',
	0b00001 : 'go_Me:ed',
	0b00010 : 'go_Me:lpc',
	0b00011 : 'go_Me_cond:ed',
	0b00101 : 'go_Mu_ed',
	0b00111 : 'go_Mu_cond:ed',
	0b01000 : 'go_Sl:T',
	0b01001 : 'go_Sl:ed',
	0b01010 : 'go_Sl:lpc',
	0b01011 : 'go_Sl_cond:ed',
	0b01100 : 'go_S:T',
	0b01111 : 'go_S_cond:T',
	0b10100 : 'abort_trm',
	0b11000 : 'rty',
	0b11001 : 'rty_inc',
	0b11100 : 'rty_drp',
	0b11110 : 'ack_ed_dead',
	0b11111 : 'ack_dead'
	}

        __ttype_PCL_str = {
        0b00000 : 'addr_error',
        0b00100 : 'addr_ack_done',
        0b11000 : 'rty',
        0b11010 : 'addr_ack_rty',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

        __ttype_RWITM_str = {
        0b00000 : 'addr_error',
        0b00001 : 'go_M:ed',
        0b00010 : 'go_M:lpc',
        0b00011 : 'go_M:T',
        0b00101 : 'go_Mu_bk:ed',
        0b00110 : 'go_Mu_bk:lpc',
        0b00111 : 'go_Mu_bk:T',
        0b01001 : 'go_M_bk_inc:ed',
        0b01011 : 'go_M_bk_inc:T',
        0b01101 : 'go_M_bk_cond:ed',
        0b01110 : 'go_M_bk_inc_cond:T',
        0b01111 : 'go_M_bk_cond:T',
        0b10100 : 'abort_trm',
        0b10101 : 'abort_trm_ed',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11010 : 'rty_ed',
        0b11011 : 'rty_ed_inc',
        0b11100 : 'rty_drp',
        0b11101 : 'rty_ed_drp',
        0b11110 : 'ack_ed_dead',
        0b11111 : 'ack_dead'
        }

        __ttype_CLAIM_str = {
        0b00000 : 'addr_error',
        0b00001 : 'go_M',
        0b00010 : 'go_M:lpc',
        0b00101 : 'go_M_bk',
        0b00110 : 'go_M_bk:lpc',
        0b01001 : 'go_M_bk_inc',
        0b10100 : 'abort_trm',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11010 : 'rty_lost_claim',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

        __ttype_Write_str = {
        0b00000 : 'addr_error',
        0b00100 : 'addr_ack_done',
        0b00110 : 'addr_hpc_ack_done',
        0b00111 : 'addr_hpc_ack_resend',
        0b01000 : 'addr_ack_bk',
        0b01010 : 'addr_hpc_ack_bk',
        0b01011 : 'addr_hpc_ack_bk_inc',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

        __ttype_FCI_str = {
        0b00000 : 'addr_error',
        0b00011 : 'addr_ack_resend',
        0b00100 : 'addr_ack_done',
        0b00101 : 'addr_hpc_ack_resend_inc',
        0b00110 : 'addr_hpc_ack_done',
        0b00111 : 'addr_hpc_ack_resend',
        0b01000 : 'addr_ack_bk',
        0b01010 : 'addr_hpc_ack_bk',
        0b01011 : 'addr_hpc_ack_bk_inc',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

        __ttype_Inject_str = {
        0b00000 : 'addr_error',
        0b00110 : 'addr_hpc_ack_done',
        0b01010 : 'addr_hpc_ack_bk',
        0b01011 : 'addr_hpc_ack_bk_inc',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11010 : 'rty_dma_w',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

        __ttype_CPWrite_str = {
        0b00000 : 'addr_error',
        0b00100 : 'addr_ack_done',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

       	__ttype_LCO_str = {
        0b00000 : 'addr_error',
        0b00001 : 'target:no_data',
        0b00010 : 'Sl:no_data',
        0b00100 : 'target:data',
        0b01001 : 'hpc:no_data',
        0b11000 : 'rty',
        0b11100 : 'rty_drp',
        }

        __ttype_Ack_BK_str = {
        0b00000 : 'addr_error',
        0b00100 : 'addr_ack_done',
        0b01000 : 'addr_ack_bk',
        0b10100 : 'abort_trm',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

        __ttype_Ack_str = {
        0b00000 : 'addr_error',
        0b00100 : 'addr_ack_done',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

        __ttype_TM_str = {
        0b00000 : 'no_tk_mgr',
        0b00100 : 'ack_done',
        0b11000 : 'rty',
        0b11100 : 'rty_drp',
        }

        __ttype_Cop_str = {
        0b00000 : 'addr_error',
        0b00010 : 'addr_ack_hpc',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11100 : 'rty_drp',
        }

	__ttypes_str = {
		'00000001qttsh' : ['rd_go_s','read'],
		'00000010qttsh' : ['rd_go_m','read'],
		'00000100padeh' : ['cl_dma_rd','read'],
		'00001001padeh' : ['pref_go_s','read'],
		'00001010padeh' : ['pref_go_m','read'],
		'00001100padeh' : ['cl_rd_nc','read'],
		'000101c000000' : ['cl_probe','pcl'],
		'00100000qttsh' : ['rwitm','rwitm'],
		'00110000qtt00' : ['dclaim','claim'],
		'00110100qtt00' : ['dcbz','claim'],
		'01000001pSSSL' : ['tlbi_op','tm'],
		'0100001000000' : ['tlbi_t','tm'],
		'01000011pSSS0' : ['tlbi_set','tm'],
		'0100010100IGL' : ['tlbivax_op','tm'],
		'0100011000000' : ['tlbivax_t','tm'],
		'0100100100000' : ['msgsnd_op','tm'],
		'0100101000000' : ['msgsnd_t','tm'],
		'0100110100000' : ['icbi_op','tm'],
		'0100111000000' : ['icbi_t','tm'],
		'0101000000000' : ['cp_m','cpwrite'],
		'0101000000001' : ['cp_t','cpwrite'],
		'0101000000010' : ['cp_tn','cpwrite'],
		'0101000010000' : ['hca.hpc_act_updt','cpwrite'],
		'0101000100000' : ['hca.hpc_ref_updt','cpwrite'],
		'0101000110000' : ['hca.hpc_dcy_updt','cpwrite'],
		'0101001000000' : ['htm_cl_w','cpwrite'],
		'0101010000000' : ['cp_ig','cpwrite'],
		'0101011000000' : ['cp_me','cpwrite'],
		'0101100000000' : ['cl_w_cln_m','cpwrite'],
		'0101100000001' : ['cl_w_cln_t','cpwrite'],
		'0101100000010' : ['cl_w_cln_tn','cpwrite'],
		'01100001ttttt' : ['lco_ig','lco'],
		'01100101ttttt' : ['lco_sl','lco'],
		'01101000ttttt' : ['lco_t','lco'],
		'01101001ttttt' : ['lco_te','lco'],
		'01101010ttttt' : ['lco_tn','lco'],
		'01101011ttttt' : ['lco_ten','lco'],
		'01101100ttttt' : ['lco_m','lco'],
		'01101101ttttt' : ['lco_me','lco'],
		'01101110ttttt' : ['lco_mu','lco'],
		'01110000xxxxx' : ['cl_dma_w_i','write'],
		'01110010xxxxx' : ['cl_dma_w_hp','write'],
		'01110100ttttt' : ['cl_fci_w_i','fci'],
		'01110101ttttt' : ['cl_fci_w_t','fci'],
		'01111000xxxxx' : ['cl_dma_inj','inj'],
		'011111xxxxxxx' : ['pr_dma_inj','inj'],
		'1000000000001' : ['dcbfl','claim'],
		'1000000000010' : ['dcbf','ack_bk'],
		'1000000000011' : ['dcbfc','ack_bk'],
		'1000000000110' : ['dcbi','ack_bk'],
		'100000c001010' : ['dcbfk','ack_bk'],
		'10000100000LL' : ['armw_add','ack_bk'],
		'1000010001100' : ['hca.act_updt','ack_bk'],
		'10000100100LL' : ['armw_and','ack_bk'],
		'1000010011100' : ['hca.ref_updt','ack_bk'],
		'10000101000LL' : ['armw_or','ack_bk'],
		'1000010101100' : ['hca.dcy_updt','ack_bk'],
		'10000101100LL' : ['armw_xor','ack_bk'],
		'100001011111f' : ['pte_updt','ack_bk'],
		'100010000tt00' : ['bkill','ack_bk'],
		'100010010tt00' : ['bkill_inc','ack_bk'],
		'1000101000000' : ['bkill_flush','ack_bk'],
		'10010100000LL' : ['armwf_add','ack_bk'],
		'10010100100LL' : ['armwf_and','ack_bk'],
		'10010101000LL' : ['armwf_or','ack_bk'],
		'10010101100LL' : ['armwf_xor','ack_bk'],
		'100101100ccLL' : ['armwf_cas','ack_bk'],
		'100110xxxxxxx' : ['dma_pr_w','ack_bk'],
		'101000iwHPwww' : ['cop_req','cop'],
		'101010i000000' : ['asb_notify','cop'],
		'101011iaaaaaa' : ['asb_credit_wr','cop'],
		'1100000000000' : ['hca_req.ref_updt','ack'],
		'1100010000000' : ['pMisc_RESERVED','ack'],
		'110001xxxxxx1' : ['pMisc_Switch_AB_command','ack'],
		'110001xxxxx1x' : ['pMisc_Malfunction_Alert_command','ack'],
		'110001xxxx1xx' : ['pMisc_Global_Trace_command','ack'],
		'1100010001xxx' : ['pMisc_TOD_Packet','ack'],
		'1100010010xxx' : ['pMisc_XPCB_Status_Reporting','ack'],
		'1100010100000' : ['pMisc_HTM_extended_marker_NCU','ack'],
		'1100010100xxx' : ['pMisc_HTM','ack'],
		'1100011000xxx' : ['pMisc_AxScom','ack'],
		'1100100000000' : ['link_chk.data_chk','ack'],
		'1100101000000' : ['link_chk.abort_op','ack'],
		'110011xxxxxxx' : ['cl_cln','ack'],
		'110100xxxxxxx' : ['ci_pr_rd','ack'],
		'110101xxxxxxx' : ['dma_pr_rd','ack'],
		'110110rtttsss' : ['ci_pr_ooo_w','ack'],
		'110111rtttsss' : ['ci_pr_w','ack'],
		'1110000000001' : ['sync','ack'],
		'1110000000010' : ['eieio','ack'],
		'111001xxxxxxx' : ['ptesync','ack'],
		'11101000HPccc' : ['cop_cmd','ack'],
		'111100xxxxx00' : ['ris_Interrupt_Request','ack'],
		'111100xxxxx01' : ['ris_Interrupt_Return','ack'],
		'111100xxxxx10' : ['ris_End_of_Interrupt','ack'],
		'111100xxxxx11' : ['ris_Interrupt_Forward','ack'],
		'1111010000001' : ['chgrate.hang','ack'],
		'111101R000010' : ['chgrate.req','ack'],
		'111101R000100' : ['chgrate.grant','ack'],
		'1111011000001' : ['chgrate.alert','ack'],
		'1111100000000' : ['rpt_hang.check','ack'],
		'1111100000001' : ['rpt_hang.poll','ack'],
		'1111100000010' : ['rpt_hang.data','ack'],
		'111110000100u' : ['rpt_hang.fcheck','ack'],
		'111111000xxxx' : ['pbop','ack'],
		'111111100xxxx' : ['fpbop','ack'],
		'1111111111111' : ['nop','ack'],
	}

	__ttype_dict_lookup = {
		'read'		: __ttype_Read_str,
		'pcl'		: __ttype_PCL_str,
		'rwitm'		: __ttype_RWITM_str,
		'claim'		: __ttype_CLAIM_str,
		'tm' 		: __ttype_TM_str,
		'cpwrite' 	: __ttype_CPWrite_str,
		'lco' 		: __ttype_LCO_str,
		'write'		: __ttype_Write_str,
		'fci' 		: __ttype_FCI_str,
		'inj' 		: __ttype_Inject_str,
		'ack_bk'	: __ttype_Ack_BK_str,
		'cop'		: __ttype_Cop_str,
		'ack' 		: __ttype_Ack_str,
	}

	__ttypes = []
	for key in __ttypes_str.keys():
		match = int(re.sub(r'[^01]', '0', key), 2)
		mask = re.sub(r'[01]', '1', key)
		mask = int(re.sub(r'[^01]', '0', mask), 2)
		__ttypes.append((match, mask, __ttypes_str[key]))


	def lookup(self, ttype, tsize):
		val = (ttype << 7) | tsize

		for (match, mask, ttype) in self.__ttypes:
			if (val & mask) == (match & mask):
				return ttype[0]

		raise ValueError("Invalid ttype %x tsize %x" % ttype, tsize)

	def group_lookup(self, ttype, tsize):
		val = (ttype << 7) | tsize

		for (match, mask, ttype) in self.__ttypes:
			if (val & mask) == (match & mask):
				return ttype[1]

		raise ValueError("Invalid ttype %x tsize %x" % ttype, tsize)

	def cresp_lookup(self, ttype, tsize, cresp_ttype):
		group = self.group_lookup(ttype,tsize)
                dict_lookup = self.__ttype_dict_lookup[group]
		if cresp_ttype in dict_lookup:
        	        return dict_lookup[cresp_ttype]
		else:
			print "Can't find " + str(cresp_ttype) + " in " + str(group)
			return -1
		

		


if __name__ == '__main__':
	tt = ttypes()
#	print tt.lookup(0, 0x20)
