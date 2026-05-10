# CIR: Relative Vtable support

PR: https://github.com/llvm/llvm-project/pull/195025

This PR is to support relative vtables for CIR.

So basically we have two things to do:

- generate(called emit) relative stable instead of absolute address vtable
- generate code to use the vtable

## getVirtualFunctionPointer

Let's see the original LLVM code:
```assembly
; Function Attrs: mustprogress noinline nounwind optnone
define dso_local void @_Z14call_through_AP1A(ptr noundef %pa) #0 {
entry:
  %pa.addr = alloca ptr, align 8
  store ptr %pa, ptr %pa.addr, align 8
  %0 = load ptr, ptr %pa.addr, align 8
  %vtable = load ptr, ptr %0, align 8
  %1 = call ptr @llvm.load.relative.i32(ptr %vtable, i32 0)
  call void %1(ptr noundef nonnull align 8 dereferenceable(12) %0)
  ret void
}
```

Good news! LLVM has intrinsics to support relative stable which means we don't have to implement the offset compute heal outselves.

So what I do is just create a new cir attribute which is corresponding to the ``llvm.load.relative.i32`` intrinsic.

```cpp
      // Relative vtables store 32-bit offsets in the vtable entries.
      //
      // Keep this as a CIR-level relative virtual call operation and let
      // the CIR-to-LLVM lowering translate it to:
      //
      //   call ptr @llvm.load.relative.i32(ptr %vtable,
      //                                   i32 (vtableIndex * 4))
      //
      // The result is the resolved virtual function pointer.
      vfuncLoad = cir::VTableGetRelativeVirtualFnAddrOp::create(
          builder, loc, tyPtr, vtable, vtableIndex);
```

## emitVtableDefinition

### Analyze the LLVM code

This is much more complex. See the original LLVM code:

```assembly
@_ZTV1A.local = internal unnamed_addr constant { [3 x i32] } { [3 x i32] [
i32 0, 

i32 trunc(
i64 sub (i64 ptrtoint (ptr @_ZTI1A.rtti_proxy to i64), i64 ptrtoint (ptr getelementptr inbounds ({ [3 x i32] }, ptr @_ZTV1A.local, i32 0, i32 0, i32 2) to i64)) to i32), 

i32 trunc (
i64 sub (i64 ptrtoint (ptr dso_local_equivalent @_ZN1A1fEv to i64), i64 ptrtoint (ptr getelementptr inbounds ({ [3 x i32] }, ptr @_ZTV1A.local, i32 0, i32 0, i32 2) to i64)) to i32)

] }, align 4

@_ZTV1A = unnamed_addr alias { [3 x i32] }, ptr @_ZTV1A.local

@_ZTI1A = constant { ptr, ptr } { ptr getelementptr inbounds (i8, ptr @_ZTVN10__cxxabiv117__class_type_infoE, i32 8), ptr @_ZTS1A }, align 8

@_ZTVN10__cxxabiv117__class_type_infoE = external global [0 x ptr]

@_ZTS1A = constant [3 x i8] c"1A\00", align 1

@_ZTI1A.rtti_proxy = linkonce_odr hidden unnamed_addr constant ptr @_ZTI1A, comdat
```

Since we reuse the ``llvm.load.relative.i32`` in getVirtualFunctionPointer, we have to make sure the vtable we generated is absolutely consistent with the above.

The core global variable is @_ZTV1A.local, not we don't care about why we have an alias and focus on the value of the variable.

It's an array with type i32.



The first element is ``offset-to-top`` .

Since it's already **offset**, we have the same meaning in relative vtable. It's easy case to implement. We only need to make sure the type is i32 instead of u8* in classic implementation(no use relative vtable).



The second element is a ``offset to the proxy of rtti``. 

It's basically a sub instruction.

i64 ptrtoint (ptr @_ZTI1A.rtti_proxy to i64) - i64 ptrtoint (ptr getelementptr inbounds ({ [3 x i32] }, ptr @_ZTV1A.local, i32 0, i32 0, i32 2) to i64))

If we don't care about the ptr to int cast. It should be:

ptr @_ZTI1A.rtti_proxy - ptr getelementptr inbounds ({ [3 x i32] }, ptr @_ZTV1A.local, i32 0, i32 0, i32 2

But what's fucking ptr getelementptr inbounds ({ [3 x i32] }, ptr @_ZTV1A.local, i32 0, i32 0, i32 2

**Why we have three indices while there's a 1 * 3 array???**

(x, y, z)

We focus on **z** which means the index of the array.

So ``2`` here is the index of **first virtual function slot** of the table.

The vtable layout looks like:

- Offset-to-top
- RTTI
- function1
- function2
- functionX
- ....

In relative vtable, we define the offset as the real address sub the address of first function slot.







