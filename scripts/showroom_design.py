"""Generate branded cursor showroom graphics without altering cursor artwork."""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BRAND='New ValenAero Arrow'
def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),size)
def colors(dark):return ('#171a20','#f7f6f1','#b1b5bd','#fa9259') if dark else ('#f2f1ed','#20232a','#73767d','#cf642b')
def background(w,h,dark):
    bg,fg,muted,accent=colors(dark)
    y,x=np.mgrid[0:h,0:w].astype(float)
    a=x/w;b=y/h
    field=np.sin(a*9+b*4)+.52*np.cos(a*15-b*6)+.28*np.sin(b*19+a*5)
    ripple=(.5+.5*np.cos(field*5.2))**10
    shade=(np.sin(a*3-b*2)+1)*.5
    rgb=np.array(tuple(bytes.fromhex(bg[1:])),dtype=float)
    amount=(ripple*2.7+shade*2.8)*(1 if dark else -1)
    arr=np.clip(rgb[None,None,:]+amount[:,:,None],0,255).astype(np.uint8)
    im=Image.fromarray(arr,'RGB').convert('RGBA')
    ImageDraw.Draw(im).rounded_rectangle((2,2,w-3,h-3),radius=30,outline='#343840' if dark else '#dbdad5',width=3)
    return im
def text_center(d,xy,text,f,fill):
    d.text((xy[0]-d.textlength(text,font=f)/2,xy[1]),text,font=f,fill=fill)
def wrap(text,f,width):
    lines=['']
    for word in text.split():
        candidate=(lines[-1]+' '+word).strip()
        if f.getlength(candidate)>width:lines.append(word)
        else:lines[-1]=candidate
    return lines
def glyph(canvas,im,center,size,angle=0):
    pic=im.resize((size,size),Image.Resampling.LANCZOS)
    if angle:pic=pic.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
    canvas.alpha_composite(pic,(round(center[0]-pic.width/2),round(center[1]-pic.height/2)))
def label(role,lang):
    label=role[1 if lang=='es' else 2]
    return label.replace('Apple','Clásica' if lang=='es' else 'Classic').replace('propia','reflejada').replace('Custom','Mirrored')

def render_showroom(out,previews,roles):
 for lang in ['es','en']:
  for dark in [False,True]:
    mode='dark' if dark else 'light';bg,fg,muted,accent=colors(dark)
    # Hero: typographic left half, floating cursor composition on the right.
    hero=background(1600,900,dark);d=ImageDraw.Draw(hero)
    d.rounded_rectangle((82,79,218,119),radius=12,fill='#263749' if dark else '#dbe8ef')
    d.text((99,84),'WINDOWS 11',font=font(19,True),fill=fg)
    d.text((240,85),'GRATIS · CÓDIGO ABIERTO' if lang=='es' else 'FREE & OPEN SOURCE',font=font(19),fill=muted)
    d.text((78,239),'New ValenAero',font=font(90,True),fill=fg)
    d.text((78,342),'Arrow',font=font(118,True),fill=fg)
    d.rounded_rectangle((83,510,167,516),radius=3,fill=accent)
    lines=['Inspiración valenciana.','Espíritu New Aero.'] if lang=='es' else ['Valencian roots.','A New Aero spirit.']
    for i,line in enumerate(lines):d.text((82,550+i*43),line,font=font(31),fill=muted)
    d.text((82,750),'robertrga / new-valenaero-arrow',font=font(23),fill=fg)
    d.text((82,793),'17 funciones · 2 variantes · HiDPI' if lang=='es' else '17 roles · 2 variants · HiDPI',font=font(23),fill=muted)
    placements=[('01-normal',1030,225,255,-9),('15-link',1390,227,190,11),('06-text',1260,398,165,-8),('04-busy',1000,540,165,0),('11-diagonal-1',1435,554,175,-9),('18-working-rainbow',1202,694,190,7),('13-move',1480,802,155,-12),('19-alternate-custom',1460,28,180,-8)]
    for key,x,y,size,angle in placements:glyph(hero,previews[key][0],(x,y),size,angle)
    hero.convert('RGB').save(out/f'New_ValenAero_Arrow_Header_{lang}_{mode}.png')

    # Collection: an open grid instead of individual cards.
    board=background(1600,1390,dark);d=ImageDraw.Draw(board)
    d.text((82,62),'La colección.' if lang=='es' else 'The collection.',font=font(64,True),fill=fg)
    d.text((84,151),'17 funciones de Windows + 2 variantes' if lang=='es' else '17 Windows roles + 2 variants',font=font(24),fill=muted)
    d.text((1260,85),'19 / HiDPI',font=font(25,True),fill=accent)
    d.line((82,208,1518,208),fill='#373b43' if dark else '#d4d3ce',width=2)
    for i,role in enumerate(roles):
        row,col=divmod(i,5);x=160+col*320
        if row==3:x+=160 # center the final four roles
        y=322+row*245
        glyph(board,previews[role[0]][0],(x,y),160)
        lines=wrap(label(role,lang),font(23),280)
        for k,line in enumerate(lines):text_center(d,(x,y+88+k*29),line,font(23),fg)
    d.line((82,1244,1518,1244),fill='#373b43' if dark else '#d4d3ce',width=2)
    d.text((82,1273),BRAND,font=font(41,True),fill=fg)
    d.text((85,1330),'32 · 48 · 64 · 96 · 128 px',font=font(22),fill=muted)
    text_center(d,(1350,1298),'robertrga / GPL-3.0',font(20),muted)
    board.convert('RGB').save(out/f'New_ValenAero_Arrow_Showroom_{lang}_{mode}.png')

    # Animated strip: the exact same source frames used by the ANI files.
    backdrop=background(1200,480,dark);d=ImageDraw.Draw(backdrop)
    d.text((46,30),BRAND,font=font(34,True),fill=fg)
    d.text((47,79),'En movimiento.' if lang=='es' else 'In motion.',font=font(21),fill=muted)
    frames=[]
    for step in range(40):
        canvas=backdrop.copy();draw=ImageDraw.Draw(canvas)
        for i,key in enumerate(['03-working-blue','18-working-rainbow','04-busy']):
            x=205+i*395
            glyph(canvas,previews[key][step],(x,260),220)
            role=next(r for r in roles if r[0]==key)
            for k,line in enumerate(wrap(label(role,lang),font(22),350)):
                text_center(draw,(x,387+k*27),line,font(22),fg)
        frames.append(canvas.convert('RGB'))
    durations=[10*(round((i+1)*100/60)-round(i*100/60)) for i in range(40)]
    frames[0].save(out/f'New_ValenAero_Arrow_Animations_{lang}_{mode}.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2)
