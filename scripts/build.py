import ctypes, hashlib, io, json, shutil, struct, textwrap, tomllib, zipfile, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[1]
PORTABLE=(ROOT/'sources/svg').exists()
REPO=ROOT if PORTABLE else ROOT/'outputs/new-valenaero-arrow'
CURSORS=REPO/'cursors'; SHOW=REPO/'showroom'; SRC=REPO/'sources'
for p in [CURSORS,SHOW,SRC,REPO/'scripts']:p.mkdir(parents=True,exist_ok=True)
RASTERS=REPO/'.cache/rasters' if PORTABLE else ROOT/'work/apple_rasters'
ORIGINAL=SRC/'New_ValenAero_Arrow_Original.cur' if PORTABLE else Path(os.environ['CURSOR_SOURCE'])
SIZES=[32,48,64,96,128]
data=ORIGINAL.read_bytes();BASE={}
for i in range(struct.unpack_from('<H',data,4)[0]):
    n,_,_,_,hx,hy,length,offset=struct.unpack_from('<BBBBHHII',data,6+i*16)
    BASE[n]=(Image.frombytes('RGBA',(n,n),data[offset+40:offset+40+n*n*4],'raw','BGRA',0,-1),(hx,hy))
CONF=tomllib.loads((SRC/'win_rg.build.toml' if PORTABLE else ROOT/'work/apple_cursor/configs/win_rg.build.toml').read_text())['cursors']
# id, Spanish label, English label, Windows role, source
ROLES=[
 ('01-normal','Selección normal','Normal Select','Arrow','original'),
 ('02-help','Selección de ayuda','Help Select','Help','question_arrow'),
 ('03-working-blue','Segundo plano · azul','Working in Background · Blue','AppStarting','left_ptr_watch'),
 ('04-busy','Ocupado','Busy','Wait','wait'),
 ('05-precision','Selección con precisión','Precision Select','Crosshair','cross'),
 ('06-text','Selección de texto','Text Select','IBeam','xterm'),
 ('07-handwriting','Escritura a mano','Handwriting','NWPen','pencil'),
 ('08-unavailable','No disponible','Unavailable','No','crossed_circle_badge'),
 ('09-vertical','Ajuste vertical','Vertical Resize','SizeNS','sb_v_double_arrow'),
 ('10-horizontal','Ajuste horizontal','Horizontal Resize','SizeWE','sb_h_double_arrow'),
 ('11-diagonal-1','Ajuste diagonal 1','Diagonal Resize 1','SizeNWSE','bottom_right_corner'),
 ('12-diagonal-2','Ajuste diagonal 2','Diagonal Resize 2','SizeNESW','bottom_left_corner'),
 ('13-move','Mover','Move','SizeAll','all-scroll'),
 ('14-alternate-apple','Selección alternativa · Apple','Alternate Select · Apple','UpArrow','right_ptr'),
 ('15-link','Selección de vínculo','Link Select','Hand','hand2'),
 ('16-location','Seleccionar ubicación','Location Select','Pin','pin_badge'),
 ('17-person','Seleccionar persona','Person Select','Person','person_badge'),
 ('18-working-rainbow','Segundo plano · multicolor','Working in Background · Rainbow','AppStarting','rainbow'),
 ('19-alternate-custom','Selección alternativa · propia','Alternate Select · Custom','UpArrow','mirrored'),
]
CACHE={}
def asset(name):
    if name not in CACHE:CACHE[name]=Image.open(RASTERS/(name+'.png')).convert('RGBA')
    return CACHE[name].copy()
def fit(im,height):
    box=im.getchannel('A').point(lambda v:255 if v>=4 else 0).getbbox();im=im.crop(box)
    return im.resize((round(im.width*height/im.height),height),Image.Resampling.LANCZOS)
def frame(role,n,step=0):
    src=role[4];arrow,hp=BASE[n]
    if src=='original':return arrow.copy(),hp
    if src=='mirrored':return ImageOps.mirror(arrow),(n-1-hp[0],hp[1])
    if src in ['question_arrow','left_ptr_watch','rainbow','pin_badge','person_badge','crossed_circle_badge']:
        im=arrow.copy()
        name=f'left_ptr_watch-{step+1:02}' if src=='left_ptr_watch' else (f'wait-{step+1:02}' if src=='rainbow' else src)
        badge=fit(asset(name),round(n*(12 if src=='question_arrow' else 10)/32))
        im.alpha_composite(badge,(n-badge.width-max(1,round(n/32)),round(n*2/32)))
        return im,hp
    name=f'wait-{step+1:02}' if src=='wait' else src
    conf=CONF.get(src,{});dim=256 if src=='wait' else 257
    return asset(name).resize((n,n),Image.Resampling.LANCZOS),tuple(round(conf.get(k,128)*n/dim) for k in ['x_hotspot','y_hotspot'])
def cur(entries,png=False):
    dirs=[];images=[];offset=6+16*len(entries)
    for im,(hx,hy) in entries:
        n=im.width
        if png:
            stream=io.BytesIO();im.save(stream,format='PNG');payload=stream.getvalue()
        else:
            stride=((n+31)//32)*4;mask=bytearray(stride*n);alpha=im.getchannel('A').tobytes()
            for y in range(n):
                for x in range(n):
                    if not alpha[y*n+x]:mask[(n-1-y)*stride+x//8]|=128>>(x%8)
            payload=struct.pack('<IiiHHIIiiII',40,n,2*n,1,32,0,4*n*n,0,0,0,0)+im.tobytes('raw','BGRA',0,-1)+mask
        dirs.append(struct.pack('<BBBBHHII',n,n,0,0,hx,hy,len(payload),offset));images.append(payload);offset+=len(payload)
    return struct.pack('<HHH',0,2,len(entries))+b''.join(dirs+images)
def chunk(tag,payload):return tag+struct.pack('<I',len(payload))+payload+(b'\0' if len(payload)%2 else b'')
def ani(frames):
    header=struct.pack('<9I',36,len(frames),len(frames),0,0,32,1,1,1)
    payload=b'ACON'+chunk(b'anih',header)+chunk(b'LIST',b'fram'+b''.join(chunk(b'icon',f) for f in frames))
    return b'RIFF'+struct.pack('<I',len(payload))+payload
manifest=[];previews={}
for role in ROLES:
    count=40 if role[4] in ['left_ptr_watch','wait','rainbow'] else 1
    filename='New_ValenAero_Arrow_'+role[0].split('-',1)[1].replace('-','_').title()+('.ani' if count>1 else '.cur')
    payload=[cur([frame(role,n,s) for n in SIZES],png=count>1) for s in range(count)]
    (CURSORS/filename).write_bytes(data if role[4]=='original' else (ani(payload) if count>1 else payload[0]))
    manifest.append(dict(file=filename,es=role[1],en=role[2],role=role[3],frames=count,hotspots={n:frame(role,n)[1] for n in SIZES}))
    previews[role[0]]=[frame(role,128,s)[0] for s in range(count)]
assert (CURSORS/'New_ValenAero_Arrow_Normal.cur').read_bytes()==data

sys.path.insert(0,str(REPO/'scripts' if PORTABLE else ROOT/'work'))
from showroom_design import render_showroom
render_showroom(SHOW,previews,ROLES)

# Four selectable schemes: blue/rainbow background + Apple/custom alternate arrow.
files=[m['file'] for m in manifest];schemes=[]
for rainbow in [False,True]:
 for custom in [False,True]:
    chosen=files[:17].copy()
    if rainbow:chosen[2]=files[17]
    if custom:chosen[13]=files[18]
    label='New ValenAero Arrow - '+('Rainbow' if rainbow else 'Blue')+' - '+('Custom Alternate' if custom else 'Apple Alternate')
    paths=['%10%\\Cursors\\NewValenAeroArrow\\'+f for f in chosen]
    schemes.append('HKCU,"Control Panel\\Cursors\\Schemes","'+label+'",0x00000000,"'+','.join(paths)+'"')
inf='\n'.join(['[Version]','Signature="$Windows NT$"','','[DefaultInstall]','CopyFiles=CursorFiles','AddReg=SchemeReg','','[DestinationDirs]','CursorFiles=10,"Cursors\\NewValenAeroArrow"','','[SourceDisksNames]','1="New ValenAero Arrow"','','[SourceDisksFiles]',*[f+'=1,cursors' for f in files],'','[CursorFiles]',*files,'','[SchemeReg]',*schemes,''])
(REPO/'New_ValenAero_Arrow_Install.inf').write_text(inf,encoding='utf-16')

# Read-only Windows validation, including all native animation steps.
u=ctypes.WinDLL('user32',use_last_error=True);g=ctypes.WinDLL('gdi32',use_last_error=True)
u.LoadImageW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_int,ctypes.c_int,ctypes.c_uint];u.LoadImageW.restype=ctypes.c_void_p
u.DestroyCursor.argtypes=[ctypes.c_void_p]
class II(ctypes.Structure):_fields_=[('icon',ctypes.c_int),('x',ctypes.c_uint),('y',ctypes.c_uint),('mask',ctypes.c_void_p),('color',ctypes.c_void_p)]
u.GetIconInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(II)];g.DeleteObject.argtypes=[ctypes.c_void_p]
g.CreateCompatibleDC.argtypes=[ctypes.c_void_p];g.CreateCompatibleDC.restype=ctypes.c_void_p
g.CreateDIBSection.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p,ctypes.c_uint];g.CreateDIBSection.restype=ctypes.c_void_p
g.SelectObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p];g.SelectObject.restype=ctypes.c_void_p;g.DeleteDC.argtypes=[ctypes.c_void_p]
u.DrawIconEx.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint]
hdc=g.CreateCompatibleDC(None);bits=ctypes.c_void_p();hdr=ctypes.create_string_buffer(struct.pack('<IiiHHIIiiII',40,128,-128,1,32,0,65536,0,0,0,0))
bmp=g.CreateDIBSection(hdc,hdr,0,ctypes.byref(bits),None,0);old=g.SelectObject(hdc,bmp)
for m in manifest:
 for n in SIZES:
    h=u.LoadImageW(None,str(CURSORS/m['file']),2,n,n,16);assert h,(m['file'],n)
    info=II();assert u.GetIconInfo(h,ctypes.byref(info));assert (info.x,info.y)==tuple(m['hotspots'][n])
    g.DeleteObject(info.mask);g.DeleteObject(info.color)
    if n==128 and m['frames']>1:
        hashes=[]
        for step in range(40):
            ctypes.memset(bits,0,65536);assert u.DrawIconEx(hdc,0,0,h,128,128,step,None,3);g.GdiFlush()
            hashes.append(hashlib.sha256(ctypes.string_at(bits,65536)).hexdigest())
        assert len(set(hashes))==40;m['native_distinct_frames']=40
    u.DestroyCursor(h)
g.SelectObject(hdc,old);g.DeleteObject(bmp);g.DeleteDC(hdc)
setup=ctypes.WinDLL('setupapi',use_last_error=True)
setup.SetupOpenInfFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint)];setup.SetupOpenInfFileW.restype=ctypes.c_void_p;setup.SetupCloseInfFile.argtypes=[ctypes.c_void_p]
line=ctypes.c_uint();h=setup.SetupOpenInfFileW(str(REPO/'New_ValenAero_Arrow_Install.inf'),None,2,ctypes.byref(line));assert h and h!=ctypes.c_void_p(-1).value,ctypes.get_last_error();setup.SetupCloseInfFile(h)
(REPO/'New_ValenAero_Arrow_Verification.json').write_text(json.dumps({'load_and_hotspot_checks':95,'native_animated_frames_verified':120,'inf_parse':'OK; not installed','original_sha256':hashlib.sha256(data).hexdigest(),'cursors':manifest},ensure_ascii=False,indent=2),encoding='utf-8')

if not PORTABLE:
    shutil.copytree(ROOT/'work/apple_cursor/svg',SRC/'svg',dirs_exist_ok=True)
    shutil.copyfile(ORIGINAL,SRC/'New_ValenAero_Arrow_Original.cur');shutil.copyfile(ROOT/'work/apple_cursor/configs/win_rg.build.toml',SRC/'win_rg.build.toml')
    shutil.copyfile(ROOT/'work/apple_cursor/LICENSE',REPO/'LICENSE')
    renderer=(ROOT/'work/render_apple.cjs').read_text()
    renderer=renderer.replace(next(line for line in renderer.splitlines() if line.startswith('let sharp;')),"const sharp=require('sharp');")
    (REPO/'scripts/render.cjs').write_text(renderer,encoding='utf-8')
    shutil.copyfile(__file__,REPO/'scripts/build.py')
    shutil.copyfile(ROOT/'work/showroom_design.py',REPO/'scripts/showroom_design.py')
(REPO/'package.json').write_text(json.dumps({'private':True,'scripts':{'render':'node scripts/render.cjs'},'dependencies':{'sharp':'^0.34.0'}},indent=2),encoding='utf-8')
(REPO/'.gitignore').write_text('node_modules/\n.cache/\n__pycache__/\n*.zip\n',encoding='utf-8')
readme='''# New ValenAero Arrow

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="showroom/New_ValenAero_Arrow_Header_en_dark.png">
  <img alt="New ValenAero Arrow — Windows cursor collection" src="showroom/New_ValenAero_Arrow_Header_en_light.png">
</picture>

**Valencian roots. A New Aero spirit.**

[Español](LEEME.md) · [Cursor files](cursors/) · [Showroom](showroom/) · [License](LICENSE)

A free and open-source cursor theme for Windows, built around a compact black arrow, a white outline and a subtle grey halo.

17 Windows cursor roles, plus two optional variants. Five resolutions: 32, 48, 64, 96 and 128 px. The normal cursor is an unmodified copy of the original file. Help, both background animations, unavailable, location and person use the custom arrow. The custom alternate is its horizontal mirror with a mirrored hotspot.

## Showroom

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="showroom/New_ValenAero_Arrow_Showroom_en_dark.png">
  <img alt="Cursor collection" src="showroom/New_ValenAero_Arrow_Showroom_en_light.png">
</picture>

## Variants

* Working in Background: blue disc or rainbow Busy wheel.
* Alternate Select: classic right arrow or mirrored custom arrow.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="showroom/New_ValenAero_Arrow_Animations_en_dark.gif">
  <img alt="Blue, rainbow and busy animations" src="showroom/New_ValenAero_Arrow_Animations_en_light.gif">
</picture>

## Installation

Extract the complete folder. Right-click `New_ValenAero_Arrow_Install.inf` > Show more options > Install. This copies the cursors and registers four schemes; it does not activate one. Open Mouse Properties > Pointers, choose a `New ValenAero Arrow` scheme and Apply. Choose the previous scheme to restore its appearance.

The four schemes combine Blue/Rainbow with Apple Alternate/Custom Alternate. The filenames also allow individual manual selection.

## Validation

Windows loaded all 19 files at all five sizes and confirmed their hotspots (95 checks). DrawIconEx rendered 40 distinct frames for each of the three animations. The INF passed the Windows parser; it was not executed. ANI timing follows upstream `win_delay=1`: 1/60 s per frame. GIF previews approximate it using the GIF format's 10 ms time units. No system settings were changed during generation.

## Credits and source

Apple cursor SVGs: [ful1e5/apple_cursor](https://github.com/ful1e5/apple_cursor), revision `fe044a42b4e9cea16ea762d2ed9004f6d7b35543`, GPL-3.0. Original SVG sources and configuration are in `sources/`. Changes include custom-arrow compositions, an alternate mirrored arrow, multi-resolution Windows encoding and bilingual showroom assets. The custom arrow was supplied by the repository owner. This project is not affiliated with Apple.

The source artwork and these adaptations are distributed under GPL-3.0; see `LICENSE`.

## Build from source (Windows)

Requires Python 3.11+, Pillow, NumPy, Node.js and sharp. From this folder, install the dependencies with `npm install` and `python -m pip install Pillow numpy`, then run `npm run render` and `python scripts/build.py`. This rebuilds cursor files, showroom assets and the ZIP in the parent folder. The validation uses Windows APIs without applying any cursor settings.
'''
for lang in ['es','en']:
    for mode in ['light','dark']:
        readme=readme.replace(f'showroom/showroom-{lang}-{mode}.png',f'showroom/New_ValenAero_Arrow_Showroom_{lang}_{mode}.png').replace(f'showroom/animations-{lang}-{mode}.gif',f'showroom/New_ValenAero_Arrow_Animations_{lang}_{mode}.gif')
(REPO/'README.md').write_text(readme,encoding='utf-8')
spanish='''# New ValenAero Arrow

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="showroom/New_ValenAero_Arrow_Header_es_dark.png">
  <img alt="New ValenAero Arrow — Colección de cursores para Windows" src="showroom/New_ValenAero_Arrow_Header_es_light.png">
</picture>

**Inspiración valenciana. Espíritu New Aero.**

[English](README.md) · [Cursores](cursors/) · [Licencia](LICENSE)

19 archivos para 17 funciones de Windows y dos variantes adicionales. Los cursores con flecha de ayuda, segundo plano, no disponible, ubicación y persona utilizan la flecha propia. Selección alternativa ofrece una flecha clásica o la flecha propia reflejada, con hotspot también reflejado.

## Colección

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="showroom/New_ValenAero_Arrow_Showroom_es_dark.png">
  <img alt="Colección de cursores" src="showroom/New_ValenAero_Arrow_Showroom_es_light.png">
</picture>

## Variantes

* Segundo plano: disco azul o ruleta multicolor.
* Selección alternativa: flecha clásica o reflejada.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="showroom/New_ValenAero_Arrow_Animations_es_dark.gif">
  <img alt="Animaciones azul, multicolor y ocupado" src="showroom/New_ValenAero_Arrow_Animations_es_light.gif">
</picture>

## Instalación

Para instalar después de revisar: extrae la carpeta completa, clic derecho en New_ValenAero_Arrow_Install.inf > Mostrar más opciones > Instalar. Registra cuatro esquemas, sin aplicar ninguno. Después elige uno en Propiedades del mouse > Punteros. Puedes regresar a tu esquema anterior desde ese panel.

Cuatro combinaciones: segundo plano azul/multicolor y selección alternativa clásica/reflejada. Ver README.md para créditos, licencia y comprobaciones. No se ha instalado ni aplicado nada durante la preparación.
'''
for mode in ['light','dark']:
    spanish=spanish.replace(f'showroom/showroom-es-{mode}.png',f'showroom/New_ValenAero_Arrow_Showroom_es_{mode}.png').replace(f'showroom/animations-es-{mode}.gif',f'showroom/New_ValenAero_Arrow_Animations_es_{mode}.gif')
(REPO/'LEEME.md').write_text(spanish,encoding='utf-8')
from vivid import build as build_vivid
build_vivid(REPO)
with zipfile.ZipFile(REPO.parent/'New_ValenAero_Arrow.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in REPO.rglob('*'):
    if f.is_file() and not any(p in ['.cache','node_modules','__pycache__'] for p in f.relative_to(REPO).parts):z.write(f,f.relative_to(REPO.parent))
print(json.dumps({'cursors':21,'png':12,'gif':8,'native_checks':105,'animation_frames':200,'output':str(REPO)}))
