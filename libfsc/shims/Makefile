CC = gcc
CFLAGS = -Wall -I.. -O2
LDFLAGS =

CORE_SRC = ../fsc_core.c
SHIMS = fsc_sqlite_shim fsc_kernel_driver fsc_udp_shim fsc_postgres_shim fsc_mysql_shim

all: $(SHIMS)

fsc_sqlite_shim: fsc_sqlite_shim.c $(CORE_SRC)
	$(CC) $(CFLAGS) $^ -o $@

fsc_kernel_driver: fsc_kernel_driver.c $(CORE_SRC)
	$(CC) $(CFLAGS) $^ -o $@

fsc_udp_shim: fsc_udp_shim.c $(CORE_SRC)
	$(CC) $(CFLAGS) $^ -o $@

fsc_postgres_shim: fsc_postgres_shim.c $(CORE_SRC)
	$(CC) $(CFLAGS) $^ -o $@

fsc_mysql_shim: fsc_mysql_shim.c $(CORE_SRC)
	$(CC) $(CFLAGS) $^ -o $@

clean:
	rm -f $(SHIMS)

run: all
	./fsc_sqlite_shim
	@echo "----------------------------------------"
	./fsc_kernel_driver
	@echo "----------------------------------------"
	./fsc_udp_shim
	@echo "----------------------------------------"
	./fsc_postgres_shim
	@echo "----------------------------------------"
	./fsc_mysql_shim

.PHONY: all clean run
