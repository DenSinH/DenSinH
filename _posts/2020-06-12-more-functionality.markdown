---
layout: post
title:  "More functionality"
date:   2020-06-12 20:21:00 +0200
categories: GameBoy Advance, emulation
---

## Interrupt Requests
They seemed intimidating at first, but it was time to implement these. Interrupt Requests (IRQs) are controlled by a few different factors:
  - the CPSR `I` bit: If this bit is enabled, all IRQs are blocked
  - the IME (Interrupt Master Enable) IO register: If this has a value of 0 stored in it, all IRQs are disabled.
  - the IE (Interrupt Enable) register: This register determines what IRQs are enabled.
  - the IF (Interrupt Request Flags) register: This register keeps track of what IRQs are currently being requested.

To keep track of the interrupts, I made an `Interrupt` enum:

{% highlight csharp %}
[Flags]
public enum Interrupt : ushort
{
    LCDVBlank           = 0x0001,
    LCDHBlank           = 0x0002,
    LCDVCountMatch      = 0x0004,
    TimerOverflow       = 0x0008,

    // obtained by shifting:
    //Timer1Overflow    =*0x0010*,
    //Timer2Overflow    =*0x0020*,
    //Timer3Overflow    =*0x0040*,

    SerialCommunication = 0x0080,
    DMA                 = 0x0100,

    // obtained by shifting:
    //DMA1              =*0x0200*,
    //DMA2              =*0x0400*,
    //DMA3              =*0x0800*,

    Keypad              = 0x1000,
    GamePak             = 0x2000
}
{% endhighlight %}
this way, whenever I want to request an interrupt from somewhere in my emulator, I don't have to look up what the bitmask for it was. I implemented a `Request` method in my `IF` register class, where I would just "or" the `ushort` value of a given interrupt with the register's content.

Handling interrupts turned out to be simpler than I expected:
{% highlight csharp %}
private bool HandleIRQs()
{
    if ((this.mem.IORAM.IF.raw & this.mem.IORAM.IE.raw) != 0)
    {
        this.mem.IORAM.HALTCNT.Halt = false;

        if (this.mem.IORAM.IME.Enabled && (this.I == 0))
        {
            this.DoIRQ();
            return true;
        }
    }
    return false;
}
{% endhighlight %}

Some of this stuff is not important now, but most of it is. This method is ran before every single CPU instruction. It checks whether an IRQ is requested. If that is the case, then we can clear the HALTCNT register (this register can be set to wait for an interrupt). Then if the IME and the CPSR I bit are not preventing us from executing an IRQ, we actually do it
{% highlight csharp %}
private void DoIRQ()
{
    this.ChangeMode(Mode.IRQ);
    this.I = 1;

    this.mem.CurrentBIOSReadState = MEM.BIOSReadState.DuringIRQ;

    if (this.Pipeline.Count == 0) this.PC += (uint)((this.state == State.ARM) ? 4 : 2);

    // store address of instruction that did not get executed + 4
    // we check for IRQ before filling the pipeline, so we are 2 (in THUMB) or 4 (ARM) ahead
    LR = this.PC + (uint)((this.state == State.THUMB) ? 2 : 0);  // which is now LR_irq
    this.state = State.ARM;

    this.PC = IRQVector;
    this.PipelineFlush();
}
{% endhighlight %}
When handling an IRQ, only a few things happen: we change the mode to IRQ (and switch out banked registers as well). Because of the way I handle the pipeline in my CPU, we HAVE to make sure we are at the right offset relative to the next instruction that _would_ be executed. Then we store the return value (the address of the instruction that _would_ be executed, + 4, regardless of what state we are in) in LR, which after the mode change is the LR corresponding to the IRQ mode.

IRQs are always entered in ARM state. We jump the PC to the IRQ vector in memory (`0x18`), and we flush the pipeline, as we would when changing PC. We also set the `I` CPSR bit, because we don't want to get stuck jumping to the IRQ vector forever.

After this, the BIOS does some magic (jumps to a location in eWRAM where the ROM makers _should_ have stored an IRQ handler), and the ROM will handle the rest.

## Software Interrupts

Software Interrupts (SWIs) are similar to IRQs, except not really. SWIs are called by an SWI instruction. Both the THUMB and the ARM state have an instruction for this. Only a few bits are used to signify it is an SWI, and the rest is used to determine what type of SWI it is. This can be some arithmetic function (square root, arctan), or something else (IntrVBlankWait, which tells the CPU to wait until a VBlank interrupt happens). I handle my SWIs like this:
{% highlight csharp %}
private int SWIInstruction(uint Instruction)
{
    this.ChangeMode(Mode.Supervisor);
    this.I = 1;
    LR = this.PC - (uint)((this.state == State.THUMB) ? 2 : 4);  // which is now LR_svc
    this.state = State.ARM;

    this.PC = SWIVector;
    this.PipelineFlush();

    // Software interrupt instructions take 2S + 1N incremental cycles to execute
    return (SCycle << 1) + NCycle;
}
{% endhighlight %}
Basically, we do the same as for IRQs, except we switch to Supervisor mode instead of IRQ mode. We also know for sure that our pipeline is filled here, because we can only call this from within an instruction.
