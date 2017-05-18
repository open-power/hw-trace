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

int htm_allocate(uint64_t i_mem_size)
{
	int fd;
	ssize_t bytes_written = 0, bytes_to_write;
	char nbuf[strlen(MEMTRACE_DIR)+16];
	char buf[20];

	printf("mem size %d\n", i_mem_size);

	bytes_to_write = snprintf(buf, sizeof(buf), "%"PRIu64, i_mem_size);
	snprintf(nbuf, sizeof(nbuf), "%s/%s", MEMTRACE_DIR, "enable");
	fd = open(nbuf, O_WRONLY);

	if (fd < 0) {
	perror("Failed to open memtrace enable file");
	exit(1);
	}

	bytes_written = write(fd, buf, bytes_to_write);

	if (bytes_written < bytes_to_write){
		ERR("Error writing allocation size\n");
		exit(1);
	}
	printf("allocation successful\n");
        return 0;
}

