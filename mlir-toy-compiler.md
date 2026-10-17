---
layout: post
title: "MLIR: Dialect 和 Operation 的简单理解和使用"
date: 2026-10-17
description: 跟着 MLIR Toy 教程，从一个叫 zl 的 dialect 开始，理解 Dialect、Operation 与 TableGen，并用 CMake 把它们串起来。
tags: [mlir, compiler]
wip: true
---

> 参考：https://mlir.llvm.org/docs/Tutorials/Toy 进行实践，主要目的是学习 MLIR 写法和底层原理，[纯手写代码仓库](https://github.com/xiongzile/mlir-toy-zl) 
>
> 本文主要了解 MLIR 的基本概念，以及引入 MLIR 相关依赖的基本配置

## Dialect

Dialect 体现在 MLIR 其实类似一个 scope，比如我开发的编译器叫 zl compiler，因此我给我的 dialect 命名为 zl。我们通过写这样的 tablegen 代码就可生成一个 dialect 方言：

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

目前只是一个空壳，因为我们没有给它添加任何 Operation，在配置好 Cmake 文件之后，它可以生成一个头文件和一个对应的 cpp 文件，这个是头文件：

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

这个是 cpp 文件：

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

管理 Dialect 的类逻辑很清晰，结构比较简单，它会自动生成一个标识自己的名字的函数，然后在构建函数里调用 

initialize，这个函数他默认是不会有任何实现的，需要外部使用它

外部使用同样是用头文件 include 头文件，用 cpp 文件 include cpp 文件，注意两点：

- td 文件只能 include td 文件，因此我们使用它的头文件需要 include 对应的 mlir 源码头文件
- 目前只需要在 cpp 文件中手动实现 initialize 函数，一般就是把 Operation 注册进来

基于 td 生成各种 C++ 相关文件的 cli 工具是 mlir-tablegen，可以直接通过 LLVM 源码的 -DLLVM_ENABLE_PROJECTS 开启 mlir 模块构建出来

我们这个例子的头文件是通过：--gen-dialect-decls 生成的，对应的 cpp 文件则是 --gen-dialect-defs

更多命令行工具使用方法直接通过 mlir-tablegen --help 查询即可

## Operation

Operation 是 Dialect 的灵魂，没有 Op 的 Dialect 就是一个命名空间，没有实际作用

要让 mlir-tablegen 生成 Operation，我们可以在**同一个文件**写，不需要因为语义是不同的就拆文件，mlir-tablegen 是可以识别同文件里的不同生成对象的，然后通过 -gen-op-decls 和 -gen-op-defs 就能生成对应的头文件和 cpp 文件

这样体感上 Cmake 好写一点，不过标准的工程肯定建议把两者分开

写 Op 我们要在 td 中引入对应的基础 td 文件：

```cpp
include "mlir/IR/OpBase.td"
```

然后基于它的 class Op<XX...> 声明我们的 Op 即可，参考代码：

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

这里需要重点关注的就是 

- arguments
- results

比如这里的 constant op，返回一个 F64 的 tensor，就是它的 results

MLIR 的 op arguments 语义不单单指操作数，比如这里他是一个 attr； attr 的内容是表示我们返回的 tensor 形状

基于我们给的 arguments 和 results，生成代码中会有一个这样的构造函数:

```cpp
static ConstantOp create(::mlir::OpBuilder &builder, ::mlir::Location location, ::mlir::Type resultType0, ::mlir::DenseElementsAttr value);
```

参数的顺序是 results 在前，arguments 在后，生成代码的 arguments 部分的内部顺序和 arguments 严格保持一致

这里的的语法是：

```cpp
let arguments = (ins type1:$value1, type2:$value2);
```

这里的 arguments 类型是 dag（有向无环图），是 tablegen 内置的类型

dag 的声明就是 (operation operand1 operand2) 这里我们写的 ins 是 mlir-tablegen 规定的 dag 操作符，所以需要这么写

results 同理

这里的 type（更准确来说是 constraints) 不是随便写的，可以在这两个文件里面查，查到有定义的才可以写：

```cpp
mlir/include/mlir/IR/CommonTypeConstraints.td
mlir/include/mlir/IR/CommonAttrConstraints.td
```

比如我们刚写的 attr 就可以找到对应的声明行：

```cpp
def F64ElementsAttr : FloatElementsAttr<64>;
```

## CMake 引入依赖

问题的本质是要在我们的编译流程里加入“基于 td 生成 cpp 和 h 文件，然后让原工程依赖这些文件”。如果用 Gradle 之类的构建工具是非常简单的，但是用 Cmake 就比较麻烦了。索性 LLVM 对外提供了一套好用的 Cmake 函数，让我们可以比较简单的基于 Cmake 开发 MLIR 编译器，这是我的 cmake 脚本参考：

主要步骤为：

- 注入 MLIR_DIR 和 LLVM_DIR 路径声明
- 使用 find_package 导入 MLIR 依赖
- 使用 include 导入 MLIR 相关 cmake 配置函数
- 使用 mlir_tablegen 配置代码生成相关的参数和 target
- 将生成代码添加为依赖
- 将 MLIR 添加为依赖

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

