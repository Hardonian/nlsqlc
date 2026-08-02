CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -Wformat=2 -Wundef
CPPFLAGS ?= -Iinclude
all: libnlsql.a nlsqlc
libnlsql.a: src/nlsql.o
	ar rcs $@ $^
src/nlsql.o: src/nlsql.c include/nlsql/nlsql.h
	$(CC) $(CFLAGS) $(CPPFLAGS) -c $< -o $@
nlsqlc: cli/nlsqlc.c libnlsql.a
	$(CC) $(CFLAGS) $(CPPFLAGS) $< libnlsql.a -o $@
test: all
	$(CC) $(CFLAGS) $(CPPFLAGS) tests/test_core.c libnlsql.a -o /tmp/nlsql-tests
	/tmp/nlsql-tests
clean:
	rm -f src/*.o libnlsql.a nlsqlc /tmp/nlsql-tests
.PHONY: all test clean
