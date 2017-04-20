all: libraries htm

CFLAGS=-O2 -g -Wall -m64
CC = $(CROSS_COMPILE)gcc
htm: htm.c htm_status.c htm_xscom.c xscom.c htm_setup.c htm_ctrl.c htm_utils.c htm_allocate.c htm_dump.c lib/htm_mtspr.h

	echo ${CC}
	$(CC) $(CFLAGS) -o $@ $^ -Llib -lhtm_mtspr

LIB_DIR = lib
.PHONY: libraries

libraries: 
	$(MAKE) -C $(LIB_DIR)

.PHONY: clean
clean:
	rm -rf htm
	$(MAKE) -C $(LIB_DIR) clean 

.PHONY: distclean
distclean: clean
	rm -rf *.c~ *.h~ *.i *.s Makefile~

