#!/usr/bin/python

import re

class ttypes:

	__ttype_Read_str = {
	0b00000 : 'addr_error',
	0b00001 : 'go_Me:ed',
	0b00010 : 'go_Me:lpc',
#	0b00011 : 'go_Me_cond:ed',
	0b00011 : 'go_Mu:ed',
	0b00100 : 'go_Sl:T',
#	0b00101 : 'go_Mu_ed',
	0b00101 : 'go_Sl:ed',
	0b00110 : 'go_Sl:lpc',
#	0b00111 : 'go_Mu_cond:ed',
	0b00111 : 'go_S:T',
#	0b01000 : 'go_Sl:T',
#	0b01001 : 'go_Sl:ed',
	0b01001 : 'go_Me_cond:ed',
#	0b01010 : 'go_Sl:lpc',
#	0b01011 : 'go_Sl_cond:ed',
#	0b01100 : 'go_S:T',
	0b01100 : 'go_Mu_cond:ed',
	0b01101 : 'go_Sl_cond:T',
#	0b01111 : 'go_S_cond:T',
	0b01111 : 'go_Sl_cond:ed',
	0b10011 : 'go_S_cond:T',
	0b10100 : 'abort_trm',
	0b10111 : 'rty_lpc_only',
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
#       0b00101 : 'go_Mu_bk:ed',
        0b00101 : 'go_M_bk:ed',
#       0b00110 : 'go_Mu_bk:lpc',
        0b00110 : 'go_M_bk:lpc',
#       0b00111 : 'go_Mu_bk:T',
        0b00111 : 'go_M_bk:T',
        0b01001 : 'go_M_bk_inc:ed',
        0b01011 : 'go_M_bk_inc:T',
        0b01101 : 'go_M_bk_cond:ed',
        0b01110 : 'go_M_bk_inc_cond:T',
        0b01111 : 'go_M_bk_cond:T',
        0b10100 : 'abort_trm',
        0b10101 : 'abort_trm_ed',
	0b10111 : 'rty_lpc_only',
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
	0b10111 : 'rty_lpc_only',
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
#       0b01011 : 'addr_hpc_ack_bk_inc',
	0b10111 : 'rty_lpc_only',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
	0b11010 : 'rty_hpc_lpc_only',
	0b11011 : 'rty_hpc_inc',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

#        __ttype_FCI_str = { # was in P8
#        0b00000 : 'addr_error',
#        0b00011 : 'addr_ack_resend',
#        0b00100 : 'addr_ack_done',
#        0b00101 : 'addr_hpc_ack_resend_inc',
#        0b00110 : 'addr_hpc_ack_done',
#        0b00111 : 'addr_hpc_ack_resend',
#        0b01000 : 'addr_ack_bk',
#        0b01010 : 'addr_hpc_ack_bk',
#        0b01011 : 'addr_hpc_ack_bk_inc',
#        0b11000 : 'rty',
#        0b11001 : 'rty_inc',
#        0b11100 : 'rty_drp',
#        0b11111 : 'ack_dead'
#        }

        __ttype_Inject_str = {
        0b00000 : 'addr_error',
	0b00100 : 'addr_ack_done',
        0b00110 : 'addr_hpc_ack_done',
	0b01000 : 'addr_ack_bk',
        0b01010 : 'addr_hpc_ack_bk',
#       0b01011 : 'addr_hpc_ack_bk_inc',
	0b10111 : 'rty_lpc_only',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11010 : 'rty_dma_w',
	0b11011 : 'rty_hpc_inc',
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
#       0b00000 : 'addr_error',
        0b00001 : 'target:no_data',
        0b00010 : 'Sl:no_data',
        0b00100 : 'target:data',
        0b01001 : 'hpc:no_data',
        0b11000 : 'rty',
	0b11010 : 'target:rty_short',
	0b11011 : 'target:rty_long',
#       0b11100 : 'rty_drp',
        }

        __ttype_Ack_BK_str = {
        0b00000 : 'addr_error',
        0b00100 : 'addr_ack_done',
        0b01000 : 'addr_ack_bk',
        0b10100 : 'abort_trm',
	0b10111 : 'rty_lpc_only',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

        __ttype_Ack_str = {
        0b00000 : 'addr_error',
        0b00100 : 'addr_ack_done',
	0b10111 : 'rty_lpc_only',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11100 : 'rty_drp',
        0b11111 : 'ack_dead'
        }

	__ttype_Poll_str = { # new in P9
	0b00000 : 'poll_error',
	0b00100 : 'ack_done',
	0b00101 : 'ack_none',
	0b00111 : 'assign_7',
	0b01000 : 'assign_8',
	0b01001 : 'assign_9',
	0b01010 : 'assign_a',
	0b01011 : 'assign_b',
	0b01100 : 'assign_c',
	0b01101 : 'assign_d',
	0b01110 : 'assign_e',
	0b01111 : 'assign_f',
	0b10000 : 'assign_0',
	0b10001 : 'assign_1',
	0b10010 : 'assign_2',
	0b10011 : 'assign_3',
	0b10100 : 'assign_4',
	0b10101 : 'assign_5',
	0b10110 : 'assign_6',
	0b11000 : 'rty',
	0b11100 : 'rty_drp'
	}

        __ttype_TM_str = {
        0b00000 : 'no_tk_mgr',
        0b00100 : 'ack_done',
        0b11000 : 'rty',
	0b11001 : 'rty_op',
        0b11100 : 'rty_drp',
	0b11111 : 'ack_dead'
        }

        __ttype_Cop_str = {
        0b00000 : 'addr_error',
        0b00010 : 'addr_ack_hpc',
        0b11000 : 'rty',
        0b11001 : 'rty_inc',
        0b11100 : 'rty_drp',
	0b11111 : 'ack_dead'
        }

	__ttype_RMA_str = { # new in P9
	0b00000 : 'addr_error',
	0b00100 : 'ack_initiated',
	0b00101 : 'ack_query',
	0b00110 : 'ack_query_abort',
	0b10100 : 'ack_busy',
	0b10101 : 'ack_reject',
	0b11000 : 'rty',
	0b11001 : 'rty_inc',
	0b11010 : 'ack_rty',
	0b11100 : 'rty_drp',
	0b11111 : 'ack_dead'
	}

	__ttypes_P9_str = {
#		<Command class><Secondary encode> : [<mnemonic>, <command group>]
#		See the documentation for each mnemonic in the PowerBus Arch document. 
#		The existing encoding is based on v3. The modified one should be based on v4.
#		'00000001qttsh' : ['rd_go_s','read'], As per v3 PB arch
		'000000001httsq0' : ['rd_go_s','read'], # As per v4 PB arch

#		'00000010qttsh' : ['rd_go_m','read'],
		'000000010httsqm' : ['rd_go_m','read'],

#		'0000001(eh)0httsq0' : ['rd_larx','read'],
                '0000001i0httsq0' : ['rd_larx','read'], # 'i' -> (eh) hint bit

		'000001000h00sq1' : ['rd_me_64','read'],

#		'00000100padeh' : ['cl_dma_rd','read'],
#		'0000011000(cl0)(cl1)nd0' : ['cl_dma_rd','read'],
		'0000011000ccnd0' : ['cl_dma_rd','read'], # 'cc' denotes (cl0)(cl1)

#		'00001001padeh' : ['pref_go_s','read'],
#		'0000100(sw_pf)(ld_pr)h(cl0)(cl1)nd0' : ['pref_go_s','read'],
		'0000100wlhccnd0' : ['pref_go_s','read'], # 'w'->(sw_pf),'l'->(ld_pr)

#		'00001010padeh' : ['pref_go_m','read'],
#		'0000101(sw_pf)(ld_pr)h(cl0)(cl1)ndm' : ['pref_go_m','read'],
		'0000101wlhccndm' : ['pref_go_m','read'],

#		'00001100padeh' : ['cl_rd_nc','read'],
#		'0000110F00(cl0)(cl1)nd0' : ['cl_rd_nc','read'],
		'0000110F00ccnd0' : ['cl_rd_nc','read'],

#		'000101c000000' : ['cl_probe','pcl'],
		'0000111xxxxxxxx' : ['cl_probe','pcl'],

#		'00100000qttsh' : ['rwitm','rwitm'],
		'000100000httsqm' : ['rwitm','rwitm'],

		'000100100httsq0' : ['rwitm_stwx','rwitm'],

#		'00110000qtt00' : ['dclaim','claim'],
		'0001100000tt000' : ['dclaim','claim'],

		'0001100010tt000' : ['dclaim_stwx','claim'],

#		'00110100qtt00' : ['dcbz','claim'],
		'0001101000tt000' : ['dcbz','claim'],

#		'01110000xxxxx' : ['cl_dma_w_i','write'],

		'001110000xxxxxx' : ['cl_dma_w','write'],

#		'01110010xxxxx' : ['cl_dma_w_hp','write'],
		'001110010xxxxxx' : ['cl_dma_w_hp','write'],

#		'01111000xxxxx' : ['cl_dma_inj','inj'],
		'001111000xxxxxx' : ['cl_dma_inj','inj'],

#		'011111xxxxxxx' : ['pr_dma_inj','inj'],
		'0011111xxxxxxx0' : ['pr_dma_inj','inj'],

#		'01000001pSSSL' : ['tlbi_op','tm'],
		'001000001pSSSSF' : ['tlbi_op1','tm'],
		'001000010pSSSS1' : ['tlbi_op2','tm'],

#		'0100001000000' : ['tlbi_t','tm'],
		'001000000000000' : ['tlbi_t','tm'],

#		'01000011pSSS0' : ['tlbi_set','tm'],
		'001000011pSSSS0' : ['tlbi_set','tm'],

		'001000100000000' : ['slbi_t','tm'],

		'001000101pSSSSF' : ['slbi_op1','tm'],

		'001000110pSSSS1' : ['slbi_op2','tm'],

		'001000111pSSSS0' : ['slbi_set','tm'],

#		'0100010100IGL' : ['tlbivax_op','tm'],
#		'0100011000000' : ['tlbivax_t','tm'],
#		'0100101000000' : ['msgsnd_t','tm'],
#		'0100110100000' : ['icbi_op','tm'],
#		'0100111000000' : ['icbi_t','tm'],

#		'0101000000000' : ['cp_m','cpwrite'],
		'00101000000000m' : ['cp_m','cpwrite'],

#		'0101000000001' : ['cp_t','cpwrite'],
		'00101000000001m' : ['cp_t','cpwrite'],

#		'0101000000010' : ['cp_tn','cpwrite'],
		'00101000000011m' : ['cp_tn','cpwrite'],

#		'0101000010000' : ['hca.hpc_act_updt','cpwrite'],
		'001010000100000' : ['hca.hpc_act_updt','cpwrite'],

#		'0101000100000' : ['hca.hpc_ref_updt','cpwrite'],
		'001010001000000' : ['hca.hpc_ref_updt','cpwrite'],

#		'0101000110000' : ['hca.hpc_dcy_updt','cpwrite'],
		'001010001100000' : ['hca.hpc_dcy_updt','cpwrite'],

#		'0101001000000' : ['htm_cl_w','cpwrite'],
		'001010010000000' : ['htm_cl_w','cpwrite'],

#		'0101010000000' : ['cp_ig','cpwrite'],
		'001010100000000' : ['cp_ig','cpwrite'],

#		'0101011000000' : ['cp_me','cpwrite'],
		'001010110000000' : ['cp_me','cpwrite'],

#		'0101100000000' : ['cl_w_cln_m','cpwrite'],
#		'0101100000001' : ['cl_w_cln_t','cpwrite'],
#		'0101100000010' : ['cl_w_cln_tn','cpwrite'],

#		'01100001ttttt' : ['lco_ig','lco'],
		'001100001ttttt0' : ['lco_ig','lco'],

#		'01100101ttttt' : ['lco_sl','lco'],
		'001100101ttttt0' : ['lco_sl','lco'],

#		'01101000ttttt' : ['lco_t','lco'],
		'001101000ttttt0' : ['lco_t','lco'],

#		'01101001ttttt' : ['lco_te','lco'],
		'001101001ttttt0' : ['lco_te','lco'],

#		'01101010ttttt' : ['lco_tn','lco'],
		'001101010ttttt0' : ['lco_tn','lco'],

#		'01101011ttttt' : ['lco_ten','lco'],
		'001101011ttttt0' : ['lco_ten','lco'],

#		'01101100ttttt' : ['lco_m','lco'],
		'001101100tttttm' : ['lco_m','lco'],

#		'01101101ttttt' : ['lco_me','lco'],
		'001101101tttttm' : ['lco_me','lco'],

#		'01101110ttttt' : ['lco_mu','lco'],
		'001101110tttttm' : ['lco_mu','lco'],

#		'01110100ttttt' : ['cl_fci_w_i','fci'], # No FCI in P9
#		'01110101ttttt' : ['cl_fci_w_t','fci'],

#		'1000000000001' : ['dcbfl','claim'],

		'010000000000010' : ['dcbfl','ack_bk'],

		'010000000000100' : ['dcbf','ack_bk'],

#		'1000000000011' : ['dcbfc','ack_bk'],
		'010000000000110' : ['dcbfc','ack_bk'],

#		'100000c001010' : ['dcbfk','ack_bk'],
		'010000000010100' : ['dcbfk','ack_bk'],

#		'1000000000110' : ['dcbi','ack_bk'],

#		'10000100000LL' : ['armw_add','ack_bk'],
		'0100001000000Le' : ['armw_add','ack_bk'],

#		'1000010001100' : ['hca.act_updt','ack_bk'],
		'010000100011000' : ['hca.act_updt','ack_bk'],

		'0100001000111ff' : ['pte_updt2','ack_bk'],

#		'10000100100LL' : ['armw_and','ack_bk'],
		'0100001001000Le' : ['armw_and','ack_bk'],

#		'1000010011100' : ['hca.ref_updt','ack_bk'],
		'010000100111000' : ['hca.ref_updt','ack_bk'],

#		'100001011111f' : ['pte_updt','ack_bk'],
		'0100001001111f0' : ['pte_updt','ack_bk'],

#		'10000101000LL' : ['armw_or','ack_bk'],
		'0100001010000Le' : ['armw_or','ack_bk'],

#		'1000010101100' : ['hca.dcy_updt','ack_bk'],
		'010000101011000' : ['hca.dcy_updt','ack_bk'],

#		'10000101100LL' : ['armw_xor','ack_bk'],
		'0100001011000Le' : ['armw_xor','ack_bk'],

		'0100001100000Le' : ['armw_cas_t','ack_bk'],

		'0100001100010Le' : ['armw_cas_imax_u','ack_bk'],

		'0100001100011Le' : ['armw_cas_imax_s','ack_bk'],

		'0100001100100Le' : ['armw_cas_imin_u','ack_bk'],

		'0100001100101Le' : ['armw_cas_imin_s','ack_bk'],

#		'100010000tt00' : ['bkill','ack_bk'],
		'0100010000tt000' : ['bkill','ack_bk'],

		'0100010000tt010' : ['bkill_stwx','ack_bk'],

#		'100010010tt00' : ['bkill_inc','ack_bk'],
		'0100010010tt000' : ['bkill_inc','ack_bk'],

		'0100010010tt010' : ['bkill_stwx_inc','ack_bk'],

#		'1000101000000' : ['bkill_flush','ack_bk'],
		'010001010000000' : ['bkill_flush','ack_bk'],

		'010001010000001' : ['bkill_wrto','ack_bk'],

		'0100100000000Le' : ['armwf_inc_b','ack_bk'],

		'0100100001000Le' : ['armwf_inc_e','ack_bk'],

		'0100100010000Le' : ['armwf_dec_b','ack_bk'],

#		'100101100ccLL' : ['armwf_cas','ack_bk'],
		'0100100100010Le' : ['armwf_cas_imax_u','ack_bk'],

		'0100100100011Le' : ['armwf_cas_imax_s','ack_bk'],

		'0100100100100Le' : ['armwf_cas_imin_u','ack_bk'],

		'0100100100101Le' : ['armwf_cas_imin_s','ack_bk'],

#		'10010100000LL' : ['armwf_add','ack_bk'],
		'0100101000000Le' : ['armwf_add','ack_bk'],

#		'10010100100LL' : ['armwf_and','ack_bk'],
		'0100101001000Le' : ['armwf_and','ack_bk'],

#		'10010101000LL' : ['armwf_or','ack_bk'],
		'0100101010000Le' : ['armwf_or','ack_bk'],

#		'10010101100LL' : ['armwf_xor','ack_bk'],
		'0100101011000Le' : ['armwf_xor','ack_bk'],

		'0100101100010Le' : ['armwf_cas_e','ack_bk'],

		'0100101100100Le' : ['armwf_cas_ne','ack_bk'],

		'0100101100110Le' : ['armwf_cas_u','ack_bk'],

#		'100110xxxxxxx' : ['dma_pr_w','ack_bk'],
		'0100110xxxxxxx0' : ['dma_pr_w','ack_bk'],

#		'101000iwHPwww' : ['cop_req','cop'],
		'0101000xwHPwww0' : ['cop_req','cop'],

#		'101010i000000' : ['asb_notify','cop'],
#		'101011iaaaaaa' : ['asb_credit_wr','cop'],

		'010110100000000': ['intrp_histogram','ack'],

		'010110100000100': ['intrp_blk_updt','ack'],

		'010111000000000': ['cps_status_req','ack'],

		'010111000000001': ['cps_status_rtn','ack'],

		'010111000000010': ['cps_abort_req','ack'],

		'0101111s0000000': ['hpc_read','ack'],

#		'1100000000000' : ['hca_req.ref_updt','ack'],
		'011000000000000' : ['hca_req.ref_updt','ack'],

#		'1100010000000' : ['pMisc_RESERVED','ack'],
		'011000100000000' : ['pMisc_RESERVED','ack'],

#		'110001xxxxxx1' : ['pMisc_Switch_AB_command','ack'],
		'0110001xxxxxx1x' : ['pMisc_Switch_AB_command','ack'],

#		'110001xxxxx1x' : ['pMisc_Malfunction_Alert_command','ack'],
		'01100010xxxx1x0' : ['pMisc_Malfunction_Alert_command','ack'],

#		'110001xxxx1xx' : ['pMisc_Global_Trace_command','ack'],
		'01100010xxx1xx0' : ['pMisc_Global_Trace_command','ack'],

#		'1100010001xxx' : ['pMisc_TOD_Packet','ack'],
		'01100010001xxx0' : ['pMisc_TOD_Packet','ack'],

#		'1100010010xxx' : ['pMisc_XPCB_Status_Reporting','ack'],

#		'1100010100000' : ['pMisc_HTM_extended_marker_NCU','ack'],
		'011000101000000' : ['pMisc_HTM_extended_marker_NCU','ack'], # extended for pMisc_HTM with xxx set to 000 (14:31)

#		'1100010100xxx' : ['pMisc_HTM','ack'],
		'01100010100xxx0' : ['pMisc_HTM','ack'],

#		'1100011000xxx' : ['pMisc_AxScom','ack'],
		'01100010010xxx0' : ['pMisc_AxScom','ack'],

		'011000110000000' : ['pMisc_PBAx_messaging','ack'],

		'011000100000001' : ['pMisc_Global_PMU_command','ack'], # new in P9

#		'1100100000000' : ['link_chk.data_chk','ack'],
		'011001000000000' : ['link_chk.data_chk','ack'],

#		'1100101000000' : ['link_chk.abort_op','ack'],
		'011001010000000' : ['link_chk.abort_op','ack'],

#		'101010i000000' : ['asb_notify','cop'],
		'0110011xxxxxxxx' : ['asb_notify','ack'],

#		'110100xxxxxxx' : ['ci_pr_rd','ack'],
		'01101000tttsss0' : ['ci_pr_rd','ack'],

		'01101010ttt1000' : ['read_rng','ack'],

#		'110110rtttsss' : ['ci_pr_ooo_w','ack'],
		'0110110rtttsss0' : ['ci_pr_ooo_w','ack'],

#		'110111rtttsss' : ['ci_pr_w','ack'],
		'0110111rtttsss0' : ['ci_pr_w','ack'],

		'011100000000000' : ['tlbi_chk','ack'],

#		'1110000000001' : ['sync','ack'],
		'011100000000010' : ['sync','ack'],

		'011100000000011' : ['pf_promote','ack'],

#		'1110000000010' : ['eieio','ack'],
		'011100000000100' : ['eieio','ack'],

#		'111001xxxxxxx' : ['ptesync','ack'],
		'0111001xxxxxxxx' : ['ptesync','ack'],

		'0111010xxxxxxxx' : ['msgsnd','ack'],

#		'1111010000001' : ['chgrate.hang','ack'],
		'011110100000010' : ['chgrate.hang','ack'],

#		'111101R000010' : ['chgrate.req','ack'],
		'0111101R0000100' : ['chgrate.req','ack'],

#		'111101R000100' : ['chgrate.grant','ack'],
		'0111101R0001000' : ['chgrate.grant','ack'],

#		'1111011000001' : ['chgrate.alert','ack'],
		'011110110000010' : ['chgrate.alert','ack'],

#		'1111100000000' : ['rpt_hang.check','ack'],
		'011111000000000' : ['rpt_hang.check','ack'],

#		'1111100000001' : ['rpt_hang.poll','ack'],
		'011111000000010' : ['rpt_hang.poll','ack'],

#		'1111100000010' : ['rpt_hang.data','ack'],
		'011111000000100' : ['rpt_hang.data','ack'],

#		'111111000xxxx' : ['pbop','ack'],
		'01111110000f000' : ['pbop.disable_all','ack'],

		'01111110000f001' : ['pbop.enable_rCmd_only','ack'],

		'01111110000f010' : ['pbop.enable_data_only','ack'],

		'01111110000f011' : ['pbop.enable_all','ack'],

#		'1111111111111' : ['nop','ack'],
		'011111111111111' : ['nop','ack'],

		'0001111000000ss' : ['intrp_poll','poll'],

		'0001111000001ss' : ['intrp_bcast','poll'],

		'0001111000010ss' : ['intrp_assign','poll'],

		'010011100000000' : ['cl_rma_rd','rma'],

		'01001111000000L' : ['cl_rma_w','rma'],

#		'110011xxxxxxx' : ['cl_cln','ack'],
#		'110101xxxxxxx' : ['dma_pr_rd','ack'],
#		'11101000HPccc' : ['cop_cmd','ack'],
#		'111100xxxxx00' : ['ris_Interrupt_Request','ack'],
#		'111100xxxxx01' : ['ris_Interrupt_Return','ack'],
#		'111100xxxxx10' : ['ris_End_of_Interrupt','ack'],
#		'111100xxxxx11' : ['ris_Interrupt_Forward','ack'],
#		'111110000100u' : ['rpt_hang.fcheck','ack'],
#		'111111000xxxx' : ['pbop','ack'],
#		'111111100xxxx' : ['fpbop','ack'],
	}

	__ttype_P9_dict_lookup = {
		'read'		: __ttype_Read_str,
		'pcl'		: __ttype_PCL_str,
		'rwitm'		: __ttype_RWITM_str,
		'claim'		: __ttype_CLAIM_str,
		'tm' 		: __ttype_TM_str,
		'cpwrite' 	: __ttype_CPWrite_str,
		'lco' 		: __ttype_LCO_str,
		'write'		: __ttype_Write_str,
#		'fci' 		: __ttype_FCI_str, No fci in P9
		'inj' 		: __ttype_Inject_str,
		'ack_bk'	: __ttype_Ack_BK_str,
		'cop'		: __ttype_Cop_str,
		'ack' 		: __ttype_Ack_str,
		'poll'		: __ttype_Poll_str, # new in P9
		'rma'		: __ttype_RMA_str, # new in P9
	}

	__ttypes_P9 = []
	for key in __ttypes_P9_str.keys():
		match = int(re.sub(r'[^01]', '0', key), 2) # Replace all chars that are neither '0' nor '1' with '0'
		mask = re.sub(r'[01]', '1', key) # Replace all 0 and 1 with 1. Leave the non digits as is
		mask = int(re.sub(r'[^01]', '0', mask), 2) # Replace all non digits with 0 in previous mask generated
		__ttypes_P9.append((match, mask, __ttypes_P9_str[key]))


	def lookup(self, ttype, tsize):
#		val = (ttype << 7) | tsize # PB v3. <ttype>:<secondary encode> is mapped as 6:7. Total of 13 bits. In PB v4 this is 7:8
		val = (ttype << 8) | tsize
		for (match, mask, ttype) in self.__ttypes_P9:
			if (val & mask) == (match & mask):
				return ttype[0]	# return the mnemonic
                print('val: %x' %(val))
		raise ValueError("Invalid ttype %x tsize %x" % ttype, tsize)

	def group_lookup(self, ttype, tsize):
#		val = (ttype << 7) | tsize # PB v3. <ttype>:<secondary encode> is mapped as 6:7. Total of 13 bits. In PB v4 this is 7:8
		val = (ttype << 8) | tsize

		for (match, mask, ttype) in self.__ttypes_P9:
			if (val & mask) == (match & mask):
				return ttype[1] # return the group name

		raise ValueError("Invalid ttype %x tsize %x" % ttype, tsize)

	def cresp_lookup(self, ttype, tsize, cresp_ttype):
		group = self.group_lookup(ttype,tsize)
                dict_lookup = self.__ttype_P9_dict_lookup[group]
		if cresp_ttype in dict_lookup:
        	        return dict_lookup[cresp_ttype] # return the cresp mapping 'target:no_data' if cresp passed was 0b00001
		else:
			print "Can't find " + str(cresp_ttype) + " in " + str(group)
			return -1
		

		


if __name__ == '__main__':
#	tt = ttypes()
	tt = ttypes_P9()

	print tt.lookup(0, 0x20)
