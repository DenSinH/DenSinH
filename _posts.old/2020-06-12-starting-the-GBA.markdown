---
layout: post
title:  "[BLOG] Starting the GBA"
date:   2020-06-12 17:21:00 +0200
categories: GameBoy Advance, emulation
---

Then I started working on my next project, a GameBoy Advance (GBA) emulator! This promised to be even more of a challenge. There was less documentation (not an entire Wiki full of it!) and a lot more to it.

First things first: the CPU implementation. There were 2 main sources I used for this: the [ARM7TDMI Data Sheet]({{site.baseurl}}/Docs/ARM7TDMI.pdf) and [GBATek](https://problemkaputt.de/gbatek.htm). The data sheet proved very useful in the beginning: it explained most instructions in detail, even provided instruction timings (something for later), and was in general very clear. GBATek was also very useful, but I found this to be more useful for describing edge cases (what happens when you use R15 in a STM/LDM instruction etc.).

The manual started off describing interrupts, which in my opinion is quite strange. I got a bit scared, because interrupts were something I never got quite right in the NES. After this though, it started with the actual structure of the CPU.

First of all, some stuff that is something that isn't ARM7TDMI specific: all CPUs (that I know of) have some form of storing some information about the previous arithmetic operation that happened. In the GBA, this register is called the Current Program Status Register (CPSR). In this register, not all bits are used in the ARM7TDMI (some of them might be used in later processors with the same architecture, the ARM7TDMI uses the ARMv4t, little endian architecture). The top 4 bits are very important. They serve as the bits that store the information on the last arithmetic operation:

| Flag | Meaning |
|------|---------|
| N(egatve)    | Result of last operation was negative (bit 31 was set) |
| Z(ero)       | Result of last operation was zero (all bits 0) |
| C(arry)      | The last operation produced carry (E.g. `0xffff_ffff + 0x1`) |
| (o)V(erflow) | The last operation produced overflow, meaning that the sign of the result is not the sign you would expect (E.g. `0x7fff_ffff + 0x1`, where both operands are positive, but the result is negative)

The ARM7TDMI can operate in 2 different states: ARM and THUMB. In the ARM state, the CPU uses 32 bit instructions, and in the THUMB state it uses 16 bit instructions. States can be switched between using a BX (branch and exchange) instruction. In the ARM state, every instruction has a condition code in the first 4 bits. The condition code uses the 4 bits described above to determine whether the instruction gets executed or not. An example is `Z is set`, or `Z is clear AND (N equals V)` (I actually messed this last one up, causing me some problems...). In THUMB mode (almost) every instruction gets executed unconditionally.

The instructions get read before they are executed, using a 3-stage pipeline. In the actual GBA, three things happen at the same time, every instruction:
 - an instruction is "prefetched" (it is read from memory, put into the pipeline, and the PC is incremeted by either 2 (THUMB) or 4 (ARM) bytes)
 - an instruction is decoded (this happens to the one that was prefetched the instruction before the one we are executing)
 - an instruction is executed

when emulating the pipeline, we don't "decode" the instruction in the meanwhile, we just do that when the instruction is actually happening. We do however prefetch instructions, and keep them in some sort of pipeline. First I just used a `Queue<uint>` for this, but since I only need to store at most 2 instructions in it at a time, I implemented my own class for the pipeline, basically equivalent to the `Queue<uint>`, but I can always add functionality to it this way, and it turned out to be faster!

The pipeline can also be "flushed". This happens whenever the value of PC is changed by an instruction (whether that be a branch, or a store to it with some form of data processing (basic arithmetic operations)). When the pipeline is flushed, it simply means that all instructions contained in it are removed, so basically `Pipeline.Clear()` if I were to use a `Queue<uint>`.

There are some other important bits in the CPSR: the bottom 8. Bit 7 is the `I` bit, or the IRQ disable bit. Setting this bit makes it so no interrupts can be thrown. The `F` bit is the FIQ disable bit. However, since the GBA uses an adapted variant of the ARM7TDMI, this bit is not important, as FIQs cannot be thrown normally. We will just ignore this bit. Then there is the `T` bit, or the state bit. This bit signifies if we are in THUMB (1) or ARM (0) state.

The bottom 5 bits are called the "mode bits". They represent what operating mode we are in. There exist 7 valid modes for the ARM7TDMI, however only 4 are relevant: User/System (so 2 modes) are really just the normal modes of operation. IRQ mode signifies that we are handling an IRQ, we enter this mode when an interrupt is acknowledged. Supervisor mode is entered when we do an SWI. An SWI jumps the program counter (PC) into the BIOS, and executes a function there (such as `SQRT`, or `ARCTAN`, but also something like waiting for a certain interrupt to happen). Any other combination of mode bits is invalid, and will never occur (if you emulate it correctly).

I implemented my CPSR much in the same way I did for my NES:

{% highlight csharp %}
private uint CPSR
        {
            get => (SR_RESERVED << 8) | (uint)(
                    (N << 31) |
                    (Z << 30) |
                    (C << 29) |
                    (V << 28) |
                    (I << 7) |
                    (F << 6) |
                    ((int)(this.state) << 5) |
                    (byte)this.mode
                    );
            set
            {
              ...
{% endhighlight %}
and something similar for `set`.

The ARM7TDMI has 16 general use 32 bit registers. They are called general use, but register 15 (R15) is the PC, so storing values in this for arithmetic will not work, and R14 is usually used as link register (LR), storing a value to return to after we execute a function of some sort. R13 is used as the stack pointer (SP). Some of these can be banked (so swapped out for other ones) depending on what mode we are in. When we are in User/System mode, we use the "normal" registers. The only modes that are relevant for the GBA only bank registers 13 and 14.

In ARM mode, we can see all 16 non-banked registers, and in THUMB mode we can generally only see the lowest 8. However, in some THUMB instructions, the LR or the SP can be used, and in the "Hi register operations" instruction, values can be read or written to registers R8-R15.

There are 5 more registers, one for each mode other than User/System (so only 2 are relevant): the SPSR. This stands for Special Program Status Register. Whenever a mode change happens, the value of the CPSR is copied into this register, so that when we return from, say, an interrupt, we can just resume as normal.

After all of this was implemented, it was time to start working on the instructions. All of these are explained very well in GBATek and the manual, so I will not describe those in detail. Something that is good to know, is that the Undefined instruction, and every Coprocessor related instruction does NOT apply to the GBA. The GBA does not use these instructions, and Undefined mode is invalid, so the Undefined instruction would not make much sense.

Decoding these instructions I did in a way different (and better) way than the NES. What I did was make a lookup table (LUT) of all the instructions. What type of instruction you use is determined only by a subset of the bits in the instruction, the rest are simply parameters. For ARM instructions, the mode is determined by 12 bits: bits 27-20 and bits 7-4. For THUMB you only need the top 6 bits. What I did was create a `delegate` type for my instructions, which for ARM was

{% highlight csharp %}
private delegate int ARMInstruction(uint Instruction);
private ARMInstruction[] ARMInstructions = new ARMInstruction[0x1000];  // 12 bits determine the instruction
{% endhighlight %}

and then before the CPU started running, I initialized this table to the correct instructions:

{% highlight csharp %}
private void InitARM()
{
    for (uint Instruction = 0; Instruction < 0x1000; Instruction++)
    {
        // Bits 27-20 and 7-4 of an instruction
        switch ((Instruction & 0xc00) >> 10)
        {
            case 0b00:
                // Data Processing / Multiply / Multiply Long / Single Data Swap / Branch & Exchange / Halfword Data Transfer
                if ((Instruction & 0xfcf) == 0x009)
                {
                    // Multiply
                    this.ARMInstructions[Instruction] = this.Multiply;
                }
                else if ((Instruction & 0xf8f) == 0x089)
                {
                    // Multiply Long
                    this.ARMInstructions[Instruction] = this.MultiplyLong;
                }
                else if ((Instruction & 0xfbf) == 0x109)
                ...
{% endhighlight %}
This allows for quick access to the type of instruction we want to execute.

When testing your emulator in the beginning, it might be nice to compare it to existing emulators (such as [mGBA](https://mgba.io/), or [No$GBA](https://www.nogba.com/)). Both of these have a way to produce logs, so you could implement something like it for your own, and compare it to the logs produced by these 2 (pretty accurate) emulators.

Some good roms to start testing with are [armwrestler](https://github.com/destoer/armwrestler-gba-fixed), to test the very basics of your CPU. (The one I linked to here is NOT the original upload, but an adapted one that fixed some of the tests, and removed the "ARMv5t" test, which could confuse a lot of people, as it tests things that are not possible on the GBA). Once that is going, it could be nice to use [GBASuite](https://github.com/jsmolka/gba-suite). These ROMs test more edge-case scenario's, but the ROMs won't crash (in general) if you pass armwrestler.
