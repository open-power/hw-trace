#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <inttypes.h>
#include <stdarg.h>

#include "xscom.h"
#include "htm.h"
#define ERR(fmt...)     do { fprintf(stderr, fmt); fflush(stderr); } while(0)

int htm_read_xscom(uint32_t  i_ex_target,  uint64_t addr, int i_htm_type, uint64_t *val, ...)
{
	int rc;
	uint32_t cpu_id = i_ex_target >> 4;
	uint8_t l_ex_number = i_ex_target & 0xf;
	va_list ap;
#ifdef P9
	uint64_t *val1;
#endif

	va_start(ap, val); /* We will definitely pass in at least one variable to fill in */
	switch(i_htm_type){
        case HTM_FABRIC:
#ifdef P9
               	rc = xscom_read(i_ex_target, NHTM0_BASE+addr, val);
		val1 = va_arg(ap, uint64_t *);
               	rc = xscom_read(i_ex_target, NHTM1_BASE+addr, val1);
#else
               	rc = xscom_read(i_ex_target, NHTM_BASE+addr, val);
#endif
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
	va_end(ap);

	return rc;

}

int htm_write_xscom(uint32_t i_ex_target, uint64_t addr, int i_htm_type, uint64_t val, ...)
{
	int rc;
	uint32_t cpu_id = i_ex_target >> 4;
	uint8_t l_ex_number = i_ex_target & 0xf;
	va_list ap;
#ifdef P9
	uint64_t *val1;
#endif

	va_start(ap, val);
	switch(i_htm_type){
        case HTM_FABRIC:
#ifdef P9 /* do we always write the same value for both NHTMs or can they be different? */
	  /* _write_scom is now variadic. So, we can write different values to both NHTMs,
 * 	  though this might not be required */
                	rc=xscom_write(i_ex_target, NHTM0_BASE+addr, val);
			val1 = va_arg(ap, uint64_t *);
			if ((val != HTM_TRIG_STOP) && (val1 != HTM_TRIG_STOP)) /* A stop trigger is issued only to NHTM0 */
                		rc=xscom_write(i_ex_target, NHTM1_BASE+addr, val1);
#else
                	rc=xscom_write(i_ex_target, NHTM_BASE+addr, val);
#endif
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
	va_end(ap);
	return rc;

}
