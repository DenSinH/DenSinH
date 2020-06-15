---
layout: post
title:  "[INFO] Graphic Effects"
date:   2020-06-12 21:21:00 +0200
categories: GameBoy Advance, emulation
---
The GBA has many graphic capabilities. For game _and_ emulator development, [Tonc](https://www.coranac.com/tonc/text/) is a great resource for them. Some of the information on it can be a bit overwhelming though. It took me a while to get everything right, so I thought I would try and explain it in some more detail, at least for what I know of it.

## Mosaic Effects

One of the simplest graphic effects is the mosaic effect. What this effect does is"makes your sprites blocky". The effect is not used very often as far as I know, and some emulators such as No$GBA and mGBA do not implement the mosaic effects properly as of now. `mos_demo` from Tonc can be seen below:

<img src="{{site.baseurl}}/Images/GBA/GFX/mosaic.png">

Basically, the `MOSAIC` IO register holds value for the amount backgrounds and objects stretch in the X and Y direction. A pixel at the point `(x, y)` would get the same color as the pixel at the point `(x - (x % MosaicHStretch), y - (y % MosaicVStretch))`. Basically, you snap it to a grid spaced by `MosaicHStretch` in the X direction, and `MosaicVStretch` in the Y direction.

The way I handled this in rendering was by checking if Mosaic was enabled, and if it was, then I would calculate the `EffectiveY` as `scanline - (scanline % MosaicVStretch)`. If it was not enabled, `EffectiveY` would just be `scanline`. Where `scanline` is the y-coordinate of the current scanline we are rendering.

Within this scanline, I would only draw a new pixel if `x % MosaicHStretch == 0`, otherwise I would just copy the value from `x - (x % MosaicHStretch)` (`EffectiveX`). For affine objects/backgrounds you would transform the layer anyway, so you could just take the `EffectiveY` and `EffectiveX` as described in the transformation.

## Windowing

Windowing is a bit more advanced. What windowing does is it basically turns off all or a part of a background. The `DISPCNT` dictates if any of the windows are turned on or not. If none of the windows are turned on, everything is displayed as normal.

If at least one of the windows is turned on though, the screen gets "masked" by this window as to what pixels are turned on or not. The `WINxH` and `WINxV` registers contain the lower (inclusive) and upper (exclusive) coordinates for window `x`. Basically, any region between both upper and lower coordinates belongs to the `WININ` region, and any other area belongs to the `WINOUT` area. The corresponding registers (`WININ` and `WINOUT`) tell you whether a layer should be displayed in the corresponding region.

These values in `WINxH` and `WINxV` do wrap around. An example is seen below (screenshot of `win_demo` from Tonc):

<img src="{{site.baseurl}}/Images/GBA/GFX/windowing.png">

The way this demo works is as follows: both windows 0 and 1 are enabled. Window 1 (lowest priority) is a big static layer, and window 1 is a smaller layer that you can move around. The behind-most layer is enabled in WINOUT, it will be displayed everywhere. This is the layer with the checkered pattern. The layer on top of this is only enabled in WININ for window 1, but not in WININ for window 0. The way the layers are overlayed can be seen in this very clear picture from Tonc:

<img src="{{site.baseurl}}/Images/GBA/GFX/tonc_win_demo.png">

These layers are simple enough, but then there's the `OBJ` window. Objects have a GFX mode. If this mode is `0b10`, the object is not rendered normally, but is part of the object window. Any nontransparent pixel of the sprite is part of OBJWININ, and any part that is not is part of OBJWINOUT.

The way I handled this in my emulator was as follows: Before every scanline, I would fill a mask (`bool[width]`, where `width` is the width of the GBA screen) for every relevant layer (BG0-3 and OBJ, but only if they were being rendered). If no windows were enabled, I would just fill the whole thing with `true` and be done. Otherwise, I would fill it with `WindowOutEnable` for the layer I was currently making the mask for.

Then, because the OBJ window has the lowest priority, I would check that one first. I loop over OAM, and render any objects in GFX mode `0b10` into a special array holding their colors. If a color was not transparent, I would change the value in the window mask to `OBJWindowIn` (which might be the same as `WindowOutEnable`).

After this is done, I need to check window 0 and 1. Checking these is simple enough: I would just get the values for the coordinate bounds from the `WINxH` and `WINxV` registers, and generate the mask with this method:

{% highlight csharp %}
private void MaskWindow<T>(ref T[] Window, T WindowInEnable, byte X1, byte X2, byte Y1, byte Y2)
{
    if (Y1 <= Y2)
    {
        // no vert wrap and out of bounds: return
        if (scanline < Y1 || scanline > Y2) return;
    }
    else
    {
        // vert wrap and "in bounds": return
        if ((scanline < Y1) && (scanline > Y2)) return;
    }

    if (X1 <= X2)
    {
        // no hor wrap
        // slice in WININ
        for (int x = X1; x < X2; x++)
        {
            Window[x] = WindowInEnable;
        }
    }
    else
    {
        // slices in WININ
        for (int x = 0; x < X2; x++)     Window[x] = WindowInEnable;
        for (int x = X1; x < width; x++) Window[x] = WindowInEnable;
    }
}
{% endhighlight %}

After this, whenever I would try to render a pixel into one of my layers' scanline arrays, I would only allow it to render a pixel if `Window[x]` was `true` for that layer.

## Alpha Blending

 
