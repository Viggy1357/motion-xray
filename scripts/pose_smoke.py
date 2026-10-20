#!/usr/bin/env python3
"""Local Docker-only pose diagnostic using real MediaPipe provider."""
from __future__ import annotations

import argparse
import hashlib
import json
import importlib.metadata
import platform
import resource
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts.media import VideoAsset
from contracts.pose import PoseSequence
from providers.pose.mediapipe_provider import MediaPipePoseProvider, probe_video
from providers.pose.artifacts import read_pose_frames


def sha256_file(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def get_peak_rss_kib() -> int | None:
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return int(usage.ru_maxrss)  # Linux: KiB already
    except Exception:
        return None


def get_child_peak_rss_kib() -> int | None:
    try:
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        return int(usage.ru_maxrss)
    except Exception:
        return None


def guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
    }.get(ext, "application/octet-stream")


def build_html(frames: list[dict], meta: dict, segment: dict) -> str:
    # Safe JSON for embedding: escape < to prevent </script>
    def safe_json(obj: Any) -> str:
        return json.dumps(obj, separators=(",", ":")).replace("<", "\\u003c")

    frame_json = safe_json(frames)
    meta_json = safe_json(meta)
    seg_json = safe_json(segment)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Pose Smoke Diagnostic</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;padding:1rem;background:#111;color:#eee;max-width:1200px}}
h1{{font-size:1.1rem;margin:0 0 .5rem}}.row{{display:flex;gap:1rem;flex-wrap:wrap}}
.box{{background:#1a1a1a;border:1px solid #333;border-radius:6px;padding:.6rem;flex:1 1 240px;min-width:220px;box-sizing:border-box}}
#vwrap{{position:relative;display:block;width:100%}}#vc{{width:100%;max-width:640px;display:block}}
#oc,#sc{{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none}}
#sc{{pointer-events:none}}.lbl{{font-size:.75rem;color:#aaa;margin-top:.3rem}}
input[type=range]{{width:100%}}#info{{font-size:.8rem;color:#ccc;white-space:pre-wrap}}
#chooser{{margin-bottom:.5rem}}.muted{{color:#777}}
</style></head><body>
<h1>Pose Smoke Diagnostic</h1>
<div id="chooser"><input type="file" id="fin" accept="video/*"><span class="muted"> or place source as media/ + local server</span></div>
<div class="row"><div class="box"><div id="vwrap">
<video id="vc" controls loop crossorigin="anonymous" playsinline></video>
<canvas id="oc"></canvas><canvas id="sc"></canvas>
</div><div class="lbl">2D overlay (green=anatomical left, blue=anatomical right)</div>
<input type="range" id="slider" min="0" max="0" value="0">
<div id="info"></div></div>
<div class="box"><canvas id="skel" width="400" height="400" style="width:100%;max-width:400px"></canvas>
<div class="lbl">Estimated 3D; identity unverified; no rep count or score</div>
<div class="lbl">Drag to rotate yaw (hold Shift for pitch)</div></div></div>
<script>
const frames={frame_json},meta={meta_json},seg={seg_json};
const vc=document.getElementById('vc'),oc=document.getElementById('oc'),sc=document.getElementById('sc'),skel=document.getElementById('skel'),slider=document.getElementById('slider'),info=document.getElementById('info'),fin=document.getElementById('fin');
const ctx=oc.getContext('2d'),s3=skel.getContext('2d'),sctx=sc.getContext('2d');
let vw=0,vh=0,drag=false,lastX=0,lastY=0,yaw=0,pitch=0,curFrame=null,hasVideo=false;
const TORSO=['left_shoulder','right_shoulder','right_hip','left_hip','left_shoulder'];
const ARM_L=['left_shoulder','left_elbow','left_wrist'];
const ARM_R=['right_shoulder','right_elbow','right_wrist'];
const LEG_L=['left_hip','left_knee','left_ankle'];
const LEG_R=['right_hip','right_knee','right_ankle'];
const CHAINS=[TORSO,ARM_L,ARM_R,LEG_L,LEG_R];
const SIDE={{left_shoulder:'L',left_elbow:'L',left_wrist:'L',left_hip:'L',left_knee:'L',left_ankle:'L',right_shoulder:'R',right_elbow:'R',right_wrist:'R',right_hip:'R',right_knee:'R',right_ankle:'R'}};
function resize(){{if(!vw)return;oc.width=sc.width=vc.clientWidth;oc.height=sc.height=vc.clientHeight;draw2D();draw3D();}}
function fmt(t){{return t.toFixed(3)+'s';}}
function findFrame(ts){{
  if(!frames.length)return null;
  let best=0,bd=Math.abs(frames[0].timestamp_s-ts);
  for(let i=1;i<frames.length;i++){{let d=Math.abs(frames[i].timestamp_s-ts);if(d<bd){{bd=d;best=i;}}}}
  return bd<=0.08?frames[best]:null;
}}
function draw2D(){{
  ctx.clearRect(0,0,oc.width,oc.height);
  if(!curFrame||!hasVideo)return;
  const t=vc.currentTime;
  if(t<seg.start_s||t>seg.start_s+seg.duration_s){{
    ctx.fillStyle='#ff8';ctx.font='14px sans-serif';ctx.fillText('Outside analyzed segment',10,20);return;
  }}
  const j=curFrame.joints||{{}};
  const pts={{}};
  for(const k in j){{if(j[k].valid&&j[k].xy)pts[k]=j[k].xy;}}
  const sx=oc.width,sy=oc.height;
  for(const chain of CHAINS){{
    ctx.beginPath();
    for(let i=0;i<chain.length;i++){{
      const n=chain[i];if(!pts[n])continue;
      const x=pts[n][0]*sx,y=pts[n][1]*sy;
      if(i===0||!pts[chain[i-1]])ctx.moveTo(x,y);else ctx.lineTo(x,y);
    }}
    ctx.strokeStyle='#888';ctx.lineWidth=2;ctx.stroke();
  }}
  for(const k in pts){{
    const x=pts[k][0]*sx,y=pts[k][1]*sy;
    const side=SIDE[k];
    ctx.fillStyle=side==='L'?'#4f4':side==='R'?'#48f':'#ccc';
    ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#ccc';ctx.font='10px sans-serif';ctx.fillText(k,x+5,y);
  }}
}}
function project3D(xyz){{
  const c=Math.cos(yaw),s=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
  const x=xyz[0]*c-xyz[2]*s;
  const z=xyz[0]*s+xyz[2]*c;
  const y=xyz[1]*cp-z*sp;
  return [x*180+200,-y*180+200];
}}
function draw3D(){{
  s3.clearRect(0,0,400,400);
  if(!curFrame){{s3.fillStyle='#777';s3.fillText('No frame',10,20);return;}}
  const j=curFrame.joints||{{}};
  const pts={{}};
  for(const k in j){{if(j[k].valid&&j[k].xyz)pts[k]=j[k].xyz;}}
  if(!Object.keys(pts).length){{s3.fillStyle='#777';s3.fillText('No valid 3D points',10,20);return;}}
  s3.strokeStyle='#555';s3.lineWidth=1;
  for(const chain of CHAINS){{
    s3.beginPath();
    for(let i=0;i<chain.length;i++){{
      const n=chain[i];if(!pts[n])continue;
      const [x,y]=project3D(pts[n]);
      if(i===0||!pts[chain[i-1]])s3.moveTo(x,y);else s3.lineTo(x,y);
    }}
    s3.stroke();
  }}
  for(const k in pts){{
    const [x,y]=project3D(pts[k]);
    const side=SIDE[k];
    s3.fillStyle=side==='L'?'#4f4':side==='R'?'#48f':'#ccc';
    s3.beginPath();s3.arc(x,y,4,0,Math.PI*2);s3.fill();
    s3.fillStyle='#aaa';s3.font='9px sans-serif';s3.fillText(k,x+5,y);
  }}
  s3.fillStyle='#777';s3.fillText('Yaw '+(yaw*180/Math.PI).toFixed(0)+'° Pitch '+(pitch*180/Math.PI).toFixed(0)+'°',10,390);
}}
function updateInfo(){{
  if(!curFrame){{info.textContent='No frame';return;}}
  const lines=['Frame '+curFrame.frame_index+' @ '+fmt(curFrame.timestamp_s),'Segment '+fmt(seg.start_s)+'..'+fmt(seg.start_s+seg.duration_s)];
  const j=curFrame.joints||{{}};
  let valid=0,total=0;
  for(const k in j){{total++;if(j[k].valid)valid++;}}
  lines.push('Joints valid: '+valid+'/'+total);
  info.textContent=lines.join('\\n');
}}
function onTime(){{
  if(vc.currentTime<seg.start_s||vc.currentTime>=seg.start_s+seg.duration_s){{
    curFrame=null;draw2D();draw3D();info.textContent='Outside analyzed segment';return;
  }}
  const f=findFrame(vc.currentTime);
  if(f&&f!==curFrame){{curFrame=f;slider.value=frames.indexOf(f);draw2D();draw3D();updateInfo();}}
  else if(!f){{curFrame=null;draw2D();draw3D();updateInfo();}}
}}
function onSlider(){{
  const i=parseInt(slider.value,10);
  if(frames[i]){{vc.currentTime=frames[i].timestamp_s;curFrame=frames[i];draw2D();draw3D();updateInfo();}}
}}
vc.addEventListener('loadedmetadata',()=>{{vw=vc.videoWidth;vh=vc.videoHeight;resize();vc.currentTime=seg.start_s;}});
vc.addEventListener('timeupdate',onTime);
vc.addEventListener('resize',resize);
window.addEventListener('resize',resize);
async function loadSource(blob){{
  const digest=await crypto.subtle.digest('SHA-256',await blob.arrayBuffer());
  const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
  if(hash!==meta.source_hash){{hasVideo=false;info.textContent='Source hash mismatch: choose the analyzed video';return;}}
  if(vc.src.startsWith('blob:'))URL.revokeObjectURL(vc.src);
  vc.src=URL.createObjectURL(blob);hasVideo=true;
}}
fin.addEventListener('change',(e)=>{{const f=e.target.files[0];if(f)loadSource(f);}});
if(meta.source_basename){{fetch('media/'+encodeURIComponent(meta.source_basename))
  .then(r=>{{if(!r.ok)throw Error('source unavailable');return r.blob();}})
  .then(loadSource).catch(()=>{{info.textContent='Choose the original video locally to inspect it';}});}}
slider.max=Math.max(0,frames.length-1);slider.addEventListener('input',onSlider);
skel.addEventListener('mousedown',e=>{{drag=true;lastX=e.clientX;lastY=e.clientY;}});
window.addEventListener('mousemove',e=>{{if(!drag)return;const dx=e.clientX-lastX,dy=e.clientY-lastY;lastX=e.clientX;lastY=e.clientY;const sh=e.shiftKey;yaw+=dx*0.01;if(sh)pitch+=dy*0.01;else yaw+=dy*0.005;pitch=Math.max(-1.4,Math.min(1.4,pitch));draw3D();}});
window.addEventListener('mouseup',()=>drag=false);
function tick(){{onTime();requestAnimationFrame(tick);}}
resize();onSlider();requestAnimationFrame(tick);
</script></body></html>"""


def run_once(
    provider: MediaPipePoseProvider,
    video_asset: VideoAsset,
    artifact_root: Path,
) -> tuple[dict, list[dict], str, int, PoseSequence]:
    t0 = time.perf_counter()
    sequence = provider.infer(video_asset)
    elapsed = time.perf_counter() - t0

    artifact_key = sequence.frames_artifact_key
    expected_sha256 = Path(artifact_key).stem
    frames = read_pose_frames(artifact_root, artifact_key, expected_sha256=expected_sha256)

    # Compute per-joint coverage and invalid frames
    joint_names = set()
    for f in frames:
        joint_names.update(f.joints.keys())
    joint_names = sorted(joint_names)

    joint_coverage: dict[str, float] = {}
    all_invalid_count = 0
    for jn in joint_names:
        valid = sum(1 for f in frames if f.joints.get(jn) and f.joints[jn].valid)
        joint_coverage[jn] = valid / len(frames) if frames else 0.0

    for f in frames:
        if not any(f.joints.get(jn) and f.joints[jn].valid for jn in joint_names):
            all_invalid_count += 1

    first_pts = frames[0].timestamp_s if frames else None
    last_pts = frames[-1].timestamp_s if frames else None
    actual_rate = sequence.sample_rate_hz

    # Serialize frames lightly for HTML
    frame_dicts = []
    for f in frames:
        joints = {}
        for k, j in f.joints.items():
            joints[k] = {
                "valid": j.valid,
                "xy": j.xy,
                "xyz": j.xyz,
            }
        frame_dicts.append({
            "frame_index": f.frame_index,
            "timestamp_s": f.timestamp_s,
            "joints": joints,
        })

    artifact_path = artifact_root / artifact_key
    artifact_bytes = artifact_path.stat().st_size if artifact_path.exists() else 0
    artifact_sha256 = sha256_file(artifact_path) if artifact_path.exists() else ""

    diag = {
        "elapsed_s": round(elapsed, 4),
        "artifact_key": artifact_key,
        "artifact_bytes": artifact_bytes,
        "artifact_sha256": artifact_sha256,
        "frame_count": len(frames),
        "first_pts": first_pts,
        "last_pts": last_pts,
        "actual_rate_hz": round(actual_rate, 2),
        "all_invalid_frames": all_invalid_count,
        "joint_coverage": {k: round(v, 4) for k, v in joint_coverage.items()},
    }

    return diag, frame_dicts, artifact_sha256, artifact_bytes, sequence


def main() -> int:
    parser = argparse.ArgumentParser(description="Pose smoke diagnostic")
    parser.add_argument("--video", required=True, help="Video path relative to --source-root")
    parser.add_argument("--source-root", default="/workspace/data", help="Source root directory")
    parser.add_argument("--checkpoint", default="/workspace/models/pose_landmarker_full.task", help="Model checkpoint path")
    parser.add_argument("--checkpoint-sha256", default=None, help="Model SHA256 (default: read from JSON)")
    parser.add_argument("--output-dir", default="/out/pose-smoke/lat-pulldown", help="Output directory")
    parser.add_argument("--start-s", type=float, default=10.0, help="Segment start seconds")
    parser.add_argument("--duration-s", type=float, default=10.0, help="Segment duration seconds")
    parser.add_argument("--repeat", action="store_true", help="Run provider twice for cold/second measurements")
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    relative = Path(args.video)
    if relative.is_absolute() or any(p in ("", ".", "..") for p in args.video.split("/")) or chr(92) in args.video:
        raise ValueError("video must be a safe relative source path")
    video_path = (source_root / relative).resolve()
    if not video_path.is_relative_to(source_root):
        raise ValueError("video escapes source root")
    if not video_path.exists():
        print(f"ERROR: video not found: {video_path}", file=sys.stderr)
        return 1

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        print(f"ERROR: checkpoint not found: {checkpoint_path}", file=sys.stderr)
        return 1

    checkpoint_sha256 = args.checkpoint_sha256
    if checkpoint_sha256 is None:
        meta_path = Path("/workspace/data/pose_models/mediapipe-full-v1.json")
        if meta_path.exists():
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
                checkpoint_sha256 = meta.get("sha256", "")
            except Exception:
                pass
        if not checkpoint_sha256:
            print("ERROR: could not determine checkpoint sha256", file=sys.stderr)
            return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Hash source
    source_hash = sha256_file(video_path)
    source_bytes = video_path.stat().st_size

    # Probe
    probe = probe_video(video_path)

    # Build VideoAsset
    video_asset = VideoAsset(
        id=str(uuid.uuid4()), owner_session_id="local-pose-diagnostic",
        storage_key=args.video, sha256=source_hash, mime=guess_mime(video_path),
        bytes=source_bytes, duration_s=probe.duration_s, width=probe.width,
        height=probe.height, rotation=probe.rotation, created_at=datetime.now(timezone.utc),
    )

    provider = MediaPipePoseProvider(
        checkpoint_path=str(checkpoint_path),
        checkpoint_sha256=checkpoint_sha256,
        source_root=source_root,
        artifact_root=output_dir,
        start_s=args.start_s,
        duration_s=args.duration_s,
        sample_rate_hz=30,
        visibility_threshold=0.6,
    )

    # Run(s)
    runs: list[dict] = []
    all_frame_dicts: list[dict] = []
    all_hashes: list[str] = []

    diag1, frames1, hash1, bytes1, sequence = run_once(provider, video_asset, output_dir)
    runs.append(diag1)
    all_frame_dicts = frames1
    all_hashes.append(hash1)

    if args.repeat:
        # Re-instantiate provider for second run
        provider2 = MediaPipePoseProvider(
            checkpoint_path=str(checkpoint_path),
            checkpoint_sha256=checkpoint_sha256,
            source_root=source_root,
            artifact_root=output_dir,
            start_s=args.start_s,
            duration_s=args.duration_s,
            sample_rate_hz=30,
            visibility_threshold=0.6,
        )
        diag2, frames2, hash2, bytes2, sequence = run_once(provider2, video_asset, output_dir)
        runs.append(diag2)
        if hash2 != hash1:
            all_hashes.append(hash2)
            # Keep both artifacts; frames from second run for HTML if different
            all_frame_dicts = frames2

    # Write manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        f.write(sequence.model_dump_json(indent=2))

    # Build diagnostic metadata
    self_rss = get_peak_rss_kib()
    child_rss = get_child_peak_rss_kib()

    diagnostic = {
        "source_hash": source_hash,
        "source_name": video_path.name,
        "source_bytes": source_bytes,
        "segment_start_s": args.start_s,
        "segment_duration_s": args.duration_s,
        "probe": {
            "width": probe.width,
            "height": probe.height,
            "duration_s": probe.duration_s,
            "rotation": probe.rotation,
        },
        "model_sha256": checkpoint_sha256,
        "sdk_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "mediapipe": importlib.metadata.version("mediapipe"),
            "numpy": importlib.metadata.version("numpy"),
            "opencv-contrib-python": importlib.metadata.version("opencv-contrib-python"),
        },
        "provider_source_sha256": sha256_file(Path(sys.modules[MediaPipePoseProvider.__module__].__file__)),
        "peak_rss_kib": {"self": self_rss, "children": child_rss},
        "runs": runs,
        "artifact_hashes": all_hashes,
        "total_artifact_bytes": sum((output_dir / "pose" / (h + ".jsonl")).stat().st_size for h in all_hashes),
    }

    diag_path = output_dir / "diagnostic.json"
    with open(diag_path, "w") as f:
        json.dump(diagnostic, f, indent=2, default=str)

    # Build HTML
    meta = {
        "source_basename": video_path.name,
        "source_hash": source_hash,
        "model_sha256": checkpoint_sha256,
    }
    segment = {
        "start_s": args.start_s,
        "duration_s": args.duration_s,
    }
    html = build_html(all_frame_dicts, meta, segment)
    html_path = output_dir / "diagnostic.html"
    with open(html_path, "w") as f:
        f.write(html)

    # Summary stdout
    print(f"Source: {video_path.name} ({source_bytes} bytes, {source_hash[:16]}...)")
    print(f"Segment: {args.start_s}s +{args.duration_s}s")
    print(f"Frames: {runs[0]['frame_count']} @ ~{runs[0]['actual_rate_hz']:.1f} Hz")
    print(f"All-invalid frames: {runs[0]['all_invalid_frames']}")
    print("Elapsed: " + ", ".join(f"run{i+1}={r['elapsed_s']:.2f}s" for i, r in enumerate(runs)))
    print(f"Artifacts: {all_hashes}")
    print(f"Output: {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
