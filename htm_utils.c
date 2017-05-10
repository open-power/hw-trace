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

uint64_t get_htm_last_reg(uint32_t i_target, int htm_type)
{
	int rc;
	uint64_t htm_last_data;

	rc=htm_read_xscom(i_target, HTM_LAST, htm_type, &htm_last_data);

	if (rc) {
		ERR("xscom HTM Status Register read_ex failed rc=%d\n", rc);
	}
	return htm_last_data;

}

uint64_t get_htm_status_reg(uint32_t i_target, int htm_type)
{
	int rc;
	uint64_t htm_status_data;
	rc=htm_read_xscom(i_target, HTM_STAT,htm_type, &htm_status_data);
	if (rc) {
		ERR("xscom HTM Status Register read_ex failed rc=%d\n", rc);
	}
	return htm_status_data;

}

uint64_t get_htm_last_size(uint32_t i_target, int htm_type)
{
	uint64_t start, last;
	start = get_mem_start(i_target);
	last = get_htm_last_reg(i_target, htm_type);
	return last - start;
}

