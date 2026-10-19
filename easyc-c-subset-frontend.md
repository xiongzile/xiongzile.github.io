---
layout: post
title: "EasyC: a C Subset Front End in Plain C"
date: 2024-06-04
description: A lexer, a recursive-descent parser and an AST walker that turn a C subset into quadruples — about 2500 lines of plain C, no compiler frameworks.
tags: [compiler]
---

> Originally written in Chinese on [cnblogs](https://www.cnblogs.com/Luvm/articles/18231508.html) (2024-06-04). This is the English version.

I wrote this compiler while learning compiler construction, following the steps in the textbook and using nothing but plain C. It currently goes from raw C source to quadruples, which is exactly the part a beginner needs to see working end to end.

## Why it might be worth reading

- The structure is flat and the coupling is low: one file per stage.
- It follows the course material closely instead of hiding it behind a framework.
- No parsing generators, no LLVM, no ANTLR — only basic C, so it reads like code a student could have written.

## What it does

- Raw string to a token stream
- Token stream to an AST
- AST to quadruples
- Roughly 2500 lines in total

## Project layout

- `build` — intermediate object files (`*.o`)
- `easyc` — the generated quadruples
- `log` — compiler logs, including errors
- `src` — the sources
  - `lex.c` — raw string to token stream
  - `parser.c` — token stream to AST
  - `ast.c` — AST to quadruples
  - `symbol.c` — a small hash table
  - `main.c` — drives the whole thing
- `include` — headers
- `test` — test inputs
  - `max.c` — maximum of two numbers
  - `fibonacci.c` — the n-th Fibonacci number
  - `expr.c` — expression parsing
  - `complex.for.c`, `complex.if.c` — nesting
  - `undefined_error1.c`, `undefined_error2.c` — use of an undefined variable
  - `double_defined_error.c`, `double_defined_global_error.c` — redefinition
  - `identifiler_error1.c`, `identifiler_error2.c` — invalid variable names, as rvalue and lvalue
  - `not_right.c` — a pile of random letters
  - `for_error.c` — `for` without braces

## lex.c

The core loop:

```c
int lexer(char *file_lexeme, struct Token *maintoken)
{
    int ntoken = 0;
    char *pchar = file_lexeme;
    while(*pchar) {
        char first_char = *pchar;
        struct Token token;
        memset(token.lexeme, 0, 32);
        int shift = 0;
        // Two nested loops stand in for a state machine: first_char decides
        // which state we are in (operator? identifier? constant?)
        while(1) {
            if (first_char == '#') {
                token.ttype = Preprocessor;
                token.lexeme[shift++] = *pchar++;
                break;
            } else if(is_loperator(first_char, loperator)){
                token.ttype = Operator;
                token.lexeme[shift++] = *pchar++;
                break;

            } else if (is_letter(first_char)) {
                token.ttype = Identifier;
                if (is_letter(*pchar) || is_number(*pchar)) {
                    token.lexeme[shift++] = *pchar++;
                }
                else {
                    if (is_keyword(token.lexeme, keyword)) {
                        token.ttype = Keyword;
                    }
                    break;
                }

            } else if (is_number(first_char)) {
                if(is_number(*pchar)) {
                    token.lexeme[shift++] = *pchar++;
                } else {
                    token.ttype = Constant;
                    break;
                }
            } else if (is_delimiter(first_char, delimiter)) {
                token.lexeme[shift++] = *pchar++;
                token.ttype = Delimiter;
                break;
            } else if (isspace(first_char)){
                pchar++;
                break;
            } else {
                printf("unknown : %c\n", *pchar);
                pchar++;
                break;
            }
        }
        strcpy(maintoken[ntoken].lexeme, token.lexeme);
        maintoken[ntoken].ttype = token.ttype;
        if (isspace(maintoken[ntoken].lexeme[0]) || maintoken[ntoken].lexeme[0] == 0)
            ntoken--;
        ntoken++;
        if (*pchar == '\n' || *pchar == ' ' || *pchar == '\t') {
            pchar++;
        }
    }
    // Post-processing: give each keyword its own token type.
    for (int i = 0; i < ntoken; i++) {
        if (maintoken[i].ttype == Keyword) {
            if (strcmp(maintoken[i].lexeme, "char") == 0) {
                maintoken[i].ttype = Char;
            }
            if (strcmp(maintoken[i].lexeme, "short") == 0) {
                maintoken[i].ttype = Short;
            }
            if (strcmp(maintoken[i].lexeme, "int") == 0) {
                maintoken[i].ttype = Int;
            }
            if (strcmp(maintoken[i].lexeme, "long") == 0) {
                maintoken[i].ttype = Long;
            }
            if (strcmp(maintoken[i].lexeme, "void") == 0) {
                maintoken[i].ttype = Void;
            }

        }
        // Operators are matched against the operator table: something like "<<<"
        // would be classified as an Operator but is not a legal one.
        if (maintoken[i].ttype == Operator && !(is_operator(maintoken[i].lexeme, loperator))) {
            maintoken[i].ttype = Unknown;
            fprintf(stderr, "error : cannot identify %s\n", maintoken[i].lexeme);
            continue;
        }
        // The "<" and ">" of #include <xx.h> are overloaded. This compiler does
        // not implement include or define yet, but the tokens should still look right.
        if (strcmp(maintoken[i].lexeme, "<") == 0) {
            if (strcmp(maintoken[i - 1].lexeme, "include") == 0) {
                maintoken[i].ttype = Delimiter;
            }
        }
        if (strcmp(maintoken[i].lexeme, ">") == 0) {
            if (strcmp(maintoken[i - 5].lexeme, "include") == 0) {

                maintoken[i].ttype = Delimiter;
            }
        }
    }

}
```

The central data structure is small:

```c
enum tokentype{Identifier = 0, Keyword, Constant, Operator, Delimiter, Comment, Preprocessor, Unknown, Char, Short, Int, Long, Void};

struct Token {
	enum tokentype ttype;
	char lexeme[32];
};

```

For `int`, for example, the token is `ttype = Int` and `lexeme = "int"`.

## parser.c

This file does more work:

- report errors
- define the AST node types
- walk the token array and build the tree

The error helper:

```c
void errormsg(struct Token *token, const char *format, ...)
{
    fprintf(stderr, "line %d -> ", token[curtoken].line);
    va_list args;
    va_start(args, format);
        vfprintf(stderr, format, args);
    va_end(args);
        exit(-1);
}

```

A few AST node declarations (abridged):

```c
  struct Token {
  	enum tokentype ttype;
      	char lexeme[32];
};
  /* Only part of the AST is shown */

/* Function or variable declaration, both at global scope */
struct AST_node_declarations {
    struct AST_node *basis;
    union {
        struct AST_node_var_dec_only *var;
        struct AST_node_func_dec *func;
    }real_dec;
};

/* Global variable declaration */
struct AST_node_var_dec_only {
    struct AST_node *basis;
    enum var_type_enum var_type;
    char *var_name;
    long init_val;
};

/* Function declaration */
struct AST_node_func_dec {
    struct AST_node *basis;
    enum func_type_enum func_type;
    char *func_name;
    struct func_symbol *sym;
    struct AST_node_func_paras *params;
    struct AST_node_stmt *stmt;
    long para_addr;
};

/* Function parameters */
struct AST_node_func_paras {
    struct AST_node *basis;
    int paras_count;
    int paras_capacity; // grown on demand
    char **paras_name;
    enum var_type_enum *paras_type;
};
// ......

```

Two globals carry the parser state: `maxtoken` (number of tokens) and `curtoken` (the token being examined).

The parser is recursive descent. One example — function parameters, which also shows the grow-by-doubling pattern:

```c
/* Build the AST node for a function's parameter list */
struct AST_node_func_paras *paras(struct Token *token) {

    struct AST_node_func_paras *params = malloc(sizeof(struct AST_node_func_paras));

    if (!params) {
        perror("Failed to allocate memory for func_paras");
        exit(EXIT_FAILURE);
    }

    params->basis = malloc(sizeof(struct AST_node));
    if (!params->basis) {
        perror("Failed to allocate memory for basis");
        exit(EXIT_FAILURE);
    }
    params->basis->type = PARAMS;
    params->paras_count = 0;
    params->paras_capacity = 5;
    params->paras_name = malloc(params->paras_capacity * sizeof(char *));
    params->paras_type = malloc(params->paras_capacity * sizeof(enum func_type_enum));
    if (!params->paras_name || !params->paras_type) {
        perror("Failed to allocate memory for parameters");
        exit(EXIT_FAILURE);
    }

    // (
    if (strcmp(token[curtoken].lexeme, "(") != 0) {
        errormsg("paras error: missing (\n");
    }

    curtoken++;
    // )
    if (strcmp(token[curtoken].lexeme, ")") == 0) {
        curtoken++;
        return params;
    }

    while (1) {
        if (params->paras_count >= params->paras_capacity) { // grow
            params->paras_capacity *= 2;
            params->paras_name = realloc(params->paras_name, params->paras_capacity * sizeof(char *));
            params->paras_type = realloc(params->paras_type, params->paras_capacity * sizeof(enum func_type_enum));
            if (!params->paras_name || !params->paras_type) {
                perror("Failed to reallocate memory for parameters");
                exit(EXIT_FAILURE);
            }
        }

        switch (token[curtoken].ttype) {
            case Char:
                params->paras_type[params->paras_count] = VCHAR;
                break;
            case Short:
                params->paras_type[params->paras_count] = VSHORT;
                break;
            case Int:
                params->paras_type[params->paras_count] = VINT;
                break;
            case Long:
                params->paras_type[params->paras_count] = VLONG;
                break;
            default:
                errormsg("paras error: invalid type\n");
        }

        curtoken++;
        // Identifier
        if (token[curtoken].ttype != Identifier) {
            errormsg("paras error: missing identifier\n");
        }

        params->paras_name[params->paras_count] = strdup(token[curtoken].lexeme);
        if (!params->paras_name[params->paras_count]) {
            perror("Failed to allocate memory for parameter name");
            exit(EXIT_FAILURE);
        }

        params->paras_count++;
        curtoken++;

        // , or )
        if (strcmp(token[curtoken].lexeme, ",") == 0) {
            curtoken++;
        } else if (strcmp(token[curtoken].lexeme, ")") == 0) {
            curtoken++;
            return params;
        } else {
            errormsg("paras error: missing , or )\n");
        }
    }
    return params;
}

```

Building the AST pays off twice: the code generator gets a shape it can walk, and everything downstream stops thinking in tokens.

## ast.c

Its only job is to walk the AST and emit quadruples:

```c
struct emit_node{
    int no;
    char *op;
    char *arg1;
    char *arg2;
    char *result;
};

```

The interesting part is control flow, because jumps need patching. `if`, `for`, and the backfill helper:

```c
/* Abridged */
static int if_helper(struct AST_node_state_if *if_node, char *scope, long addr)
{
    struct AST_node_expr *left, *right;
    char *op = if_node->condition->op;
    left = if_node->condition->left;
    right = if_node->condition->right;
    char *tmp1 = new_temp();
    char *tmp2 = new_temp();
    walk_expr(left, scope, addr, tmp1);
    walk_expr(right, scope, addr, tmp2);
    jmp_emit_helper(tmp1, tmp2, op);
    walk_stmt(if_node->if_body, scope, addr);
    if (if_node->else_body) {
        emit("j", NULL, NULL, "todo");
        backfill();
        walk_stmt(if_node->else_body, scope, addr);
        backfill();
    } else {
        backfill();
    }
    return 0;
}
static int for_helper(struct AST_node_state_for *for_node, char *scope, long addr)
{
    struct AST_node_state_dec *init = for_node->init;
    char *tmp = new_temp();
    walk_expr(init->init_val, scope, addr, tmp);
    emit("=", tmp, NULL, init->var_name);
    insert_symbol(symbol_t, init->var_name, (char *)var_type_str[init->var_type], scope, addr);
    struct AST_node_condition *cond = for_node->cond;
    char *tmp1 = new_temp();
    char *tmp2 = new_temp();
    int record = pc;
    walk_expr(cond->left, scope, addr, tmp1);
    walk_expr(cond->right, scope, addr, tmp2);
    jmp_emit_helper(tmp1, tmp2, cond->op);
    struct AST_node_stmt *stmt = for_node->body;
    walk_stmt(stmt, scope, addr);
    struct AST_node_state_let *update = for_node->update;
    char *tmp3 = new_temp();
    walk_expr(update->var_expr, scope, addr, tmp3);
    emit("=", tmp3, NULL, update->var_name);
    char buf[16];
    memset(buf, 0, 16);
    sprintf(buf, "%d", record);
    emit("j", NULL, NULL, buf);
    backfill();
    return 0;
}
static inline void jmp_emit_helper(char *left_buf, char *right_buf, char *op)
{
        if (strcmp(op, ">") == 0) {
            emit("j<=", left_buf, right_buf, "todo");
        } else if (strcmp(op, "<") == 0) {
            emit("j>=", left_buf, right_buf, "todo");
        } else if (strcmp(op, ">=") == 0) {
            emit("j<", left_buf, right_buf, "todo");
        } else if (strcmp(op, "<=") == 0) {
            emit("j>", left_buf, right_buf, "todo");
        } else if (strcmp(op, "==") == 0) {
            emit("j!=", left_buf, right_buf, "todo");
        } else if (strcmp(op, "!=") == 0) {
            emit("j==", left_buf, right_buf, "todo");
        }
}
static inline void backfill()
{
    for (int i = emit_count - 3; i >= 0; i--) {
        if (strcmp(emits[i]->result, "todo") == 0) {
            char buf[16];
            memset(buf, 0, 16);
            sprintf(buf, "%d", pc);
            memset(emits[i]->result, 0, 4);
            strncpy(emits[i]->result, buf, 8);
            break;
        }
    }
}
char *new_temp() {
    char *temp = malloc(20);
    sprintf(temp, "t%d", temp_var_count++);
    return temp;
}

```

The jump targets are written as `todo` and filled in later, once the destination instruction number is known.

## Calling convention

The generated quadruples assume a simple convention:

- `a0`–`a6` carry the arguments
- `a7` carries the return value

## References

- The LL(1) grammar for expressions, from the Peking University compiler course notes
- [Linux kernel coding style](https://www.kernel.org/doc/html/latest/process/coding-style.html) for the code conventions

---

*The original Chinese post is on [cnblogs](https://www.cnblogs.com/Luvm/articles/18231508.html).*
