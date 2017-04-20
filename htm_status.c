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


void parse_htm_status(uint64_t stat_reg){

	if(stat_reg == 0)
		printf("HTM_STAT: HTM uninitialized \n");
	if(stat_reg & HTM_STAT_CRESP_OV)
		printf("HTM_STAT: CRESP Overflow - more than 255 dropped \n");
	if(stat_reg & HTM_STAT_REPAIR)
		printf("HTM_STAT: REPAIR     (There was Address Error.  Fix Address) \n");
	if(stat_reg & HTM_STAT_ADDR_ERROR)
		printf("HTM_STAT: ADDR ERROR (Wait for REPAIR bit set, Then fix Address)\n");
	if(stat_reg & HTM_STAT_REC_DROPPED)
		printf("HTM_STAT: Records Were Dropped \n");
	if(stat_reg & HTM_STAT_INIT)
		printf("HTM_STAT: INIT       (Fleeting State - normally don't see)  \n");
	if(stat_reg & HTM_STAT_PREREQ)
		printf("HTM_STAT: PREREQ     (Pre-allocating memory buffers) \n");
	if(stat_reg & HTM_STAT_READY)
		printf("HTM_STAT: READY      (Ready for START Trigger) \n");
	if(stat_reg & HTM_STAT_TRACING)
		printf("HTM_STAT: TRACING    (Capturing Records) \n");
	if(stat_reg & HTM_STAT_PAUSED)
		printf("HTM_STAT: PAUSED     (Pause Capture Records) \n");
	if(stat_reg & HTM_STAT_FLUSH)
		printf("HTM_STAT: FLUSH      (Trace Stopped.  Writing pre-allocated buffers to memory to clean up) \n");
	if(stat_reg & HTM_STAT_COMPLETE)
		printf("HTM_STAT: COMPLETE   (Ready for RESET Trigger)\n");
	if(stat_reg & HTM_STAT_ENABLE)
		printf("HTM_STAT: HTM_STAT: ENABLE     (Fleeting State - normally don't see)\n");
	if(stat_reg & HTM_STAT_STAMP)
		printf("HTM_STAT: STAMP      (Stopping Trace, filling buffers w/ Complete Stamp) \n");
	
}
void get_htm_status(uint32_t i_ex_target, int htm_type){
	uint64_t htm_status_data, memory_size, memory_start;
	htm_status_data = get_htm_status_reg(i_ex_target, htm_type);
/*	printf("HTM STATUS REGISTER: %16" PRIx64 "\n",htm_status_data);*/
	printf("---------------------------------------------\n");
	memory_size = get_mem_size(i_ex_target >> 4);
	memory_start = get_mem_start(i_ex_target >> 4);
	printf("Chip: %d \n",i_ex_target >> 4);
	printf("Core: %d \n",i_ex_target & 0xff);
	printf("Memory Start: 0x%"PRIx64" \n",memory_start);
	printf("Memory Size:  %"PRId64"M\n",memory_size>>20);
	parse_htm_status(htm_status_data);
	printf("Status Reg:  %"PRIx64"\n",htm_status_data);
	printf("HTM_LAST:  0x%"PRIx64"\n",get_htm_last_reg(i_ex_target, htm_type));
	printf("---------------------------------------------\n");
}

