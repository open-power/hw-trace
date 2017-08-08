#ifndef __HTM_H
#define __HTM_H

#include <stdint.h>
#include <stdbool.h>

extern bool verbose;

/* Bit utilities */
#define PPC_BIT(bit)            (0x8000000000000000UL >> (bit))
#define PPC_BITMASK(bs,be)      ((PPC_BIT(bs) - PPC_BIT(be)) | PPC_BIT(bs))
#define PPC_BITLSHIFT(be)       (63 - (be))
#define GETFIELD(fname, val)                    \
        (((val) & fname##_MASK) >> fname##_LSH)
#define SETFIELD(fname, oval, fval)                     \
        (((oval) & ~fname##_MASK) | \
         ((((typeof(oval))(fval)) << fname##_LSH) & fname##_MASK))

#define CORE_MULTIPLIER 0x01000000
#define MEMTRACE_DIR "/sys/kernel/debug/powerpc/memtrace"
#define MEMTRACE_C0 "00000000"
#define MEMTRACE_C1 "00000001"
#define MEMTRACE_C8 "00000008"
#define MEMTRACE_C10 "00000010"
#define MEMTRACE_C11 "00000011"

/* SCOM Address for Core HTM */
#define CHTM_BASE  0x10011000

/* SCOM Address for Nest HTM */
#define NHTM_BASE  0x02010880

#define NCU_MODE_REG 0x10010C0A



/* SCOM ADDRESS FOR MCS4 */
#define MCS4_MCFGPQ 0x02011c00
#define MCS4_MCMODE 0x02011c07
#define MCS4_FIRMASK 0x02011c43

/* SCOM ADDRESS FOR MCS5 */
#define MCS5_MCFGPQ 0x02011c80
#define MCS5_MCMODE 0x02011c87
#define MCS5_FIRMASK 0x02011cc3

/* SCOM ADDRESS FOR MCS6 */
#define MCS6_MCFGPQ 0x02011d00
#define MCS6_MCMODE 0x02011d07
#define MCS6_FIRMASK 0x02011d43

/* SCOM ADDRESS FOR MCS7 */
#define MCS7_MCFGPQ 0x02011d80
#define MCS7_MCMODE 0x02011d87
#define MCS7_FIRMASK 0x02011dc3

#define MCS_VALID	PPC_BIT(0)

#define MCS_BUFFER_MASK PPC_BITMASK(28,31)
#define MCS_BUFFER_LSH PPC_BITLSHIFT(31)
#define MCS_FIRMASK_DISABLE_TIMEOUT PPC_BIT(27)

#define HTM_FABRIC  0
#define HTM_EVENT   1
#define HTM_OCC     2
#define HTM_CORE    3
#define HTM_LLAT    4
#define HTM_OHA     5
#define HTM_DMW     6

/*offsets valid for NHTM and CHTM*/
#define HTM_MODE  0x0
#define HTM_MEM   0x1
#define HTM_STAT  0x2
#define HTM_LAST  0x3
#define HTM_TRIG  0x4
#define HTM_CTRL  0x5

#define HTM_512M_OR_16M	0b000000000
#define HTM_1G_OR_32M 	0b000000001
#define HTM_2G_OR_64M 	0b000000011
#define HTM_4G_OR_128M 	0b000000111
#define HTM_8G_OR_256M 	0b000001111
#define HTM_16G_OR_512M 0b000011111
#define HTM_32G_OR_1G	0b000111111
#define HTM_64G_OR_2G 	0b001111111
#define HTM_128G_OR_4G 	0b011111111
#define HTM_256G_OR_8G 	0b111111111

/* NCU HTM_ENABLE bits*/
#define HTM_ENABLE				PPC_BIT(0)

/*HTM_MODE bits */
#define HTM_MODE_TRACE_ENABLE			PPC_BIT(0)
#define HTM_MODE_CONTENT_SEL_MASK               PPC_BITMASK(1,2)
#define HTM_MODE_CONTENT_SEL_LSH                PPC_BITLSHIFT(2)
#define HTM_MODE_CAPTURE_MASK   	        PPC_BITMASK(4,12)
#define HTM_MODE_CAPTURE_LSH	                PPC_BITLSHIFT(12)
#define HTM_MODE_PRECISE_MODE                  	PPC_BIT(6)
#define HTM_MODE_WRAP_MODE                  	PPC_BIT(13)
#define HTM_MODE_DISABLE_TSTAMPS            	PPC_BIT(14)
#define HTM_MODE_SINGLE_TSTAMPS             	PPC_BIT(15)
#define HTM_MODE_DISABLE_CORE_ITRACE_STALL  	PPC_BIT(16)
#define HTM_MODE_MARKERS_ONLY               	PPC_BIT(17)
#define HTM_MODE_DISABLE_FORCE_GRP_SCOPE    	PPC_BIT(18)

#define HTM_MODE_CONTENT_SEL_NHTM_FABRIC     0
#define HTM_MODE_CONTENT_SEL_NHTM_EVENT_BUS  1
#define HTM_MODE_CONTENT_SEL_NHTM_OCC        2


/* HTM_MEM bits */

#define HTM_MEM_ALLOC		PPC_BIT(0)
#define HTM_MEM_SIZE_SMALL	PPC_BIT(13)
#define HTM_MEM_BASE_MASK	PPC_BITMASK(14,39)
#define HTM_MEM_BASE_LSH	PPC_BITLSHIFT(39)
#define HTM_MEM_SIZE_MASK	PPC_BITMASK(40,48)
#define HTM_MEM_SIZE_LSH	PPC_BITLSHIFT(48)


/*HTM_STAT bits */

#define HTM_STAT_CRESP_OV	PPC_BIT(2)
#define HTM_STAT_REPAIR 	PPC_BIT(3)
#define HTM_STAT_ADDR_ERROR 	PPC_BIT(6)
#define HTM_STAT_REC_DROPPED 	PPC_BIT(7)
#define HTM_STAT_INIT 		PPC_BIT(8)
#define HTM_STAT_PREREQ 	PPC_BIT(9)
#define HTM_STAT_READY 		PPC_BIT(10)
#define HTM_STAT_TRACING	PPC_BIT(11)
#define HTM_STAT_PAUSED 	PPC_BIT(12)
#define HTM_STAT_FLUSH 		PPC_BIT(13)
#define HTM_STAT_COMPLETE	PPC_BIT(14)
#define HTM_STAT_ENABLE 	PPC_BIT(15)
#define HTM_STAT_STAMP 		PPC_BIT(16)

// Bit definitions for HTM_TRIG (EN.TPC.NHTM.SC.HTM_TRIG, EXP.TP.ECO_DOM.CHTM.SC.HTM_TRIG)
#define HTM_TRIG_START       PPC_BIT(0)
#define HTM_TRIG_STOP        PPC_BIT(1)
#define HTM_TRIG_PAUSE       PPC_BIT(2)
#define HTM_TRIG_RESET       PPC_BIT(4)
#define HTM_TRIG_MARK_VALID  PPC_BIT(5)

/*HTM_FILT bits */
#define HTM_FILT_TTAG_MASK	PPC_BITMASK(0,19)
#define HTM_FILT_TTAG_LSH	PPC_BITLSHIFT(19)
#define HTM_FILT_MASK	PPC_BITMASK(32,51)
#define HTM_FILT_LSH	PPC_BITLSHIFT(51)

/* NHTM-only offsets */
#define NHTM_FILT        0x6
#define NHTM_TTYPE_FILT  0x7
#define NHTM_CFG         0x8

/*HTM_TTYPEFILT bits */
#define HTM_TTYPE_PAT_MASK	PPC_BITMASK(0,5)
#define HTM_TTYPE_PAT_LSH	PPC_BITLSHIFT(5)
#define HTM_TSIZE_PAT_MASK	PPC_BITMASK(6,12)
#define HTM_TSIZE_PAT_LSH	PPC_BITLSHIFT(12)
#define HTM_TTYPE_MASK_MASK	PPC_BITMASK(16,21)
#define HTM_TTYPE_MASK_LSH	PPC_BITLSHIFT(21)
#define HTM_TSIZE_MASK_MASK	PPC_BITMASK(22,28)
#define HTM_TSIZE_MASK_LSH	PPC_BITLSHIFT(28)
#define HTM_TTYPE_INVERT  	PPC_BIT(32)

/* Bit definitions for HTM_CTRL */
#define HTM_CTRL_TRIG_MASK	PPC_BITMASK(0,1)
#define HTM_CTRL_TRIG_LSH	PPC_BITLSHIFT(1)
#define HTM_CTRL_MTSPR_TRIG 	PPC_BIT(2)
#define HTM_CTRL_MTSPR_MARK 	PPC_BIT(3)
#define HTM_CTRL_MARK_MASK      PPC_BITMASK(4,5)
#define HTM_CTRL_MARK_LSH       PPC_BITLSHIFT(5)
#define HTM_CTRL_STOP_ON_DBG_TRIG0       = 6;
#define HTM_CTRL_STOP_ON_DBG_TRIG1       = 7;
#define HTM_CTRL_TRC_RUN_TRIG_ACTION     = 8;
#define HTM_CTRL_STOP_ON_OTHER_DBG_TRIG0 = 9;
#define HTM_CTRL_STOP_ON_OTHER_DBG_TRIG1 = 10;
#define HTM_CTRL_STOP_ON_CHIPLET_XSTOP   = 13;


/* CHTM-only offsets */
#define CHTM_IMA_STAT  0xA
#define CHTM_PDBAR     0xB

/* MARK_TYPE is 6:15 */
#define HTM_TRIG_MARK_TYPE   6
#define HTM_TRIG_MARK_TYPE_LEN   10

/* NHTM-only */
#define NHTM_STAT_PBUS_PAR_ERROR  18;
#define NHTM_STAT_PBUS_INV_CRESP  19;


#define HTM_MODE_CONTENT_SEL_LEN  2;

#define HTM_MODE_CONTENT_SEL_CHTM_CORE  0
#define HTM_MODE_CONTENT_SEL_CHTM_LLAT  1
#define HTM_MODE_CONTENT_SEL_CHTM_OHA   2
#define HTM_MODE_CONTENT_SEL_CHTM_MEM   3

/* Bit definitions for NHTM_FILT*/
#define NHTM_FILT_FILTER_PATTERN     = 0;
#define NHTM_FILT_FILTER        = 32;

#define NHTM_FILT_FILTER_PATTERN_LEN = 20;
#define NHTM_FILT_FILTER_LEN    = 20;

/* Bit definitions for NHTM_TTYPE_FILT */
#define NHTM_TTYPE_FILT_TTYPE_PATTERN = 0;
#define NHTM_TTYPE_FILT_TSIZE_PATTERN = 6;
#define NHTM_TTYPE_FILT_TTYPE    = 16;
#define NHTM_TTYPE_FILT_TSIZE    = 22;
#define NHTM_TTYPE_FILT_CAPTURE_INV   = 32;

#define NHTM_TTYPE_FILT_TTYPE_PATTERN_LEN = 6;
#define NHTM_TTYPE_FILT_TSIZE_PATTERN_LEN = 7;
#define NHTM_TTYPE_FILT_TTYPE_LEN    = 6;
#define NHTM_TTYPE_FILT_TSIZE_LEN    = 7;

/* HTM_MODE bit definitions when Content Select = NHTM Fabric Trace */
#define HTM_MODE_CAP_HTM_WRITES      = 4;
#define HTM_MODE_ENABLE_FILT_ON_ALL  = 5;
#define HTM_MODE_CRESP_MODE          = 6;
#define HTM_MODE_LIMIT_MEM_BUF_ALLOC = 8;
#define HTM_MODE_ENABLE_CTAG_TRACE   = 9;
#define HTM_MODE_ENABLE_ATAG_TRACE   = 10;

#define HTM_MODE_CRESP_MODE_LEN     = 2;

#define HTM_MODE_CRESP_MODE_FLUSH   = 0;
#define HTM_MODE_CRESP_MODE_PRECISE = 2;
#define HTM_MODE_CRESP_MODE_IGNORE  = 3;

/* HTM_MODE bit definitions when Content Select = Core Trace */
#define HTM_MODE_HOLD_TRACE_ACTIVE  = 5;
#define HTM_MODE_PAUSE_ON_PURGE     = 9;

/* HTM_MODE bit definitions when Content Select = NHTM Event Bus */
#define HTM_MODE_LIMIT_MEMORY_BUF_ALLOC = 8;

/* HTM_MODE bit definitions when Content Select = LLAT */
#define HTM_MODE_DIS_CAP_ON_FAILED_DISPATCH = 4;
#define HTM_MODE_DIS_CAP_ON_FAILED_STORES   = 5;
#define HTM_MODE_DIS_CAP_OF_PB_AND_L3_HIT   = 6;
#define HTM_MODE_ENABLE_PAUSE_ON_PURGE      = 7;

/* HTM_MODE bit definitions when Content Select = IMA */
#define HTM_MODE_ENABLE_HPMC_IMA_MODE         = 4;
#define HTM_MODE_ENABLE_POWERPROXY_WRITE_MODE = 5;

/* Bit definitions for HTM_MEM */
#define HTM_MEM_TRC_MEM_ALLOC      = 0;
#define HTM_MEM_TRC_MEM_SCOPE      = 1;
#define HTM_MEM_TRC_MEM_PRIORITY   = 4;
#define HTM_MEM_TRC_MEM_SIZE_SMALL = 13;
#define HTM_MEM_TRC_MEM_BASE_ADDR  = 14;
#define HTM_MEM_TRC_MEM_SIZE       = 40;

#define HTM_MEM_TRC_MEM_SCOPE_LEN     = 3;
#define HTM_MEM_TRC_MEM_PRIORITY_LEN  = 2;
#define HTM_MEM_TRC_MEM_BASE_ADDR_LEN = 26;
#define HTM_MEM_TRC_MEM_SIZE_LEN      = 9;

#define HTM_MEM_TRC_MEM_SCOPE_NODAL     = 0;
#define HTM_MEM_TRC_MEM_SCOPE_GROUP     = 1;
#define HTM_MEM_TRC_MEM_SCOPE_SYSTEM    = 2;
#define HTM_MEM_TRC_MEM_SCOPE_REMOTE    = 3;
#define HTM_MEM_TRC_MEM_SCOPE_FRGN_LNK0 = 4;
#define HTM_MEM_TRC_MEM_SCOPE_FRGN_LNK1 = 5;

#define HTM_MEM_TRC_MEM_PRIORITY_LOW  = 0;
#define HTM_MEM_TRC_MEM_PRIORITY_MED  = 1;
#define HTM_MEM_TRC_MEM_PRIORITY_HIGH = 2;

#define HTM_MEM_TRC_MEM_SIZE_SMALL_512M_TO_256G = 0;
#define HTM_MEM_TRC_MEM_SIZE_SMALL_16M_TO_8G    = 1;

#define HTM_MEM_TRC_MEM_SIZE_512M_OR_16M = 0x0;
#define HTM_MEM_TRC_MEM_SIZE_1G_OR_32M   = 0x1;
#define HTM_MEM_TRC_MEM_SIZE_2G_OR_64M   = 0x3;
#define HTM_MEM_TRC_MEM_SIZE_4G_OR_128M  = 0x7;
#define HTM_MEM_TRC_MEM_SIZE_8G_OR_256M  = 0xF;
#define HTM_MEM_TRC_MEM_SIZE_16G_TO_512M = 0x1F;
#define HTM_MEM_TRC_MEM_SIZE_32G_OR_1G   = 0x3F;
#define HTM_MEM_TRC_MEM_SIZE_64G_OR_2G   = 0x7F;
#define HTM_MEM_TRC_MEM_SIZE_128G_OR_4G  = 0xFF;
#define HTM_MEM_TRC_MEM_SIZE_256G_OR_8G  = 0x1FF;


#define HTM_CTRL_TRIG_CTRL_LEN = 2;
#define HTM_CTRL_MARKER_CTRL_LEN  = 2;

#define HTM_CTRL_TRIG_CTRL_LOCAL_GLOBAL_TRIG = 0;
#define HTM_CTRL_TRIG_CTRL_LOCAL_TRIG        = 1;
#define HTM_CTRL_TRIG_CTRL_GLOBAL_TRIG       = 2;

#define HTM_CTRL_MARKER_CTRL_LOCAL_GLOBAL_MARK = 0;
#define HTM_CTRL_MARKER_CTRL_LOCAL_MARK        = 1;
#define HTM_CTRL_MARKER_CTRL_GLOBAL_MARK       = 2;
#define HTM_CTRL_MARKER_CTRL_NO_MARK           = 3;


#define MAX_NR_CPUS     1024

struct cpu {
	bool		present;
	bool		thread0;
	uint32_t 	hw_no;
	uint32_t 	chip_id;
	uint32_t 	ex_target;
};
struct htm_args {
	uint32_t target;
	int htm_type;
	uint64_t mem_base;
	uint64_t mem_size;
	int reserve_queue;
	bool use_small_mem_size;
	bool nowrap;
	bool precise;
	bool use_spr;
};

int htm_read_xscom(uint32_t i_ex_target, uint64_t addr, int i_htm_type, uint64_t *val);
int htm_write_xscom(uint32_t i_ex_target, uint64_t addr, int i_htm_type, uint64_t val);
void get_htm_status(uint32_t i_ex_target, int htm_type);
/*int htm_setup(uint32_t i_ex_target, int i_htm_type, bool i_nowrap, bool i_precise);*/
int htm_setup(struct htm_args i_args);

/*htm_util.c*/
uint64_t get_mem_size(uint32_t cpu);
uint64_t get_mem_start(uint32_t cpu);
uint64_t get_htm_status_reg(uint32_t i_target, int htm_type);
uint64_t get_htm_last_reg(uint32_t i_target, int htm_type);
uint64_t get_htm_last_size(uint32_t i_target, int htm_type);

int htm_reset (uint32_t i_target, int i_htm_type);
int htm_start (uint32_t i_target, int i_htm_type);
int htm_stop (uint32_t i_target, int i_htm_type);
int htm_pause (uint32_t i_target, int i_htm_type);
int htm_set_marker(uint32_t i_target, int i_htm_type, uint64_t marker_val);
int htm_allocate (uint64_t i_mem_size);
int htm_filter (bool filter, uint32_t i_target, int i_htm_type);
int htm_dump (uint32_t i_target, char* filename, uint64_t start_addr, uint64_t dump_size);
char *get_chip_dir(uint32_t i_target);


#endif /* __HTM */
