#include<tree.h>
#include<strtab.h>
#include<stdio.h>
#include<stdlib.h>
#include<string.h>

typedef struct treenode tree;

// the root of the ast
tree *ast;

tree *maketree(int kind) {
  return NULL;
}
tree *maketreeWithVal(int kind, int val) {
  return NULL;
}
void addChild(tree *parent, tree *child) {
}
void printAst(tree *root, int nestLevel) {
  // this function shouldn't be called with a NULL node
  // you should be able to remove this return check
  if (!root) return;
  // we print nestLevel*2 spaces, then we print the number 123
  // if nestLevel == 0 then there are 0 leading spaces
  // if nestLevel == 1 then there are 2 leading spaces
  // we can easily tab out print statements with this method
  printf("%*s%d\n", nestLevel*2, "", 123);
  // we can also print our variable spacing first ...
  // printf("%*s", nestLevel*2, "");
  // then print the node information
  // printf("%s\n", "addexpr");
  // then we print the child nodes
  // for i from zero to root->numchildren printast(root->child[i], nestlevel+1)
}
