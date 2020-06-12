---
layout: post
title:  "Introduction to Emulation"
date:   2020-06-12 12:34:51 +0200
categories: introduction, emulation
---

About a year ago, all I knew from emulation was from when I had used them on my phone to play GameBoy games. About 2 months ago that changed. I came home from my exchange in Canada, and was a bit bored after watching Netflix and playing games for a week. I had been pretty busy coding in Canada, but I was starting to feel the urge again.

I started working on some fruitless projects, until I came along a [video](https://www.youtube.com/watch?v=cjDwPCWm6-w&t=478s) by Kalle Halden on YouTube, about how he made a space invaders emulator.

This looked like something fun to do, so without really watching the video much further I started on the emulation project anyone should start at: a [CHIP-8 emulator](https://github.com/DenSinH/chip8). It wasn't too much work, after one afternoon I had most the stuff done, and the day after I sort of finished it. By then I mostly only used Python, as it is the language I first learnt, and I really liked it. I knew a bit of Java and some C#, but I didn't want to bother.

A CHIP-8 system is nothing crazy, it isn't super fast, so Python being interpreted wasn't much of a problem. After this project though, I started to look into other stuff I could work on. I decided to work on an NES emulator. After looking at some of the docs for the CPU opcodes I started working on it. This was considerably more difficult. There were a lot more things to take into account. Some instructions were a lot more complicated, there was cycle accuracy (which I didn't take into account at all when making my CHIP-8 emulator).

This made the project so much more fun though! Seeing it progress and things working after much effort was great! First thing to do was getting through the nestest.log file found [here](http://www.qmtpro.com/~nes/misc/). This took quite some effort already. When I was done with this, I decided to try and see how fast my (then only MOS6502) emulator could handle it. Mind you, it was still written in Python (here come the people saying it is possible...). I found that my CPU would be about 20 times too slow. Doing some optimizations and compiling it with Cython sped it up quite a bit, to about 1/10th of the speed of the actual MOS6502.

I decided I had to switch languages. First of all I tried Java, but that was quite annoying, as the builtin `byte` type is signed... I decided to translate the whole thing over to C# as well (which by then didn't take all too much effort, because the syntax is pretty similar to Java I found). After figuring out you can turn off Debug mode in VS, I decided that was the way to go.

I figured out how to get stuff on the screen (in Python I would just use PyGame, which is really easy to use). I did this by writing the colors to an `int[]` of the correct dimensions, to then turn in into a `BitMap` 60 times per second and blit it to a Windows Form. Now that this was in place, it was time to actually get something on the screen. This was also way, way more difficult then the CHIP-8 emulator. Instead of 2 colors you have 64, and there are a lot more intricacies in the NES' PPU.

Fortunately there was the [NesDev Wiki](http://wiki.nesdev.com/w/index.php/Nesdev_Wiki). Along with some help from others (thank you Dillon!), I got some stuff working, and I got the first thing on the screen (of course, nestest!)

<img src="{{site.baseurl}}/Images/NES/nestest_faillure.png">

Of course, stuff wasn't correct right away, the colors were all off, and the selector was in the middle of the text (`~~ Run all**ests`). After more testing, coding and finding stupid mistakes, I got the actual thing running:

<img src="{{site.baseurl}}/Images/NES/nestest.png">

Of course, my MOS6502 implementation ran though the log just fine, so the results of the tests weren't surprising. Now all that was left was completing the PPU implementation, adding every other feature there was, and even audio! After adding in some of the more specific behavior of the NES, I was able to run even some of the more [Tricky-to-emulate games](https://wiki.nesdev.com/w/index.php/Tricky-to-emulate_games)!

<img src="{{site.baseurl}}/Images/NES/smbworking.png">

After I got this running, all that was left was adding in more mappers. My NES emulator seemed to be getting to its final stages. Of course, it is nowhere near perfect, but I didn't really want to add in perfect cycle accuracy or anything. I had learnt a lot, and loved this project!
