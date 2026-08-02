CC ?= cc
PREFIX ?= /usr/local
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -Wformat=2 -Wundef
LDFLAGS ?= -static
CPPFLAGS ?= -Iinclude
all: libnlsql.a nlsqlc
libnlsql.a: src/nlsql.o
	ar rcs $@ $^
src/nlsql.o: src/nlsql.c include/nlsql/nlsql.h
	$(CC) $(CFLAGS) $(CPPFLAGS) -c $< -o $@
nlsqlc: cli/nlsqlc.c libnlsql.a
	$(CC) $(CFLAGS) $(CPPFLAGS) $< libnlsql.a $(LDFLAGS) -o $@
test: all
	$(CC) $(CFLAGS) $(CPPFLAGS) tests/test_core.c libnlsql.a -o /tmp/nlsql-tests
	/tmp/nlsql-tests
	$(CC) $(CFLAGS) $(CPPFLAGS) tests/test_question.c libnlsql.a -o /tmp/nlsql-question-tests
	/tmp/nlsql-question-tests
clean:
	rm -f src/*.o libnlsql.a nlsqlc /tmp/nlsql-tests /tmp/nlsql-question-tests
install: all
	install -d "$(DESTDIR)$(PREFIX)/bin" "$(DESTDIR)$(PREFIX)/lib" "$(DESTDIR)$(PREFIX)/include/nlsql"
	install -m 0755 nlsqlc "$(DESTDIR)$(PREFIX)/bin/nlsqlc"
	install -m 0644 libnlsql.a "$(DESTDIR)$(PREFIX)/lib/libnlsql.a"
	install -m 0644 include/nlsql/nlsql.h "$(DESTDIR)$(PREFIX)/include/nlsql/nlsql.h"
.PHONY: all test clean install
