#!/usr/bin/env python3
"""Synthesize soft, non-cartoonish SFX (numpy only). 48 kHz stereo 24-bit WAV.
Usage: python3 make_sfx.py [out_dir]  (default ./sfx)."""
import numpy as np, wave, os
SR=48000
import os, sys
OUT=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.getcwd(), "sfx")
os.makedirs(OUT, exist_ok=True)
rng=np.random.default_rng(7)

def pink(n):
    # Voss-McCartney-ish via FFT shaping
    w=rng.standard_normal(n)
    X=np.fft.rfft(w); f=np.fft.rfftfreq(n,1/SR); f[0]=f[1]
    X/=np.sqrt(f); y=np.fft.irfft(X,n); return y/np.abs(y).max()

def svf_bandpass(x, fc, q):
    """Chamberlin state-variable filter with per-sample cutoff array fc."""
    low=band=0.0; out=np.zeros_like(x); damp=1.0/q
    for i in range(len(x)):
        f=2*np.sin(np.pi*min(fc[i],SR/6)/SR)
        high=x[i]-low-damp*band
        band+=f*high; low+=f*band
        out[i]=band
    return out

def onepole_lp(x, fc):
    a=np.exp(-2*np.pi*fc/SR); y=np.zeros_like(x); s=0.0
    for i in range(len(x)):
        s=(1-a)*x[i]+a*s; y[i]=s
    return y

def write(name, st, peak_db=-6.0):
    st=st/np.abs(st).max()*10**(peak_db/20)
    st=np.clip(st,-1,1)
    data=(st*(2**23-1)).astype(np.int32)
    b=bytearray()
    for l,r in data:
        b+=int(l).to_bytes(4,'little',signed=True)[:3]+int(r).to_bytes(4,'little',signed=True)[:3]
    with wave.open(os.path.join(OUT,name),'wb') as w:
        w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); w.writeframes(bytes(b))
    print(name, f"{len(st)/SR:.3f}s")

def fade(n, ms_in=4, ms_out=8):
    e=np.ones(n); a=int(SR*ms_in/1000); b=int(SR*ms_out/1000)
    if a: e[:a]=np.linspace(0,1,a)
    if b: e[-b:]=np.linspace(1,0,b)
    return e

def whoosh(dur, f0, f1, peak_pos, q=1.4, lp=5000, pan=(-0.35,0.35)):
    n=int(SR*dur); t=np.arange(n)/n
    fc=f0*(f1/f0)**t                       # exponential sweep
    x=pink(n)
    y=svf_bandpass(x,fc,q)
    y=onepole_lp(onepole_lp(y,lp),lp)
    # smooth asymmetric envelope peaking at peak_pos
    env=np.where(t<peak_pos,(t/peak_pos)**2.2,((1-t)/(1-peak_pos))**1.6)
    env=np.convolve(env,np.ones(480)/480,mode='same')
    y=y*env*fade(n,3,15)
    p=np.linspace(pan[0],pan[1],n)          # gentle stereo drift
    L=y*np.sqrt((1-p)/2); R=y*np.sqrt((1+p)/2)
    return np.stack([L,R],1)

def pop(dur=0.085, f0=880, f1=520, tau=0.020):
    n=int(SR*dur); t=np.arange(n)/SR
    f=f1+(f0-f1)*np.exp(-t/0.012)
    ph=2*np.pi*np.cumsum(f)/SR
    y=np.sin(ph)*np.exp(-t/tau)
    att=int(SR*0.0025); y[:att]*=np.linspace(0,1,att)
    y=onepole_lp(y,3500)*fade(n,0,10)
    return np.stack([y,y],1)

def tick(dur=0.05, f=2300, tau=0.006):
    n=int(SR*dur); t=np.arange(n)/SR
    y=np.sin(2*np.pi*f*t)*np.exp(-t/tau)*0.8
    nz=onepole_lp(rng.standard_normal(n),4000)*np.exp(-t/0.003)*0.25
    y=(y+nz); att=int(SR*0.001); y[:att]*=np.linspace(0,1,att)
    y=onepole_lp(y,6000)*fade(n,0,10)
    return np.stack([y,y],1)

def door_click(dur=0.16):
    n=int(SR*dur); t=np.arange(n)/SR; y=np.zeros(n)
    for t0,amp in ((0.0,1.0),(0.038,0.6)):          # latch: two soft transients
        k=int(t0*SR); m=n-k; tt=np.arange(m)/SR
        thump=np.sin(2*np.pi*150*tt)*np.exp(-tt/0.018)
        clk=onepole_lp(rng.standard_normal(m),1800)*np.exp(-tt/0.004)*1.6
        y[k:]+=amp*(thump+clk)
    y=onepole_lp(y,2500)*fade(n,1,20)
    return np.stack([y,y],1)

if __name__=="__main__":
    write("whoosh_soft_in.wav",  whoosh(0.55, 260, 2200, 0.82))
    write("whoosh_soft_out.wav", whoosh(0.50, 2000, 300, 0.18, pan=(0.35,-0.35)))
    write("air_swish_in.wav",    whoosh(0.34, 700, 3200, 0.75, q=1.1, lp=6500, pan=(-0.2,0.2)))
    write("air_swish_out.wav",   whoosh(0.32, 3000, 700, 0.25, q=1.1, lp=6500, pan=(0.2,-0.2)))
    write("pop_soft.wav",        pop())
    write("tick_soft.wav",       tick())
    write("door_click_soft.wav", door_click())
