# 基于 MLIR 开发一个 toy compiler

> 本文参考：https://mlir.llvm.org/docs/Tutorials/Toy 进行实践，主要目的是学习 MLIR 写法和底层原理，[纯手写代码仓库](https://github.com/xiongzile/mlir-toy-zl) 本文不会对编译原理基础部分做探讨，默认读者知道 Lexer 和 AST 怎么写，因此重心在怎么复用 LLVM/MLIR 的基础设施构建一个编译器
>
> 和官方教程的主要区别是会讲代码的细节和使用上容易踩坑的点，视角更小，要理解 MLIR 设计应该参考官方文档

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









