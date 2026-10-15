CC:=gcc
#CFLAGS:=-I./src -std=gnu99
CFLAGS:=-I./src -std=gnu99 -O0 -ggdb3 -Wall

LEX:=flex

# Which lex runtime library to link, decided when make runs rather than
# hardcoded, because it differs by platform:
#
#   -lfl    flex's own library. Linux, and Zeus.
#   -ll     the BSD lex library. This is what macOS ships; it has no libfl
#           unless you install flex yourself through Homebrew.
#   (none)  neither is installed. That is fine: the only thing this project
#           takes from the library is yywrap(), and src/scanner.l declares
#           %option noyywrap, so nothing is needed.
#
# Force a particular choice if you ever need to:   make LEXLIB=-ll
LEXLIB := $(shell for l in -lfl -ll; do \
	  printf 'int main(void){return 0;}' \
	    | $(CC) -x c - $$l -o /dev/null >/dev/null 2>&1 \
	    && { echo $$l; break; }; \
	done)

OBJDIR:=obj

YACC:=yacc
YFLAGS:=-v -d -b $(OBJDIR)/y
GRAMMAR:=src/parser.y

GRAMMAROBJS:=$(OBJDIR)/lex.yy.o $(OBJDIR)/y.tab.o
OBJS:=$(GRAMMAROBJS) $(OBJDIR)/tree.o $(OBJDIR)/driver.o $(OBJDIR)/strtab.o

BIN:=$(OBJDIR)/mcc

all: $(BIN)

.PHONY: clean test

# Order-only prerequisite, so every rule that writes into obj/ waits for the
# directory to exist. Without it, make -j can start a compile before mkdir has
# run.
$(OBJDIR):
	mkdir -p $(OBJDIR)

$(BIN): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LEXLIB)

$(OBJDIR)/y.tab.o: $(OBJDIR)/y.tab.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJDIR)/lex.yy.o: $(OBJDIR)/lex.yy.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

# yacc writes y.tab.c and y.tab.h in a single run. Listing both on the left of
# one rule does NOT tell make that: it reads it as two separate rules that
# happen to share a recipe, so under make -j it will cheerfully start two yacc
# processes writing the same two files at once, and the result is a truncated
# y.tab.c and a baffling syntax error in parser.y.
#
# So y.tab.c is the real target, and y.tab.h simply waits for it. The test
# guards the case where y.tab.h is missing but y.tab.c is up to date.
$(OBJDIR)/y.tab.c: $(GRAMMAR) src/tree.h | $(OBJDIR)
	$(YACC) $(YFLAGS) $<

$(OBJDIR)/y.tab.h: $(OBJDIR)/y.tab.c
	@test -f $@ || { rm -f $<; $(MAKE) $<; }

$(OBJDIR)/lex.yy.c: src/scanner.l $(OBJDIR)/y.tab.h | $(OBJDIR)
	$(LEX) -o $@ $<

$(OBJDIR)/tree.o: src/tree.c src/tree.h | $(OBJDIR)
	$(CC)  $(CFLAGS) -c $< -o $@

$(OBJDIR)/driver.o: src/driver.c src/tree.h $(OBJDIR)/y.tab.h | $(OBJDIR)
	$(CC)  $(CFLAGS) -c $< -o $@

$(OBJDIR)/strtab.o: src/strtab.c src/strtab.h $(OBJDIR)/y.tab.h | $(OBJDIR)
	$(CC)  $(CFLAGS) -c $< -o $@

clean:
	@rm -rf $(OBJDIR)

test: $(BIN)
	python3 test/run_tests.py --program $(BIN) $(ARGS)
