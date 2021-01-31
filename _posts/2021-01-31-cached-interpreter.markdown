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

<b>Note: this is not a general guide for writing a cached interpreter, and this approach might not be viable on every system. In this post I will explain why that is, and focus on my thought
process and the implementation for my cached interpreter.</b>

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
wouldn't have to decode it again if we store the information on the instruction. This is "caching" the instruction. We can make it even better than this though, we can make entire 
blocks of instructions at once, so that we dont have to look up the cached instruction every time, but just look up a block and run for multiple instructions at once! 

Now, the GBA memory map has some mirroring, and code cannot be ran from all regions. So I decided to split things up a bit. There are 3 regions I allow caching in:
	- the BIOS: this region cannot be written to, so once we make a cached block, we never have to delete it again!
	- ROM: this region is also not writeable, so we can save the cache blocks forever!
	- iWRAM: code often gets run from here because it takes very few cycles to fetch data from here. We have to handle this region slightly differently though, because code can
			 get overwritten.
			 
Cache "blocks" are blocks of instructions following each other that can be executed after each other. These blocks have to end somewhere, and the most logical places are branches or
on certain boundaries. I set these boundaries at every 256 bytes. This number is rather arbitrary, but setting this number allows you to only delete certain blocks when writes to
iWRAM happen.

The idea for the main loop of the emulator becomes slightly different:
```
check if current address has a cached block 
if it doesn't have one, and none can be created: 
	run interpreter normally, until it can 
if it doesn't have one, and one can be created:
	make a cache block and run interpreter normally*, but record the instructions
if it has one:
	run the cache block**
```
Now this is not the entire story. As I mentioned before, there is still a scheduler, and IRQs might happen that interrupt a block. Now what I could naively do (and did at first) is just
break whenever we are interrupted by the scheduler. I don't need to always break though. Some events, like adding a sample to the audio buffer, shouldn't need to interrupt the CPU at all, since
they don't have anything to do with it! 

I changed up my scheduler slightly, and made every event return a boolean, whether they directly affected the CPU state or not. Events that do are events like IRQs, or DMAs where an IRQ happened inbetween.
The extra steps will be:
```
(*): check if the scheduler interrupted the CPU, and if so, return from making the block

(**): check if the scheduler interrupted the CPU, and if so, return from running the block
```

This might seem a bit abstract, so here is some actual code. Before I added the cached interpreter, the main loop essentially looked like this (some details like pipeline stuff are left out):
```CXX
while (true) {
	while (!Scheduler.ShouldDoEvents()) {
		CPU.Step();
	}

	Scheduler.DoEvents();
}
```
with 
```
ARM7TDMI::Step() {
	u32 instruction;
	if (ARMMode){ 
		instruction = Mem->Read<u32>(pc - 8);
		if (CheckCondition(instruction >> 28)) {
			(this->*ARMInstructions[ARMHash(instruction)])(instruction);
		}
	}
	else {
		instruction = Mem->Read<u16>(pc - 4);
		(this->*THUMBInstructions[THUMBHash(instruction)])(instruction);
	}
}
```
A classic interpreter loop. Now we want to add something to store our cache blocks in. 
```CXX
// a simple struct holding the instruction and the handler
struct CachedInstruction {
	const u32 Instruction;
	const void __fastcall (ARM7TDMI::*Pointer)(u32 instruction);
}

// a struct holding a block of instructions
struct InstructionCache {
	const bool ARM;
	const bool Deletable;  // true in iWRAM
	const u16 AccessTime;
	std::vector<CachedInstruction> Instructions;
}
```
And we want some lookup tables for the cache blocks in our CPU.
```CXX
std::array<std::unique_ptr<InstructionCache>, (Mem::BIOSSize >> 1)> BIOSCache = {};
std::array<std::unique_ptr<InstructionCache>, ((Mem::iWRAMSize - Mem::StackSize) >> 1)> iWRAMCache = {};
std::array<std::unique_ptr<InstructionCache>, (Mem::ROMSize >> 1)> ROMCache = {};
```
You might notice some things here. First of all, the `unique_ptr`s. I know that dynamic allocation is slow in general. I rewrote it to not use dynamic allocation, and I did not notice a difference.
Main reason for this might be that blocks will never be deleted in ROM and in the BIOS, and it might be rare for blocks to be deleted in iWRAM. Another benefit this has is that I don't have to 
worry about writing a bump allocator (a big region of memory that I push instructions to until it overflows, and then reset the entire thing), the `unique_ptr`s will handle memory allocation for me!

Another thing to note is that I shift the size of the respective regions by 1. This is because all instructions must be aligned by 4 in ARM mode, and 2 in THUMB mode. 

Last thing, for the iWRAM cache I subtract `Mem::StackSize`. This is an arbitrary number (that I think I put at `0x400`). I did this, because when writes to iWRAM happen, I have to check out which
blocks have to be deleted. Since the stack is also in iWRAM, a lot of pushes will happen, and I don't want to check which blocks to delete on every push/pop.

One last thing then. We need to keep track of our current cache.
```CXX
std::unique_ptr<InstructionCache>* CurrentCache = nullptr;
```
The way this works is very convenient. This might seem like 2 layers of indirection, but while running the cache we can just look at the object that is finally pointed at. In general this is what
we will be doing anyway. This is convenient, because we can use `nullptr` to encode different states:
```
CurrentCache == nullptr: no cache present, no cache can be made
CurrentCache == nullptr*: no cache present, cache can be made
otherwise: cache present!
```
We also need a way to update the current cache:
```CXX
 constexpr std::unique_ptr<InstructionCache>* ARM7TDMI::GetCache(const u32 address) {
	switch (static_cast<MemoryRegion>(address >> 24)) {
		case MemoryRegion::BIOS: {
			const u32 index = (address & (Mem::BIOSSize - 1)) >> 1;
			if (likely(address < Mem::BIOSSize)) {
				// check if cache exists
				if (BIOSCache[index]) {
					return &BIOSCache[index];
				}

				// show that no cache exists, but can be created
				return &BIOSCache[index];
			}

			// no cache
			return nullptr;
		}
		case MemoryRegion::iWRAM: {
			const u32 index = (address & (Mem::iWRAMSize - 1)) >> 1;
			if ((address & (Mem::iWRAMSize - 1)) < (Mem::iWRAMSize - Mem::StackSize)) {
				if (iWRAMCache[index]) {
					return &iWRAMCache[index];
				}
				// mark index as filled for faster page clearing
				iWRAMCacheFilled[(address & (Mem::iWRAMSize - 1)) / Mem::InstructionCacheBlockSizeBytes].push_back(index);
				return &iWRAMCache[index];
			}
			return nullptr;
		}
		case MemoryRegion::ROM: {
			const u32 index = (address & (Mem::ROMSize - 1)) >> 1;
			if (ROMCache[index]) {
				return &ROMCache[index];
			}
			return &ROMCache[index];
		}
		default:
			return nullptr;
	}
}
```
Ignore the `iWRAMCacheFilled` line for now. Alright, so now we have everything set up to make caches! First of all, we need different run loops:
```CXX
ARM7TDMI::Run();
ARM7TDMI::RunMakeCache();
ARM7TDMI::RunCache();
```
Running the cache is the simplest method:
```CXX
void ARM7TDMI::RunCache() {
    // run created cache
    const InstructionCache& cache = **CurrentCache;
    const u8 cycles = cache.AccessTime;
    const bool deletable = cache.Deletable;

    if (cache.ARM) {
        // ARM mode, we need to check the condition now too
        for (const auto& instr : cache.Instructions) {
            if (unlikely(Scheduler->ShouldDoEvents())) {
                if (unlikely(Scheduler->DoEvents())) {
                    return;  // CPU state affected
                }
            }

            *timer += cycles;  // add time we would otherwise spend fetching the opcode from memory
            if (CheckCondition(instr.Instruction >> 28)) {
                (this->*instr.Pointer)(instr.Instruction);
            }

            pc += 4;

            // block was destroyed (very unlikely)
            if (deletable && unlikely(!CurrentCache)) {
                return;
            }
        }
    }
    else {
        // THUMB mode, no need to check instructions
		/*
		 * the code here is essentially the same as above
		 */
    }
}
```
Making the block looks very similar to the old loop, but then with a twist. I changed up my basic `ARM7TDMI::Step()` to this (also slightly simplified to remove pipeline stuff):
```CXX
template<bool MakeCache>
bool ARM7TDMI::Step() {
    u32 instruction;

    bool block_end = false;
	if (ARMMode) {
        // before the instruction gets executed, we are 2 instructions ahead
        instruction = Memory->Read<u32, true>(pc - 8);
		if constexpr(MakeCache) {
            auto instr = CachedInstruction(instruction, ARMInstructions[ARMHash(instruction)]);
            (*CurrentCache)->Instructions.push_back(instr);
            // also check if Rd == pc (does not detect multiplies with pc as destination)
            block_end = IsARMBranch[ARMHash(instruction)]
                     || ((instruction & 0x0000f000) == 0x0000f000)   // any operation with PC as destination
                     || ((instruction & 0x0e108000) == 0x08108000);  // ldm r, { .. pc }
        }
        if (CheckCondition(instruction >> 28)) {
            (this->*ARMInstructions[ARMHash(instruction)])(instruction);
        }

        pc += 4;
    }
    else {
        // THUMB mode
        instruction = Memory->Read<u16, true>(pc - 4);
        // THUMB mode
        if constexpr(MakeCache) {
            auto instr = CachedInstruction(instruction, THUMBInstructions[THUMBHash((u16)instruction)]);
            (*CurrentCache)->Instructions.push_back(instr);
            // also check for hi-reg-ops with PC as destination
            block_end = IsTHUMBBranch[THUMBHash((u16)instruction)] || ((instruction & 0xfc87) == 0x4487);
        }
        (this->*THUMBInstructions[THUMBHash((u16)instruction)])(instruction);
        // same here
        pc += 2;
    }
	
    if constexpr (MakeCache) {
        if (block_end || !(corrected_pc & (Mem::InstructionCacheBlockSizeBytes - 1))) {
            // branch or block alignment
            return true;
        }
        return false;
    }
    else {
        // return whether we might have a cache block
        return InCacheRegion(corrected_pc);  // corrected_pc = pc - (ARMMode ? 8 : 4)
    }
}
```
Basically, if `MakeCache` is `true`, `Step` returns whether the block has ended or not. If `MakeCache` is `false`, `Step()` returns whether a block can be made, or might be available.
The `RunMakeCache()` method will use `Step<true>`, and the basic `Run()` method will use `Step<false>`, while we are not in a region where caches can be made.
The `RunMakeCache()` looks like
```CXX
void ARM7TDMI::RunMakeCache() {
    // run the interpreter "normally", but record the instructions we execute in the current cache
    while (true) {
        if (unlikely(Scheduler->ShouldDoEvents())) {
            if (unlikely(Scheduler->DoEvents())) {
                // CPU state affected
                // just destroy the cache, we want the caches to be as big as possible
                *CurrentCache = nullptr;
                return;
            }
        }

        if (unlikely(Step<true>())) {
            // cache done
            if (unlikely((*CurrentCache)->Instructions.empty())) {
                // empty caches will hang the emulator
                // they might happen when branches close to pc get written (self modifying code)
                *CurrentCache = nullptr;
            }
            return;
        }

        if (unlikely(!CurrentCache)) {
            // cache destroyed by near write
            return;
        }
    }
}
```
You'll notice that I destroy the cache if we get interrupted by the scheduler. This is because I never recreate any caches in ROM and BIOS, so I want them to be as long as possible. Worst case scenario, a lot of events
happen in a row, and we might make 10 blocks of 1 instruction each, while we could have easily made 1 block of 10 instructions, and saving a lot more cache block lookup time.

If we end the block because `Step` returned `true`, we save the block unless there are no instructions in it. Normally, you'd say this cannot happen. But since the ARM7TDMI has a pipeline that can 
hold instructions that might be overwritten in memory, it can! I might have started a block with instructions in the pipeline and ended it before it was empty. We don't want wrong instructions
in our cache block, so I cannot add those pipelined instructions, and the block will be invalid.

And then there is the normal running:
```CXX
while (true) {
	if (unlikely(Scheduler->ShouldDoEvents())) {
		Scheduler->DoEvents();
	}
	
	// if Step returns true, we are in a region where we can generate a cache
	if (Step<false>()) {
		break;
	}
}
```
Basically the same as the classic interpreter loop.
The entire run function becomes this:
```CXX
ARM7TDMI::Run() {
	while(true) {
		CurrentCache = GetCache(corrected_pc);
        if (unlikely(!CurrentCache)) {
            // nullptr: no cache (not iWRAM / ROM)
            // run interpreter normally, without recording cache
            while (true) {
                if (unlikely(Scheduler->ShouldDoEvents())) {
                    Scheduler->DoEvents();
                }
                // if Step returns true, we are in a region where we can generate a cache
                if (Step<false>()) {
                    break;
                }
            }
        }
        else if (unlikely(!(*CurrentCache))) {
            // possible cache, but none present
            // make new one
            if (ARMMode) {
                const auto access_time = Memory->GetAccessTime<u32>(static_cast<MemoryRegion>(pc >> 24));
                *CurrentCache = std::make_unique<InstructionCache>(access_time, true, static_cast<MemoryRegion>(pc >> 24) == MemoryRegion::iWRAM);
            }
            else {
                const auto access_time = Memory->GetAccessTime<u16>(static_cast<MemoryRegion>(pc >> 24));
                *CurrentCache = std::make_unique<InstructionCache>(access_time, false, static_cast<MemoryRegion>(pc >> 24) == MemoryRegion::iWRAM);
            }
            RunMakeCache();
        }
        else {
            // cache possible and present
            RunCache();
        }
	}
}
```
That is essentially it for making and running caches. Then for 