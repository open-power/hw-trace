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
#define BUF_SIZE 4096
#define EYE_CATCH_SIZE 4

bool is_wrapped(uint32_t i_target)
{
	int fdin, bytes_read;
	char *chip_dir;
	char nbuf[strlen(MEMTRACE_DIR)+16];
	char buf[EYE_CATCH_SIZE];
	char test[EYE_CATCH_SIZE] = {0xac,0xef,0xf0, 0x00};

	chip_dir=get_chip_dir(i_target);
	snprintf(nbuf, sizeof(nbuf), "%s/%s/%s", MEMTRACE_DIR, chip_dir,"trace");

	fdin = open(nbuf, O_RDONLY);

	if (fdin < 0) {
		perror("Failed to open input file");
		exit(1);
	}

	if (lseek(fdin, 8, SEEK_SET) < 0) {
		perror("Seek failed");
		exit(1);
	}

	bytes_read = read(fdin, buf, EYE_CATCH_SIZE);

	if (bytes_read != EYE_CATCH_SIZE) {
		ERR("Read only %d/%d bytes from %s", bytes_read, EYE_CATCH_SIZE, nbuf);
		exit(1);
	}

	int i=0;
	for (i = 0; i < EYE_CATCH_SIZE; i++){
		if (test[i] != buf[i]){
			printf("I read this %x \n", buf[i]);
			return true;
		}
	}
	close(fdin);

	return false;

}


int htm_dump(uint32_t i_target, char* filename, uint64_t start_addr, uint64_t dump_size)
{
	int fdin, fdout, bytes_read=0, bytes_written = 0;
	mode_t mode = S_IRWXU | S_IRWXG | S_IRWXO;
	char nbuf[strlen(MEMTRACE_DIR)+16];
	char buf[BUF_SIZE];
	char *chip_dir;
	uint64_t total_bytes = 0;

	if (is_wrapped(i_target)){
		printf("We have wrapped \n");
	}
	chip_dir=get_chip_dir(i_target);
	snprintf(nbuf, sizeof(nbuf), "%s/%s/%s", MEMTRACE_DIR, chip_dir,"trace");

	fdin = open(nbuf, O_RDONLY);

	/*advance to the start of the address.  This allows for portions of the memory to be 
	dumped*/
	lseek(fdin, start_addr, SEEK_SET);

	if (fdin < 0) {
		perror("Failed to open input file");
		exit(1);
	}

	fdout = open(filename, O_WRONLY | O_CREAT | O_TRUNC, mode);

	if (fdout < 0) {
		perror("Failed to open output file");
		exit(1);
	}

	do{
		if (dump_size - total_bytes < BUF_SIZE)
			bytes_read = read(fdin, buf, dump_size-total_bytes);
		else
			bytes_read = read(fdin, buf, BUF_SIZE);
		total_bytes += bytes_read;
		bytes_written = write(fdout, buf, bytes_read);
		if (bytes_written != bytes_read){
			ERR("Error writing to file \n");
			exit(1);
		}

	} while (bytes_read && (total_bytes < dump_size || dump_size == -1));
	close(fdin);
	close(fdout);
        return 0;
}

