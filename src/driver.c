#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <tree.h>
#include <strtab.h>

extern int yyparse(void);
extern FILE *yyin;

extern struct treenode *ast;
extern struct strEntry strTable[MAXIDS];

int main(int argc,char **argv) {
  FILE *infile = NULL;
  if (argc==2) {
    /* Report a bad filename instead of silently falling through to stdin,
       which looks like the program hanging. */
    infile = fopen(argv[1],"r");
    if (!infile) {
      fprintf(stderr,"%s: cannot open %s\n", argv[0], argv[1]);
      return 1;
    }
    yyin = infile;
  }
  if (!yyparse()){
    printAst(ast, 0);
    printf("SYMBOL TABLE:\n");
    for(int i=0;i<MAXIDS;++i) {
      if(strTable[i].id != NULL) {
        output_entry(i);
      }
    }
  }
  if (infile) {
    fclose(infile);
  }
  return 0;
}
