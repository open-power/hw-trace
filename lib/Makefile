all: htm_mtspr.o libhtm_mtspr.a
CFLAGS=-O2 -g -Wall -m64

htm_mtspr.o: htm_mtspr.c
	$(CC) $(CFLAGS) -c $^

libhtm_mtspr.a: htm_mtspr.o
	ar -cvq  $@ $^

.PHONY: clean

clean:
	rm htm_mtspr.o libhtm_mtspr.a
