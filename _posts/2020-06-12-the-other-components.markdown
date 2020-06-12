---
layout: post
title:  "The other components"
date:   2020-06-12 17:21:00 +0200
categories: GameBoy Advance, emulation
---

## Memory
Okay, so now we have our ARM7TDMI being emulated, it is time to get the other components running. First of all, something we actually need to run the ARM7TDMI as well: the memory. The GBA has 9 sections of memory, some mirrored, some are not. These sections are (adapted from GBATek):

|General Internal Memory| Section   | Remark  |
| ----------------------|---|---|
  `00000000-00003FFF`   |BIOS - System ROM|         (16 KBytes), read only
  `00004000-01FFFFFF`   |Not used|
  `02000000-0203FFFF`   |WRAM - On-board Work RAM|  (256 KBytes) 2 Wait
  `02040000-02FFFFFF`   |Not used|  eWRAM mirrors
  `03000000-03007FFF`   |WRAM - On-chip Work RAM|   (32 KBytes)
  `03008000-03FFFFFF`   |Not used| iWRAM mirrors
  `04000000-040003FE`   |I/O Registers|
  `04000400-04FFFFFF`   |Not used|
|Internal Display Memory| | |
  `05000000-050003FF`   |BG/OBJ Palette RAM|        (1 Kbyte)
  `05000400-05FFFFFF`   |Not used| PAL mirrors
  `06000000-06017FFF`   |VRAM - Video RAM|          (96 KBytes)
  `06018000-06FFFFFF`   |Not used| VRAM mirrors
  `07000000-070003FF`   |OAM - OBJ Attributes|      (1 Kbyte)
  `07000400-07FFFFFF`   |Not used| OAM mirrors
|External Memory (Game Pak)||
  `08000000-09FFFFFF`   |Game Pak ROM/FlashROM (max 32MB)| Wait State 0, read only
  `0A000000-0BFFFFFF`   |Game Pak ROM/FlashROM (max 32MB)| Wait State 1, read only
  `0C000000-0DFFFFFF`   |Game Pak ROM/FlashROM (max 32MB)| Wait State 2, read only
  `0E000000-0E00FFFF`   |Game Pak SRAM    (max 64 KBytes)| 8bit Bus width
  `0E010000-0FFFFFFF`   |Not used | SRAM mirrors
|Unused Memory Area|||
  `10000000-FFFFFFFF`  | Not used |upper 4bits of address bus unused|

GBATek describes some sections as "not used". A part of these sections contain mirrors for the section above it. For example, accessing `0x0204_0000` would be the same as accessing `0x0200_0000`. Some of these sections are actually not used, like the section after the BIOS. Reading from such sections yields usually unwanted (for ROM makers), but not unpredictable behavior. This is something that is hard to emulate, and is not _properly_ implemented in many of the currently available emulators.

When I started out making the memory, I simply made 9 `byte[]`s of the appropriate sizes, and 6 access functions (get/set) (word/half word/byte). A word is a 32 bit value, a half word is a 16 bit value, and a byte is, well, a byte. For starters, this was good enough. Some sections are mirrored a bit differently than others, but other than that is was fine.

## Picture Processing Unit
The other vital component of the GBA is the Picture Processing Unit (PPU). It handles everything related to getting pixels on the screen. A source that is really useful for developing this part of the GBA is [Tonc](https://www.coranac.com/tonc/text/). Tonc is a site made for GBA development, but it describes the way it renders things on the screen extremely well.

The first thing to do is implementing one of the 6 rendering modes. 3 Of these are bitmap modes, and are relatively easy to implement. Mode 5 is barely documented anywhere, and is not used in games as far as I know. The modes to focus on at this point are modes 3 and 4.

The GBA has a few layers that can be outputted to, background layers and a sprite layer. There are 4 layers to the background, each can have a priority value of 0-3 (0 is the highest). When considering bitmap modes, only background 2 (BG2) is used. For now we also do not need to worry about objects, for the ROMs we will be running at the beginning will just use these bitmap modes, and no objects whatsoever.

In bitmap modes, palette entry used per pixel are written to VRAM. You would simply read a halfword from VRAM and get a halfword from PAL based on that address. To get started, the code for mode 4 would look something like this:

{% highlight csharp %}
ushort offset = (ushort)(this.gba.mem.IORAM.DISPCNT.IsSet(DISPCNTFlags.DPFrameSelect) ? 0xa000 : 0);

if (this.gba.mem.IORAM.DISPCNT.DisplayBG(2))
{
    for (int x = 0; x < width; x++)
    {
        this.Display[width * scanline + x] = this.GetPaletteEntry((uint)this.gba.mem.VRAM[offset + width * scanline + x] << 1);
    }
}
else
{
    for (int x = 0; x < width; x++)
    {
        this.Display[width * scanline + x] = 0;
    }
}
{% endhighlight %}

Of course, this is not all that there is to it, but it's good enough for now. For every pixel on the screen, you read a value from VRAM and get a corresponding palette entry to put on the display.

There are still some things in here that I didn't describe, and they are the IO registers. One section of memory is very special: the IORAM. Instead of normal bytes, it holds registers. Each register corresponds to something different. The ones that are most important as of now are DISPSTAT and DISPCNT. They control the DISPlay.

## IO Registers
Because every IO register does something different, I had to come up with a way to implement them. What I decided to do was make an `IORegister` interface, and make a separate class for every IO register, so that each may have it's own functionality, but we can always call a write and a read function. The interface looked like this:

{% highlight csharp %}
public interface IORegister
{
    ushort Get();
    void Set(ushort value, bool setlow, bool sethigh);
}
{% endhighlight %}

All registers (except 2) are either 16 or 32 bit. What I decided to do was make an array of 16 bit registers, and make another wrapper for 32 bit (4 byte) registers. In the end, almost every register inherits from an `abstract` class `IORegister2`, which implements the most basic version of reading and writing:

{% highlight csharp %}
public abstract class IORegister2 : IORegister
{
    protected ushort _raw;

    public virtual ushort Get()
    {
        return this._raw;
    }

    public virtual void Set(ushort value, bool setlow, bool sethigh)
    {
        if (setlow)
            this._raw = (ushort)((this._raw & 0xff00) | (value & 0x00ff));
        if (sethigh)
            this._raw = (ushort)((this._raw & 0x00ff) | (value & 0xff00));
    }
}
{% endhighlight %}

the `setlow` and `sethigh` bools must be used because it is possible that only half of the register gets written to. I also added a `ZeroRegister` class, which does nothing when you write to it, and returns 0 on reads. A `UnusedRegister` class, a 32 bit register that returns "open bus" when read, and does nothing on writes. And finally, a `DefaultRegister` class. This one is just for while I am developing my emulator. I do not have all registers implemented yet, so they are basically placeholders. They are essentially the same as the `IORegister2` class, except not abstract.
