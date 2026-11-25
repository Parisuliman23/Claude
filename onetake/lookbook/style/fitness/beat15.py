# Original gym beat: 140 BPM, dark minor, 808s. 2-bar build, then the drop.
import numpy as np, wave
SR=44100; BPM=140; B=60/BPM; BAR=4*B; NBARS=9; L=NBARS*BAR
out=np.zeros(int(SR*(L+3))); rng=np.random.default_rng(7)
def add(s,at,g=1.0):
    i=int(at*SR); n=min(len(s),len(out)-i); out[i:i+n]+=s[:n]*g
def T(d): return np.arange(int(SR*d))/SR
def kick():
    t=T(0.35); return np.tanh(3*np.sin(2*np.pi*(45+160*np.exp(-t*35))*t)*np.exp(-t*9))
def clap():
    t=T(0.25); n=rng.standard_normal(len(t)); e=np.exp(-t*18)
    for o in (0.0,0.012,0.024): e+=np.where(t>o,np.exp(-(t-o)*90),0)*0.6
    s=np.convolve(n,[1,-0.9],'same')*e; return s/np.abs(s).max()
def hat(open_=False):
    t=T(0.18 if open_ else 0.05); n=np.diff(rng.standard_normal(len(t)+1))
    return n*np.exp(-t*(20 if open_ else 90))*0.35
def hz(m): return 440*2**((m-69)/12)
def s808(m,d):
    t=T(d); f=hz(m); ph=2*np.pi*np.cumsum(f*(1+0.5*np.exp(-t*40)))/SR
    return np.tanh(2.2*np.sin(ph))*np.minimum(1,t/0.005)*np.exp(-t*1.2)*np.minimum(1,(d-t)/0.03)
def saw(f,d,cut=0.3):
    t=T(d); s=sum(np.sin(2*np.pi*f*k*t)/k for k in range(1,9))*cut
    return s*np.minimum(1,t/0.01)*np.exp(-t*3)
# A minor: progression roots (MIDI) per bar: A, F, C, G (low)
roots=[33,29,36,31]; lead=[69,72,76,72, 67,69,72,69, 64,67,72,67, 67,71,74,71]
for b in range(NBARS):
    t0=b*BAR; r=roots[b%4]; drop=b>=1; last=b>=NBARS-1
    # lead arp (eighths)
    for i in range(8):
        n=lead[(b%4)*4+i%4]; add(saw(hz(n),B/2*0.9),t0+i*B/2,0.09 if drop else 0.06)
    # hats: 16ths, with rolls every 4th bar
    step=B/4
    for i in range(16):
        add(hat(),t0+i*step,0.9 if drop else 0.5)
    if drop and b%4==3:
        for i in range(12): add(hat(),t0+3*B+i*B/12,0.7)
    if drop and not last:
        for kb in (0,1.5,2.5): add(kick(),t0+kb*B,0.9)
        add(clap(),t0+2*B,0.55)
        add(s808(r,B*1.4),t0,0.75); add(s808(r,B*0.9),t0+1.5*B,0.6); add(s808(r+(12 if b%2 else 0),B),t0+2.5*B,0.6)
    if last:
        add(kick(),t0,0.9); add(s808(r,BAR),t0,0.7)
# riser into the drop + impact
t=T(BAR); n=rng.standard_normal(len(t)); env=(t/BAR)**2
rs=np.convolve(n,np.ones(6)/6,'same')*env*0.25+np.sin(2*np.pi*(200+800*(t/BAR)**2)*t)*env*0.08
add(rs,0)
add(kick(),BAR,1.0); ti=T(1.2); add(rng.standard_normal(len(ti))*np.exp(-ti*5)*0.25,BAR)
out=out[:int(SR*L)]; f=int(SR*1.2); out[-f:]*=np.linspace(1,0,f)
out=np.tanh(out*1.2); out=out/np.abs(out).max()*0.9
st=np.stack([out,out],1)
with wave.open("beat15.wav","wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype(np.int16).tobytes())
print(L, BAR)
