---
layout: post
title: "Unix Programming, Starting From a Copy"
date: 2024-03-29
description: "A first pass at Unix system programming: argv, file descriptors, open/fstat/read/write, and why a 60-line file copy still takes an afternoon."
tags: [unix]
---

> Originally written in Chinese on [cnblogs](https://www.cnblogs.com/Luvm/articles/18104804.html) (2024-03-29). This is the English version.

This is for readers with no Unix programming experience who know some C and can use `cd`, `ls` and `mkdir`. The exercise it walks through is CS631 HW1: a bare-bones `cp`.

## Why bother

After a semester of C, most people can compute Pascal's triangle and not much else. The language feels like a closed box: you print different things into a black window. System programming is the way out of the box, and it takes much less effort than it looks.

The exercise asks for a program that copies one file to another, with three cases:

- the destination is a directory — copy the source into it
- the destination is an existing file — overwrite its contents
- the destination does not exist — create it and copy

It ships with a test script, which turns out to matter more than the code.

## Start with `main`

Not `int main(void)`, but:

```c
int main(int argc, char *argv[])
```

If you type `sleep 10` in a shell, something has to tell `sleep` how long to sleep. That something is `argv`. For `sleep 10`, `argc == 2` and `argv == ["sleep", "10"]`. The names are conventional; you could call them `a` and `b`.

For our program `argc` should be 3 — `cp source dest` — so anything else has to be rejected:

```c
if (argc != 3) {
     perror("input format error");
     exit(EXIT_FAILURE);
}
```

`perror` prints the last system call's error message, and `EXIT_FAILURE` is just a macro from `stdlib.h`:

```c
#define EXIT_FAILURE    1   /* Failing exit status.  */
#define EXIT_SUCCESS    0   /* Successful exit status.  */
```

## Two ways to read a file

C offers two families:

- `read()` — a system call, declared in `<unistd.h>`, works on file descriptors
- `fread()` — a libc function, declared in `<stdio.h>`, works on `FILE *`

```c
ssize_t read(int fd, void *buf, size_t count)
size_t fread(void *ptr, size_t size, size_t nmemb, FILE *stream)
```

The unfamiliar types are typedefs: `size_t` is `unsigned long` on this machine, `ssize_t` is the signed version. That is not the interesting difference; the interesting one is that `read` goes straight to the kernel.

### What a system call is

A system call is how a user program asks the kernel to do something it is not allowed to do itself: touch a device, open a file, send a packet. Textbooks describe it as "the interface between user space and kernel space", which is correct and unhelpful.

Here is the practical version: it is a function call that crosses a boundary. Your `printf` is a library function that eventually issues a `write` system call. The path is roughly `user → library function → system call → kernel → hardware`, and for this exercise you only need the first three.

## Opening the source

```c
int fd1;
if ((fd1 = open(argv[1], O_RDONLY)) < 0) {
    perror("open file1: error");
    exit(EXIT_FAILURE);
}
struct stat fd1_st;
if (fstat(fd1, &fd1_st) < 0) {
    perror("fstat file1: error\n");
    exit(EXIT_FAILURE);
}

if ((fd1_st.st_mode & S_IFMT) == S_IFDIR) {
    perror("file1 is a directory\n");
    exit(EXIT_FAILURE);
}
```

In that snippet there are two library functions (`perror`, `exit`), two system calls (`open`, `fstat`) and one struct (`struct stat`). Taking them in turn:

**`perror`** — `void perror(const char *s)` prints `s` followed by the last error.

**`exit`** — `void exit(int status)` ends the process. Unlike `return`, it does not unwind back to the caller: it calls into the kernel and the process is gone.

**`open`** — `int open(const char *pathname, int flags, mode_t mode)`. The flags say how you want to open the file (`O_RDONLY`, `O_WRONLY`, `O_RDWR`, …). The return value is a file descriptor, a small integer that identifies this open file for everything you do next.

That last sentence is the whole idea: after `open`, the file *is* an integer. You never touch the path again.

**`fstat`** — `int fstat(int fd, struct stat *buf)` fills a `struct stat` with the file's metadata. If the return value is negative, the call failed and you should stop.

So a file, from C's point of view, is a descriptor plus a `stat`. That is all the later code deals with.

## Reading and writing

```c
ssize_t read(int fd, void *buf, size_t count);
ssize_t write(int fd, const void *buf, size_t count);
```

The buffer is just an array:

```c
char filebuf[512];
memset(filebuf, 0, 512) // do not forget to zero an uninitialized array
while ((byte_read = read(fd1, filebuf, CHUNK_SIZE)) > 0) { // CHUNK_SIZE is a macro
            ...
}
```

The copy loop is then two calls:

```c
char filebuf[512];
memset(filebuf, 0, 512) // do not forget to zero an uninitialized array
while ((byte_read = read(fd1, filebuf, CHUNK_SIZE)) > 0) {
    if(write(fd2, filebuf, byte_read) < 0) {
        perror("write to file error");
        exit(EXIT_FAILURE);
    }
}
```

`read` returns the number of bytes actually read, `0` at end of file, and `-1` on error. `write` returns the number of bytes written, which is not always all of them — that is one of the details this post glosses over, and one of the reasons the assignment takes longer than it looks.

## The details that cost me an afternoon

- Where does writing start if the destination already exists? Do you need `O_TRUNC`?
- What happens if `open` fails because the file does not exist — and which flag combination creates it?
- Permissions: `open` takes a third argument when it creates a file.
- The test script is about four hundred lines of shell. When several cases fail, reading it tells you what is actually being checked.

That script is worth the time. It is also, for most people, the first time they read shell seriously.

## A closing note

If you reached the end, you are probably new to this and still enthusiastic. The post is deliberately slow — it spends several paragraphs on file descriptors — because that is the level I needed when I started, and this was the first piece of writing I ever published.

---

*The original Chinese post is on [cnblogs](https://www.cnblogs.com/Luvm/articles/18104804.html).*
