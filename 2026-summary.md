---
layout: post
title: "[WIP] 2026 Year in Review"
date: 2026-10-16
description: "From intern to TikTok Android Client Infra engineer: reflections on builds, reliability, efficiency, and a year of work and learning."
tags: [build, life]
wip: true
---

## A few thoughts

2026 has been an unusual year, both for me and for computing.

On a personal level, I joined ByteDance full-time in July 2026 as a member of TikTok Android Client Infra. Although I had already spent a year there as an intern, this was still a significant moment: I went from being a happy intern with "no real responsibility or pressure" to a full-time employee expected to identify gaps in our infrastructure and fill them independently.

After nearly two years of this work, from February 2025 to October 2026, I would describe it as "dirty work that takes some skill."

There is no clearly defined technology stack. It is less about specializing in one narrow field and more about dealing with whatever comes our way.

If I had to summarize my daily work in one sentence, it would be "keeping TikTok's client build process reliable and efficient." These three words capture the essence of the job:

- **Builds**
- **Reliability**
- **Efficiency**

**What is a build?**

Programmers write code, and their immediate output is usually a collection of text files. Whether they work on the frontend, backend, or client, what humans deliver is almost always text. A build turns that output into something a computer can accept and understand.

This is a straightforward definition. In different development environments, it usually means:

- For a C developer, compiling and linking C source files into an executable or a shared library (`.so`).
- For a Java developer, compiling Java source code into an executable JAR.

**How are Android client builds different?**

For Android client developers, however, the process is **considerably more complicated**.

An Android client build must package Java, Kotlin, C++, and resource files into an APK that Android understands. Even junior developers can usually grasp the overall process of a C or Java build. In Android development, many feature developers have little visibility into the build pipeline: they do not really know how their code and resources become software that runs on a phone.

To understand the whole pipeline, you need to know at least the following:

- What is Gradle, and how does it work with the Android Gradle Plugin (AGP) to support Android builds?
- How is an Android application structured, and how does an Android device consume that format? Going further, what is an AAB?
- How are resources compiled? How do references such as `R.id.XX` and `R.string.XX` resolve to actual resources at runtime?
- How does DEX bytecode differ from Java class-file bytecode? How does bytecode move through the build pipeline?
- How is C++ code loaded?

The reality of ByteDance's large client applications is even more complicated:

- The same source code can produce local, CI, production, and regression-test builds. How do they differ, and why are those differences necessary?
- How do we provide a stable build environment and reduce "it works on my machine" problems?

- How do we put strong safeguards in place against production risks, including static analysis and privacy compliance?
- How do we share code across HarmonyOS, Android, and iOS to improve development efficiency?

- How do we push bytecode performance and application size optimizations as far as possible, using transforms, R8, Redex, and other tools?

These technical and architectural questions are not directly about product features, but improving this infrastructure has substantial benefits for long-term product development. Doing the work well requires infrastructure engineers to have broad technical knowledge and the ability to learn. How quickly and cleanly you can solve an unfamiliar problem is a key measure of your ability as an infrastructure engineer.

In **Work review**, I will discuss some of the work I have done, taken over, or observed over the past year, along with my reflections on it.

**What does build reliability mean?**

Take LLVM as an example. Its repository is a huge monorepo, with many pull requests merged every day, yet reports of a merge leaving the main branch unable to build are rare. This is one aspect of reliability: code on the main branch can consistently be built. The repository also has extensive regression tests, which must pass before a pull request is merged. As a result, new features usually do not break existing ones, and the impact of a change is easier to control.

This lets developers focus on the feature they are working on, while the infrastructure layer takes on much of the burden of protecting the project from disruptive changes.

Compared with the relatively simple structure of a C++ project, Android projects are much less straightforward. As discussed above, their build pipelines are considerably more complicated, which makes reliability harder to maintain. During my time in this role, I have encountered the following challenges. This post describes the problems rather than exploring their technical details.

Incremental builds are an important way to optimize large projects and the main path used in daily development. You can think of them as a build's "warm start." In practice, however, they have several problems:

- Incremental builds depend on intermediate artifacts. Unexpected intermediate state can cause failures that require falling back to a full build.
- Gradle's daemon reuses a JVM process across builds. If the build pipeline leaks memory, repeated builds will eventually fail with an out-of-memory error.
- Actual performance falls short of expectations. We have not fully achieved the ultimate goal of incremental compilation: running only the work that is strictly necessary.

We call the packages delivered to users "production builds." To make them as deterministic as possible, rather than relying on an unstable environment, our production packaging pipeline always performs a full build and avoids incremental paths. This leads to **very long build times, usually more than two hours**, yet we still encounter the following problems:

- Building exactly the same source code multiple times can produce different artifacts, although the differences usually do not affect functionality.
- The packaging process can still fail.

Improving this situation is ongoing work. Client applications continue to evolve, with new features and new apps, and so do the toolchains: Kotlin, Gradle, and compiler versions all change. The problems do not stand still. Solving one makes room for another, so this is a continuous maintenance effort.

## Work review

## Open-source contributions

## Where things stand technically

## Looking ahead

Keep working on compilers and build efficiency.

