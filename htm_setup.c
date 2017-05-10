#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <inttypes.h>

#include "xscom.h"
#include "htm.h"
#define ERR(fmt...)     do { fprintf(stderr, fmt); fflush(stderr); } while(0)
#define DBG(fmt...)     do { if (verbose) printf(fmt); } while(0)
#define MAX_TIMEOUT 5
#define QUEUE_SIZE 16
#define MEG 0x100000

uint64_t parse_mem_size(uint64_t i_memsize, bool *i_use_small_mem)
{
	uint64_t memsize;
	*i_use_small_mem=false;
	char buf[20];
	memsize = i_memsize / MEG;
	if (memsize < 1024){
		snprintf(buf, sizeof buf, "%"PRIu64, memsize);
		strcat(buf,"M");
		DBG("memsize %s\n",buf);
	}else{
		memsize = memsize / 1024;
		snprintf(buf, sizeof buf, "%"PRIu64, memsize);
		strcat(buf,"G");
	}

	if (strcasecmp(buf, "16M") == 0) {memsize = HTM_512M_OR_16M;*i_use_small_mem=true;}
	else if (strcasecmp(buf, "32M") == 0) {memsize = HTM_512M_OR_16M;*i_use_small_mem=true;}
	else if (strcasecmp(buf, "32M") == 0) {memsize = HTM_1G_OR_32M;*i_use_small_mem=true;}
	else if (strcasecmp(buf, "64M") == 0) {memsize = HTM_2G_OR_64M;*i_use_small_mem=true;}
	else if (strcasecmp(buf, "128M") == 0) {memsize = HTM_4G_OR_128M;*i_use_small_mem=true;}
	else if (strcasecmp(buf, "256M") == 0) {memsize = HTM_8G_OR_256M;*i_use_small_mem=true;}
	else if (strcasecmp(buf, "512M") == 0) {memsize = HTM_512M_OR_16M;}
	else if (strcasecmp(buf, "1G") == 0) {memsize = HTM_1G_OR_32M;}
	else if (strcasecmp(buf, "2G") == 0) {memsize = HTM_2G_OR_64M;}
	else if (strcasecmp(buf, "4G") == 0) {memsize = HTM_4G_OR_128M;}
	else if (strcasecmp(buf, "8G") == 0) {memsize = HTM_8G_OR_256M;}
	else if (strcasecmp(buf, "16G") == 0) {memsize = HTM_16G_OR_512M;}
	else if (strcasecmp(buf, "32G") == 0) {memsize = HTM_32G_OR_1G;}
	else if (strcasecmp(buf, "64G") == 0) {memsize = HTM_64G_OR_2G;}
	else if (strcasecmp(buf, "128G") == 0) {memsize = HTM_128G_OR_4G;}
	else if (strcasecmp(buf, "256G") == 0) {memsize = HTM_256G_OR_8G;}
	else {
		fprintf(stderr, "Failed to find a valid memory configuration for %s \n",buf);
		exit(1);
	}
	return memsize;
}

int wait_until_ready(uint32_t i_target, int i_htm_type)
{
	int rc, timer;
	uint64_t data=0;
	timer=0;
	do {
		rc=htm_read_xscom(i_target, HTM_STAT, i_htm_type, &data);
		if (rc) {
			ERR("xscom HTM_MEM read failed, rc=%d\n", rc);
			return -1;
		}
		timer++;
		sleep(1);
		if(timer == MAX_TIMEOUT){
			ERR("Timed out waiting for HTM_STAT_READY");
			return -1;
		}
		printf("DATA RECEIVED %llx \n", data);
	} while(!(data & HTM_STAT_READY));
	printf("Congratulations, HTM has reached ready state\n");
	return 0;
}

int set_htm_mem(uint32_t i_target, int i_htm_type, uint64_t i_mem_base, uint64_t i_mem_size, bool i_use_small_mem_size)
{
	/* Prepare to set HTM_MEM register */
	int rc;
	uint64_t data;
	printf("Target is still %d \n", i_htm_type);
	/*First we need to ensure HTM_MEM_ALLOC=0*/
	rc=htm_read_xscom(i_target, HTM_MEM, i_htm_type, &data);
	if (rc) {
		ERR("1xscom HTM_MEM read failed, rc=%d\n", rc);
		return -1;
	}

	/* initially set HTM_MEM_ALLOC to 0.  The transition to 1 will notify
	   htm that the trace memory information has been updated            */
	data &= ~HTM_MEM_ALLOC; 
	rc=htm_write_xscom(i_target, HTM_MEM, i_htm_type, data);
	if (rc) {
		ERR("1xscom HTM_MEM write failed, rc=%d\n", rc);
		return -1;
	}

	data = 0;
	/* Read scom back after setting the HTM_MEM_ALLOC off */
	rc=htm_read_xscom(i_target, HTM_MEM, i_htm_type, &data);
	if (rc) {
		ERR("2xscom HTM_MEM read failed, rc=%d\n", rc);
		return -1;
	}

	if (i_use_small_mem_size){
		 /*      rc=htm_read_xscom(i_ex_target, HTM_MEM, i_htm_type, &data);*/
		DBG("Using Small Memory \n");
		data |= HTM_MEM_SIZE_SMALL;
	} else {
		DBG("Using Large Memory \n");}
	data = SETFIELD(HTM_MEM_BASE, data, (i_mem_base>>24));
	data = SETFIELD(HTM_MEM_SIZE, data, i_mem_size);
	data |= HTM_MEM_ALLOC;

	rc=htm_write_xscom(i_target, HTM_MEM, i_htm_type, data);
	if (rc) {
		ERR("xscom HTM_MEM write failed, rc=%d\n", rc);
		return -1;
	}
	rc=htm_read_xscom(i_target, HTM_MEM, i_htm_type, &data);
	if (rc) {
		ERR("xscom HTM_MEM read failed, rc=%d\n", rc);
		return -1;
	}
	/*	printf("After it all HTM_MEM is %"PRIx64"\n",data);*/
	return 0;
}

int update_mcs_regs(uint32_t i_target, uint32_t reserve_queue)
{
	int rc;
	uint64_t data;
	uint32_t cpu_id = i_target >> 4;
	rc=xscom_read(i_target, MCS4_MCFGPQ, &data);
	if (data & MCS_VALID){
		/* Set number of CL's to reserve */
		printf("MCS4 is valid and ready to go\n");
		rc=xscom_read(cpu_id, MCS4_MCMODE, &data);
                if (rc) {
			ERR("xscom MCS4_MCMODE read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		rc=xscom_write(cpu_id, MCS4_MCMODE, data);
                if (rc) {
			ERR("xscom MCS4_MCMODE write failed, rc=%d\n", rc);
			return -1;
 		}
	
		/*Disable timeout in memory controller */
		rc=xscom_read(cpu_id, MCS4_FIRMASK, &data);
                if (rc) {
			ERR("xscom MCS4_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}
		data |= MCS_FIRMASK_DISABLE_TIMEOUT;
		rc=xscom_write(cpu_id, MCS4_FIRMASK, data);
                if (rc) {
			ERR("xscom MCS4_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}

	}


	rc=xscom_read(i_target, MCS5_MCFGPQ, &data);
	if (data & MCS_VALID){
		printf("MCS5 is valid and ready to go\n");

		/* Set number of CL's to reserve */
		rc=xscom_read(i_target, MCS5_MCMODE, &data);
                if (rc) {
			ERR("xscom MCS5_MCMODE read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		rc=xscom_write(i_target, MCS5_MCMODE, data);
                if (rc) {
			ERR("xscom MCS5_MCMODE write failed, rc=%d\n", rc);
			return -1;
 		}
		
		/*Disable timeout in memory controller */
		rc=xscom_read(i_target, MCS5_FIRMASK, &data);
                if (rc) {
			ERR("xscom MCS5_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}
		data |= MCS_FIRMASK_DISABLE_TIMEOUT;
		rc=xscom_write(i_target, MCS5_FIRMASK, data);
                if (rc) {
			ERR("xscom MCS5_FIRMASK write failed, rc=%d\n", rc);
			return -1;
 		}
	}


	rc=xscom_read(i_target, MCS6_MCFGPQ, &data);
	if (data & MCS_VALID){
		printf("MCS6 is valid and ready to go\n");

		/* Set number of CL's to reserve */
		rc=xscom_read(i_target, MCS6_MCMODE, &data);
                if (rc) {
			ERR("xscom MCS6_MCMODE read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		rc=xscom_write(i_target, MCS6_MCMODE, data);
                if (rc) {
			ERR("xscom MCS6_MCMODE write failed, rc=%d\n", rc);
			return -1;
 		}
		
		/*Disable timeout in memory controller */
		rc=xscom_read(i_target, MCS6_FIRMASK, &data);
                if (rc) {
			ERR("xscom MCS6_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}
		data |= MCS_FIRMASK_DISABLE_TIMEOUT;
		rc=xscom_write(i_target, MCS6_FIRMASK, data);
                if (rc) {
			ERR("xscom MCS6_FIRMASK write failed, rc=%d\n", rc);
			return -1;
 		}
	}


	rc=xscom_read(i_target, MCS7_MCFGPQ, &data);
	if (data & MCS_VALID){
		printf("MCS7 is valid and ready to go\n");
		
		/* Set number of CL's to reserve */
		rc=xscom_read(i_target, MCS7_MCMODE, &data);
                if (rc) {
			ERR("xscom MCS7_MCMODE read failed, rc=%d\n", rc);
			return -1;
 		}

		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		rc=xscom_write(i_target, MCS7_MCMODE, data);
                if (rc) {
			ERR("xscom MCS7_MCMODE write failed, rc=%d\n", rc);
			return -1;
 		}
		
		/*Disable timeout in memory controller */
		rc=xscom_read(i_target, MCS7_FIRMASK, &data);
                if (rc) {
			ERR("xscom MCS7_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}
		data |= MCS_FIRMASK_DISABLE_TIMEOUT;
		rc=xscom_write(i_target, MCS7_FIRMASK, data);
                if (rc) {
			ERR("xscom MCS7_FIRMASK write failed, rc=%d\n", rc);
			return -1;
 		}
	}
	return 0;

}


int htm_setup(struct htm_args i_args)
{

/*int htm_setup(uint32_t i_ex_target, int i_htm_type, bool i_nowrap, bool i_precise)
{*/
	int rc;
	uint64_t data, mem_size, mem_base, mod_mem_size;
	uint64_t target_reg;
	bool use_small_mem_size;

	mem_size = get_mem_size(i_args.target);
	mod_mem_size = parse_mem_size(mem_size, &use_small_mem_size);
	mem_base = get_mem_start(i_args.target);
	rc=htm_read_xscom(i_args.target, HTM_STAT, i_args.htm_type, &data);

	if(!(data & HTM_STAT_COMPLETE) && !(data & HTM_STAT_REPAIR) && (data))
	{
		printf("Huge error, data not in complete, repair, or blank state\n");
		exit(1);
	}
/*	printf("You're lucky, we're ready to proceed\n");*/

	/* Prepare to set HTM_MEM register */
	data = 0;

	/* Setup MCS buffer reservation for HTM */
	
	update_mcs_regs(i_args.target,8);
	rc = set_htm_mem(i_args.target, i_args.htm_type, mem_base, mod_mem_size, use_small_mem_size);

	/* start with clean slate */
	data = 0;


	if(!i_args.nowrap){
		/* Enable wrap mode */
		data |= HTM_MODE_WRAP_MODE;
	}
	/* Software enable of htm trace */
	data |= HTM_MODE_TRACE_ENABLE;

	if (i_args.htm_type == HTM_LLAT){
		data = 	SETFIELD(HTM_MODE_CONTENT_SEL, data, HTM_MODE_CONTENT_SEL_CHTM_LLAT);
	data = 	SETFIELD(HTM_MODE_CAPTURE, data, 0b001000000);
		rc=htm_write_xscom(i_args.target, HTM_MODE, i_args.htm_type, data);

	data = 0;
	data |= HTM_MODE_TRACE_ENABLE;
	target_reg = 0x10010C0A + ((i_args.target & 0xf)*CORE_MULTIPLIER);
	printf("we are targetting %llx with %llx \n",target_reg, data);
	rc=xscom_write((i_args.target>>4), target_reg, data);
	} else 	if (i_args.htm_type == HTM_FABRIC){
		/* Set Trace mode to use fabric */
		data = 	SETFIELD(HTM_MODE_CONTENT_SEL, data, HTM_MODE_CONTENT_SEL_NHTM_FABRIC);
		data = 	SETFIELD(HTM_MODE_CAPTURE, data, 0b010000000);

		if(i_args.precise)
			data |=	HTM_MODE_PRECISE_MODE;
		rc=htm_write_xscom(i_args.target, HTM_MODE, i_args.htm_type, data);
		if (rc) {
			ERR("xscom HTM_MODE write failed, rc=%d\n", rc);
	                return -1;
		}

	/* IS NEST Filtering Supported yet? */
	rc=htm_read_xscom(i_args.target, NHTM_FILT, i_args.htm_type, &data);
	data = SETFIELD(HTM_FILT, data, 0xfffff);
	rc=htm_write_xscom(i_args.target, NHTM_FILT, i_args.htm_type, data);

/* TODO: pervasive misc is off by default  make a flag*/
	rc=htm_read_xscom(i_args.target, NHTM_TTYPE_FILT, i_args.htm_type, &data);
	data = SETFIELD(HTM_TTYPE_MASK, data, 0xff);
	data = SETFIELD(HTM_TSIZE_MASK, data, 0xff);
	/*data |= HTM_TTYPE_INVERT;
	data = SETFIELD(HTM_TTYPE_PAT, data, 0b110001);
	data = SETFIELD(HTM_TSIZE_PAT, data, 0b1000000);*/
	rc=htm_write_xscom(i_args.target, NHTM_TTYPE_FILT, i_args.htm_type, data);
	    if (rc) {
                ERR("xscom HTM_MODE write failed, rc=%d\n", rc);
                return -1;
        }

	}
	rc=htm_reset(i_args.target, i_args.htm_type);
     	if (rc) {
               	ERR("HTM TRIGGER RESET failed, rc=%d\n", rc);	                
		return -1;
        }
	wait_until_ready(i_args.target, i_args.htm_type);	
	/*Reset trigget in HTM_TRIG */

return 0;	
}
