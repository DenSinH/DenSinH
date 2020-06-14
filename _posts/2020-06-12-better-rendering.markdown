---
layout: post
title:  "Better Rendering"
date:   2020-06-12 21:21:00 +0200
categories: GameBoy Advance, emulation
---

## Tiled modes

Bitmaps take up a lot of memory space, so it is a lot more efficient to draw things using tiles. Most games use tiled rendering modes (0 - 2) to get stuff on screen. To do this, games store tile IDs and other information to VRAM, in sections commonly known as "Screenblocks", and tile data to sections commonly known as "Character blocks", or charblocks.

Rendering in tile modes can be either regular or affine. Regular means you take the sprite from the charblock, and you blit it to the screen in a certain location. Affine means the sprite might be rotated and/or scaled by a certain amount. The amount it is rotated/scaled is set in some IO registers. The top left corner of the screen is also stored in some IO registers (which are only used for regular layers).

You can read most this stuff on [Tonc](https://www.coranac.com/tonc/text/). I handle my rendering on a per scanline basis, and I do it as follows: I have a `ushort[]` for every background layer. I reset only the relevant ones every scanline. Then I draw each background into the scanline, and when those are all done, I combine them all into the screen.

#### Regular Background layers
For these I get all the data I need from IO registers: `VOFS`, `HOFS`, the base charblock and base screenblock (because there are multiple of those). With these values, I determine what value I should read from VRAM for each tile. I do not render each pixel individually, but I render a sliver of a tile at a time. This is because no rotation or scaling is applied in these layers, and the Tile ID and most other data is the same for every pixel in the sliver. After determining this, I draw the sliver. This can be either an 8bpp or a 4bpp sliver, meaning it either contains a direct color (8bpp) or a palette entry (4bpp).

For a 4bpp sliver I do this (there are some graphic effects that are not shown)
{% highlight csharp %}
for (int dx = 0; dx < 4; dx++)  // we need to look at nibbles here
{
    for (int ddx = 0; ddx < 2; ddx++)
    {
        VRAMEntry = this.gba.mem.VRAM[TileLineBaseAddress + dx];

        if (0 <= ScreenX && ScreenX < width)
        {
            if (Line[ScreenX] == 0x8000)
            {
                PaletteNibble = (byte)(UpperNibble ? ((VRAMEntry & 0xf0) >> 4) : (VRAMEntry & 0x0f));
                if (PaletteNibble > 0)  // non-transparent
                    Line[ScreenX] = this.GetPaletteEntry(PaletteBase + (uint)(2 * PaletteNibble));
            }
        }
        ScreenX += XSign;
    }
}
{% endhighlight %}
Basically, I only draw if the current pixel in the scanline is transparent (`0x8000`). I get the palette entry from VRAM based on the TileID that was provided. I get the appropriate nibble from it, with no graphic effects that would be first the lower nibble, then the upper nibble. Then I determine if the pixel is not transparent, and I draw it if it isn't.

8bpp slivers are a bit simpler, they are handled like this:
{% highlight csharp %}
for (int dx = 0; dx < 8; dx++)
{
    if (0 <= ScreenX && ScreenX < width)
    {
        if (Line[ScreenX] == 0x8000)
        {
            VRAMEntry = this.gba.mem.VRAM[TileLineBaseAddress + dx];
            if (VRAMEntry != 0)
                Line[ScreenX] = this.GetPaletteEntry(PaletteOffset + 2 * (uint)VRAMEntry);
        }
    }

    ScreenX += XSign;
}
{% endhighlight %}
I basically do the same, except the color is determined in a different way.

#### Regular objects
The nice part about regular objects is that the sprite data is stored in a very similar way. Basically what I did for regular backgrounds, I can also do for regular objects, except in an object layer! Objects may have 4 priorities as well, even though there is only one layer (though different background layers may have the same priority). To handle this, I also have 4 `ushort[]`s to store all objects for the current scanline.

I loop over OAM, and for each object I find, I draw it into the `ushort[]` corresponding to its priority. Because the sprites are stored in basically the same way, just at a different location in memory, I call the exact same function when rendering regular objects, as when rendering regular backgrounds, except with a different `Line` parameter!

#### Affine Background layers
These I do have to draw per pixel
