#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <inttypes.h>
#include "htm.h"
#include "xscom.h"

#define CREATE_MARKER   8

#define ERR(fmt...)     do { fprintf(stderr, fmt); fflush(stderr); } while(0)

int htm_trigger (uint32_t i_target, int i_htm_type, uint64_t trigger)
{
	int rc;
	uint64_t data = 0;

	data |= trigger;
        rc=htm_write_xscom(i_target, HTM_TRIG, i_htm_type, data);
        if (rc) {
		ERR("xscom HTM_MODE write failed, rc=%d\n", rc);
		return -1;
	}

return 0;
}

int htm_reset (uint32_t i_target, int i_htm_type)
{
	printf("Trigger\n");
	return htm_trigger(i_target, i_htm_type, HTM_TRIG_RESET);
}

int htm_set_marker(uint32_t i_target, int i_htm_type, uint64_t marker_val)
{

        /* And the Marker trigger to the value being added */
        return htm_trigger(i_target, i_htm_type, (marker_val<<4 | CREATE_MARKER));
}

int htm_start (uint32_t i_target, int i_htm_type)
{
/*	uint64_t htm_status_data;
	htm_status_data = get_htm_status_reg(i_target, i_htm_type);
	if(htm_status_data & HTM_STAT_READY)*/
	return htm_trigger(i_target, i_htm_type, HTM_TRIG_START);
/*
	else{
		ERR("Cannot start trace, HTM is not in READY MODE");
		get_htm_status(i_target, i_htm_type);
		return -1;
	}*/
}
int htm_stop (uint32_t i_target, int i_htm_type)
{
	int rc;
	uint64_t data=0;
	
	rc=htm_trigger(i_target, i_htm_type, HTM_TRIG_STOP);
	
	do{
		rc=htm_read_xscom(i_target, HTM_STAT, i_htm_type, &data);
	        if (rc) {
			ERR("xscom HTM_ write failed, rc=%d\n", rc);
			return -1;
		}
		sleep(1);
	}while(!(data &= HTM_STAT_COMPLETE));

	return 0;
}
int htm_pause (uint32_t i_target, int i_htm_type)
{
	return htm_trigger(i_target, i_htm_type, HTM_TRIG_PAUSE);
}
int htm_filter (bool filter, uint32_t i_target, int i_htm_type)
{
	int rc;
	uint64_t data=0;

/*	rc=htm_read_xscom(i_target, NHTM_FILT, i_htm_type, &data);
	 if (rc) {
                        ERR("xscom NHTM_FILT read failed, rc=%d\n", rc);
                        return -1;
        	 }
*/
	if(filter){
		printf("filtering true \n");
		data = SETFIELD(HTM_FILT, data, 0x0007f);
		data = SETFIELD(HTM_FILT_TTAG, data, 0x02800);
	}else{

		data = SETFIELD(HTM_FILT, data, 0xfffff);
	}
	rc=htm_write_xscom(i_target, NHTM_FILT, i_htm_type, data);
	 if (rc) {
                        ERR("xscom NHTM_FILT read failed, rc=%d\n", rc);
                        return -1;
        	 }
	return 0;
}
