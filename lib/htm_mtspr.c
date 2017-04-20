#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include "htm_mtspr.h"
#define SPR_TRACE	0x3ee
#define START_TRACE	1
#define STOP_TRACE	2
#define PAUSE_TRACE	4
#define RESET_TRACE	16
#define CREATE_MARKER   8 

static inline void mtspr_trace(uint64_t i_val)
{

	int register r3 asm("3");
	/*printf("Writing %d \n",i_val);*/
        asm volatile("ld %1,%0" :: "m" (i_val) , "r"(r3));
        asm volatile("mtspr %1,%0" : "=r"(r3) : "i"(SPR_TRACE): "memory");
}

void htm_start_mtspr()
{
	mtspr_trace(START_TRACE);
}

void htm_stop_mtspr()
{
	mtspr_trace(STOP_TRACE);
}

void htm_pause_mtspr()
{
	mtspr_trace(PAUSE_TRACE);
}

void htm_reset_mtspr()
{
	mtspr_trace(RESET_TRACE);
}
void htm_mark_mtspr(uint64_t marker_val)
{
	/*Only 10 bits allowed for marker val.  */
	/*printf("Before: %d After: %d \n",marker_val, marker_val << 4);*/

	/* And the Marker trigger to the value being added */
	mtspr_trace((marker_val<<4) | CREATE_MARKER);
}
