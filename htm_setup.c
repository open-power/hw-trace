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
	timer=0;
	uint64_t data=0;
#ifdef P9
	uint64_t data1=0;
	do {
		rc=htm_read_xscom(i_target, HTM_STAT, i_htm_type, &data, &data1);
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
	printf("DATA RECEIVED (data) %llx \n", data);
	printf("DATA RECEIVED (data1) %llx \n", data1);
	}while((!(data & HTM_STAT_READY)) || (!(data1 & HTM_STAT_READY)));
#else
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
	}while(!(data & HTM_STAT_READY));
#endif
	printf("Congratulations, HTM has reached ready state\n");
	return 0;
}

int set_htm_mem(uint32_t i_target, int i_htm_type, uint64_t i_mem_base, uint64_t i_mem_size, bool i_use_small_mem_size)
{
        /* Prepare to set HTM_MEM register */
	int rc;
        uint64_t data;

	memset(&data, 0, sizeof(uint64_t));
#ifdef P9
	uint64_t data1;
	memset(&data1, 0, sizeof(uint64_t));
#endif

	printf("Target is still %d \n", i_htm_type);
	/*First we need to ensure HTM_MEM_ALLOC=0*/
#ifdef P9
	rc=htm_read_xscom(i_target, HTM_MEM, i_htm_type, &data, &data1);
#else
	rc=htm_read_xscom(i_target, HTM_MEM, i_htm_type, &data);
#endif
        if (rc) {
		ERR("1xscom HTM_MEM read failed, rc=%d\n", rc);
                return -1;
        }

	/* initially set HTM_MEM_ALLOC to 0.  The transition to 1 will notify
	   htm that the trace memory information has been updated            */
	data &= ~HTM_MEM_ALLOC; 
#ifdef P9
        rc=htm_write_xscom(i_target, HTM_MEM, i_htm_type, data, data1);
	data1 = 0;
#else
        rc=htm_write_xscom(i_target, HTM_MEM, i_htm_type, data);
#endif
        if (rc) {
		ERR("1xscom HTM_MEM write failed, rc=%d\n", rc);
                return -1;
        }
	
	data = 0;
	/* Read scom back after setting the HTM_MEM_ALLOC off */
#ifdef P9
	data1 = 0;
	rc=htm_read_xscom(i_target, HTM_MEM, i_htm_type, &data, &data1);
#else
	rc=htm_read_xscom(i_target, HTM_MEM, i_htm_type, &data);
#endif
        if (rc) {
		ERR("2xscom HTM_MEM read failed, rc=%d\n", rc);
                return -1;
        }

        if (i_use_small_mem_size){
        /*      rc=htm_read_xscom(i_ex_target, HTM_MEM, i_htm_type, &data);*/
                DBG("Using Small Memory \n");
                data |= HTM_MEM_SIZE_SMALL;
#ifdef P9
                data1 |= HTM_MEM_SIZE_SMALL;
#endif
        }
        else{   DBG("Using Large Memory \n");}

	/* trim out the lower 3 bytes. But why? */
        data = SETFIELD(HTM_MEM_BASE, data, (i_mem_base>>24)); 
        data = SETFIELD(HTM_MEM_SIZE, data, i_mem_size);
        data |= HTM_MEM_ALLOC;
#ifdef P9
        data1 = SETFIELD(HTM_MEM_BASE, data1, (i_mem_base>>24)); 
        data1 = SETFIELD(HTM_MEM_SIZE, data1, i_mem_size);
        data1 |= HTM_MEM_ALLOC;
#endif

#ifdef P9
        rc=htm_write_xscom(i_target, HTM_MEM, i_htm_type, data, data1);
        if (rc) {
		ERR("3xscom HTM_MEM write failed, rc=%d\n", rc);
                return -1;
        }

	data1 = 0;
	data = 0;
	rc=htm_read_xscom(i_target, HTM_MEM, i_htm_type, &data, &data1);
        if (rc) {
		ERR("4xscom HTM_MEM read failed, rc=%d\n", rc);
                return -1;
        }
#else
        rc=htm_write_xscom(i_target, HTM_MEM, i_htm_type, data);
        if (rc) {
		ERR("3xscom HTM_MEM write failed, rc=%d\n", rc);
                return -1;
        }
	rc=htm_read_xscom(i_target, HTM_MEM, i_htm_type, &data);
        if (rc) {
		ERR("4xscom HTM_MEM read failed, rc=%d\n", rc);
                return -1;
        }
#endif
/*	printf("After it all HTM_MEM is %"PRIx64"\n",data);*/
	return 0;

}

#ifdef P9
int update_mcs_regs_P9(uint32_t i_target, uint32_t reserve_queue)
{
	int rc;
	uint64_t data;
	uint32_t cpu_id = i_target >> 4;

	memset(&data, 0, sizeof(uint64_t));
	rc=xscom_read(i_target, MC01PBI01_MCFGPQ, &data);
	if (data & MCS_VALID){
		/* Set number of CL's to reserve */
		printf("MC01PBI01 is valid and ready to go\n");

		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC01P0_MCPERF0, &data);
                if (rc) {
			ERR("xscom MC01P0_MCPERF0 read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		data = SETFIELD(MCS_BUFFER_SEL,data,0);

		rc=xscom_write(cpu_id, MC01P0_MCPERF0, data);
                if (rc) {
			ERR("xscom MC01P0_MCPERF0 write failed, rc=%d\n", rc);
			return -1;
 		}
	
		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC01P1_MCPERF0, &data);
                if (rc) {
			ERR("xscom MC01P1_MCPERF0 read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		data = SETFIELD(MCS_BUFFER_SEL,data,0);

		rc=xscom_write(cpu_id, MC01P1_MCPERF0, data);
                if (rc) {
			ERR("xscom MC01P1_MCPERF0 write failed, rc=%d\n", rc);
			return -1;
 		}

		/*Disable timeout in memory controller */
		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC01PBI01_FIRMASK, &data);
                if (rc) {
			ERR("xscom MC01PBI01_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}
		data |= MCS_FIRMASK_DISABLE_TIMEOUT;
		rc=xscom_write(cpu_id, MC01PBI01_FIRMASK, data);
                if (rc) {
			ERR("xscom MC01PBI01_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}

	}
	else {
		printf("MC01PBI01 is not ready yet. Skipping..\n");
	}

	memset(&data, 0, sizeof(uint64_t));
	rc=xscom_read(i_target, MC01PBI23_MCFGPQ, &data);
	if (data & MCS_VALID){
		/* Set number of CL's to reserve */
		printf("MC01PBI23 is valid and ready to go\n");

		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC01P2_MCPERF0, &data);
                if (rc) {
			ERR("xscom MC01P2_MCPERF0 read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		data = SETFIELD(MCS_BUFFER_SEL,data,0);

		rc=xscom_write(cpu_id, MC01P2_MCPERF0, data);
                if (rc) {
			ERR("xscom MC01P2_MCPERF0 write failed, rc=%d\n", rc);
			return -1;
 		}
	
		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC01P3_MCPERF0, &data);
                if (rc) {
			ERR("xscom MC01P3_MCPERF0 read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		data = SETFIELD(MCS_BUFFER_SEL,data,0);

		rc=xscom_write(cpu_id, MC01P3_MCPERF0, data);
                if (rc) {
			ERR("xscom MC01P3_MCPERF0 write failed, rc=%d\n", rc);
			return -1;
 		}

		/*Disable timeout in memory controller */
		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC01PBI23_FIRMASK, &data);
                if (rc) {
			ERR("xscom MC01PBI23_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}
		data |= MCS_FIRMASK_DISABLE_TIMEOUT;
		rc=xscom_write(cpu_id, MC01PBI23_FIRMASK, data);
                if (rc) {
			ERR("xscom MC01PBI23_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}

	}
	else {
		printf("MC01PBI23 is not ready yet. Skipping..\n");
	}

	memset(&data, 0, sizeof(uint64_t));
	rc=xscom_read(i_target, MC23PBI01_MCFGPQ, &data);
	if (data & MCS_VALID){
		/* Set number of CL's to reserve */
		printf("MC23PBI01 is valid and ready to go\n");

		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC23P0_MCPERF0, &data);
                if (rc) {
			ERR("xscom MC23P0_MCPERF0 read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		rc=xscom_write(cpu_id, MC23P0_MCPERF0, data);
                if (rc) {
			ERR("xscom MC23P0_MCPERF0 write failed, rc=%d\n", rc);
			return -1;
 		}
	
		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC23P1_MCPERF0, &data);
                if (rc) {
			ERR("xscom MC23P1_MCPERF0 read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		rc=xscom_write(cpu_id, MC23P1_MCPERF0, data);
                if (rc) {
			ERR("xscom MC23P1_MCPERF0 write failed, rc=%d\n", rc);
			return -1;
 		}

		/*Disable timeout in memory controller */
		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC23PBI01_FIRMASK, &data);
                if (rc) {
			ERR("xscom MC23PBI01_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}
		data |= MCS_FIRMASK_DISABLE_TIMEOUT;
		rc=xscom_write(cpu_id, MC23PBI01_FIRMASK, data);
                if (rc) {
			ERR("xscom MC23PBI01_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}

	}
        else {
                printf("MC23PBI01 is not ready yet. Skipping..\n");
        }

	memset(&data, 0, sizeof(uint64_t));
	rc=xscom_read(i_target, MC23PBI23_MCFGPQ, &data);
	if (data & MCS_VALID){
		/* Set number of CL's to reserve */
		printf("MC23PBI23 is valid and ready to go\n");

		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC23P2_MCPERF0, &data);
                if (rc) {
			ERR("xscom MC23P2_MCPERF0 read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		rc=xscom_write(cpu_id, MC23P2_MCPERF0, data);
                if (rc) {
			ERR("xscom MC23P2_MCPERF0 write failed, rc=%d\n", rc);
			return -1;
 		}
	
		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC23P3_MCPERF0, &data);
                if (rc) {
			ERR("xscom MC23P3_MCPERF0 read failed, rc=%d\n", rc);
			return -1;
 		}
		data = SETFIELD(MCS_BUFFER,data,reserve_queue);
		rc=xscom_write(cpu_id, MC23P3_MCPERF0, data);
                if (rc) {
			ERR("xscom MC23P3_MCPERF0 write failed, rc=%d\n", rc);
			return -1;
 		}

		/*Disable timeout in memory controller */
		memset(&data, 0, sizeof(uint64_t));
		rc=xscom_read(cpu_id, MC23PBI23_FIRMASK, &data);
                if (rc) {
			ERR("xscom MC23PBI23_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}
		data |= MCS_FIRMASK_DISABLE_TIMEOUT;
		rc=xscom_write(cpu_id, MC23PBI23_FIRMASK, data);
                if (rc) {
			ERR("xscom MC23PBI23_FIRMASK read failed, rc=%d\n", rc);
			return -1;
 		}

	}
        else {
                printf("MC23PBI23 is not ready yet. Skipping..\n");
        }

	return 0;

}
#else
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
#endif

int htm_setup(struct htm_args i_args)
{

/*int htm_setup(uint32_t i_ex_target, int i_htm_type, bool i_nowrap, bool i_precise)
{*/
	int rc;
	uint64_t data, mem_size, mem_base, mod_mem_size;
#ifdef P9
	uint64_t data1; /* P9, extra NHTM */
#endif
	uint64_t target_reg;
	bool use_small_mem_size;

	mem_size = get_mem_size(i_args.target);
	/* Small sizes are classified similarly on P8 and P9 */
	mod_mem_size = parse_mem_size(mem_size, &use_small_mem_size);
	mem_base = get_mem_start(i_args.target);
#ifdef P9
	rc=htm_read_xscom(i_args.target, HTM_STAT, i_args.htm_type, &data, &data1); /* for NHTM0 and 1 */
#else
	rc=htm_read_xscom(i_args.target, HTM_STAT, i_args.htm_type, &data);
#endif

	if(!(data & HTM_STAT_COMPLETE) && !(data & HTM_STAT_REPAIR) && (data))
	{
		printf("Huge error, data not in complete, repair, or blank state\n");
		exit(1);
	}
#ifdef P9
	if(!(data1 & HTM_STAT_COMPLETE) && !(data1 & HTM_STAT_REPAIR) && (data1))
	{
		printf("Huge error, data1 not in complete, repair, or blank state\n");
		exit(1);
	}
	data1 = 0;
#endif
/*	printf("You're lucky, we're ready to proceed\n");*/

	/* Prepare to set HTM_MEM register */
	data = 0;

	/* Setup MCS buffer reservation for HTM */
	/* Same number of reservation queus per MCS on P9? */	
	/* Need the addresses for MCS0-3 on P9! */
#ifdef P9
	update_mcs_regs_P9(i_args.target,8);
#else
	update_mcs_regs(i_args.target,8);
#endif

	rc = set_htm_mem(i_args.target, i_args.htm_type, mem_base, mod_mem_size, use_small_mem_size);

	/* start with clean slate */
	data = 0;

#ifdef P9
	data1 = 0;
#endif

	if(!i_args.nowrap){
		/* Enable wrap mode */
		data |= HTM_MODE_WRAP_MODE;
#ifdef P9
		data1 |= HTM_MODE_WRAP_MODE;
#endif
	}
	/* Software enable of htm trace */
	data |= HTM_MODE_TRACE_ENABLE;
#ifdef P9
	data1 |= HTM_MODE_TRACE_ENABLE;
#endif
//FIXME: Need to add code to perform special wakeup on all cores in target chip.
//putscom pu.ex -all 100f010b 0 1 1 -ib 
	if (i_args.htm_type == HTM_LLAT){
		data = 	SETFIELD(HTM_MODE_CONTENT_SEL, data, HTM_MODE_CONTENT_SEL_CHTM_LLAT);
	data = 	SETFIELD(HTM_MODE_CAPTURE, data, 0b001000000);
		rc=htm_write_xscom(i_args.target, HTM_MODE, i_args.htm_type, data);

	data = 0;
	data |= HTM_MODE_TRACE_ENABLE;
	target_reg = 0x10010C0A + ((i_args.target & 0xf)*CORE_MULTIPLIER);
	printf("we are targetting %llx with %llx \n",target_reg, data);
	rc=xscom_write((i_args.target>>4), target_reg, data);
        
        data = 0x8000000000000000;
	target_reg = 0x100f010b + ((i_args.target & 0xf)*CORE_MULTIPLIER);
	rc=xscom_write((i_args.target>>4), target_reg, data);

	} else 	if (i_args.htm_type == HTM_FABRIC){
		/* Set Trace mode to use fabric */
		data = 	SETFIELD(HTM_MODE_CONTENT_SEL, data, HTM_MODE_CONTENT_SEL_NHTM_FABRIC);
		/* bit 5 (HTM_CAPTURE bit 1) remains as is in P9 */
		data = 	SETFIELD(HTM_MODE_CAPTURE, data, 0b010000000);

#ifdef P9
		data1 =	SETFIELD(HTM_MODE_CONTENT_SEL, data1, HTM_MODE_CONTENT_SEL_NHTM_FABRIC);
		data1 = SETFIELD(HTM_MODE_CAPTURE, data1, 0b010000000);
#endif
		if(i_args.precise) {
			data |=	HTM_MODE_PRECISE_MODE; /* Is this bit 6 or 6:7 ? */
#ifdef P9
			data1 |=HTM_MODE_PRECISE_MODE; /* Is this bit 6 or 6:7 ? */
#endif
		}
		/* Will write data into NHTM0 (and data1 into NHTM1) + HTM_MODE if P9 */
#ifdef P9
		rc=htm_write_xscom(i_args.target, HTM_MODE, i_args.htm_type, data, data1);
#else
		rc=htm_write_xscom(i_args.target, HTM_MODE, i_args.htm_type, data);
#endif
		if (rc) {
			ERR("xscom HTM_MODE write failed, rc=%d\n", rc);
	                return -1;
		}

	/* IS NEST Filtering Supported yet? */
	data = 0;
#ifdef P9
	data1 = 0;
	rc=htm_read_xscom(i_args.target, NHTM_FILT, i_args.htm_type, &data, &data1);
#else
	rc=htm_read_xscom(i_args.target, NHTM_FILT, i_args.htm_type, &data);
#endif

#ifdef P9
	data = SETFIELD(HTM_FILT, data, 0x7fffff); /* bits 0..22 */
	data1 = SETFIELD(HTM_FILT, data1, 0x7fffff);
#else
	data = SETFIELD(HTM_FILT, data, 0xfffff); /* bits 0..19 */
#endif

#ifdef P9
	rc=htm_write_xscom(i_args.target, NHTM_FILT, i_args.htm_type, data, data1);
#else
	rc=htm_write_xscom(i_args.target, NHTM_FILT, i_args.htm_type, data);
#endif

/* TODO: pervasive misc is off by default  make a flag*/
	data = 0;
#ifdef P9
	data1 = 0;
	rc=htm_read_xscom(i_args.target, NHTM_TTYPE_FILT, i_args.htm_type, &data, &data1);
#else
	rc=htm_read_xscom(i_args.target, NHTM_TTYPE_FILT, i_args.htm_type, &data);
#endif

#ifdef P9
	data  = SETFIELD(HTM_TTYPE_MASK, data, 0x7f); /* 17..23 (7)*/
	data  = SETFIELD(HTM_TSIZE_MASK, data, 0xff); /* 24..31 (8)*/
	data1 = SETFIELD(HTM_TTYPE_MASK, data1, 0x7f); /* 17..23 (7)*/
	data1 = SETFIELD(HTM_TSIZE_MASK, data1, 0xff); /* 24..31 (8)*/
#else
	data = SETFIELD(HTM_TTYPE_MASK, data, 0xff); /* P8: 16..21 (6)*/
	data = SETFIELD(HTM_TSIZE_MASK, data, 0xff); /* P8: 22..28 (7)*/
#endif
#ifdef P9
	rc=htm_write_xscom(i_args.target, NHTM_TTYPE_FILT, i_args.htm_type, data, data1);
#else
	rc=htm_write_xscom(i_args.target, NHTM_TTYPE_FILT, i_args.htm_type, data);
#endif
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
