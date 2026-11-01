#!/usr/bin/env python3
"""Make original short-form car motivation edits from individually licensed Pexels stock."""
import json
import math
import os
import pathlib
import random
import shutil
import struct
import subprocess
import urllib.request
import wave

HERE = pathlib.Path(__file__).resolve().parent
SOURCE_FILE = HERE / "sources.json"
OUT = HERE / "clips"
TEMP = HERE / "_work"
SOURCES = {s["id"]: s for s in json.loads(SOURCE_FILE.read_text())["sources"]}
FONTPATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Three 2.7-second segments with distinct sequence and the user's original voice: ambition.
EDIT_PLAN = [
    (["lambo-road", "lambo-wheel", "yellow-hood"], ["LOCK IN", "NO EXCUSES", "JUST WORK"], "Lock in. No shortcuts. #supercars #motivation #lockin #mindset"),
    (["black-car", "lambo-road", "city-street"], ["MOVE", "IN", "SILENCE"], "Move in silence. Let results speak. #luxurycars #discipline #focus"),
    (["yellow-hood", "lambo-road", "city-timelapse"], ["DREAM", "PLAN", "EXECUTE"], "Dreams need action. #supercar #goals #grind #lockin"),
    (["lambo-wheel", "black-car", "night-traffic"], ["THE VISION", "THE PROCESS", "THE RESULT"], "The process is everything. #cars #vision #discipline"),
    (["city-street", "lambo-road", "black-car"], ["NO CROWD", "NO NOISE", "JUST FOCUS"], "Work while nobody watches. #mindset #nightdrive #cars"),
    (["lambo-road", "yellow-hood", "city-street"], ["YOUR TIME", "IS NOT", "UNLIMITED"], "Every day matters. #lockin #motivation #luxurycars"),
    (["black-car", "lambo-wheel", "city-timelapse"], ["FIRST", "THE WORK", "THEN REWARDS"], "Nothing replaces consistency. #supercars #goals #work"),
    (["lambo-wheel", "night-traffic", "lambo-road"], ["THEY TALK", "YOU BUILD", "STAY LOCKED"], "Keep building. #lockin #luxury #discipline"),
    (["yellow-hood", "black-car", "night-traffic"], ["LESS TALK", "MORE WORK", "EVERY DAY"], "One day at a time. #supercars #mindset #focus"),
    (["city-timelapse", "lambo-road", "lambo-wheel"], ["ONE GOAL", "ALL IN", "NO REGRETS"], "Make it count. #motivation #supercar #lockin"),
]

def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *map(str,args)], check=True,timeout=80)

def fetch_sources():
    p = TEMP / "sources"
    p.mkdir(parents=True, exist_ok=True)
    for key, source in SOURCES.items():
        target = p / (key + ".mp4")
        if target.is_file() and target.stat().st_size > 100000:
            continue
        req = urllib.request.Request(source["url"], headers={"User-Agent":"Mozilla/5.0","Accept":"video/mp4"})
        with urllib.request.urlopen(req,timeout=35) as res, target.open("wb") as out:
            # bounded streaming; refuse unexpectedly enormous media
            count = 0
            while True:
                b = res.read(262144)
                if not b: break
                count += len(b)
                if count > 90_000_000: raise RuntimeError("Input too large: " + key)
                out.write(b)
        data = target.read_bytes()[:40]
        if len(data)<100 or b"ftyp" not in data:
            raise RuntimeError("Not an MP4: "+key)
        print("downloaded", key, target.stat().st_size)
    return p

def soundtrack(path, n, length=8.1, rate=22050):
    # Original synthesized pulse, not sampled or copied music.
    random.seed(19000+n)
    bass = [55.0, 65.4, 49.0, 73.4][n % 4]
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        buffer = bytearray()
        for k in range(int(length*rate)):
            t=k/rate
            kick_phase=t%0.6
            kick=0.38*math.sin(2*math.pi*(53+28*math.exp(-30*kick_phase))*kick_phase)*math.exp(-22*kick_phase)
            hat_phase=t%0.3
            hat=0.035*(random.random()*2-1)*math.exp(-80*hat_phase)
            beat=int(t/.6)
            note=bass * (2**([0,3,7,5][(beat//2)%4]/12))
            synth=0.075*(math.sin(2*math.pi*note*t)+0.3*math.sin(2*math.pi*note*2*t))
            x=max(-0.9,min(0.9,kick+hat+synth))
            buffer += struct.pack("<h", int(x*32767))
        w.writeframes(buffer)

def render_one(srcdir,n,job):
    identifiers,words,caption=job
    work=TEMP/("edit-%02d"%n)
    work.mkdir(parents=True,exist_ok=True)
    segments=[]
    for j,(key,word) in enumerate(zip(identifiers,words)):
        input_file=srcdir/(key+".mp4")
        output_file=work/("part%d.mp4"%j)
        pos=[0.50,0.47,0.53][j]
        vf=(
            "scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop=720:1280:(in_w-out_w)*{pos}:0,"
            "fps=24,eq=contrast=1.09:saturation=1.12,"
            "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.14:t=fill,"
            f"drawtext=fontfile={FONTPATH}:text='{word}':fontcolor=white:fontsize=55:"
            "borderw=4:bordercolor=black@0.80:x=(w-text_w)/2:y=(h-text_h)*0.57"
        )
        ff("-ss",0,"-i",input_file,"-t",2.7,"-vf",vf,
            "-an","-c:v","libx264","-preset","veryfast","-crf","29",
            "-pix_fmt","yuv420p","-r","24","-threads","2",output_file)
        segments.append(output_file)
    listing=work/"concat.txt"
    listing.write_text("".join("file '"+str(p.resolve())+"'\n" for p in segments))
    audio=work/"music.wav"
    soundtrack(audio,n)
    target=OUT/("clip-%02d.mp4"%n)
    ff("-f","concat","-safe","0","-i",listing,"-i",audio,"-map","0:v:0","-map","1:a:0",
       "-c:v","copy","-c:a","aac","-b:a","96k","-movflags","+faststart","-shortest",target)
    subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1",str(target)],check=True)
    if target.stat().st_size < 100_000 or target.stat().st_size > 20_000_000:
        raise RuntimeError("Output file invalid size")
    print("created",target,target.stat().st_size)
    return {"number":n,"filename":target.name,"on_screen_text":words,"caption":caption,"sources":identifiers,"bytes":target.stat().st_size}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    TEMP.mkdir(parents=True,exist_ok=True)
    srcdir=fetch_sources()
    output=[]
    for n,job in enumerate(EDIT_PLAN,1):
        output.append(render_one(srcdir,n,job))
    (HERE/"batch.json").write_text(json.dumps({"status":"EDITED_NOT_PUBLISHED","license":"Pexels License","videos":output},indent=2)+"\n")
    shutil.rmtree(TEMP)
    print("TOTAL",len(output))

if __name__=="__main__":
    main()
