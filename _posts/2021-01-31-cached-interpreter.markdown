---
layout: post
title:  "[GBA] Writing a cached interpreter"
date:   2021-01-31 20:00:00 +0200
categories: emulation development, optimizations
---

### Writing a cached interpreter

A while ago, I rewrote my GBA emulator (GBAC-) in C++ (DSHBA) to make it faster. I wanted to add a hardware renderer, and really focus on optimizing it all the way.
After I was "done", and had reached framerates higher than I had ever hoped before, I recently came back to it, and wanted to try to write a cached interpreter. 
I have heard a lot of talks about JITs and cached interpreters for performance gain, and since I had reached pretty insane framerates already, I wanted to go even further.

#### Why not a JIT?

Something you might ask is: "why did you write a cached interpreter and not a JIT". The short answer to this is this: accuracy. The GBA is a fairly old system. Usually for older
systems, timings are important. Where for modern systems, you don't have to worry about cycles for the most part, other than being in the right ballpark (this is mainly because for 
more modern systems, the programmer himself can also rely less on specific timings due to pipelining, OoO execution and other advanced techniques), for the GBA you still sort of have to.
A lot of tests, even in the official AGS Aging Cartridge test from Nintendo, some tests require accuracy within 16 cycles (in a frame of ~1200 cycles, or 1 scanline), or some even perfect
cycle accuracy. Games may also rely on specific timings. 

My old GBA emulator and my new one had the same performance in terms of accuracy. I passed most AGS tests, a lot of Endrift's tests, but not any of the crazy perfect cycle accuracy ones. This
was good enough for me, but I wouldn't want to reduce accuracy for the sake of speed. These timings are easiest to emulate in an interpreter. In a JIT, you want to mostly just keep track of
your GPRs (General Purpose Registers), and not of PPU events happening, or audio samples being requested, and most importantly: IRQs firing at the right times. These things, will often require 
me to check the scheduler, or break blocks early at "random" moments. These things combined led me to write a cached interpreter and not a JIT.

#### How does a cached interpreter work?

First of all, this is how my interpreter loop looked:
```
check scheduler:
	if there are events to handle: do events 
	otherwise: step once
```
Then let's first look at the classic interpreter. The idea for this is very simple:
```
fetch opcode from memory
decode opcode 
run instruction handler
```
Alright, simple enough. This seems very straight forward, but there is a step here that we can remove. If we decode an instruction, and later on we get to the same address, we
wouldn't have to decode it again if we store the information on the instruction. This is "caching" the instruction. 