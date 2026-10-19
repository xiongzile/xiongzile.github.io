---
layout: post
title: "6.S081 Lab: mmap"
date: 2024-11-28
description: Implementing mmap and munmap in xv6 — a fixed VMA table, page-fault driven mapping, write-back for MAP_SHARED, and the details that cost the most debugging time.
tags: [os]
---

> Originally published on [cnblogs](https://www.cnblogs.com/Luvm/articles/18574187.html) (2024-11-28). Lightly edited.

This is about the `mmap` lab from 6.S081: virtual memory, memory-mapped files, and how mapping lets a program work with a large file without reading it all first.

## Before you start

If you have not written any code yet, do not read my code. It will not help you make progress. Reading source is usually a good habit; not at this point.

If you are close to finishing, a few debugging notes:

**Print is faster than gdb.** I did not use gdb for this lab. When the code misbehaves I already know roughly where it went wrong, so printing is quicker than stepping. If you understand how the code works, you do not need a debugger.

**Read `mmaptest.c`.** Nobody finishes this lab without reading it. Adding prints inside `mmaptest.c` is worth the trouble.

**The file size does not change.** `mmap` does not extend the file. If `fileA` is 5000 bytes and you map 10000 and then write `addr[6000]`, nothing panics — but that write must not extend the file. Make sure your implementation keeps the file at its original size.

**`mmap` does not map eagerly.** If `uvmunmap` reports "not mapped", that can be correct: `mmap` followed immediately by `munmap` never touches a page, so nothing was mapped. Either make `uvmunmap` tolerate this or check for it in `munmap`; both are fine.

**Finding a safe virtual address range.** xv6 gives you no interface for this, so you have to pick one. I used `myproc()->sz` as the base. It passes all the tests, but it is not genuinely safe.

The lab description covers everything else. Do not skip any of it. Note that *Hint: use* and *Hint: see* mean different things.

One more: do not use `filewrite` for write-back. You have to decide the file offset yourself.

I am not going to explain how to add a system call to xv6. Copying the code here will not compile — the full source is [on GitHub](https://github.com/xiongzile/xv6-mmap).

The functions involved:

- `sysfile.c` — `sys_mmap`, `sys_munmap`, `writeback` (a helper)
- `file.c` — `filedup`, `filewrite`, `fileclose`
- `vm.c` — `mappages`, `uvmunmap`
- `proc.c` — `usertrap`, `exit`, `fork`

About 100 lines change.

## struct vma

```c
struct vma {
        uint64  addr;
        uint    length;
        uint    prot;	//PROT_READ PROT_WRITE...
        uint    flags;  //MAP_PRIVATE MAP_SHARED
        struct  file *f;

        uint64  start; //set when mmap is called the first time.
};
```

## sys_mmap

This one is easy: find a free slot in the process's VMA array and fill it in.

```c
uint64 sys_mmap(void)
{
        struct file *f;
        uint64 addr;
        int length;
        int prot;
        int flags;
        int offset;
        argaddr(0, &addr);
        argint(1, &length);
        argint(2, &prot);
        argint(3, &flags);
        argfd(4, 0, &f);
        argint(5, &offset);
        /*
        printf("debug: argstest...\n");
        printf("addr = %ld, length = %d, prot = %d, flags = %d, offset = %d\n",
               addr, length, prot, flags, offset);
        */
        if (!f->writable && (prot & PROT_WRITE) && (flags & MAP_SHARED))
                return -1;
        filedup(f);
        struct proc *p = myproc();
        for (int i = 0; i < NVMA; i++) {
                struct vma *vma = &p->vmas[i];
                if (vma->prot == PROT_NONE) { // found unused vma
                        vma->addr = p->sz;
                        vma->length = PGROUNDUP(length);
                        vma->prot = prot;
                        vma->flags = flags;
                        vma->f = f;
                        vma->start = vma->addr;
                        //printf("mmap: address = %p\n", (void *)addr);
                        p->sz += vma->length;
                        return vma->addr;
                }
        }
        return 0;
}
```

Using `p->sz` as the base passes every test, including the newer ones. I have seen people use `TRAMPOLINE`; that may be cleaner.

Do not forget `filedup` to bump the file's reference count — the lab description mentions this.

## usertrap

A read page fault has cause `0xd`, a write page fault `0xf`, so handle both. When a fault arrives, first check whether the address falls inside a mapped VMA. If it does, allocate a physical page and map it; if it does not, kill the process.

I do not recommend `uvmalloc` here: one trap needs exactly one page mapped.

```c
uint64 va = r_stval();
if (va >= p->sz || va > MAXVA ||
    PGROUNDUP(va) == PGROUNDDOWN(p->trapframe->sp))
	setkilled(p);
else {
	struct vma *vma = (struct vma *)0;
	for (int i = 0; i < NVMA; i++) {
		if (p->vmas[i].prot != PROT_NONE &&
		    va >= p->vmas[i].addr &&
		    va < p->vmas[i].addr + p->vmas[i].length) {
			vma = &p->vmas[i];
			break;
		}
	}
	if (vma) { // mmaped
		va = PGROUNDDOWN(va);
		uint64 offset = va - vma->addr;
		uint64 mem = (uint64)kalloc();
		if (mem == 0) {
			setkilled(p);
		} else {
			memset((void *)mem, 0, PGSIZE);
			ilock(vma->f->ip);
			if (readi(vma->f->ip, 0, mem, offset,
				  PGSIZE) < 0)
				setkilled(p);
			iunlock(vma->f->ip);
			int flag = PTE_U;
			if (vma->prot & PROT_READ)
				flag |= PTE_R;
			if (vma->prot & PROT_WRITE)
				flag |= PTE_W;
			if (vma->prot & PROT_EXEC)
				flag |= PTE_X;
			// cannot write a readonly page
			if (r_scause() == 15 &&
			    !(vma->prot & PROT_WRITE)) {
				kfree((void *)mem);
				setkilled(p);
			}
			if (mappages(p->pagetable, va, PGSIZE,
				     mem, flag) != 0) {
				kfree((void *)mem);
				setkilled(p);
			}
		}
	} else { // not mmaped
		setkilled(p);
	}
```

## sys_munmap

Before writing it, know which arguments are legal. Unlike Linux, this implementation only unmaps from the beginning or the end of a VMA — there is no linked list of mappings to split in the middle.

Given:

```c
vma->addr = 0x8000;
vma->length = 8192;
```

the legal calls are:

- `addr = 0x8000`, `0 <= length <= 8192` — unmaps from the front, then `vma->addr += length`, `vma->length -= length`
- `0x8000 < addr < 0x10000`, `length = 0x10000 - addr` — unmaps to the end, then `vma->length -= length`

`mmaptest.c` tests both, so support both.

```c
uint64 sys_munmap(void)
{
#define MIN(x, y) ((x) < (y) ? (x) : (y))
        uint64 addr;
        int length;
        argaddr(0, &addr);
        argint(1, &length);
        length = PGROUNDUP(length);
        struct proc *p = myproc();
        for (int i = 0; i < NVMA; i++) {
                struct vma *v = &p->vmas[i];
                if (v->prot != PROT_NONE &&
                    (v->addr <= addr && addr < v->addr + v->length)) {
                        if ((v->flags & MAP_SHARED) && (v->prot & PROT_WRITE)) {
                                int max =
                                        ((MAXOPBLOCKS - 1 - 1 - 2) / 2) * BSIZE;
                                int foff = addr - v->start;
                                writeback(v->f, addr, foff,
                                          MIN(length, (v->f->ip->size - foff)),
                                          max);
                        }
                        uvmunmap(p->pagetable, addr, length / PGSIZE, 1);
                        v->length -= length;
                        if (v->length == 0) {
                                fileclose(v->f);
                                memset(v, 0, sizeof(*v));
                                return 0;
                        }
                        if (addr == v->addr) {
                                v->addr += length;
                        }
                }
        }
        return 0;
}
```

Look at this line:

```c
int foff = addr - v->start;
```

This is why I said not to use `filewrite`: the file offset is measured from where the mapping started, not from the current address. Example:

```c
vma->addr = 0x0000;
vma->length = 8192;

munmap(vma->addr, 4096);     // writeback at file offset 0
vma->addr = 0x1000;
vma->length = 4096;

munmap(vma->addr, 4096);     // writeback at file offset 4096, not 0x1000
```

Without storing `start`, that offset is hard to recover.

## writeback

Modelled on `filewrite`, but with an explicit file offset:

```c
// referring filewrite
void writeback(struct file *f, uint64 addr, int foff, int n, int limit)
{
        int i = 0;
        int r = 0;
        while (i < n) {
                int n1 = n - i;
                if (n1 > limit)
                        n1 = limit;
                begin_op();
                ilock(f->ip);
                if ((r = writei(f->ip, 1, addr + i, foff, n1)) > 0)
                        foff += r;
                iunlock(f->ip);
                end_op();
                if (r != n1) {
                        // error from writei
                        break;
                }
                //printf("hello\n");
                i += r;
        }
}
```

The last step is `exit` and `fork`: close the files and drop the VMAs on exit, and copy them on fork. Both are straightforward.

If you paid attention to the points above, debugging the rest is not hard.

The complete implementation is [on GitHub](https://github.com/xiongzile/xv6-mmap), alongside a small C compiler if you are curious.

---

*The original post is on [cnblogs](https://www.cnblogs.com/Luvm/articles/18574187.html).*
