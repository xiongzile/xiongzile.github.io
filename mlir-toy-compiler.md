---
layout: post
title: "MLIR: Understanding and Using Dialects and Operations"
date: 2026-10-17
description: Following the MLIR Toy tutorial to understand dialects, operations, and TableGen, starting with a dialect named zl and connecting the pieces with CMake.
tags: [mlir, compiler]
wip: true
---

> These notes follow the [MLIR Toy tutorial](https://mlir.llvm.org/docs/Tutorials/Toy/) to learn how to write MLIR code and understand the underlying mechanisms. [My hand-written implementation](https://github.com/xiongzile/mlir-toy-zl).
>
> This post covers basic MLIR concepts and the configuration needed to add MLIR dependencies.

## Dialect

A dialect in MLIR acts somewhat like a scope. For example, my compiler is called the zl compiler, so I named its dialect `zl`. The following TableGen definition generates a dialect:

```cpp
#ifndef ZL_DIALECT
#define ZL_DIALECT
include "mlir/IR/OpBase.td"
// Provide a definition of the 'zl' dialect in the ODS framework so that we
// can define our operations.
def Zl_Dialect : Dialect {
  // The namespace of our dialect, this corresponds 1-1 with the string we
  // provided in `ToyDialect::getDialectNamespace`.
  let name = "zl";

  // A short one-line summary of our dialect.
  let summary = "A high-level dialect for analyzing and optimizing the "
                "Toy language";

  // A much longer description of our dialect.
  let description = [{
    The Toy language is a tensor-based language that allows you to define
    functions, perform some math computation, and print results. This dialect
    provides a representation of the language that is amenable to analysis and
    optimization.
  }];

  // The C++ namespace that the dialect class definition resides in.
  let cppNamespace = "::zl";
}
#endif
```

At this point, the dialect is just a shell because we have not added any operations. Once CMake is configured, TableGen can generate a header and a corresponding C++ file. Here is the header:

```cpp
/*===- TableGen'erated file -------------------------------------*- C++ -*-===*\
|*                                                                            *|
|* Dialect Declarations                                                       *|
|*                                                                            *|
|* Automatically generated file, do not edit!                                 *|
|* From: ZLDialect.td                                                         *|
|*                                                                            *|
\*===----------------------------------------------------------------------===*/

namespace zl {

/// A high-level dialect for analyzing and optimizing the Toy language
/// The Toy language is a tensor-based language that allows you to define
/// functions, perform some math computation, and print results. This dialect
/// provides a representation of the language that is amenable to analysis and
/// optimization.
class ZlDialect : public ::mlir::Dialect {
  explicit ZlDialect(::mlir::MLIRContext *context);

  void initialize();
  friend class ::mlir::MLIRContext;
public:
  ~ZlDialect() override;
  static constexpr ::llvm::StringLiteral getDialectNamespace() {
    return ::llvm::StringLiteral("zl");
  }
};

} // namespace zl
MLIR_DECLARE_EXPLICIT_TYPE_ID(::zl::ZlDialect)
```

And here is the C++ file:

```cpp
/*===- TableGen'erated file -------------------------------------*- C++ -*-===*\
|*                                                                            *|
|* Dialect Definitions                                                        *|
|*                                                                            *|
|* Automatically generated file, do not edit!                                 *|
|* From: ZLDialect.td                                                         *|
|*                                                                            *|
\*===----------------------------------------------------------------------===*/

MLIR_DEFINE_EXPLICIT_TYPE_ID(::zl::ZlDialect)
namespace zl {
ZlDialect::ZlDialect(::mlir::MLIRContext *context)
    : ::mlir::Dialect(getDialectNamespace(), context, ::mlir::TypeID::get<ZlDialect>())
    
     {
  
  initialize();
}
ZlDialect::~ZlDialect() = default;
} // namespace zl
```

The generated dialect class is straightforward. It provides a function that returns the dialect's name and calls `initialize` from its constructor. There is no default implementation of `initialize`; the dialect's implementation must provide it.

To use the generated files, include the generated header in your header and the generated C++ file in your C++ source. Two points are worth keeping in mind:

- A `.td` file can only include other `.td` files, so your C++ header must also include the corresponding MLIR headers.
- For now, the only function we need to implement manually in the C++ file is `initialize`, which typically registers operations.

The command-line tool that generates these C++ files from `.td` definitions is `mlir-tblgen`. You can build it from LLVM's source tree by enabling the MLIR project with `-DLLVM_ENABLE_PROJECTS`.

In this example, the header is generated with `--gen-dialect-decls`, and the corresponding C++ file with `--gen-dialect-defs`.

Run `mlir-tblgen --help` for more information about the command-line options.

## Operation

Operations are the heart of a dialect. Without operations, a dialect is little more than a namespace.

We can define operations in **the same file** as the dialect. There is no need to split them simply because they describe different things: `mlir-tblgen` can identify different kinds of definitions in one file. The `-gen-op-decls` and `-gen-op-defs` options generate the corresponding header and C++ file.

I find this slightly easier to configure in CMake, although a conventional project should keep the two kinds of definitions separate.

To define an operation, first include the base `.td` file:

```cpp
include "mlir/IR/OpBase.td"
```

Then define the operation using its `Op<...>` class. For example:

```cpp
// Base class for zl dialect operations. This operation inherits from the base
// `Op` class in OpBase.td, and provides:
//   * The parent dialect of the operation.
//   * The mnemonic for the operation, or the name without the dialect prefix.
//   * A list of traits for the operation.
class Zl_OP<string mnemonic, list<Trait> traits = []> :
    Op<Zl_Dialect, mnemonic, traits>;

def ConstantOp : Zl_OP<"constant"> {
  // Provide a summary and description for this operation. This can be used to
  // auto-generate documentation of the operations within our dialect.
  let summary = "constant operation";
  let description = [{
    Constant operation turns a literal into an SSA value. The data is attached
    to the operation as an attribute. For example:

      %0 = "zl.constant"()
         { value = dense<[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]> : tensor<2x3xf64> }
        : () -> tensor<2x3xf64>
  }];

  // The constant operation takes an attribute as the only input.
  // `F64ElementsAttr` corresponds to a 64-bit floating-point ElementsAttr.
  let arguments = (ins F64ElementsAttr:$value);

  // The generic call operation returns a single value of TensorType.
  // F64Tensor corresponds to a 64-bit floating-point TensorType.
  let results = (outs F64Tensor);

  // Add additional verification logic to the constant operation. Setting this bit
  // to `1` will generate a `::llvm::LogicalResult verify()` declaration on the
  // operation class that is called after ODS constructs have been verified, for
  // example the types of arguments and results. We implement additional verification
  // in the definition of this `verify` method in the C++ source file.
  let hasVerifier = 1;
}
```

The two fields to focus on are:

- arguments
- results

For this constant operation, the result is a tensor of `f64` values, as specified by `results`.

An operation's `arguments` are not limited to operands. Here, the argument is an attribute describing the tensor we return, including its shape.

Given these `arguments` and `results`, the generated code includes the following creation function:

```cpp
static ConstantOp create(::mlir::OpBuilder &builder, ::mlir::Location location, ::mlir::Type resultType0, ::mlir::DenseElementsAttr value);
```

Result types come first, followed by arguments. The order of the arguments in the generated function matches their order in the definition exactly.

The syntax is:

```cpp
let arguments = (ins type1:$value1, type2:$value2);
```

Here, `arguments` has the TableGen built-in type `dag`, or directed acyclic graph.

A DAG is written as `(operation operand1 operand2)`. The `ins` operator is the convention required by `mlir-tblgen` for operation arguments. The same principle applies to `results`.

The types, or more precisely constraints, cannot be arbitrary names. Look up their definitions in these two files:

```cpp
mlir/include/mlir/IR/CommonTypeConstraints.td
mlir/include/mlir/IR/CommonAttrConstraints.td
```

For example, the attribute we used above has this definition:

```cpp
def F64ElementsAttr : FloatElementsAttr<64>;
```

## Adding dependencies with CMake

The essential task is to add a step to the build pipeline that generates C++ source and header files from `.td` files, then make the existing project depend on those outputs. This is straightforward with a build tool such as Gradle, but a little more involved with CMake. Fortunately, LLVM provides CMake helpers that make it easier to develop an MLIR-based compiler. The following is my CMake configuration.

The main steps are:

- Set the `MLIR_DIR` and `LLVM_DIR` paths.
- Import the MLIR dependency with `find_package`.
- Load the relevant CMake helpers with `include`.
- Configure code-generation options and targets with `mlir_tablegen`.
- Add a dependency on the generated code.
- Link against MLIR.

```
cmake_minimum_required(VERSION 3.31)
project(toy_mlir LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(MLIR REQUIRED CONFIG)

message(STATUS "Using MLIRConfig.cmake in: ${MLIR_DIR}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

list(APPEND CMAKE_MODULE_PATH "${MLIR_CMAKE_DIR}")
list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")

include(AddLLVM)
include(AddMLIR)
include(HandleLLVMOptions)

add_definitions(${LLVM_DEFINITIONS})
include_directories(${LLVM_INCLUDE_DIRS} ${MLIR_INCLUDE_DIRS})
set(LLVM_TARGET_DEFINITIONS include/ZLDialect.td)
mlir_tablegen(ZLDialect.h.inc      -gen-dialect-decls)
mlir_tablegen(ZLDialect.cpp.inc    -gen-dialect-defs)
mlir_tablegen(ZLOps.h.inc          -gen-op-decls)
mlir_tablegen(ZLOps.cpp.inc        -gen-op-defs)
add_public_tablegen_target(ZLDialectIncGen)

add_executable(toy_mlir
        compiler.cpp
        Lexer.h
        AST.h
        mlir/MlirGen.cpp
        mlir/MlirGen.h
        include/ZLDialect.h
        mlir/ZLDialect.cpp
)

add_dependencies(toy_mlir ZLDialectIncGen)


target_include_directories(toy_mlir SYSTEM PRIVATE
        ${LLVM_INCLUDE_DIRS}
        ${MLIR_INCLUDE_DIRS})
target_include_directories(toy_mlir PRIVATE
        include
        ${CMAKE_CURRENT_BINARY_DIR})
# generated *.inc land here
target_link_libraries(toy_mlir PRIVATE MLIRIR)

llvm_update_compile_flags(toy_mlir)
mlir_check_all_link_libraries(toy_mlir)

```

## Next Steps

Now I understand what MLIR is and know how to integrate it in my compiler.

So my next plan is to emit the MLIR with the AST provided.

Maybe I'll write a new blog to introduce the structure ``MLIRContext`` if it's interesting enough.
