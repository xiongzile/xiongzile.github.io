---
layout: post
title: "A Shell in Half an Hour"
date: 2024-03-29
description: Reading a line, splitting it into argv, fork and exec, plus a hand-written history list — a minimal Unix shell in about 200 lines of C.
tags: [unix]
---

> Originally written in Chinese on [cnblogs](https://www.cnblogs.com/Luvm/articles/18104842.html) (2024-03-29). This is the English version.

Prerequisites: you can write C, including a linked list by hand.

## What a shell actually is

Textbooks make it sound grand: an interface between the user and the kernel, a command interpreter, a way to manage processes and I/O. All true, and all of it reduces to two jobs:

- read a command the user typed (`ls`, `dir`, …)
- do something about it

So a toy shell needs very little from us: read a line from stdin, then interpret it. The version I built does this:

- runs ordinary commands (`ls`, `ls -l`, `mkdir testdir`)
- implements `history` and `quit`, which bash provides but we have to write ourselves
- `history` shows recent commands, and `!<number>` re-runs one
- `quit` exits cleanly

### What "exit cleanly" means

There are many ways to end a program, and `Ctrl-C` is not one of them. If you run `python3` and press `Ctrl-C`, you get:

```
>>> 
KeyboardInterrupt
>>> 
```

The interpreter caught the signal and stayed alive. That is the point: `Ctrl-C` sends an interrupt, it does not mean "die". The program decides what to do with it — exit, print a complaint, or ignore it. Killing the terminal works too, but that is the equivalent of pulling the power cord.

A program that never tells you how to leave it is an incomplete program, so this shell implements `quit`. It also saves you from collecting exit status 130 every time.

## Implementation

### `int main(int argc, char *argv[])`

If those two parameters are unfamiliar, see the beginning of my [Unix programming post](/unix-barebones-copy.html). For this exercise they are optional anyway.

The shell should keep running until told otherwise, so `main` is an infinite loop whose exit condition we control:

```c
int main(int argc, char *argv[]) {
    for (; ;) {
     //TODO
    }
    return 0;
}
```

Every shell prints something to say "your turn". The course requires `osh>`, so:

```c
  1 #include <stdio.h>
  2 int main () {
  3     for (; ;) {
  4         printf("osh>");
  5         char buf[64];
  6         scanf("%s", buf);
  7         printf("%s\n", buf);
  8     }
  9     return 0;
 10 }
```

This is the first thing that does not work as expected:

```
osh>fw wfwf
fw
```

`scanf("%s")` stops at whitespace, so a command with arguments is cut in half. `fgets` reads the whole line instead:

```c
  1 #include <stdio.h>
  2 #include <string.h>
  3 int main () {
  4     for (; ;) {
  5         printf("osh>");
  6         char buf[64];
  7         memset(buf, 0, 64);
  8         fgets(buf, 64, stdin);
  9         printf("%s\n", buf);
 10     }
 11     return 0;
 12 }
```

Better, except that `fgets` keeps the trailing newline. Half the job is done: we can read a command.

### From one string to `argv`

The line is still a single string with spaces in it. `strtok` splits it:

```c
char *strtok(char *str, const char *delim);
```

Pass the string on the first call and `NULL` afterwards; it returns each token and remembers where it stopped.

```c
int main() {
    printf("Welcome to my shell\n");
    initlist();
    char *argv[MAXARG];
    for (; ;) {
        cnt++;
        printf("osh> ");
        fflush(stdout);
        memset(argv, 0, 40);
        char c;
        int index = 0;
        char buf[64];
        memset(buf, 0, 64);
        fgets(buf, 64, stdin);
        if(buf[0] == '\n' || buf[0] == '\0')
            continue;
        buf[strlen(buf) - 1] = '\0';
        //printf("%s", buf);
        char *token = strtok(buf, " ");
        while(token && index < MAXARG) {
            argv[index++] = strdup(token);
            token = strtok(NULL, " ");
        }
        if (index == 1 && strcmp(argv[0], "history") == 0)
            cnt--;

        handle_retval(handler(argv,index));
        /*
        for (int i = 0; i < index; i++) {
            printf("%s ", argv[i]);
        }*/
        //should_run = 0;
    }
    return 0;
}
```

The details that look like noise are the ones that cost me time: null-terminating `buf`, skipping empty lines. For a program this small, `printf` is a better debugger than `gdb`.

### The handler

`handler` decides what to do with an `argv`:

```c
static inline int handler(char **argv, int argc)
{   /*
    printf("will execute: ");

    for (int i = 0; i < index; i++) {
        printf("%s ", argv[i]);
    }
    */

    /*handle instruction: history */
    int ins = get_ins(argv, argc);
    switch (ins) {
        case QUIT:
        case EXIT:
            printf("lshell is closing. Goodbye!\n");
            exit(0);
        case HISTRY:
            return HISTORY;
        default:
            break;
    }

    /* handler "!!" or "!1" ... */
    if (argv[0][0] == '!')
        handle_execfromhistory(argv, &argc);

    /* handler '&' */
    int flag = 0;
    if (strcmp(argv[argc - 1], "&") == 0) {
        flag = 1;
        free(argv[argc - 1]);
        argv[argc - 1] = NULL;
        argc--;
    }

    if (fork() == 0) {
        if(execvp(argv[0], argv) < 0)
            printf("error message: %s failed\n", argv[0]);
        exit(0);
    } else {
        add_list(cnt, argv);
        if (flag == 1) {
            //do nothing
        } else {
              wait(NULL);
        }
    }
    return EXEC;
}
```

Built-ins first (`quit`, `exit`, `history`), then everything else goes to `execvp`. That is the trick that makes a 200-line shell handle thousands of commands: the operating system does the work.

Two details matter:

- `execvp` replaces the current process on success, so it never returns. If it does return, it failed, and we say so.
- it has to run in a child. Calling it from `main` would replace the shell itself with the command, and you would get exactly one command per session.

A trailing `&` means "do not wait": the parent returns immediately and the child runs in the background.

### History

Recording history means keeping the last ten commands. Which data structure?

An array works, but a plain array forces you to guess a size, and the index only grows. A struct array used as a ring buffer is fine:

```c
struct instruction {
    int no;
    int argc;
    char **argv;
};
struct instrction ins[10];
```

That is elegant and cheap. I used a linked list instead, inserting at the head:

```c
struct history_commands {
    struct list_head run;
    int position;
    char **argv;
    int argc;
} hiscom;
```

I borrowed the kernel's `list_head` because it is nicer than anything I would write. The kernel headers cannot be included directly — the dependencies between kernel C files are deeper than you would expect — so I extracted the parts this exercise needs into a small header of my own.

Printing history also clears the tail of the list in one pass, in the lazy style of a segment tree's pending flags: you clean up when you happen to be walking anyway.

### `!<number>` and `!!`

```c
static inline void handle_execfromhistory(char **argv, int *argc)
{
    if(*argc != 1) return ;
    int position;
    if(strcmp(argv[0], "!!") == 0) {
        position = cnt - 1;
        if (cnt - 1 <= 0) {
            printf("No commands in history.\n");
            return ;
        }
    }else {
        char *p =argv[0];
        position = 0;
        p++;
        while (*p) {
            if(*p > '9' || *p < '0')
                return ;
            position = position * 10 + *p - '0';
            p++;
        }
    }

    //printf("position = %d\n", position);
    struct list_head *node;
    int count = 0;
    list_for_each(node, &hiscom.run) {
        struct history_commands *p = (struct history_commands *)node;
        count += 1;
        if (count > 10) {
            printf("You can only search for nearly ten instructions!\n");
            return ;
        }
        if (p->position == position) {
            *argc = p->argc;
            for (int i = 0; p->argv[i]; i++) {
                argv[i] = p->argv[i];
            }
            return ;
        }
    }
    printf("No such command in history.\n");
}
```

The first half parses the number by hand, because everything we read is a string. `sscanf` can do it in one line if you prefer:

```c
#include <stdio.h>

int main() {
    char str[] = "!2313";
    int number;
    if (sscanf(str, "!%d", &number) == 1) {
        printf("Number: %d\n", number);
    } else {
        printf("Failed to read number.\n");
    }
    return 0;
}
```

The second half walks the list to the matching entry and copies its `argv` back. Error cases are part of the exercise, and worth handling anyway.

## What I left out

Linked-list insertion and the small plumbing details. They are not the interesting part, and copying code from a blog into your editor tends to produce errors that have nothing to do with the idea. Everything here was written and tested on Linux with `vim`; the formatting may not survive a copy into Dev-C++.

The full source is in [my shell repository](https://github.com/xiongzile/myshell).

---

*The original Chinese post is on [cnblogs](https://www.cnblogs.com/Luvm/articles/18104842.html).*
