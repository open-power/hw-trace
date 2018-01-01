#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <inttypes.h>
#include <fcntl.h>
#include <errno.h>

#include "xscom.h"
#include "htm.h"
#define ERR(fmt...)     do { fprintf(stderr, fmt); fflush(stderr); } while(0)
#define MAX_TIMEOUT 5

char *get_chip_dir(uint32_t i_cpu_id){
        if(i_cpu_id==0)
                return MEMTRACE_C0;
        else if(i_cpu_id==1)
                return MEMTRACE_C1;
        else if(i_cpu_id==8)
                return MEMTRACE_C8;
        else if(i_cpu_id==16)
                return MEMTRACE_C10;
        else if(i_cpu_id==17)
                return MEMTRACE_C11;
        else
                return "error";
}

uint64_t get_mem_size(uint32_t i_target)
{
        uint64_t memsize, bytes_read = 0;
        int fd;
        char nbuf[strlen(MEMTRACE_DIR)+16];
        char buf[20];
	char *chip_dir;
	uint32_t cpu_id = i_target >> 4;
	chip_dir = get_chip_dir(cpu_id);
        snprintf(nbuf, sizeof(nbuf), "%s/%s/%s", MEMTRACE_DIR, chip_dir,"size");

        fd = open(nbuf, O_RDONLY);

        if (fd < 0) {
                perror("Failed to open size file");
                exit(1);
        }

        bytes_read = read(fd, buf, 18);
	if (! bytes_read) {
		ERR("COULD NOT READ MEMORY SIZE\n");
		exit(1);
	}
        memsize = strtoul(buf, NULL, 16);
        return memsize;
}

uint64_t get_mem_start(uint32_t i_target)
{
        int fd;
	uint64_t bytes_read = 0;
        char nbuf[strlen(MEMTRACE_DIR)+16];
        char buf[20];
	char *chip_dir;
	uint32_t cpu_id = i_target >> 4;

	chip_dir = get_chip_dir(cpu_id);
        snprintf(nbuf, sizeof(nbuf), "%s/%s/%s", MEMTRACE_DIR, chip_dir,"start");
        
	fd = open(nbuf, O_RDONLY);

        if (fd < 0) {
                perror("Failed to open file start file ");
                exit(1);
        }

        bytes_read = read(fd, buf, 18);
	if (! bytes_read) {
		ERR("COULD NOT READ MEMORY SIZE\n");
		exit(1);
	}

        return strtoull(buf, NULL, 16);
}

uint64_t *get_htm_last_reg_multi(uint32_t i_target, int htm_type){
	int rc;
	uint64_t *htm_last_data_multi;
	
	htm_last_data_multi = (uint64_t *)malloc(2*sizeof(uint64_t));
	rc=htm_read_xscom(i_target, HTM_LAST, htm_type, (uint64_t *)htm_last_data_multi, (uint64_t *)(htm_last_data_multi + 1));

        if (rc) {
                ERR("xscom HTM Status Register read_ex failed rc=%d\n", rc);
        }
        return htm_last_data_multi;
}

uint64_t get_htm_last_reg(uint32_t i_target, int htm_type){
        int rc;
	uint64_t htm_last_data;

        rc=htm_read_xscom(i_target, HTM_LAST, htm_type, &htm_last_data);
        if (rc) {
                ERR("xscom HTM Status Register read_ex failed rc=%d\n", rc);
        }
        return htm_last_data;

}

uint64_t get_htm_status_reg(uint32_t i_target, int htm_type){
//FIXME: Need to look at htm_type and if llat do the shifting for ex 
//chip in register address
        int rc;
        uint64_t htm_status_data;
	
#ifdef P9
        uint64_t htm_status_data1;
        rc=htm_read_xscom(i_target, HTM_STAT, htm_type, &htm_status_data, &htm_status_data1);
#else
        rc=htm_read_xscom(i_target, HTM_STAT, htm_type, &htm_status_data);
#endif
        if (rc) {
                ERR("xscom HTM Status Register read_ex failed rc=%d\n", rc);
        }
        return htm_status_data;
}

uint64_t *get_htm_status_reg_multi(uint32_t i_target, int htm_type) {
	int rc;
	
#ifdef P9
	uint64_t *htm_status_data_multi = (uint64_t *)malloc(2*sizeof(uint64_t));
	rc=htm_read_xscom(i_target, HTM_STAT, htm_type, htm_status_data_multi, (uint64_t*)(htm_status_data_multi + 1));
#else
	uint64_t *htm_status_data_multi = (uint64_t *)malloc(sizeof(uint64_t));
	rc=htm_read_xscom(i_target, HTM_STAT, htm_type, htm_status_data_multi);
#endif

        if (rc) {
                ERR("xscom HTM Status Register read_ex failed rc=%d\n", rc);
        }

	return htm_status_data_multi;
}

uint64_t get_htm_last_size(uint32_t i_target, int htm_type){

	uint64_t start, last;
	start = get_mem_start(i_target);
	last = get_htm_last_reg(i_target, htm_type);
	return last - start;
}

uint64_t *get_htm_last_size_multi(uint32_t i_target, int htm_type){

	uint64_t start, *last_multi, *last_delta_multi;
	start = get_mem_start(i_target);

	last_delta_multi = (uint64_t*)malloc(2*sizeof(uint64_t));

	last_multi = get_htm_last_reg_multi(i_target, htm_type);

	*last_delta_multi = *last_multi - start;
	*((uint64_t*)(last_delta_multi + 1)) = *((uint64_t *)(last_multi + 1)) - start;

	return last_delta_multi;
}

char *get_processor_version() {
	char cmd[150];
	int fd, b_read;
	char buf[7];

	memset(cmd, 0, 150);
        strcpy(cmd,"cat /proc/cpuinfo  | grep cpu | awk -F\" \"  '{print $3}'| head -n1 > /tmp/procver.out");
	system(cmd);

	fd = open("/tmp/procver.out",O_RDONLY);
	if (fd == -1) {
		printf("unable to get processor version(open).. exiting.. error: %d\n",errno);
		exit(-1);
	}
	b_read = read(fd, buf, 7);	
	if (b_read == 0) {
		printf("unable to get processor version(read).. exiting.. error: %d\n",errno);
		exit(-2);
	}
	close(fd);

	memset(cmd, 0, 150);
	strcpy(cmd,"rm -f /tmp/procver.out");
	system(cmd);
	
	return buf;
}

/* Identify the nhtm that this trace record corresponds to. Write to the corresponding file */
int target_nhtm_bit(uint64_t trace_record_addr) {
	uint64_t nhtm_bitmask = 0x80;  /* bit 56 identifies if trace record is for nhtm0/1 */

	if (trace_record_addr & nhtm_bitmask) /* bit 56 is set */
		return 1;
	else
		return 0;
}

int target_nhtm(uint64_t trace_record_addr) {

	if ((trace_record_addr%0x20) == 0) /* nhtm0 */
		return 0;
	else
		return 1;		   /* nhtm1 */
}
