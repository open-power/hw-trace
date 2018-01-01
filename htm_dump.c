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
#define BUF_SIZE 4096
#define EYE_CATCH_SIZE 4
#define TRCREC_SIZE 16  /* 128 bits per record */

#define	cleanup_and_exit	{close(fdout1); close(fdout0); close(fdin); exit(1);}

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

        lseek(fdin, 8, SEEK_SET);
	bytes_read = read(fdin, buf, EYE_CATCH_SIZE);
	
        int i=0;
        for (i = 0; i < EYE_CATCH_SIZE; i++){
                if (test[i] != buf[i]){
                    printf("I read this %lx \n", buf[i]);
		    close(fdin);
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
		if (!bytes_written){
			ERR("Error writing to file \n");
			exit(1);
		}
	
	}while(bytes_read && (total_bytes < dump_size || dump_size == -1));
	close(fdin);
	close(fdout);
        return 0;
}

/* Dump to a single file, aggregated data from nhtm0 and nhtm1. */
int htm_dump_fabric_trace_single(uint32_t i_target, char* filename, uint64_t memory_start, uint64_t start_addr0,\
			uint64_t dump_size0, uint64_t start_addr1, uint64_t dump_size1) {
        int fdin, fdout, bytes_read=0, bytes_written = 0, ret;
	uint64_t trace_record_addr; 
	int nhtm_itercount, i, residue_bytes_read;
        mode_t mode = S_IRWXU | S_IRWXG | S_IRWXO;
        char nbuf[strlen(MEMTRACE_DIR)+16];
        char buf[BUF_SIZE];
        char *chip_dir;
        uint64_t total_bytes = 0;
	uint64_t dump_size;
	uint64_t start_addr;

        if (is_wrapped(i_target)){
                printf("We have wrapped \n");
        }
        chip_dir=get_chip_dir(i_target);
        snprintf(nbuf, sizeof(nbuf), "%s/%s/%s", MEMTRACE_DIR, chip_dir,"trace");

        fdin = open(nbuf, O_RDONLY);

        if (fdin < 0) {
                ERR("Failed to open input trace location:%s\n",strerror(errno));
                exit(1);
        }

	/* set start_addr to the lesser of start_addr0 and start_addr1 */
	if (start_addr0 <= start_addr1)
		start_addr = start_addr0;
	else
		start_addr = start_addr1;

	start_addr = dump_size1 - dump_size0; /* max dump size - user specified dump size */

#if 0 /* This commented section is useful if we are dumping for nhtm0 and nhtm1 separately */
	/* set start_addr to the lesser of start_addr0 and start_addr1 */
	if (start_addr0 <= start_addr1) {
		start_addr = start_addr0;
                start_addr_low = start_addr0;
                start_addr_high = start_addr1;
	}
	else {
		start_addr = start_addr1;
                start_addr_low = start_addr1;
                start_addr_high = start_addr0;
	}

	end_addr0 = start_addr0+dump_size0;
	end_addr1 = start_addr1+dump_size1;

	if (end_addr0 <= end_addr1) {
		end_addr_low = end_addr0;
		end_addr_high = end_addr1;
	}
	else {
		end_addr_low = end_addr1;
		end_addr_high = end_addr0;
	}
#endif
        /*advance to the start of the address.  This allows for portions of the memory to be
        dumped*/
        ret = lseek(fdin, start_addr, SEEK_SET);
	if (ret == -1) { /* lseek failed */
		ERR("Failed to (lseek) set the pointer to the start of the file. %s\n", strerror(errno));
		exit(1);
	}

        fdout = open(filename, O_WRONLY | O_CREAT | O_TRUNC, mode);

        if (fdout < 0) {
                ERR("Failed to open output file for nhtm:%s\n",strerror(errno));
		close(fdin);
                exit(1);
        }
#if 0 /* this commented section is useful if we are fetching dumps for nhtm0 and nhtm1 separately. */
	if (usersize == true) { /* dump_size0 = dump_size1 */
		if (start_addr_high > end_addr_low) /* nhtm0 and 1 dump locations are discontinuous and non-overlapping */
		/* start0 : end0 : start1 : end1 or start1 : end1 : start0 : end0 */
		/* end0<->start1 or end1<->start0 needs to be skipped */
		/* However, include the entire range start0/1<->end1/0 since we read at one go. */
		/* The regions to skip are handled later */
		 dump_size = dump_size0*2 + start_addr_high - end_addr_low;
		else
		 dump_size = (start_addr_high - start_addr_low) + dump_size0 + \
                              (end_addr_high - end_addr_low);	
	}
	else  {/* dump_size = memory_size for both nhtm0/1. The larger of the two is the region to capture */
		if (dump_size0 <= dump_size1)
			dump_size = dump_size1;
		else
			dump_size = dump_size0;
	}
#endif
	dump_size = dump_size0 + TRCREC_SIZE;	 /* to ensure the last trace record is processed */

        do{
		if (dump_size - total_bytes < BUF_SIZE)
			bytes_read = read(fdin, buf, dump_size-total_bytes);
		else
			bytes_read = read(fdin, buf, BUF_SIZE);
		if (bytes_read==-1 || bytes_read==0) {
			ERR("Error reading from file(1) \n");
			break;
		}
		total_bytes += bytes_read;
	        bytes_written = write(fdout, buf, bytes_read);
		if (bytes_written==-1) {
			ERR("Error writing to file(101) \n");
			break;
		}
		if (!bytes_written){
			ERR("Error writing to file(2) \n");
			break;
		}
	
	}while(bytes_read && (total_bytes < dump_size || dump_size == -1));
	close(fdin);
	close(fdout);
        return 0;
}

int htm_segregate_fabric_trace_full2(uint32_t i_target, char* filename0, char* filename1, uint64_t memory_start, uint64_t start_addr0, \
				uint64_t dump_size0, uint64_t start_addr1, uint64_t dump_size1, bool usersize) {

        int fdin, fdout, bytes_read=0, bytes_written = 0, ret;
	int fdout0, fdout1;
	uint64_t trace_record_addr = 0, trace_offset = 0; 
	int nhtm_itercount, i, residue_bytes_read;
        mode_t mode = S_IRWXU | S_IRWXG | S_IRWXO;
        char nbuf[strlen(MEMTRACE_DIR)+16];
        char buf[BUF_SIZE];
        char *chip_dir;
        uint64_t total_bytes = 0;
	uint64_t dump_size;
	uint64_t start_addr;
	uint64_t end_addr0, end_addr1;
	uint64_t start_addr_low, start_addr_high, end_addr_low, end_addr_high;

        if (is_wrapped(i_target)){
                printf("We have wrapped \n");
        }
        chip_dir=get_chip_dir(i_target);
        snprintf(nbuf, sizeof(nbuf), "%s/%s/%s", MEMTRACE_DIR, chip_dir,"trace");

        fdin = open(nbuf, O_RDONLY);

        if (fdin < 0) {
                ERR("Failed to open input trace location:%s\n",strerror(errno));
                exit(1);
        }

	/* set start_addr to the lesser of start_addr0 and start_addr1 */
	if (start_addr0 <= start_addr1) {
		start_addr = start_addr0;
                start_addr_low = start_addr0;
                start_addr_high = start_addr1;
	}
	else {
		start_addr = start_addr1;
                start_addr_low = start_addr1;
                start_addr_high = start_addr0;
	}

	end_addr0 = start_addr0+dump_size0;
	end_addr1 = start_addr1+dump_size1;

	if (end_addr0 <= end_addr1) {
		end_addr_low = end_addr0;
		end_addr_high = end_addr1;
	}
	else {
		end_addr_low = end_addr1;
		end_addr_high = end_addr0;
	}

        /*advance to the start of the address.  This allows for portions of the memory to be
        dumped*/
        ret = lseek(fdin, start_addr, SEEK_SET);
	if (ret == -1) { /* lseek failed */
		ERR("Failed to (lseek) set the pointer to the start offset in the trace file. %s\n", strerror(errno));
		exit(1);
	}

        fdout0 = open(filename0, O_WRONLY | O_CREAT | O_TRUNC, mode);

        if (fdout0 < 0) {
                ERR("Failed to open output file for nhtm0:%s\n",strerror(errno));
		close(fdin);
                exit(1);
        }

	fdout1 = open(filename1, O_WRONLY | O_CREAT | O_TRUNC, mode);

	if (fdout1 < 0) {
		ERR("Failed to open output file for nhtm1:%s\n",strerror(errno));
		close(fdout0);
		close(fdin);
		exit(1);
	}
	if (usersize == true) { /* dump_size0 = dump_size1 */
		if (start_addr_high > end_addr_low) /* nhtm0 and 1 dump locations are discontinuous and non-overlapping */
		/* start0 : end0 : start1 : end1 or start1 : end1 : start0 : end0 */
		/* end0<->start1 or end1<->start0 needs to be skipped */
		/* However, include the entire range start0/1<->end1/0 since we read at one go. */
		/* The regions to skip are handled later */

		 dump_size = dump_size0 + dump_size1 + start_addr_high - end_addr_low; /* since we can now have different dump sizes for nhtm0 and 1*/
		else
		/* Since there is a overlap, and start0 : start1 : end0 : end1, we need to read */
		/* the entire region from start0 to end1 */
                 dump_size = end_addr_high - start_addr_low; 
	}
	else  {/* dump_size = memory_size for both nhtm0/1. The larger of the two is the region to capture */
		if (dump_size0 <= dump_size1)
			dump_size = dump_size1;
		else
			dump_size = dump_size0;
	}

	dump_size = dump_size + TRCREC_SIZE;	 /* to ensure the last trace record is processed */

	trace_record_addr = memory_start + start_addr; /* get the actual address at the start offset (start_addr) */
	trace_offset = start_addr;

	do {
		if (dump_size - total_bytes >= BUF_SIZE) {
			memset(&buf[0],0,BUF_SIZE);
			bytes_read = 0;
			bytes_read = read(fdin, buf, BUF_SIZE);
			if (bytes_read == -1)  {
				ERR("Error reading from trace location:%s\n",strerror(errno));
				cleanup_and_exit
			}
			else if (bytes_read == 0) {
				ERR("0 bytes read from trace location:%s\n",strerror(errno));
				cleanup_and_exit
			}
			else {
			nhtm_itercount = bytes_read / TRCREC_SIZE; /* 4096 / 16 = 256, if we read 4K */
			for (i=0;i<nhtm_itercount;i++) {
				bytes_written = 0;
				/* For the non-overlap case: s0 < e0 < s1 < e1, if current ptr is outside */
				/* the s0:e0 range, skip nhtm0 addresses. Similarly, outside the s1:e1    */
				/* range, skip nhtm1 addresses. This works for overlap case as well	  */
				/* where s0 < s1 < e0 < e1						  */
				if (target_nhtm_bit(trace_record_addr)==1) { /* nhtm1 */
					if ((trace_offset > end_addr1) || (trace_offset < start_addr1)) {
						trace_record_addr += TRCREC_SIZE;
						trace_offset += TRCREC_SIZE;
						continue;
					}
					bytes_written = write(fdout1, &buf[i*TRCREC_SIZE], TRCREC_SIZE);
					if (bytes_written == -1) {
						ERR("Error writing to file(88):%s\n",strerror(errno));
						cleanup_and_exit
					}
					if (!bytes_written){
						ERR("Error writing to file(11):%s \n",strerror(errno));
						cleanup_and_exit
					}
				}
				else { /* nhtm0 */
					if ((trace_offset > end_addr0) || (trace_offset < start_addr0)) {
						trace_record_addr += TRCREC_SIZE;
						trace_offset += TRCREC_SIZE;
						continue;
					}
					bytes_written = write(fdout0, &buf[i*TRCREC_SIZE], TRCREC_SIZE);
					if (bytes_written == -1) {
						ERR("Error writing to file(88):%s\n",strerror(errno));
						cleanup_and_exit
					}
					if (!bytes_written){
						ERR("Error writing to file(11):%s \n",strerror(errno));
						cleanup_and_exit
					}
				}				
				trace_record_addr += TRCREC_SIZE;
				trace_offset += TRCREC_SIZE;
			} /* end for */
			} /* end else */
			/* assuming that a read of 4K will always fill a buffer with 4K */
		} /* end if dump_size */
		else {
			memset(&buf[0],0,BUF_SIZE);
			bytes_read = read(fdin, buf, dump_size - total_bytes);
			if (bytes_read == -1)  {
				ERR("Error reading from trace location(2):%s\n",strerror(errno));
				cleanup_and_exit
			}
			else if (bytes_read == 0) {
				ERR("0 bytes read from trace location(2):%s\n",strerror(errno));
			}
			else {
			nhtm_itercount = bytes_read / TRCREC_SIZE; 
			for (i=0;i<nhtm_itercount;i++) {
				bytes_written = 0;
				if (target_nhtm_bit(trace_record_addr)==1) { /* nhtm1 */
					if ((trace_offset > end_addr1) || (trace_offset < start_addr1)) {
						trace_record_addr += TRCREC_SIZE;
						trace_offset += TRCREC_SIZE;
						continue;
					}
					bytes_written = write(fdout1, &buf[i*TRCREC_SIZE], TRCREC_SIZE);
					if (bytes_written == -1) {
						ERR("Error writing to file(88):%s\n",strerror(errno));
						cleanup_and_exit
					}
					if (!bytes_written){
						ERR("Error writing to file(11):%s \n",strerror(errno));
						cleanup_and_exit
					}
				}
				else { /* nhtm0 */
					if ((trace_offset > end_addr0) || (trace_offset < start_addr0)) {
						trace_record_addr += TRCREC_SIZE;
						trace_offset += TRCREC_SIZE;
						continue;
					}
					bytes_written = write(fdout0, &buf[i*TRCREC_SIZE], TRCREC_SIZE);
					if (bytes_written == -1) {
						ERR("Error writing to file(88):%s\n",strerror(errno));
						cleanup_and_exit
					}
					if (!bytes_written){
						ERR("Error writing to file(11):%s \n",strerror(errno));
						cleanup_and_exit
					}
				}				
				trace_record_addr += TRCREC_SIZE;
				trace_offset += TRCREC_SIZE;
			} /* end for */
			} /* end else */
		}
		total_bytes += bytes_read;
		} while (bytes_read && (total_bytes < dump_size || dump_size == -1));
	close(fdout1);
	close(fdout0);
	close(fdin);

	return 0;
}

/* Extract 36-bit synchronization data from a 64 bit (high) stamp */
uint64_t get_sync_time(uint64_t stamp_hi) {
	uint64_t bit16_51_mask = 0x0000fffffffff000;

	uint64_t *st_hi = stamp_hi;

	return ((*st_hi & bit16_51_mask) >> 12);
}

/* Extract embedded timestamp from a cresp / rcmd lower 64-bit */
int get_embedded_timestamp(uint64_t rec_lo) {
/*	uint64_t bit31_34_mask = 0x00000001e0000000; */ /* the elapsed cycles */
	uint64_t bit30_33_mask = 0x00000003c0000000; /* the elapsed cycles */

	uint64_t *r_lo = rec_lo;

	return ((*r_lo & bit30_33_mask) >> 28);
}

/* get command type and subtype */
void get_cmd_and_subcmd_type(uint64_t tracerec_hi, uint64_t tracerec_lo, int *cmd_type, int *subcmd_type) {
	uint64_t cmdtype_mask 		= 0xc000000000000000;
	uint64_t stamp_record_mask 	= 0xACEFF00000000000;
	uint64_t stamp_complete_mask 	= 0xACEFF10000000000;
	uint64_t stamp_time_mask 	= 0xACEFF80000000000;

	uint64_t *hi = tracerec_hi;
	uint64_t *lo = tracerec_lo;

	if (*hi & cmdtype_mask == 0x0) {
		*cmd_type = STAMP; /*stamp 0x1*/
		if ((*lo & stamp_record_mask) == stamp_record_mask)
			*subcmd_type = RECORD; /* stamp record 0x4*/	
		else if ((*lo & stamp_complete_mask) == stamp_complete_mask)
			*subcmd_type = COMPLETE; /* stamp complete 0x5*/
		else if ((*lo & stamp_time_mask) == stamp_time_mask)
			*subcmd_type = TIME; /* time stamp 0x6*/
	}
	else if (((*hi & cmdtype_mask) >> 62) == 0x1)
		*cmd_type = CRESP; /*cresp 0x2*/

	else if (((*hi & cmdtype_mask) >> 63) == 0x1)
		*cmd_type = RCMD; /*rcmd. Might contain a cresp .0x3*/
}

void process_stamp(uint64_t stamp_hi, uint64_t stamp_lo, int subcmd, uint64_t *ts_stamp) {
	*ts_stamp = get_sync_time(stamp_hi);
	if (subcmd == RECORD) {
		printf("the first stamp of NHTM0 is a record..\n");
	}
	else if (subcmd == COMPLETE) {
		printf("Trace complete ..\n");
	}
}

/* Is there a cresp in the rcmd? */
int cresp_in_rcmd(uint64_t rec_lo) {
	uint64_t cresp_in_rcmd_mask = 0x20000000;

	uint64_t *r_lo = rec_lo;

	return (*r_lo & cresp_in_rcmd_mask);		
}

void process_cresp_or_rcmd(uint64_t rec_hi, uint64_t rec_lo, int subcmd, int *ts_delta) {
	/* fetching the embedded timestamp (31:34). It is 94:97 on the 128-bit trace */

	*ts_delta = get_embedded_timestamp(rec_lo);

	if (*ts_delta == 0x1)
		printf("Possible back-to-back trace records..\n");
/*
	1) back-to-back rcmds?
	2) cresp inside a rcmd?
*/
	if (cresp_in_rcmd(rec_lo)) { 
		printf("cresp found within rcmd..\n");
	}	
}

/* Generate a time-sequenced stream from two separate files (for nhtm0 and nhtm1) */
int htm_get_single_stream(char *file0, char *file1, char *file01) {
/* 1. the traces run independently. Bit 56 of the trace address determines if it is for nhtm0 or 1 */
/* 2. Each STAMP trace record also has a synchronization stamp */
/* Steps:
	a) Look for the last COMPLETE stamp before the end of the NHTM trace in both NHTM0 and NHTM1.
	b) Check the synchronization timestamp information in the COMPLETE stamp. This should show up
	in both the NHTM0 and NHTM1 trace.
	c) Go reverse picking up the 
	d) Once we reach the beginning of both traces, we should see a Record Stamp for both.
*/
/* Alternate steps:
	a) Check if the first record is a RECORD stamp, in which case we have the start time. In this case,
	there is no buffer overrrun.
	b) Alternately, the first record can be a TIME stamp, which happens if there is a buffer overrun.
	c) Once the start time is identified, look for subsequent records. If it is a rcmd, then, look for 
	the imbedded timestamp and generate an absolute time (since we know the start time). Compare this
	across the records of nhtm0 and nhtm1, and store in overall time sequence.
	d) Repeat the sequence above, until we get to a COMPLETE stamp in either nhtm0 or 1. Compare the time
	and insert in sequence.
*/
	char recbuf0[20], recbuf1[20]; /* To hold one trace record at a time */
	uint64_t ts = 0; /* common timestamp */
	int cmd = 0, subcmd = 0;
	int fdin0, fdin1, mode, fdout01;
	int bytes_f0_read = 0, bytes_f1_read = 0;
	int trc_complete_count = 0;
	int count0 = 0, count1 = 0;
	int ts0_delta = 0, ts1_delta = 0;

	int start_addr = 0; /* assume we start from offset 0 */

	memset(&recbuf0, 0, 20);
	memset(&recbuf1, 0, 20);
        fdin0 = open(file0, O_RDONLY);

        if (fdin0 < 0) {
                perror("Failed to open input file for nhtm0 for reading");
                exit(1);
        }
	lseek(fdin0, start_addr, SEEK_SET);

        fdin1 = open(file1, O_RDONLY);

        if (fdin1 < 0) {
                perror("Failed to open output file for nhtm1 for reading");
		close(fdin0);
                exit(1);
        }
	lseek(fdin1, start_addr, SEEK_SET);

	fdout01 = open(file01, O_CREAT | O_RDWR | O_TRUNC, S_IRWXU);
        if (fdout01 < 0) {
                perror("Failed to open output file for merged data");
		close(fdin0);
		close(fdin1);
                exit(1);
        }

	/* read one trace record per nhtm, set a common (higher) time,
		write all records until the common time. Repeat */
	bytes_f0_read=read(fdin0, &recbuf0[0], 16);
	bytes_f1_read=read(fdin1, &recbuf1[0], 16);

	uint64_t *recbuf0_int64_lo, *recbuf1_int64_lo;
	uint64_t *recbuf0_int64_hi, *recbuf1_int64_hi;
	int cmd0 = 0, cmd1 = 0;
	int subcmd0 = 0, subcmd1 = 0;

	uint64_t ts0 = 0;
	uint64_t ts1 = 0;
	int bytes_written0 = 0, bytes_written1 = 0;

	do {
		cmd0 = 0;
		cmd1 = 0;
		subcmd0 = 0;
		subcmd1 = 0;

		count0 = count0 + 1; /* nhtm0 specific reads */
		count1 = count1 + 1; /* nhtm1 specific reads */

		recbuf0_int64_hi = (uint64_t *)&recbuf0[0];
		recbuf0_int64_lo = (uint64_t *)&recbuf0[8];
		recbuf1_int64_hi = (uint64_t *)&recbuf1[0];
		recbuf1_int64_lo = (uint64_t *)&recbuf1[8];

		get_cmd_and_subcmd_type(recbuf0_int64_hi, recbuf0_int64_lo, &cmd0, &subcmd0);
		get_cmd_and_subcmd_type(recbuf1_int64_hi, recbuf1_int64_lo, &cmd1, &subcmd1);
		if ((cmd0 == STAMP) && (subcmd0 == RECORD)) {
		}
		if (cmd0 == STAMP) {
			process_stamp(recbuf0_int64_hi, recbuf0_int64_lo, subcmd0, &ts0);
			if ((count0 == 1) && (subcmd0 == RECORD)) {
				printf("The first stamp entry for nhtm1 is a RECORD\n");
			}
			if ((count0 > 1) && (subcmd0 == RECORD)) {
				printf("We have a RECORD stamp entry in the middle of nhtm0.. abort\n");
				exit(-1);
			}
			if (subcmd0 == COMPLETE) {
				printf("NHTM0 end of trace data reached.. \n");
			}
		}
		else if (cmd0 == CRESP || cmd0 == RCMD) {
			process_cresp_or_rcmd(recbuf0_int64_hi, recbuf0_int64_lo, subcmd0, &ts0_delta);
			ts0 += ts0_delta;
		}

		if (cmd1 == STAMP) {
			process_stamp(recbuf1_int64_hi, recbuf1_int64_lo, subcmd1, &ts1);
			if ((count1 == 1) && (subcmd1 == RECORD)) {
				printf("The first stamp entry for nhtm1 is a RECORD\n");
			}
			if ((count1 > 1) && (subcmd1 == RECORD)) {
				printf("We have a RECORD stamp entry in the middle of nhtm1.. abort\n");
				exit(-1);
			}
			if (subcmd1 == COMPLETE) {
				printf("NHTM1 end of trace data reached.. \n");
			}
		}
		else if (cmd1 == CRESP || cmd1 == RCMD) {
			process_cresp_or_rcmd(recbuf1_int64_hi, recbuf1_int64_lo, subcmd1, &ts1_delta);
			ts1 += ts1_delta;
		}

		if (ts0 <= ts1) {
		while (ts0 <= ts1) {
                    bytes_written0 = write(fdout01, &recbuf0[0], 16);
		    memset(&recbuf0[0], 0, 20);
		    bytes_f0_read=read(fdin0, &recbuf0[0], 16);
		    count0 += 1;
		    recbuf0_int64_hi = (uint64_t *)&recbuf0[0];
		    recbuf0_int64_lo = (uint64_t *)&recbuf0[8];
		    cmd0 = 0;
		    subcmd0 = 0;
		    get_cmd_and_subcmd_type(recbuf0_int64_hi, recbuf0_int64_lo, &cmd0, &subcmd0);

		    if (cmd0 == STAMP) {
			process_stamp(recbuf0_int64_hi, recbuf0_int64_lo, subcmd0, &ts0);
		    }
		    else if ((cmd0 == CRESP) || (cmd0 == RCMD)) {
			process_cresp_or_rcmd(recbuf0_int64_hi, recbuf0_int64_lo, subcmd0, &ts0_delta);
			ts0 += ts0_delta;
			/* what about back-to-back rcmds? */
		    }
		}
                bytes_written1 = write(fdout01, &recbuf1[0], 16);
		bytes_written0 = write(fdout01, &recbuf0[0], 16);
		ts = ts0; /* nhtm0 again gets to the front */
		}	
		else { /* ts0 > ts1 */
		while (ts1 <= ts0) {
                    bytes_written1 = write(fdout01, &recbuf1[0], 16);
		    memset(&recbuf1[0], 0, 20);
		    bytes_f1_read=read(fdin1, &recbuf1[0], 16);
		    recbuf1_int64_hi = (uint64_t *)&recbuf1[0];
		    recbuf1_int64_lo = (uint64_t *)&recbuf1[8];
		    cmd1 = 0;
		    subcmd1 = 0;
		    get_cmd_and_subcmd_type(recbuf1_int64_hi, recbuf1_int64_lo, &cmd1, &subcmd1);
		    count0 += 1;

		    if (cmd1 == STAMP) {
			process_stamp(recbuf1_int64_hi, recbuf1_int64_lo, subcmd1, &ts1);
		    }
		    else if ((cmd1 == CRESP) || (cmd1 == RCMD)) {
			process_cresp_or_rcmd(recbuf1_int64_hi, recbuf1_int64_lo, subcmd1, &ts1_delta);
			ts1 += ts1_delta;
			/* what about back-to-back rcmds? */
		    }
		}
                bytes_written0 = write(fdout01, &recbuf0[0], 16);
		bytes_written1 = write(fdout01, &recbuf1[0], 16);
		ts = ts1; /* nhtm1 again gets to the front */
		}

		trc_complete_count = 0;
		bytes_f0_read = 0;
		bytes_f1_read = 0;

		if (subcmd0 == COMPLETE) {
			trc_complete_count = trc_complete_count + 1;
		}
		if (subcmd1 == COMPLETE) {
			trc_complete_count = trc_complete_count + 1;
		}
		if (trc_complete_count == 2) /* both trace data complete */
				break;

		memset(&recbuf0[0], 0, 20);
		if ((subcmd0 != COMPLETE) && ((bytes_f0_read=read(fdin0, &recbuf0[0], 16))==0)) {
			printf("read failed for nhtm0. error: %d\n", errno);
		}
		memset(&recbuf1[0], 0, 20);
		if ((subcmd1 != COMPLETE) && ((bytes_f1_read=read(fdin1, &recbuf1[0], 16))==0)) {
			printf("read failed for nhtm1. error: %d\n", errno);
		}
		if ((bytes_f0_read == 0) && (bytes_f1_read == 0)) 
			break;
	} while (1);
	close(fdout01);
	close(fdin0);
	close(fdin1);
}
