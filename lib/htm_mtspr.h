#ifndef __HTM_MTSPR_H
#define __HTM_MTSPR_H

#include <stdint.h>


void htm_start_mtspr();

void htm_stop_mtspr();

void htm_mark_mtspr(uint64_t marker_val);
#endif

