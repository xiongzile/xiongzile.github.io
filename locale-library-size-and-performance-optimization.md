---
layout: post
title: "Shrinking a C++ Locale Library"
date: 2026-10-29
description: "Investigating global object initialization in an oversized date and time formatting library, and compacting locale data while keeping O2."
tags: ["Android", "C++"]
typora-copy-images-to: assets/images/locale-library-size-and-performance-optimization
---

While recently optimizing a cross-platform date and time formatting SDK, I ran into a problem: its functionality did not seem particularly complex, yet the resulting shared library was larger than expected. The compressed SO in the Android APK was still 570 KiB. A library primarily responsible for formatting dates and times should not be this large.

The SDK essentially takes a timestamp, a target language, and formatting options, then returns display text such as “October 29,” “3 minutes ago,” or “3:00–5:00 PM.” Its core implementation is in C++, shared across platforms such as Android and iOS.

## Compiler Options

The most straightforward attempt was to replace `-O2` with `-Oz`.

`-Oz` prioritizes reducing code size and affects decisions such as inlining, but it does not turn optimization off. Clang describes it as reducing code size further than `-Os`; see [Clang's documentation on optimization options](https://clang.llvm.org/docs/CommandGuide/clang.html#code-generation-options).

The effect was clear: the binary size dropped by more than half. However, after building and running performance tests on macOS, I found that performance had degraded by more than 50%. These operations take microseconds or nanoseconds, so their impact on the application still depends on how they are used. Even so, I wanted to see whether I could reduce the size while keeping `-O2`.

Why would changing compiler options alone produce such a large size difference in the same code? Where exactly did that difference come from? If I could locate the source, perhaps I would not have to choose between the two optimization levels.

## Global Initialization

Comparing the binaries, I found that most of the difference came from `.text`, the code section. Looking further, the locale configuration's global initialization functions, `__cxx_global_var_init*`, and the associated constructor code accounted for a large portion of it.

Consider a simple global variable:

```cpp
#include <string>
std::string S = "hello";
int main() {
    return 0;
}
```

In [this compilation example](https://godbolt.org/z/qKsqE7s4W), the compiler generates a `__cxx_global_var_init` entry point for it. The source contains just one line defining a string, but the binary also needs code to prepare that `std::string` object.

The multilingual configuration contains many such fields, with a separate configuration for each language. Even though the string contents are already written into the source, using them still involves constructing C++ objects. Expanding that construction logic repeatedly across configurations adds up to a substantial amount of machine code.

To understand this more clearly, I created two simplified examples: one retaining only a few strings, and another retaining the complete configuration for a single language. Here is the observed instruction count comparison:

| Example | Code | `-O2` | `-Oz` |
| --- | --- | --- | --- |
| Minimal configuration | [Godbolt](https://godbolt.org/z/oW6PnGr98) | 30 | 20 |
| Complete configuration for one language | [Godbolt](https://godbolt.org/z/f4E9PsbsT) | 6000 | 2000 |

## O2 vs. Oz

The minimal example retains just three months:

{% raw %}
```cpp
#include <array>
#include <string>
#include <string_view>

struct Config {
    union {
        std::array<std::string, 3> months;
    };

    Config() : months{{"January", "February", "March"}} {}

    ~Config() {}
};

inline Config config;

std::string_view month(unsigned index) {
    return config.months[index];
}
```
{% endraw %}

With `-Oz`, the initialization entry point calls the `Config` constructor, which then constructs three `std::string` objects at their respective addresses in `months`. This assembly retains the constructor calls:

```asm
__cxx_global_var_init:                  // @__cxx_global_var_init
        stp     x29, x30, [sp, #-16]!   // 16-byte Folded Spill
        mov     x29, sp
        adrp    x8, guard variable for config
        add     x8, x8, :lo12:guard variable for config
        ldarb   w8, [x8]
        tbnz    w8, #0, .LBB0_3
        adrp    x0, guard variable for config
        add     x0, x0, :lo12:guard variable for config
        bl      __cxa_guard_acquire
        cbz     w0, .LBB0_3
        adrp    x0, config
        add     x0, x0, :lo12:config
        bl      Config::Config() [base object constructor]
        adrp    x0, guard variable for config
        add     x0, x0, :lo12:guard variable for config
        ldp     x29, x30, [sp], #16     // 16-byte Folded Reload
        b       __cxa_guard_release
.LBB0_3:
        ldp     x29, x30, [sp], #16     // 16-byte Folded Reload
        ret
Config::Config() [base object constructor]:                         // @Config::Config() [base object constructor]
        sub     sp, sp, #48             // =48
        str     x19, [sp, #16]          // 8-byte Folded Spill
        stp     x29, x30, [sp, #32]     // 16-byte Folded Spill
        add     x29, sp, #32            // =32
        adrp    x1, .L.str
        add     x1, x1, :lo12:.L.str
        sub     x2, x29, #8             // =8
        mov     x19, x0
        bl      std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string<std::allocator<char> >(char const*, std::allocator<char> const&)
        adrp    x1, .L.str.1
        add     x0, x19, #32            // =32
        add     x1, x1, :lo12:.L.str.1
        add     x2, sp, #8              // =8
        bl      std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string<std::allocator<char> >(char const*, std::allocator<char> const&)
        adrp    x1, .L.str.2
        add     x0, x19, #64            // =64
        add     x1, x1, :lo12:.L.str.2
        mov     x2, sp
        bl      std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string<std::allocator<char> >(char const*, std::allocator<char> const&)
        ldp     x29, x30, [sp, #32]     // 16-byte Folded Reload
        ldr     x19, [sp, #16]          // 8-byte Folded Reload
        add     sp, sp, #48             // =48
        ret
month(unsigned int):                              // @month(unsigned int)
        adrp    x9, config
        mov     w8, w0
        add     x9, x9, :lo12:config
        add     x8, x9, x8, lsl #5
        ldp     x1, x0, [x8]
        ret
config:
        .zero   96

guard variable for config:
        .xword  0                       // 0x0

.L.str:
        .asciz  "January"

.L.str.1:
        .asciz  "February"

.L.str.2:
        .asciz  "March"

.L.str.3:
        .asciz  "basic_string::_M_construct null not valid"

.L.str.4:
        .asciz  "basic_string::_M_create"
```

With `-O2`, the construction logic is inlined into the initialization entry point. The compiler uses immediate values, a constant pool, and multi-byte stores to directly set the short strings' contents, lengths, and internal pointers:

```asm
.LCPI0_0:
        .xword  8                       // 0x8
        .xword  8751164182992414022     // 0x7972617572626546
__cxx_global_var_init:                  // @__cxx_global_var_init
        stp     x29, x30, [sp, #-16]!   // 16-byte Folded Spill
        mov     x29, sp
        adrp    x8, guard variable for config
        add     x8, x8, :lo12:guard variable for config
        ldarb   w8, [x8]
        tbnz    w8, #0, .LBB0_3
        adrp    x0, guard variable for config
        add     x0, x0, :lo12:guard variable for config
        bl      __cxa_guard_acquire
        cbz     w0, .LBB0_3
        adrp    x8, config
        adrp    x12, .LCPI0_0
        add     x8, x8, :lo12:config
        mov     w9, #24906
        mov     w10, #24949
        ldr     q0, [x12, :lo12:.LCPI0_0]
        movk    w9, #30062, lsl #16
        movk    w10, #31090, lsl #16
        mov     x12, x8
        mov     w11, #7
        str     w9, [x12, #16]!
        mov     w9, #24909
        stur    w10, [x8, #19]
        add     x10, x8, #48            // =48
        movk    w9, #25458, lsl #16
        str     x10, [x8, #32]
        mov     w10, #104
        stp     x12, x11, [x8]
        mov     x11, x8
        strh    w10, [x8, #84]
        mov     w10, #5
        strb    wzr, [x8, #23]
        strb    wzr, [x8, #56]
        stur    q0, [x8, #40]
        str     w9, [x11, #80]!
        adrp    x0, guard variable for config
        add     x0, x0, :lo12:guard variable for config
        stp     x11, x10, [x8, #64]
        ldp     x29, x30, [sp], #16     // 16-byte Folded Reload
        b       __cxa_guard_release
.LBB0_3:
        ldp     x29, x30, [sp], #16     // 16-byte Folded Reload
        ret
month(unsigned int):                              // @month(unsigned int)
        adrp    x9, config
        mov     w8, w0
        add     x9, x9, :lo12:config
        add     x8, x9, x8, lsl #5
        ldp     x1, x0, [x8]
        ret
config:
        .zero   96

guard variable for config:
        .xword  0                       // 0x0
```

Comparing the values with ASCII, you can recognize the bytes of `January`, `February`, and `March` in the immediate values and constant pool. Some of the data that previously appeared under string labels is now represented in the instructions that construct these objects.

The difference between the two versions is therefore more than the number of function calls. `-O2` expands the construction of specific strings at the call site, while `-Oz` makes greater use of shared, general-purpose construction logic. With only three fields, the difference is not particularly large; with an entire locale configuration, and then multiple languages, this initialization code becomes substantial.

That suggested the next direction: locale configurations are fixed data, so do they really need to exist as large numbers of `std::string` objects? Storing the string bytes and indices directly would eliminate the need to construct these objects.

## String Pool

In the original configuration, each string field corresponded to a `std::string`. The optimized representation has two parts: the string bytes are stored together in a static string pool, and each configuration field records only the offset and length of its string within that pool.

Using the same three months, the data can be represented as follows:

```text
string_pool = "January\0February\0March\0"

Field            offset    size (UTF-8 bytes)
January          0       7
February         8       8
March           17       5
```

The `\0` separators are retained between strings, so `February` begins at offset 8 and `March` at offset 17. The length is already known when reading a string, so there is no need to scan for its end.

A `LocaleString` in the configuration logically represents `offset + size`. The actual packed representation occupies just 4 bytes: the low 20 bits of a `uint32_t` store the offset, and the high 12 bits store the length in UTF-8 bytes.

```text
31                     20 19                              0
+------------------------+---------------------------------+
|     size: 12 bits      |          offset: 20 bits        |
+------------------------+---------------------------------+

packed = (size << 20) | offset
```

Here is a minimal illustration of this layout, including the string pool and the read operation:

```cpp
#include <cstdint>
#include <string_view>

inline constexpr char string_pool[] = "January\0February\0March";

struct LocaleString {
    std::uint32_t packed;

    constexpr std::string_view view() const {
        const auto offset = packed & 0xfffffu;
        const auto size = packed >> 20;
        return {string_pool + offset, size};
    }
};

inline constexpr LocaleString config[] = {
    {(7u << 20) | 0u},
    {(8u << 20) | 8u},
    {(5u << 20) | 17u},
};

std::string_view month(unsigned index) {
    return config[index].view();
}
```

This example assumes that `index` is valid and that the pool and indices have been generated correctly. The 20-bit offset and 12-bit length can represent values up to 1,048,575 and 4,095, respectively; these bounds need to be checked when generating the data. Lengths are measured in UTF-8 bytes, not character counts.

The month fields no longer own string storage that needs to be constructed. Instead, they refer to static bytes whose lifetime spans the entire program. The configuration table can also be represented as `constexpr` data, removing the need to construct these string objects one by one at runtime. This uses constant initialization; see the [C++ standard draft](https://eel.is/c++draft/basic.start.static) for the distinction between static and dynamic initialization.

The key to the optimization is the change in data representation: work previously performed to prepare the locale configuration can now be done during the build. At runtime, all that remains is to read the configuration and use the strings.

## Build-Time Generation

This layout is suitable for machines to read, but not for direct maintenance. Manually calculating offsets in the string pool whenever a month name is added or a translation changes would be error-prone.

I therefore keep the readable locale configuration in `i18n/*.json` and generate the string pool and packed configuration tables as part of the CMake build. Maintainers edit the JSON, and subsequent builds generate the corresponding C++ data.

The process looks like this:

```text
i18n/*.json
    │  Read the locale configuration and obtain the strings' UTF-8 bytes
    ▼
Build-time data generation
    │  Lay out the strings and calculate each field's offset and size
    ▼
Static string pool + constexpr locale tables
    │  Compile alongside the C++ source
    ▼
Read indices at runtime to retrieve the corresponding string slices
```

The JSON files are the source for maintaining locale configuration, while the string pool and offset tables are build artifacts. This preserves the readability of the configuration without letting its handwritten format directly determine the runtime data structure.

## Reading Packed Strings

Here is the assembly for the read operation in the earlier comparison example after adopting the packed configuration:

```asm
month(unsigned int):
        adrp    x8, config
        add     x8, x8, :lo12:config
        adrp    x9, string_pool
        add     x9, x9, :lo12:string_pool
        ldr     w8, [x8, w0, uxtw #2]
        lsr     x0, x8, #20
        and     x8, x8, #0xfffff
        add     x1, x9, x8
        ret

config:
        .word   7340032
        .word   8388616
        .word   5242897

string_pool:
        .asciz  "January\000February\000March"
```

The three integers are the packed representations of the three offset and length pairs above:

| String | offset | size | packed |
| --- | --- | --- | --- |
| January | 0 | 7 | 7340032 |
| February | 8 | 8 | 8388616 |
| March | 17 | 5 | 5242897 |

Although the new representation involves decoding and an additional memory read, I expect the performance impact to be small because the string pool has a much more compact layout than the original collection of strings. The actual effect needs to be measured.

## Results

After changing the data layout, I kept the original `-O2` compiler option and obtained the following results:

| Metric | Before | After | Change |
| --- | --- | --- | --- |
| Compressed SO size in the APK | 570 KiB | 117 KiB | **-79.5%** |
| Library load time | 1.306 ms | 0.501 ms | **-61.7%** |

The library loading and formatting performance measurements were taken on macOS and have not been repeated on a physical Android device.

## Inline Variables

During the investigation, I also noticed an `inline` before the original configuration variable. Looking it up in the standard, I learned that inline variables were introduced in C++17. Subject to the definition rules, they allow a variable definition to appear in a header included by multiple translation units. See the [standard draft's explanation of inline](https://eel.is/c++draft/dcl.inline) and [cppreference](https://en.cppreference.com/cpp/language/inline).
