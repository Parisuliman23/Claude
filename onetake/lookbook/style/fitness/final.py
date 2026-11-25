import subprocess, glob, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
R="/home/forttoujoursfitness/Claude/onetake"; U="/home/forttoujoursfitness/.claude/uploads/cf58ef65-0c76-5bd7-974b-bc72cd3188db"
BAR=60/140*4; V=sys.argv[1]
B="Montserrat_900Black"; S="Montserrat_700Bold"
def font(n,s): return ImageFont.truetype(f"{R}/assets/fonts/{n}.ttf",s)
def card(name, items):
    """items: (text, font, size, y, style) style: 'clean' white+shadow, 'pill' dark pill, 'blue' blue pill"""
    im=Image.new("RGBA",(1080,1920),(0,0,0,0)); sh=Image.new("RGBA",im.size,(0,0,0,0))
    d=ImageDraw.Draw(im)
    for txt,fn,s,y,st in items:
        f=font(fn,s); w=d.textlength(txt,font=f)
        if st=="pill": d.rounded_rectangle([540-w/2-36,y-s*0.62-14,540+w/2+36,y+s*0.62+10],radius=30,fill=(20,20,24,220))
        if st=="blue": d.rounded_rectangle([540-w/2-28,y-s*0.7-6,540+w/2+28,y+s*0.7+6],radius=22,fill=(4,68,164,235))
        if st=="clean": ImageDraw.Draw(sh).text((540,y+3),txt,font=f,fill=(0,0,0,235),anchor="mm",stroke_width=10,stroke_fill=(0,0,0,235))
        d.text((540,y),txt,font=f,fill="white",anchor="mm",stroke_width=2 if st=="clean" else 0,stroke_fill=(0,0,0,200))
    Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)),im).save(name)
if V in ("v2","final"):
    C=dict(hook=[("2 exercises",B,112,320,"clean"),("i can't live without",S,68,410,"clean")],
           ht=[("2 exercises",B,60,250,"clean"),("i can't live without",S,36,302,"clean"),("1. hip thrusts",B,62,1250,"clean")],
           trap=[("2 exercises",B,60,250,"clean"),("i can't live without",S,36,302,"clean"),("2. RDLs",B,62,1220,"clean"),("trap bar",S,56,1290,"clean")],
           bar=[("2 exercises",B,60,250,"clean"),("i can't live without",S,36,302,"clean"),("2. RDLs",B,62,1220,"clean"),("barbell",S,56,1290,"clean")],
           vs=[("save this",B,58,250,"clean"),("trap bar",B,58,880,"clean"),("vs",S,64,962,"clean"),("barbell",B,58,1045,"clean")])
else:
    C=dict(hook=[("2 EXERCISES",B,130,340,"pill"),("i can't live without",B,58,480,"blue")],
           ht=[("1. HIP THRUSTS",B,110,340,"pill")],
           trap=[("2. RDLs",B,130,340,"pill"),("trap bar",B,58,480,"blue")],
           bar=[("2. RDLs",B,130,340,"pill"),("barbell",B,58,480,"blue")],
           vs=[("SAVE THIS",B,90,280,"pill"),("TRAP BAR",B,62,870,"pill"),("VS",B,58,962,"blue"),("BARBELL",B,62,1055,"pill")])
for k,v in C.items(): card(f"x{V}_{k}.png",v)
H,amt=(820,0.06) if V=="v1" else (1060,0.035)
LAND={2,3,5,7,9}
def clip(c): return glob.glob(f"{U}/*-VID-20261123-WA000{c}.mp4")[0]
def chain(c,i):
    pulse="" if i==0 else f",scale=w='2*trunc(540*(1+{amt}*exp(-mod(t\\,{BAR:.6f})*8)))':h=-2:eval=frame,crop=1080:1920"
    if c in LAND:
        return (f"[0:v]fps=30,split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:2,eq=brightness=-0.15[bg];"
            f"[b]scale=-2:{H}:flags=lanczos,crop=1080:{H}:(iw-1080)*0.62:0,unsharp=5:5:0.6[fg];[bg][fg]overlay=0:(H-h)/2{pulse}[v]")
    return f"[0:v]fps=30,scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920{pulse}[v]"
# (clip, start, bars) ; "split" = trap bar on top, barbell below
S=[(2,2.0,1),(5,4.0,1),(4,12,2),(6,26,2),(9,9,1),("split",None,2)]
segs=[]; acc=0
for i,(c,st,b) in enumerate(S):
    out=f"y{V}{i}.mp4"; n0=round(acc*BAR*30); acc+=b; nf=round(acc*BAR*30)-n0
    if c=="split":
        inp=["-ss","19","-i",clip(4),"-ss","30","-i",clip(6)]
        vf=("[0:v]fps=30,scale=1080:-2:flags=lanczos,crop=1080:960:0:(ih-960)*0.55[t];"
            "[1:v]fps=30,scale=1080:-2:flags=lanczos,crop=1080:960:0:(ih-960)*0.6[u];[t][u]vstack,drawbox=y=957:w=1080:h=6:color=black@0.85:t=fill[v]")
    else:
        inp=["-ss",str(st),"-i",clip(c)]; vf=chain(c,i)
    subprocess.run(["ffmpeg","-nostdin","-loglevel","error","-y",*inp,"-filter_complex",vf,"-map","[v]","-frames:v",str(nf),
                    "-an","-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p","-threads","1","-filter_threads","1",out],check=True)
    segs.append(out)
open(f"y{V}.txt","w").write("".join(f"file '{s}'\n" for s in segs))
e=lambda a,b: f"between(t,{a*BAR:.3f},{b*BAR-0.001:.3f})"
cards=[("hook",e(0,1)),("ht",e(1,2)),("trap",e(2,4)),("bar",e(4,7)),("vs",e(7,9))]
inp=sum((["-i",f"x{V}_{k}.png"] for k,_ in cards),[]); fc=""; last="0:v"
for k,(c,en) in enumerate(cards):
    fc+=f"[{last}][{k+1}:v]overlay=enable='{en}'[o{k}];"; last=f"o{k}"
n=len(cards)
fc+=f"[{last}]format=yuv420p[v];[{n+2}:a]adelay=1230|1230,volume=0.45[w];[{n+1}:a][w]amix=inputs=2:normalize=0,alimiter=limit=0.95[au]"
subprocess.run(["ffmpeg","-nostdin","-loglevel","error","-y","-f","concat","-safe","0","-i",f"y{V}.txt",*inp,"-i","beat15.wav","-i",f"{R}/assets/sfx/whoosh-fast.wav",
  "-filter_complex",fc,"-map","[v]","-map","[au]","-t",f"{9*BAR:.3f}","-c:v","libx264","-preset","medium","-crf","17","-tune","film","-threads","1","-filter_threads","1",
  "-x264-params","rc-lookahead=5:sync-lookahead=0:ref=1:bframes=0","-bf","0","-r","30","-c:a","aac","-b:a","192k","-movflags","+faststart",f"two-{V}.mp4"],check=True)
print("done",V)
