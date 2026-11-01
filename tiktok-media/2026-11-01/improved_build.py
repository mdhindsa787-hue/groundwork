#!/usr/bin/env python3
"""Render cinematic, beat-paced edits with a licensed REAL phonk track (not TikTok catalog music)."""
import json, os, pathlib, shutil, subprocess, urllib.request

HERE=pathlib.Path(__file__).resolve().parent
WORK=HERE/"_improved_work"
OUT=HERE/"improved"
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
AUDIO_URL="https://cdn.pixabay.com/download/audio/2026/02/06/audio_ed25e286d8.mp3?filename=xxxdolm-phonk-music-slowed-phonk-480432.mp3"
AUDIO_PAGE="https://pixabay.com/music/phonk-phonk-music-slowed-phonk-480432/"
VIDEOS={x["id"]:x["url"] for x in json.loads((HERE/"sources.json").read_text())["sources"]}
# Each edit has a different narrative, text hook, order and soundtrack passage.
EDITS=[
  {"name":"edit-01.mp4","hook":"NO ONE IS COMING","end":"BUILD IT YOURSELF","start":36,
   "keys":["lambo-road","black-car","lambo-wheel","yellow-hood","lambo-road","city-street","night-traffic","lambo-road"],
   "caption":"No one is coming to build your future. #supercars #carsoftiktok #lockin #discipline"},
  {"name":"edit-02.mp4","hook":"THIS IS YOUR SIGN","end":"START TODAY","start":62,
   "keys":["lambo-wheel","yellow-hood","black-car","lambo-road","city-timelapse","yellow-hood","city-street","lambo-wheel"],
   "caption":"Your future self is watching. #supercars #carsofinstagram #motivation #phonk"},
  {"name":"edit-03.mp4","hook":"DON'T BLINK","end":"STAY HUNGRY","start":85,
   "keys":["black-car","city-street","lambo-road","yellow-hood","night-traffic","lambo-wheel","black-car","lambo-road"],
   "caption":"For the ones who refuse to settle. #luxurycars #phonkedit #mindset #supercars"},
]
def run(*args,limit=90):
  subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",*map(str,args)],check=True,timeout=limit)
def fetch(url,path,limit=90_000_000):
  if path.exists() and path.stat().st_size>100_000:return
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
  size=0
  with urllib.request.urlopen(req,timeout=40) as res,open(path,"wb") as f:
    while True:
      b=res.read(262144)
      if not b:break
      size+=len(b)
      if size>limit:raise RuntimeError("Media too large: "+path.name)
      f.write(b)
  head=path.read_bytes()[:32]
  if not (b"ftyp" in head or head[:3]==b"ID3" or head[:2] in (b"\xff\xfb",b"\xff\xf3")):
    raise RuntimeError("Media signature not recognized: "+path.name)
def build(edit,n):
  temp=WORK/str(n);temp.mkdir(parents=True,exist_ok=True)
  segs=[]
  for j,key in enumerate(edit["keys"]):
    inp=WORK/(key+".mp4")
    if not inp.exists():fetch(VIDEOS[key],inp)
    part=temp/("s%02d.mp4"%j)
    txt=edit["hook"] if j==0 else edit["end"] if j==7 else None
    # 1.12s cuts; 1080p, high bitrate, concise text only on beginning and finish.
    filters=[
      "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos",
      "crop=1080:1920:(in_w-out_w)/2:(in_h-out_h)/2",
      "fps=30","eq=contrast=1.11:saturation=1.15:brightness=-0.015"
    ]
    if txt:
      filters.append("drawbox=x=0:y=745:w=iw:h=360:color=black@0.20:t=fill")
      filters.append(f"drawtext=fontfile={FONT}:text='{txt}':fontcolor=white:fontsize=56:borderw=5:bordercolor=black@0.9:x=(w-text_w)/2:y=(h-text_h)/2")
    run("-ss",str((j%3)*0.9),"-i",inp,"-t","1.12","-vf",",".join(filters),"-an","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p","-r","30","-threads","2",part)
    segs.append(part)
  concat=temp/"concat.txt";concat.write_text("".join("file '"+str(x.resolve())+"'\n" for x in segs))
  result=OUT/edit["name"]
  run("-f","concat","-safe","0","-i",concat,"-ss",str(edit["start"]),"-i",WORK/"phonk.mp3",
      "-filter_complex","[1:a]atempo=1.08,volume=0.83,afade=t=in:st=0:d=0.08,afade=t=out:st=8.55:d=0.4[a]",
      "-map","0:v:0","-map","[a]","-t","8.96",
      "-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",result)
  if not (1_000_000<result.stat().st_size<35_000_000):
    raise RuntimeError("Invalid output size: "+str(result.stat().st_size))
  subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1",str(result)],check=True)
  print("EDIT_OK",n,result.stat().st_size)
  return {"filename":edit["name"],"caption":edit["caption"],"bytes":result.stat().st_size,"music":AUDIO_PAGE,"video_sources":edit["keys"],"status":"RENDERED_NOT_PUBLISHED"}
def main():
  WORK.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
  fetch(AUDIO_URL,WORK/"phonk.mp3",limit=25_000_000)
  outputs=[build(item,i+1) for i,item in enumerate(EDITS)]
  (OUT/"manifest.json").write_text(json.dumps({"music_license":"Pixabay Content License","music_page":AUDIO_PAGE,"note":"Licensed Pixabay phonk music, NOT official TikTok trending catalog sound; track may be Content ID registered", "edits":outputs},indent=2)+"\n")
  shutil.rmtree(WORK)
if __name__=="__main__":main()
