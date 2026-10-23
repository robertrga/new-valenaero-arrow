"""Build optional Vivid ANI variants without altering the original cursors."""
import ctypes, io, json, struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from showroom_design import background, colors, font

def intense(im):
    original=np.array(im);hsv=np.array(im.convert('RGB').convert('HSV')).astype(float)
    hsv[:,:,1]=np.minimum(255,hsv[:,:,1]*1.65)
    hsv[:,:,2]=np.minimum(255,hsv[:,:,2]*1.06)
    rgb=np.array(Image.fromarray(hsv.astype('uint8'),'HSV').convert('RGB')).astype(float)
    rgb=np.clip((rgb-127.5)*1.10+127.5,0,255).astype('uint8')
    mask=np.ptp(original[:,:,:3].astype(int),axis=2)>12
    result=original.copy();result[mask,:3]=rgb[mask]
    assert np.array_equal(result[:,:,3],original[:,:,3])
    assert np.array_equal(result[~mask],original[~mask])
    return Image.fromarray(result)

def chunk(tag,data):return tag+struct.pack('<I',len(data))+data+(b'\0' if len(data)%2 else b'')

def entries(cur):
    for i in range(struct.unpack_from('<H',cur,4)[0]):
        e=cur[6+i*16:22+i*16];n,p=struct.unpack_from('<II',e,8)
        yield e,Image.open(io.BytesIO(cur[p:p+n])).convert('RGBA')

def transform_cur(cur):
    dirs=[];payloads=[];offset=6+16*struct.unpack_from('<H',cur,4)[0]
    for entry,im in entries(cur):
        buf=io.BytesIO();intense(im).save(buf,format='PNG');payload=buf.getvalue()
        dirs.append(entry[:8]+struct.pack('<II',len(payload),offset));payloads.append(payload);offset+=len(payload)
    return cur[:6]+b''.join(dirs+payloads)

def chunks(data):
    pos=0
    while pos<len(data):
        tag=data[pos:pos+4];n=struct.unpack_from('<I',data,pos+4)[0]
        yield tag,data[pos+8:pos+8+n]
        pos+=8+n+(n%2)
    assert pos==len(data)

def transform(data):
    out=[]
    for tag,body in chunks(data):
        if tag==b'icon':body=transform_cur(body)
        elif tag==b'LIST' and body[:4]==b'fram':body=b'fram'+transform(body[4:])
        out.append(chunk(tag,body))
    return b''.join(out)

def frames(data):
    for tag,body in chunks(data[12:]):
        if tag==b'LIST' and body[:4]==b'fram':
            for t,cur in chunks(body[4:]):
                if t==b'icon':yield next(im for e,im in entries(cur) if e[0]==128)

def build(repo):
    repo=Path(repo);original={};vivid={};new=[]
    # Use the Windows validation helpers already configured by the main builder.
    import __main__ as builder
    u,g=builder.u,builder.g
    for name,base in [('Busy',3),('Working_Rainbow',17)]:
        src='New_ValenAero_Arrow_'+name+'.ani';dest=src[:-4]+'_Vivid.ani'
        data=(repo/'cursors'/src).read_bytes();body=b'ACON'+transform(data[12:]);result=b'RIFF'+struct.pack('<I',len(body))+body
        assert data[12:60]==result[12:60]
        (repo/'cursors'/dest).write_bytes(result)
        original[name]=list(frames(data));vivid[name]=list(frames(result))
        m=dict(builder.manifest[base]);m['file']=dest;m['variant']='Vivid';m['en']+=' · Vivid';m['es']+=' · Vivid'
        for size in builder.SIZES:
            h=u.LoadImageW(None,str(repo/'cursors'/dest),2,size,size,16);assert h
            info=builder.II();assert u.GetIconInfo(h,ctypes.byref(info));assert (info.x,info.y)==tuple(m['hotspots'][size])
            g.DeleteObject(info.mask);g.DeleteObject(info.color)
            if size==128:
                import hashlib
                dc=g.CreateCompatibleDC(None);bits=ctypes.c_void_p();hdr=ctypes.create_string_buffer(struct.pack('<IiiHHIIiiII',40,128,-128,1,32,0,65536,0,0,0,0));bmp=g.CreateDIBSection(dc,hdr,0,ctypes.byref(bits),None,0);old=g.SelectObject(dc,bmp);hashes=[]
                for step in range(40):
                    ctypes.memset(bits,0,65536);assert u.DrawIconEx(dc,0,0,h,128,128,step,None,3);g.GdiFlush();hashes.append(hashlib.sha256(ctypes.string_at(bits,65536)).hexdigest())
                assert len(set(hashes))==40
                g.SelectObject(dc,old);g.DeleteObject(bmp);g.DeleteDC(dc)
            u.DestroyCursor(h)
        new.append(m)
    report=json.loads((repo/'New_ValenAero_Arrow_Verification.json').read_text(encoding='utf8'))
    report.update(load_and_hotspot_checks=105,native_animated_frames_verified=200)
    report['cursors']+=new
    (repo/'New_ValenAero_Arrow_Verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    infpath=repo/'New_ValenAero_Arrow_Install.inf';inf=infpath.read_text(encoding='utf16')
    # Preserve the four Original schemes; add four Vivid schemes (including Blue + Vivid Busy).
    for m in new:
        inf=inf.replace('[CursorFiles]',m['file']+'=1,cursors\n[CursorFiles]',1)
        inf=inf.replace('[SchemeReg]',m['file']+'\n[SchemeReg]',1)
    for line in inf.splitlines():
        if line.startswith('HKCU,'):
            inf+=line.replace(' - Blue',' - Vivid - Blue').replace(' - Rainbow',' - Vivid - Rainbow').replace('Arrow_Busy.ani','Arrow_Busy_Vivid.ani').replace('Arrow_Working_Rainbow.ani','Arrow_Working_Rainbow_Vivid.ani')+'\n'
    infpath.write_text(inf,encoding='utf16')
    line=ctypes.c_uint();handle=builder.setup.SetupOpenInfFileW(str(infpath),None,2,ctypes.byref(line));assert handle and handle!=ctypes.c_void_p(-1).value
    builder.setup.SetupCloseInfFile(handle)
    for lang in ['en','es']:
      for dark in [False,True]:
        mode='dark' if dark else 'light';bg,fg,muted,accent=colors(dark);panels=[]
        for step in range(40):
            canvas=background(1040,570,dark);d=ImageDraw.Draw(canvas)
            d.text((38,25),'New ValenAero Arrow',font=font(30,True),fill=fg)
            d.text((38,67),'Variante Vivid · Colores intensos' if lang=='es' else 'Vivid variant · Richer colours',font=font(18),fill=muted)
            for col,(label,source) in enumerate([('Original',original),('Vivid',vivid)]):
                x=col*500+270;f=font(24,True);d.text((x-d.textlength(label,font=f)/2,115),label,font=f,fill=fg)
                for row,name in enumerate(['Busy','Working_Rainbow']):
                    y=175+row*180;canvas.alpha_composite(source[name][step],(x-64,y))
                    caption=('Ocupado' if name=='Busy' else 'Segundo plano · Multicolor') if lang=='es' else ('Busy' if name=='Busy' else 'Working in Background · Rainbow')
                    f=font(17);d.text((x-d.textlength(caption,font=f)/2,y+135),caption,font=f,fill=muted)
            d.text((38,537),'Misma velocidad, flecha y hotspot.' if lang=='es' else 'Same speed, arrow and hotspot.',font=font(15),fill=muted)
            panels.append(canvas.convert('RGB'))
        stem=repo/'showroom'/f'New_ValenAero_Arrow_Vivid_{lang}_{mode}'
        panels[0].save(str(stem)+'.png')
        sheet=Image.new('RGB',(1040,570*4))
        for i,s in enumerate([0,10,20,30]):sheet.paste(panels[s],(0,i*570))
        palette=sheet.quantize(colors=255,method=Image.Quantize.MEDIANCUT)
        indexed=[p.quantize(palette=palette,dither=Image.Dither.NONE) for p in panels]
        durations=[round((i+1)*100/60)*10-round(i*100/60)*10 for i in range(40)]
        indexed[0].save(str(stem)+'.gif',save_all=True,append_images=indexed[1:],duration=durations,loop=0,disposal=2,optimize=False)
    for filename,lang in [('README.md','en'),('LEEME.md','es')]:
        path=repo/filename;doc=path.read_text(encoding='utf8')
        heading='## Installation' if lang=='en' else '## Instalación'
        text=('### Vivid\n\nOptional richer colours for Busy and Working in Background · Rainbow. The original colours remain available. Vivid preserves the custom arrow, alpha, hotspots and animation timing. The Blue animation is unchanged; Blue + Vivid schemes use Vivid for Busy only.\n\n' if lang=='en' else '### Vivid\n\nColores más intensos opcionales para Ocupado y Segundo plano · Multicolor. Se conservan los colores originales, la flecha propia, la transparencia, los hotspots y la velocidad. La animación azul no cambia; los esquemas Azul + Vivid aplican Vivid solo a Ocupado.\n\n')
        text+=f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="showroom/New_ValenAero_Arrow_Vivid_{lang}_dark.gif">\n  <img alt="Original / Vivid" src="showroom/New_ValenAero_Arrow_Vivid_{lang}_light.gif">\n</picture>\n\n'
        doc=doc.replace(heading,text+heading).replace('19 files','21 files').replace('95 checks','105 checks').replace('three animations','five animations').replace('four schemes','eight schemes').replace('The four schemes','The eight schemes').replace('19 archivos','21 archivos').replace('cuatro esquemas','ocho esquemas').replace('Cuatro combinaciones:','Ocho combinaciones (Original/Vivid):')
        doc=doc.replace('17 Windows cursor roles, plus two optional variants.','17 Windows cursor roles, plus four optional variants (21 files).').replace('y dos variantes adicionales.','y cuatro variantes adicionales (incluidas dos Vivid).')
        doc=doc.replace('The eight schemes combine Blue/Rainbow with Apple Alternate/Custom Alternate.','The eight schemes combine Original/Vivid, Blue/Rainbow and Apple Alternate/Custom Alternate.')
        path.write_text(doc,encoding='utf8')
    print('Vivid: 21 cursor files; 105 native loads/hotspots; 200 native animation frames; 8 schemes; INF parsed, not installed.')
