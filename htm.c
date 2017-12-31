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
#include <errno.h>
#include <sys/types.h>
#include "htm.h"
#include "xscom.h"
#include "lib/htm_mtspr.h"
#include <fcntl.h>


bool verbose;
bool dummy;

#define SPR_PVR		0x11f
#define MAX_NR_CPUS	1024
#define ERR(fmt...)     do { fprintf(stderr, fmt); fflush(stderr); } while(0)
#define DBG(fmt...)	do { if (verbose) printf(fmt); } while(0)
#define KB 0x400
#define MB 0x100000
#define GB 0x40000000
#define VERSION "2.8"
#define DEFAULT_SIZE 256*MB
typedef enum Command_Choices
{
	UNSET,
	ALLOCATE,
	STATUS,
	SETUP,
	START,
	STOP,
	RESET,
	MARK,
	DUMP,
	LIST,
	AGGREGATE
} command_t;
uint16_t active_chip_mask;

uint32_t nr_cpus;

#define MAX_NR_CPUS     1024
struct cpu cpus[MAX_NR_CPUS];

static int32_t get_cpu_hw_no(int cpu_no)
{
        char *fp;
        FILE *hwidf;
        int n, hwid;

        n = asprintf(&fp, "/sys/devices/system/cpu/cpu%d/physical_id", cpu_no);
        if (n < 0) {
                perror("asprintf failure !");
                exit(1);
        }
        hwidf = fopen(fp, "r");
        if (!hwidf) {
                fprintf(stderr, "Failed to open cpu %d physical_id\n", cpu_no);
                exit(1);
        }
        n = fscanf(hwidf, "%u", &hwid);
        if (n <= 0) {
                fprintf(stderr, "Failed to read cpu %d physical_id\n", cpu_no);
                exit(1);
        }
        fclose(hwidf);
        free(fp);

        return hwid;
}


static void add_cpu(int cpu_no)
{
        struct cpu *c;

        if (nr_cpus <= cpu_no)
                nr_cpus = cpu_no + 1;
        if (nr_cpus > MAX_NR_CPUS) {
                fprintf(stderr, "Too many CPUs !\n");
                exit(1);
        }
        c = &cpus[cpu_no];
        c->present = true;
        c->hw_no = get_cpu_hw_no(cpu_no);
        c->chip_id = c->hw_no >> 7;
        c->ex_target = c->hw_no >> 3;
        c->thread0 = (c->hw_no & 7) == 0;

}


static void init_cpus(void)
{
        FILE *onlnf;
        int n, cpu, prev;
        char sep;
	printf("Entering init_cpus\n");
        onlnf = fopen("/sys/devices/system/cpu/online", "r");
        if (!onlnf) {
                fprintf(stderr, "Failed to open online CPU map\n");
                exit(1);
        }
        sep = 0;
        prev = -1;
        cpu = 0;
        for (;;) {
                n = fscanf(onlnf, "%u%c", &cpu, &sep);
                if (n <= 0)
                        break;
                if (prev >= 0) {
                        while (++prev < cpu)
                                add_cpu(prev);
                }
                add_cpu(cpu);
                if (n == 2 && sep == '-')
                        prev = cpu;
                else
                        prev = -1;
                if (n == 1 || sep == '\n')
                        break;
        }
        fclose(onlnf);
}


static void show_cpus_info()
{

	int i;
	uint32_t old_chip_id=-1;
	for (i = 0; i< nr_cpus; i++){
		struct cpu *c = &cpus[i];
		if (c->present){
			if (old_chip_id != c->chip_id){
				old_chip_id = c->chip_id;
				printf("\nchip[%2d]", c->chip_id);
			}
			if(c->thread0){
				printf("\n\t core[%d]\t\tcpus  ", c->ex_target & 0xf);
			}
			printf("%d ", i);
		}

	}
	printf("\n");

}
int enable_core_mtspr(uint32_t i_chip_id)
{
        int i, rc;
	uint32_t core_touched = -1;
	printf("Entering enable_core_mtspr\n");
        for (i = 0; i < nr_cpus; i++){
                struct cpu *c = &cpus[i];
			DBG("Reading core %d \n", c->ex_target &  0xf);
                if (c->present && (i_chip_id == c->chip_id) && (core_touched != c->ex_target)){
                       	uint64_t data;

			/* Step 1 turn on clocks in htm logic in NCU to allow
			   forwarding of MTSPR Trace commands to Power Bus*/
                       	rc=xscom_read_ex(c->ex_target, NCU_MODE_REG, &data);
	                if (rc) {
				
                        	ERR("xscom NCU_MODE_REG for chip %d core %d read failed, rc=%d\n", c->chip_id, c->ex_target, rc);
                        	return -1;
           		}

			data = data | HTM_ENABLE;

			printf("I'm writing to %d data %llu \n", NCU_MODE_REG, data);
			rc=xscom_write_ex(c->ex_target, NCU_MODE_REG, data);
			DBG("Flipping HTM_ENABLE bit in NCU_MODE_REG \n");
                        if (rc) {
                                ERR("xscom NCU_MODE_REG write failed, rc=%d\n", rc);
                                return -1;
                        }


			/* Step 2 Enable Triggering and Marking in EX chiplets*/
			rc=xscom_read_ex(c->ex_target, CHTM_BASE+HTM_CTRL, &data);
			if (rc) {
                        	ERR("xscom CHTM_HTM_CTRL read failed, rc=%d\n", rc);
                        	return -1;
                        }

			data = data | HTM_CTRL_MTSPR_TRIG | HTM_CTRL_MTSPR_MARK;
			data = SETFIELD(HTM_CTRL_TRIG, data, 0b10);
			data = SETFIELD(HTM_CTRL_MARK, data, 0b10);
			DBG("Final data looks like 0x%"PRIx64" \n", data);

                        DBG("Enabling MTSPR capabilities in CHTM_CTRL REG \n");
                        rc=xscom_write_ex(c->ex_target, CHTM_BASE+HTM_CTRL, data);
                        if (rc) {
                                ERR("xscom CHTM_CTRL write failed, rc=%d\n", rc);
                                return -1;
                        }

			/* only scom each core once */
			core_touched = c->ex_target;
                }
        }
	return 0;
}


/*HACK TO CONVERT TO HANDLE xscom's need for chip2 and chip 3 to be x10 and x11*/
int convert_chip(int cpu){
	if (cpu == 2) return 16;
	else if (cpu == 3) return 17;
	else return cpu;
}

uint64_t convert_memory(const char *arg){

	char size[5];
	char type[2];
	uint64_t memory_size;
	strcpy(type, arg+strlen(arg)-1);
	strcpy(size, arg);
	size[strlen(size)-1]='\0';
	memory_size = strtoll(size,NULL,10);

	if ((strcasecmp(type, "M") == 0) || (strcasecmp(arg, "m") == 0)){
		memory_size = memory_size*MB;
	}else if ((strcasecmp(type, "G") == 0) || (strcasecmp(arg, "g") == 0)){
		memory_size = memory_size*GB;
	}else if ((strcasecmp(type, "K") == 0) || (strcasecmp(arg, "k") == 0)){
		memory_size = memory_size*KB;
	}else{
		ERR("You have selected an invalid memory configuration Must end in M or G\n");
		exit(1);
	}

	DBG("your size is %"PRIx64" \n",memory_size);
	return memory_size;

/*
        if (strcasecmp(arg, "16M") == 0) {memsize = HTM_512M_OR_16M;*i_use_small_mem=true;}
        else if (strcasecmp(arg, "32M") == 0) {memsize = HTM_512M_OR_16M;*i_use_small_mem=true;}
        else if (strcasecmp(arg, "32M") == 0) {memsize = HTM_1G_OR_32M;*i_use_small_mem=true;}
        else if (strcasecmp(arg, "64M") == 0) {memsize = HTM_2G_OR_64M;*i_use_small_mem=true;}
        else if (strcasecmp(arg, "128M") == 0) {memsize = HTM_4G_OR_128M;*i_use_small_mem=true;}
        else if (strcasecmp(arg, "256M") == 0) {memsize = HTM_8G_OR_256M;*i_use_small_mem=true;}
        else if (strcasecmp(arg, "512M") == 0) {memsize = HTM_512M_OR_16M;}
        else if (strcasecmp(arg, "1G") == 0) {memsize = HTM_1G_OR_32M;}
        else if (strcasecmp(arg, "2G") == 0) {memsize = HTM_2G_OR_64M;}
        else if (strcasecmp(arg, "4G") == 0) {memsize = HTM_4G_OR_128M;}
        else if (strcasecmp(arg, "8G") == 0) {memsize = HTM_8G_OR_256M;}
        else if (strcasecmp(arg, "16G") == 0) {memsize = HTM_16G_OR_512M;}
        else if (strcasecmp(arg, "32G") == 0) {memsize = HTM_32G_OR_1G;}
        else if (strcasecmp(arg, "64G") == 0) {memsize = HTM_64G_OR_2G;}
        else if (strcasecmp(arg, "128G") == 0) {memsize = HTM_128G_OR_4G;}
        else if (strcasecmp(arg, "256G") == 0) {memsize = HTM_256G_OR_8G;}
*/

}

static void get_active_chips(){
	int rc;
	rc = access(MEMTRACE_DIR"/"MEMTRACE_C0"/", F_OK);
	if(rc == 0){
		active_chip_mask |= 0b0001;
	}
	rc = access(MEMTRACE_DIR"/"MEMTRACE_C1"/", F_OK);
	if(rc == 0){
		active_chip_mask |= 0b0010;
	}
	rc = access(MEMTRACE_DIR"/"MEMTRACE_C8"/", F_OK);
	if(rc == 0){
		active_chip_mask |= 0b10000;
	}
	rc = access(MEMTRACE_DIR"/"MEMTRACE_C10"/", F_OK);
	if(rc == 0){
		active_chip_mask |= 0b0100;
	}
	rc = access(MEMTRACE_DIR"/"MEMTRACE_C11"/", F_OK);
	if(rc == 0){
		active_chip_mask |= 0b1000;
	}
}

static bool is_memory_allocated(){
	if (active_chip_mask == 0)
		return false;
	else
		return true;
}

bool is_chip_active(int i_target){
	uint32_t cpu = i_target >> 4;
	if (cpu == 0){
		if (active_chip_mask & 0b0001)
			return true;
		else
			return false;
	}else if(cpu == 1){
		if (active_chip_mask & 0b0010)
			return true;
		else
			return false;
	}else if(cpu == 8){
		if (active_chip_mask & 0b10000)
			return true;
		else
			return false;
	}else if(cpu == 16){
		if (active_chip_mask & 0b0100)
			return true;
		else
			return false;
	}else if(cpu == 17){
		if (active_chip_mask & 0b1000)
			return true;
		else
			return false;
	}
	else
		return false;
	}

static int32_t memtrace_compatability(){
        int rc = access(MEMTRACE_DIR, F_OK);
        if(rc == -1){
		if (errno == ENOENT){
                	fprintf(stderr, "Failed to find directory "MEMTRACE_DIR"cannot continue\n ");
                	exit(1);
		}
        }
        return 0;
}

uint64_t prepare_and_call_setup(struct htm_args i_args){
	bool filter = false;
	int rc = 0;
	if (!is_memory_allocated()){
		printf("No Active allocations detected.  Setting default size of 256MB \n");
		htm_allocate(DEFAULT_SIZE);
	}
	/* Reread sysfs to see if chip is now in list*/
        get_active_chips();
	if (!is_chip_active(i_args.target)){
		ERR("Chip %d is not active on this machine \n",i_args.target);
		exit(1);
	}
	/* core mtspr is not required on POWER9 */
	if (get_processor_version() == "POWER8")
		enable_core_mtspr(i_args.target);
		/*rc=htm_setup(cpu_no, htm_type, nowrap, precise);*/
	rc=htm_setup(i_args);
	if (rc) {
        	ERR("htm_setup failed, rc=%d\n", rc);
        	return -1;
	}
	/* For now filter every go  but needs to be after setup so it doesn't get overwritten*/
	rc=htm_filter(filter, i_args.target, i_args.htm_type);
	if (rc) {
       		ERR("htm_filter failed, rc=%d\n", rc);
       		return -1;
        }
	return 0;
}

uint64_t prepare_and_call_start(struct htm_args i_args){
	int rc = 0;
	uint64_t status_reg = get_htm_status_reg(i_args.target, i_args.htm_type);

	/* figure out how much hasn't been done */
		/* No memory allocated...start here */
		if (!is_memory_allocated()){
			printf("No Active allocations detected.  Setting default size of 256MB \n");
			htm_allocate(DEFAULT_SIZE);
		}

		/* We are uninitialized run htm_setup */
		if (status_reg == 0){
			prepare_and_call_setup(i_args);
		/* If we are in complete mode, issue reset */
		}else if (status_reg & HTM_STAT_COMPLETE){
	                rc=htm_reset(i_args.target, i_args.htm_type);
        	        if (rc) {
                        	ERR("htm_reset failed, rc=%d\n", rc);
                        	return -1;
                	}else{
                        	printf("HTM successfully Reset \n");
                	}
		}
	/* reread HTM status register */
	status_reg = get_htm_status_reg(i_args.target, i_args.htm_type);
	/* finally ready to get start going*/
	if (status_reg & HTM_STAT_READY || is_memory_allocated()){
		if (!i_args.use_spr){
			rc=htm_start(i_args.target, i_args.htm_type);
			if (rc) {
       				ERR("htm_start failed, rc=%d\n", rc);
       				return -1;
		        }else{
				printf("HTM successfully Started \n");
        		}
		} else {
			htm_start_mtspr();
		}
	}else{
		printf ("STATUS REG %x \n", status_reg);
		ERR("We are still not in HTM READY STATE FAILING \n");
		return -1;
	}
	return 0;
}

/* Allow 2 status values to be returned in the case of P9. On older platforms, we should continue to get just 1 status value */
uint64_t prepare_and_call_start_multi(struct htm_args i_args){
	int rc = 0;
	uint64_t *status_regs_multi;

	status_regs_multi = get_htm_status_reg_multi(i_args.target, i_args.htm_type);

	/* figure out how much hasn't been done */
		/* No memory allocated...start here */
		if (!is_memory_allocated()){
			printf("No Active allocations detected.  Setting default size of 256MB \n");
			htm_allocate(DEFAULT_SIZE);
		}

		/* We are uninitialized (either NHTM0 or 1 or both) run htm_setup */
#ifdef P9
		if ((*status_regs_multi == 0) || (*(status_regs_multi + 1) == 0)){
#else
		if (*status_regs_multi == 0) {
#endif
			prepare_and_call_setup(i_args);
		/* If we are in complete mode, issue reset */
#ifdef P9
		}else if ((*status_regs_multi & HTM_STAT_COMPLETE) && (*(status_regs_multi + 1) & HTM_STAT_COMPLETE)){
#else
		}else if ((*status_regs_multi & HTM_STAT_COMPLETE)){
#endif
	                rc=htm_reset(i_args.target, i_args.htm_type);
        	        if (rc) {
                        	ERR("htm_reset failed, rc=%d\n", rc);
                        	return -1;
                	}else{
                        	printf("HTM successfully Reset \n");
                	}
		}

	/* reread HTM status register */
	*(status_regs_multi) = 0x0;
	*(status_regs_multi + 1) = 0x0;
	status_regs_multi = get_htm_status_reg_multi(i_args.target, i_args.htm_type);

	/* finally ready to get start going*/
#ifdef P9
	if (((*status_regs_multi & HTM_STAT_READY) && (*(status_regs_multi + 1) & HTM_STAT_READY)) ||\
				is_memory_allocated()) {
#else
	if ((*status_regs_multi & HTM_STAT_READY)  || is_memory_allocated()) {
#endif
		if (!i_args.use_spr){
			rc=htm_start(i_args.target, i_args.htm_type);
			if (rc) {
       				ERR("htm_start failed, rc=%d\n", rc);
       				return -1;
		        }else{
				printf("HTM successfully Started \n");
        		}
		} else {
			htm_start_mtspr();
		}
	}else{
#ifdef P9
		printf ("STATUS REG %x (1) %x (2) \n", *status_regs_multi, *(status_regs_multi + 1));
#else
		printf ("STATUS REG %x \n", *status_regs_multi);
#endif
		ERR("We are still not in HTM READY STATE FAILING \n");
		return -1;
	}
	return 0;
}

uint64_t prepare_and_call_stop(struct htm_args i_args){
	int rc = 0;
	if (! i_args.use_spr){
		rc=htm_stop(i_args.target, i_args.htm_type);
		if (rc) {
        		ERR("htm_stop failed, rc=%d\n", rc);
        		return -1;
		}else{
			printf("HTM successfully Stopped \n");
		}
	} else {
		htm_stop_mtspr();
	}
	return 0;
}
static void show_usage(void)
{
	printf("Htm tool for open power\n\n");
	printf("Basic Commands:\n");
	printf("--allocate - (once per boot) reserve memory on each chip for htm tracing\n");
	printf("	--memsize=<size> - amount of memory to reserve on each chip\n");
	printf("			   for example 32M, or 16G\n\n");
	printf("--mode=<fabric|llat> - specify whether to perform a fabric or llat trace \n");
	printf("--list_cpus - display system cpu's numa information.  This is important \n");
	printf("	      since Nest HTM(NHTM) is by chip, and core htm(CHTM) is by core\n");
	printf("--setup - initialize trace registers with specified values\n");
	printf("	--ex=<core_number> - which core to execute command against \n\n");
	printf("	[--cpu|-c] <cpu> - which chip to execute command against \n");
	printf("	--nowrap [optional] - don't wrap once trace buffer is full.\n");
	printf("	--precise [optional] - turn on precise mode and stop cresp gathering\n\n");
	printf("--start - start htm trace\n");
	printf("	--ex=<core_number> - which core to execute command against \n\n");
	printf("	--cpu=<cpu> - which chip to execute command against \n\n");
	printf("--start_mtspr - start htm trace using mtspr trigger instead of scoms \n\n");
	printf("--stop - stop trace and put it in COMPLETE state\n");
	printf("	--cpu=<cpu> - which chip to execute command against \n\n");
	printf("--stop_mtspr - stop htm trace using mtspr trigger instead of scoms \n\n");
	printf("--reset - reset trace from COMPLETE to READY state\n");
	printf("	--cpu=<cpu> - which chip to execute command against \n\n");
	printf("--mark=<marker> - puts marker in trace data where <marker> is any\n");
	printf("                  10 bit value\n\n");
	printf("--status - gather the status of htm\n");
	printf("	--cpu=<cpu> - which chip to execute command against \n");
	printf("	--ex=<core_number> - which core to execute command against \n\n");
	printf("--dump - dump all or part of trace to a file\n");
	printf("	--cpu=<cpu> - which chip to execute command against \n");
	printf("	--ex=<core_number> - which core to execute command against \n");
	printf("	--filename=<filename> - file to dump htm trace to \n");
	printf("	--filename2=<filename> - file to dump htm trace (nhtm1 in case of p9) to \n");
	printf("	Only specifying filename dumps the complete trace (nhtm0 and 1 for p9) into \n");
	printf("	a single file (filename) \n");
	printf("	--size=<size> [optional] - dump only specified amount of\n");
	printf("				   trace starting from end\n");
	printf("	--head [optional] - dump <size> amount starting at beginning of storage\n\n");
	printf("--agg - aggregate the output of nhtm0 and nhtm1 (p9 only) \n");
	printf("	--filename=<filename> - file containing trace output of nhtm0 \n");
	printf("	--filename2=<filename2> - file containing trace output of nhtm1 \n");
	printf("	--aggfile=<aggfile> - file to aggregate the nhtm traces into \n");
	printf("	--agg should be executed only after --dump has been completed \n");

	printf("[--verbose|-v]  dump all or part of trace to a file\n");

}

int parse_arg_on(const char *arg)
{
	if ((strcasecmp(arg, "yes") == 0) || (strcasecmp(arg, "on") == 0)) return 1;
	else return 0;
}
int parse_mode(const char *arg)
{
	if ((strcasecmp(arg, "fabric") == 0) || (strcasecmp(arg, "nest") == 0))
		return HTM_FABRIC;
	else if (strcasecmp(arg, "llat") == 0) 
		return HTM_LLAT;
	else {
	   perror("A valid HTM mode has not been selected\n");
	   printf(" %s'n", arg);
           exit(1);
	}
}
int main(int argc, char *argv[])
{
	struct htm_args set_args;
	int rc;
	uint64_t data = 0;
	bool status = false;
	bool dump = false;
	bool filter = false;
	bool tail = true;
	bool use_spr = false;
	uint32_t htm_type = HTM_FABRIC;

	uint64_t marker_val = 0;
#ifdef P9
	uint64_t *memory_size_multi, dump_size0=-1, dump_size1=-1, start_addr0 = 0, start_addr1 = 0;
	uint64_t dump_usize2 = -1;
	uint64_t memory_start;
#else
	uint64_t dump_size_pre_P9=-1;
#endif
	uint64_t memory_size=-1, dump_usize=-1, start_addr=0;
	/*default to cpu 0 if not specified */
	int cpu_no = 0;
	int ex_no = 0;
	command_t command = UNSET;
	char *filename = NULL;
#ifdef P9
	char *filename2 = NULL;
	/* aggregation related vars */
	char *aggfile	= NULL;
	bool agg	= false;
	bool usersize   = false; /* user specified a dump size */
	bool aggregate  = true; /* a single consolidated output for nhtm0 and nhtm1 */
#endif
	/* Check if machine is capable of allocating memory for htm.  Bail if now */
	printf("Starting htm v"VERSION"\n");

   while(1) {
                static struct option long_opts[] = {
                        {"status",       no_argument,      NULL,   'A'},
                        {"setup",      no_argument,      NULL,   'B'},   
                        {"start",       no_argument,      NULL,   'C'},
                        {"stop",        no_argument,      NULL,   'D'},
                        {"reset",        no_argument,      NULL,   'E'},
			{"list_cpus",        no_argument,      NULL,   'L'},
                        {"nowrap",        no_argument,      NULL,   'F'},
                        {"allocate",       no_argument,      NULL,   'G'},
                        {"dump",       no_argument,      NULL,   'H'},
                        {"precise",       no_argument,      NULL,   'I'},
                        {"head",       no_argument,      NULL,   'J'},
                        {"start_mtspr",        no_argument,      NULL,   'K'},
                        {"stop_mtspr",        no_argument,      NULL,   'M'},
                        {"mode",       required_argument,      NULL,   'o'},
                        {"ex",       required_argument,      NULL,   'e'},
			{"mark",         required_argument,      NULL,   'a'},
			{"size",         required_argument,      NULL,   'z'},
			{"size2",         required_argument,      NULL,   'y'},
			{"cpu",         required_argument,      NULL,   'c'},
			{"filename",     required_argument,      NULL,   'm'},
			{"memsize",     required_argument,      NULL,   's'},
			{"filter",     required_argument,      NULL,   'f'},
			{"help",        no_argument,      NULL,   'h'},
			{"verbose",        no_argument,      NULL,   'v'},
			{"filename2",        required_argument,      NULL,   'n'},
			{"agg",		no_argument, 	NULL,  'g'},
			{"aggfile",	required_argument,   NULL,  'b'},
			{NULL,0, 0, 0}

                };
	int c, oidx = 0;
#ifdef P9
	c = getopt_long(argc, argv, "c:vhz:y:", long_opts, &oidx);
#else
	c = getopt_long(argc, argv, "c:vh", long_opts, &oidx);
#endif
	if (c == EOF)
		break;
	switch(c) {
	case 'A':
		command=STATUS;
		status = true;
		break;
	case 'B':
		command=SETUP;
		break;
	case 'C':
		command=START;
		status = true;
		break;
	case 'D':
		command=STOP;
		status = true;
		break;	
	case 'E':
		command=RESET;
		status = true;
		break;	
	case 'F':
		set_args.nowrap = true;
		break;	
	case 'G':
		command=ALLOCATE;
		break;	
	case 'H':
		command=DUMP;
		dump = true;
		break;	
	case 'I':
			set_args.precise = true;
		break;
	case 'J':
		tail=false;
		break;	
	case 'L':
		command=LIST;
		break;	
	case 'K':
		command=START;
		status = true;
		set_args.use_spr = true;
		break;	
	case 'M':
		command=STOP;
		status = true;
		set_args.use_spr = true;
		break;	
	case 'a':
		command=MARK;
		marker_val = convert_chip(strtoul(optarg, NULL, 0));
		break;
	case 'c':
		cpu_no = convert_chip(strtoul(optarg, NULL, 0));
		break;
	case 'e':
		ex_no = strtoul(optarg, NULL, 0);
		break;
	case 's':
		memory_size = convert_memory(optarg);
		break;
	case 'z':
		dump_usize = convert_memory(optarg);
		usersize = true;
		break;
	case 'm':
		filename = optarg;
		break;
#ifdef P9
	case 'y':
		dump_usize2 = convert_memory(optarg); /* user dump size for nhtm1 */
		usersize = true;
		break;
	case 'n':
		filename2 = optarg; /* required if we wish to capture the nhtm1 dump for p9 */
		break;
#endif
	case 'o':
		htm_type = parse_mode(optarg);
		break;
	case 'f':
		if(parse_arg_on(optarg))
			filter = true;
		else
			filter = false;
		break;
	case 'h':
		show_usage();
		exit(0);
	case 'v':
		verbose = true;
		break;
#ifdef P9
	case 'g':
		command = AGGREGATE;
		agg = true;
		break;
	case 'b':
		aggfile = optarg;
		break;
#endif
	default:
		exit(1);
	
	}
	}


/* bail early if a command wasn't sent...save us from having to do useless work*/
	if (command == UNSET){
		printf("invalid command selected \n");
		show_usage();
		exit(0);
	}

#ifdef P9
	if (dump) { /* aggregate nhtm0 and nhtm1 output */
		if (filename == NULL) {
			ERR("Need to specify --filename (file to write consolidated binary trace data into) \n");
			exit(1);		
		}
	}
#endif
	memtrace_compatability();

	set_args.precise = false;
	set_args.nowrap = false;
	/*xscom_read(*/

	xscom_init();
	/* get the list of active chips in the machine.   */
	get_active_chips();
	init_cpus();
	
	set_args.target=(cpu_no << 4) + ex_no;
	printf("tergat is %d cpu is %d ex is%d\n", set_args.target, cpu_no, ex_no);
	set_args.htm_type = htm_type;	
	if (command == LIST){
		show_cpus_info();
		exit(0);	
	}else if (command == ALLOCATE){
		if (is_memory_allocated()){
			ERR("Allocation has already been done on this machine \n");
			exit(1);
		}
		htm_allocate(memory_size);
		exit(0);	
	
	}
	/*init_cpus();*/
	if (cpu_no < 0){
		ERR("No cpu specified.  Please use -c option \n");
		exit(1);
	}
	
	

	if (command == MARK){
		DBG("Final data looks like 0x%"PRIx64" \n", marker_val);
		htm_mark_mtspr(marker_val);

		/*htm_set_marker(cpu_no, HTM_FABRIC, marker_val);*/
		exit(0);
	} else if (command == SETUP) {
		prepare_and_call_setup(set_args);	
	} else if (command == START) {
		prepare_and_call_start_multi(set_args);
	} else if (command == STOP) {
		prepare_and_call_stop(set_args);

	} else if (command == RESET) {
		rc=htm_reset(set_args.target, set_args.htm_type);
		if (rc) {
        		ERR("htm_reset failed, rc=%d\n", rc);
        		return -1;
	        }else{
			printf("HTM successfully Reset \n");
	        }
	}

	if (command == STATUS) {
		get_htm_status(set_args.target,set_args.htm_type);
	}

	if (dump || filename != NULL){
		if(filename == NULL){
			ERR("You tried to dump a file without specifying --filename \n");
			exit(1);
		}

		/*memory_size = get_mem_size(cpu_no);*/
#ifdef P9
		memory_size_multi=get_htm_last_size_multi(set_args.target, htm_type); /* last - start */
#else
		memory_size=get_htm_last_size(set_args.target, htm_type);
#endif
		if(dump_usize == -1) {
#ifdef P9
			if (dump_usize2 == -1) { /* no dump size specified by user */
				if (filename2 != NULL) {
				dump_size0 = *memory_size_multi;
				dump_size1 = *((uint64_t*)(memory_size_multi + 1));
				}
				else { /* dump_size0 = user specified dump size. dump_size1 = max dump size possible */
				 if (*memory_size_multi > *((uint64_t*)(memory_size_multi + 1)))
					dump_size1 = *memory_size_multi;
				 else
					dump_size1 = *((uint64_t*)(memory_size_multi + 1));

				 dump_size0 = dump_size1; /* user specified dump size = max dump size possible, since dump size */
							  /* was not user specified. */
				}
			} /* end if dump_usize2 == -1 */
			else { /* dump_usize2 specified */
				printf("A dump size was specified for nhtm1 only. Assuming the same size for nhtm0\n");
				dump_usize = dump_usize2;
				if (filename2 != NULL) { /* fetch for nhtm0 and nhtm1 separately */
		 	 	dump_size0 = dump_usize;
			 	dump_size1 = dump_usize2;
				}
				else {
				 /* save the user specified dump size in dump_size0. Save the larger of the two 
				 memory sizes in dump_size1 */
				 dump_size0 = dump_usize2; /* placeholder */
				 if (*memory_size_multi > *((uint64_t*)(memory_size_multi + 1)))
					dump_size1 = *memory_size_multi;
				 else
					dump_size1 = *((uint64_t*)(memory_size_multi + 1));

				 dump_size0 = dump_size1; /* user specified dump size = max dump size possible, since dump size */
							  /* was not user specified. */
				}
			}
#else
			dump_size_pre_P9 = memory_size;
#endif
		}
		else {
#ifdef P9
			if (dump_usize2 == -1) {/* User specified one dump size only. Assume the same for both nhtm0 and nhtm1.*/
				dump_usize2 = dump_usize;
			}
			if (filename2 != NULL) { /*set only if fetching for nhtm0 and nhtm1 separately */
		 	 dump_size0 = dump_usize;
			 dump_size1 = dump_usize2;
			}
			else { /* aggregate */
			 /* save the user specified dump size in dump_size0. Save the larger of the two 
			 memory sizes in dump_size1 */
			 dump_size0 = dump_usize; /* placeholder */
			 if (*memory_size_multi > *((uint64_t*)(memory_size_multi + 1)))
				dump_size1 = *memory_size_multi;
			 else
				dump_size1 = *((uint64_t*)(memory_size_multi + 1));
			}
#else
			dump_size_pre_P9 = dump_size;
#endif
		}

		if (!tail) {
#ifdef P9
			start_addr0 = 0;
			start_addr1 = 0;
#else
			start_addr = 0;
#endif
		}
		else{
#ifdef P9
			if (filename2 != NULL) {
				if ((dump_size0 > *memory_size_multi) || \
					(dump_size1 > *((uint64_t*)(memory_size_multi + 1)))) {
					if (dump_size0 > *memory_size_multi) {
						printf("Specified dump size is too big for nhtm0 \n");
						printf("Max dump size possible: %lx\n", *memory_size_multi);
					}
					if (dump_size1 > *((uint64_t*)(memory_size_multi + 1))) {
						printf("Specified dump size is too big for nhtm1 \n");
						printf("Max dump size possible: %lx\n", *((uint64_t*)(memory_size_multi + 1)));
					}
					return -1;
				}
			start_addr0 = *memory_size_multi - dump_size0;
			start_addr1 = *((uint64_t*)(memory_size_multi + 1)) - dump_size1;
			}
			else {
				if (dump_size0 > dump_size1) { /* user specified dump size > max memory dump possible */
					printf("Aggregate: Dump size is too big.\n");
					printf("Max dump size possible: %lx\n", dump_size1);
					return -1;
				}
			}

		/* If dump_size was not specified, then, start_addr0 = start_addr1, 
		memory_size0 and memory_size1 should differ by 128 bytes? */
			 printf("start_addr0 %" PRIx64 "\n",start_addr0);
			 printf("memory_size0 %" PRIx64 "\n",*memory_size_multi);
			 if (filename2 == NULL)
			  printf("User specified dump size %" PRIx64 "\n",dump_size0);
			 else
			  printf("dump_size0 %" PRIx64 "\n",dump_size0);
			 printf("start_addr1 %" PRIx64 "\n",start_addr1);
			 printf("memory_size1 %" PRIx64 "\n",*((uint64_t*)(memory_size_multi + 1)));
			 if (filename2 == NULL)
			  printf("Max possible dump size %" PRIx64 "\n",dump_size1);
			 else
			  printf("dump_size1 %" PRIx64 "\n",dump_size1);
#else
			if (dump_size_pre_P9 > memory_size){
				printf("Dump size is too big \n");
				return -1;
			}
			start_addr = memory_size - dump_size_pre_P9;

			 printf("start_addr %" PRIx64 "\n",start_addr);
			 printf("memory_size %" PRIx64 "\n",memory_size);
			 printf("dump_size %" PRIx64 "\n",dump_size_pre_P9);
#endif
		}

#ifdef P9
		/* first get the memory start address */
		memory_start = get_mem_start(set_args.target);
		/* Call _full once _test works */
		/* If dump==true, and a single filename is specified, prepare a single binary data 
		file consolidating nhtm0 and 1 */
		/* else, prepare separate binary data files one each for nhtm0 and nhtm1 */
		if (filename2 == NULL)  { /* aggregated dump in a single output file */
		 aggregate = true;
		 htm_dump_fabric_trace_single(set_args.target, filename, memory_start,start_addr0, \
			dump_size0, start_addr1, dump_size1);
		}
		else  { /* dump for nhtm0 and nhtm1 separately */
		 aggregate = false;
		 htm_segregate_fabric_trace_full2(set_args.target, filename, filename2, memory_start, \ 
			start_addr0, dump_size0, start_addr1, dump_size1, usersize);	
                }
#else
		htm_dump(cpu_no, filename, start_addr, dump_size_pre_P9);
#endif
	}
	return 0;
}
