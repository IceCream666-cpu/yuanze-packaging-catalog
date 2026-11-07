"""Typeset the reference-led Blender product render into the established 2:3 series."""
from pathlib import Path
import argparse, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parent
W,H=2048,3072
INK=(25,40,26)

def font(name,size,index=0):
    return ImageFont.truetype('/System/Library/Fonts/'+name,size,index=index)

def tracked(draw,xy,text,face,spacing,fill):
    x,y=xy
    for ch in text:
        draw.text((x,y),ch,font=face,fill=fill,anchor='lt')
        x+=draw.textlength(ch,font=face)+spacing
    return x-xy[0]-spacing

def background():
    y,x=np.mgrid[0:H,0:W].astype(np.float32)
    light=np.exp(-((x-190)**2/(2200**2)+(y-750)**2/(2100**2)))
    color=np.zeros((H,W,3),dtype=np.float32)
    for i,(base,delta) in enumerate(zip((217,222,207),(21,18,24))):color[:,:,i]=base+delta*light
    # Broad, defocused window shadows create depth without competing with the label.
    bands=Image.new('L',(W,H),0);d=ImageDraw.Draw(bands)
    d.polygon([(1260,-200),(1440,-200),(2248,1200),(2248,1450)],fill=26)
    d.polygon([(1950,-200),(2248,-200),(2248,350)],fill=22)
    d.polygon([(-200,1940),(-200,2040),(2248,2810),(2248,2670)],fill=12)
    shade=np.asarray(bands.filter(ImageFilter.GaussianBlur(62)),dtype=np.float32)
    color-=shade[:,:,None]
    grain=np.random.default_rng(83).normal(0,.42,(H,W,1))
    return Image.fromarray(np.uint8(np.clip(color+grain,0,255)),'RGB').convert('RGBA')

def main():
    p=argparse.ArgumentParser();p.add_argument('--product');p.add_argument('--output',default='Matcha-Shampoo-海报-v1.png');a=p.parse_args()
    im=background();d=ImageDraw.Draw(im)
    brand=font('Supplemental/Arial Black.ttf',140)
    d.text((126,90),'liaose',font=brand,fill=INK,anchor='lt')
    tracked(d,(138,270),'HAIR CARE',font('HelveticaNeue.ttc',31),16,INK)
    title=font('Supplemental/Didot.ttc',245)
    d.text((124,402),'Matcha',font=title,fill=INK,anchor='lt')
    d.text((124,642),'Shampoo',font=title,fill=INK,anchor='lt')
    if a.product:
        product=Image.open(a.product).convert('RGBA')
        box=product.getchannel('A').getbbox();assert box
        product=product.crop(box)
        scale=min(1610/product.width,1815/product.height)
        product=product.resize((round(product.width*scale),round(product.height*scale)),Image.Resampling.LANCZOS)
        x=round((W-product.width)/2+115);y=H-270-product.height
        assert x>=75 and x+product.width<=W-75
        assert y>950 and y+product.height<=H-250
        # A separate contact shadow avoids rectangular shadow-catcher crop edges.
        shadow=Image.new('RGBA',(W,H),(0,0,0,0));sd=ImageDraw.Draw(shadow)
        foot=y+product.height-15
        sd.ellipse((x+product.width*.04,foot-90,x+product.width*1.04,foot+50),fill=(39,52,32,48))
        shadow=shadow.filter(ImageFilter.GaussianBlur(35));im.alpha_composite(shadow)
        contact=Image.new('RGBA',(W,H),(0,0,0,0));cd=ImageDraw.Draw(contact)
        cd.ellipse((x+product.width*.27,foot-17,x+product.width*.79,foot+20),fill=(27,42,23,74))
        im.alpha_composite(contact.filter(ImageFilter.GaussianBlur(11)))
        im.alpha_composite(product,(x,y))
    d=ImageDraw.Draw(im)
    footer='FORMULA + PACKAGING + MANUFACTURING'
    face=font('HelveticaNeue.ttc',25)
    spacing=7
    tw=sum(d.textlength(c,font=face) for c in footer)+(len(footer)-1)*spacing
    tracked(d,((W-tw)/2,H-140),footer,face,spacing,INK)
    target=ROOT/a.output
    im.convert('RGB').save(target,dpi=(300,300))
    im.convert('RGB').resize((1024,1536),Image.Resampling.LANCZOS).save(ROOT/'poster-preview.jpg',quality=95)
    print(target)

if __name__=='__main__':main()
