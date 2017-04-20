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

int htm_read_xscom(uint32_t  i_ex_target,  uint64_t addr, int i_htm_type, uint64_t *val)
{
	int rc;
	uint32_t cpu_id = i_ex_target >> 4;
	uint8_t l_ex_number = i_ex_target & 0xf;
	switch(i_htm_type){
        case HTM_FABRIC:
/*		printf("BASE %"PRIx64 ", plus %"PRIx64" \n", NHTM_BASE, addr);*/
                rc=xscom_read(i_ex_target, NHTM_BASE+addr, val);
/*		printf("VALUE %"PRIx64 " \n", *val);*/
                break;
        case HTM_CORE:
        case HTM_LLAT:
		printf(" Looking original %d cpu %d core %d \n", i_ex_target, cpu_id, l_ex_number);
                rc=xscom_read(cpu_id, (CHTM_BASE+addr) + (l_ex_number*CORE_MULTIPLIER), val);
                break;
        default:
                ERR("We Shouldn't be here, htm_type %d is not supported \n",i_htm_type);
                exit(1);

        }
	return rc;

}
int htm_write_xscom(uint32_t i_ex_target, uint64_t addr, int i_htm_type, uint64_t val)
{
	int rc;
	uint32_t cpu_id = i_ex_target >> 4;
	uint8_t l_ex_number = i_ex_target & 0xf;
	switch(i_htm_type){
        case HTM_FABRIC:
/*		printf("write BASE %"PRIx64 ", plus %"PRIx64 " \n", NHTM_BASE, addr);*/
                rc=xscom_write(i_ex_target, NHTM_BASE+addr, val);
/*		printf("write VALUE %"PRIx64 " \n", val);*/
                break;
        case HTM_CORE:
        case HTM_LLAT:
		printf("We are writing to target %d, addr %llx value %llx\n", i_ex_target, addr, val);
                rc=xscom_write(cpu_id, (CHTM_BASE+addr) + (l_ex_number*CORE_MULTIPLIER), val);
                break;
        default:
                ERR("We Shouldn't be here, htm_type %d is not supported \n",i_htm_type);
                exit(1);

        }
	return rc;

}
