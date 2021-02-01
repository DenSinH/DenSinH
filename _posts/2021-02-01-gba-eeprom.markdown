---
layout: post
title:  "[GBA] EEPROM Save Type"
date:   2021-02-01 13:00:00 +0200
categories: emulation
author: DenSinH
---

# EEPROM Save Type

The GBA has games with different sorts of backup memory. There are 3 types:
  - SRAM, straightforward RAM on the cartridge
  - Flash, flash storage on the cartridge (explained [here](https://dillonbeliveau.com/2020/06/05/GBA-FLASH.html))
  - EEPROM, which I will attempt to explain in this document.

You can see what save type a cartridge uses most accurately by using a game database. If you don't have one of those available, you can check for certain strings in the cartridge (also explained [here](https://dillonbeliveau.com/2020/06/05/GBA-FLASH.html)).

[GBATek](http://problemkaputt.de/gbatek.htm#gbacartbackupeeprom) also explains the EEPROM save type, but I found it quite brief, so I will try to add on to this documentation.

### EEPROM types

There are 2 different types of EEPROM cartridges:
  - 512 bytes / 4Kbit EEPROM
  - 8KB / 64Kbit EEPROM

Which of these 2 a cartridge has is impossible to figure out just by looking at the cartridge. Your only options are a game database, or a trick where you check the first access made to it, which I will explain later.

### Addressing and waitstates

> The eeprom is connected to Bit0 of the data bus, and to the upper 1 bit (or upper 17 bits in case of large 32MB ROM) of the cartridge ROM address bus, communication with the chip takes place serially. (GBATek)

This means that data transferred to or from the EEPROM chip is always 1 bit at a time. Any transfer made to EEPROM will be "masked" to only the bottom bit, and any read will just be 1 or 0.

On a large ROM (of greater than 16MB in size), ROM is restricted to `0800'0000h-09ff'feffh`. So, EEPROM can be accessed between `09ff'ff00` and `09ff'ffff`. This is also mirrored to the higher waitstate cartridge regions. Judging from the source code of certain emulators, it can really onlly be accessed in the `0x0dxx'xxxx` region of ROM, despite what GBATek says. On smaller ROMs, it can also be accessed between `0d00'0000h-0dff'ffffh.`

The actual address that is accessed for the EEPROM access does not matter, as the "internal address" has to be sent first, and then data can be written or read.

Data can be read or written. The initial pattern for the access is similar: the mode has to be sent, and the address as well.

This is also where the different EEPROM sizes come into play. The EEPROM can only transfer data in units of 64 bits. Addressing also works in units of 64 bits. This means, that while for a 512 byte EEPROM, you have 0x200 bytes to address, there are only 0x40 blocks of 64 bits. The address will only be in the range of `0 - 0x3f`. The bus width for a 512 byte EEPROM is 6, and the address that will be sent will also be 6 bits long.

For an 8KB EEPROM, there are 0x2000 bytes, but only 0x400 blocks of 64 bits. The address will thus only be in the range `0 - 0x3ff`. The bus width for a 8KB EEPROM is 14 bits, but the address only 10. The address that gets sent will be 14 bits long, but the first 4 bits should be zero, as they don't correspond with any blocks.

It is important to actually have the addressing happen in blocks of 8 bytes / 64 bits. I did this wrong in my emulator at first, and it caused some sneaky corrupted saves.

### Reading data

When you want to read data from the EEPROM, you have to send the following sequence of bits:
```
2 bits "11" (Read Request)
n bits eeprom address (MSB first, 6 or 14 bits, depending on EEPROM)
1 bit "0"
(GBATek)
```

#### EEPROM size detection
This `n` is what you can deduce the EEPROM size from. A trick to detect the EEPROM size is to keep it ambiguous until the first (read) request is made. Requests have to be done by DMA, since normal transfers via LDRH/STRH are too slow, and don't keep the right bits set during the transfer.

Since DMA channel 3 is the only DMA channel that can access ROM, you could, on the first (read) access, check the transfer length of DMA channel 3. If it's of length 9, a 6 bit address will be sent, and the EEPROM is (likely) a 512 byte EEPROM. If it's of length 17, a 14 bit address will be sent, and the EEPROM is (likely) an 8KB EEPROM.

This method is not perfect though. Some games, like the NES classic series, try to trick you into thinking it's the wrong EEPROM size, by doing a transfer of the "wrong" length. Your best bet will be a game database, or some sort of hybrid approach.

#### The transfer

Since it's annoying to have to place individual bits at a (half)word interval in memory to then transfer data, a common approach for games/programs is to "shift" them into memory. Basically, if I wanted to send a read request to an 8KB EEPROM to block `0x123`, I would need to transfer: `(0b11 << 15) | (0x123 << 1) | 0 = 0x18246`. Suppose `r1` holds a pointer to a the end of a 17 halfword buffer where we want to store our bits, and `r0` holds `0x18246`. One could simply do
```ARMASM
strh r0, [r1], #-2
lsr r0, #1
```
17 times, and the buffer will then be filled with
```
0x0001
...
0x3048
0x6091
0xc123
0x8246
```
such that the 0th bit of each halfword exactly reads out `0x18246` (MSB first). I can then transfer this buffer to EEPROM. Since only bit 0 is connected to the data bus, it does not matter that there is other data in the other 15 bits of each halfword.

This is how the address is transferred for a read access. After the address is transferred, we can read back the data. This again has to happen by DMA. There are 68 bytes to be read back with DMA:
```
4 bits  - ignore these
64 bits - data (conventionally MSB first)
(GBATek)
```
These accesses have to be made in the same region as the address has to be written to, but just read instead of written. After this, it is up to the game how it handles the individual bits returned by the DMA.

### Writing data

The written data immediately follows the address that is written. I have never encountered a game doing a write access before a read access, but it's possible, so it might be good to check if this is the case when trying to detect the EEPROM's size.

The data that has to be written is:
```
2 bits "10" (Write Request)
n bits eeprom address (MSB first, 6 or 14 bits, depending on EEPROM)
64 bits data (conventionally MSB first)
1 bit "0"
(GBATek)
```
So the start is similar to the read request, except a different "code". Then the address, again different sizes depending on the EEPROM's size. Then 64 bits / 8 bytes of data, and one bit to end the transfer.

These transfers might also be made in a similar way to the read access, where the data is first "shifted" to a buffer, and then transferred by DMA.

After a write transfer, games likely check if the transfer is complete. They do this by reading from the EEPROM and waiting until it returns 1. Martin Korth describes in GBATek how it's important to set a timeout if the EEPROM does not respond, but some games might just hang if you don't return 1 on reads after a write access.
