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
#ifdef P9
	uint64_t data1 = 0;

	data1 |= trigger;
        rc=htm_write_xscom(i_target, HTM_TRIG, i_htm_type, data, data1);
#else
        rc=htm_write_xscom(i_target, HTM_TRIG, i_htm_type, data);
#endif

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
	return htm_trigger(i_target, i_htm_type, HTM_TRIG_START);
}
int htm_stop (uint32_t i_target, int i_htm_type)
{
	int rc;
	uint64_t data=0;
#ifdef P9
	uint64_t data1 = 0;
#endif
	
	rc=htm_trigger(i_target, i_htm_type, HTM_TRIG_STOP);
	
	do{
#ifdef P9
		rc=htm_read_xscom(i_target, HTM_STAT, i_htm_type, &data, &data1);
#else
		rc=htm_read_xscom(i_target, HTM_STAT, i_htm_type, &data);
#endif
	        if (rc) {
			ERR("xscom HTM_ write failed, rc=%d\n", rc);
			return -1;
		}
		sleep(1);
#ifdef P9
	}while(!(data &= HTM_STAT_COMPLETE) || !(data1 &= HTM_STAT_COMPLETE));
#else
	}while(!(data &= HTM_STAT_COMPLETE));
#endif

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
#ifdef P9
	uint64_t data1=0;
#endif

	if(filter){
		printf("filtering true \n");
#ifdef P9
		data = SETFIELD(HTM_FILT, data, 0x00007f); /* 32..54: 0b000 0000 0000 0000 0111 1111 */
		data = SETFIELD(HTM_FILT_TTAG, data, 0x002800); /* 0..22: 0b000 0000 0010 1000 0000 0000 */
		data1 = SETFIELD(HTM_FILT, data1, 0x00007f); /* 32..54: 0b000 0000 0000 0000 0111 1111 */
		data1 = SETFIELD(HTM_FILT_TTAG, data1, 0x002800); /* 0..22: 0b000 0000 0010 1000 0000 0000 */
#else
		data = SETFIELD(HTM_FILT, data, 0x0007f); /* 32..51: 0b0000 0000 0000 0111 1111 */
		data = SETFIELD(HTM_FILT_TTAG, data, 0x02800); /* 0..19:  0b0000 0010 1000 0000 0000 */
#endif
	}else{
#ifdef P9
		data = SETFIELD(HTM_FILT, data, 0x7fffff);
		data1 = SETFIELD(HTM_FILT, data1, 0x7fffff);
#else
		data = SETFIELD(HTM_FILT, data, 0xfffff);
#endif
	}
#ifdef P9
	rc=htm_write_xscom(i_target, NHTM_FILT, i_htm_type, data, data1);
#else
	rc=htm_write_xscom(i_target, NHTM_FILT, i_htm_type, data);
#endif
	if (rc) {
                        ERR("xscom NHTM_FILT read failed, rc=%d\n", rc);
                        return -1;
       	}
	return 0;
}
