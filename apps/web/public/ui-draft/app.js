const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const LS_KEY='motion-xray-ui-draft-v1';
$('.skip-link').addEventListener('click',e=>{e.preventDefault();$('#main').focus()});
const ACCENTS={terracotta:'#C2571B',sage:'#6B7F5E',blue:'#4A6B8A'};
const EXERCISES={
 curl:{name:'Dumbbell bicep curl',short:'Curl',region:'arms',regionLabel:'Arms',desc:'Standing bilateral dumbbell curl, both arms moving together.',guidance:'Stand side-on to the camera, full body in frame, elbows clearly visible.',metrics:[['Elbow angle at bottom','164°'],['Elbow angle at top','42°'],['Trunk sway range','3°']],obs:'In this example your elbows drifted forward a little near the top of some reps.',cue:'Keep your upper arms still; move only your forearms.',why:'A steadier upper arm may keep the effort more on the bicep.'},
 lat:{name:'Lat pulldown',short:'Pulldown',region:'back',regionLabel:'Back',desc:'Cable pulldown filmed from a diagonal side angle.',guidance:'Sit at a diagonal side angle to the camera with your hands and the bar visible throughout.',metrics:[['Upper-arm excursion','58°'],['Elbow excursion','74°'],['Trunk angle change','8°']],obs:'In this example you leaned back a little as the bar came down.',cue:'Stay tall and pull the bar toward your upper chest.',why:'A taller torso may keep the effort more in your back.'},
 squat:{name:'Bodyweight squat',short:'Squat',region:'legs',regionLabel:'Legs',desc:'Air squat to comfortable depth.',guidance:'Stand side-on with feet to head in frame for the whole set.',metrics:[['Knee angle at bottom','88°'],['Hip angle at bottom','74°'],['Trunk lean','31°']],obs:'In this example your hips rose a little faster than your shoulders coming up.',cue:'Push the floor away and keep your chest up.',why:'Rising together may keep the squat more balanced over your feet.'},
 press:{name:'Incline dumbbell press',short:'Press',region:'chest',regionLabel:'Chest',desc:'Bilateral dumbbell press on an incline bench.',guidance:'Set the bench side-on to the camera, both dumbbells visible.',metrics:[['Elbow angle at bottom','76°'],['Elbow angle at top','161°'],['Upper-arm excursion','49°']],obs:'In this example your right elbow travelled a little wider than your left.',cue:'Explore keeping both elbows on a similar path.',why:'A matched path can feel more even from side to side.'}
};
const ORDER=['curl','lat','squat','press'];
const MILESTONES=[1,5,15];

/* ---------- store ---------- */
function freshStore(){return{v:1,saved:[],appearance:'terracotta'}}
function loadStore(){try{const raw=localStorage.getItem(LS_KEY);if(!raw)return freshStore();const d=JSON.parse(raw);
 if(!d||d.v!==1||!Array.isArray(d.saved))return freshStore();
 const seen=new Set();const iso=/^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$/;
 const ok=d.saved.length<=200&&d.saved.every(x=>x&&typeof x.analysisId==='string'&&x.analysisId.length<=200
  &&ORDER.includes(x.exercise)&&x.analysisId==='fixture-'+x.exercise+'-v1'
  &&x.region===EXERCISES[x.exercise].region
  &&typeof x.date==='string'&&x.date.length<=40&&iso.test(x.date)&&!isNaN(Date.parse(x.date))
  &&!seen.has(x.analysisId)&&seen.add(x.analysisId));
 if(!ok)return freshStore();
 const appearance=Object.keys(ACCENTS).includes(d.appearance)?d.appearance:'terracotta';
 return{v:1,saved:d.saved,appearance};}catch(e){return freshStore()}}
let store=loadStore();
function persist(s){localStorage.setItem(LS_KEY,JSON.stringify(s))}
function toast(msg){const t=$('#toast');t.textContent=msg;t.classList.add('show');clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('show'),3200)}

/* ---------- router ---------- */
const VIEWS=['home','analyse','results','progress'];
function route(){let h=(location.hash||'#home').slice(1);if(!VIEWS.includes(h))h='home';
 VIEWS.forEach(v=>{$('#view-'+v).hidden=v!==h});
 $$('.navlink').forEach(a=>{const on=a.getAttribute('href')==='#'+h;a.classList.toggle('active',on);on?a.setAttribute('aria-current','page'):a.removeAttribute('aria-current')});
 if(h!=='analyse')revokeFile();
 if(h!=='results')stopPlay();
 const head=$(h==='results'?($('#results-empty').hidden?'#results-body h1':'#results-empty h1'):'#view-'+h+' h1');if(head){head.setAttribute('tabindex','-1');head.focus({preventScroll:true})}
 window.scrollTo(0,0)}
window.addEventListener('hashchange',route);

/* ---------- appearance ---------- */
function applyAccent(name){document.documentElement.style.setProperty('--accent',ACCENTS[name]);
 if(three&&three.patchMat)three.patchMat.color.set(ACCENTS[name]);
 $$('input[name=accent]').forEach(r=>{r.checked=r.value===name})}
$('#appearance-open').addEventListener('click',()=>$('#appearance-dialog').showModal());
$$('input[name=accent]').forEach(r=>r.addEventListener('change',()=>{store.appearance=r.value;try{persist(store)}catch(e){toast('Appearance couldn’t be saved — it will reset on reload.')}applyAccent(r.value)}));

/* ---------- 3D athlete ---------- */
let three=null,selectedRegion='arms';
const reducedMQ=matchMedia('(prefers-reduced-motion: reduce)');let reduced=reducedMQ.matches;
reducedMQ.addEventListener('change',()=>{reduced=reducedMQ.matches;if(reduced){const ar=$('#autorotate');if(ar&&ar.checked){ar.checked=false;ar.dispatchEvent(new Event('change'))}}});
function showFallback(){$('#athlete-canvas').hidden=true;const fb=$('#athlete-fallback');fb.hidden=false;fb.dataset.region=selectedRegion;
 $$('#stage-controls [data-turn], #autorotate').forEach(b=>b.disabled=true)}
async function initAthlete(){
 let THREE;try{THREE=await import('./vendor/three.module.min.js')}catch(e){showFallback();return}
 const canvas=$('#athlete-canvas'),stage=$('#stage');
 let renderer;try{renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true})}catch(e){showFallback();return}
 renderer.setPixelRatio(Math.min(devicePixelRatio,2));
 const scene=new THREE.Scene();
 const cam=new THREE.PerspectiveCamera(34,1,.1,50);cam.position.set(0,1.7,7.2);cam.lookAt(0,1.6,0);
 scene.add(new THREE.HemisphereLight(0xfff6ea,0xe9ded0,2.1));
 const dir=new THREE.DirectionalLight(0xffffff,2.2);dir.position.set(3,6,4);scene.add(dir);
 const rim=new THREE.DirectionalLight(0xffd7b6,1.4);rim.position.set(-3,3,-2);scene.add(rim);
 const floor=new THREE.Mesh(new THREE.CircleGeometry(1.25,48),new THREE.MeshStandardMaterial({color:0xefdfca,roughness:1}));
 floor.rotation.x=-Math.PI/2;scene.add(floor);
 const fig=new THREE.Group();scene.add(fig);
 const skin=new THREE.MeshStandardMaterial({color:0xE8E2D6,roughness:.92});
 const patchMat=new THREE.MeshStandardMaterial({color:ACCENTS[store.appearance],roughness:.85});
 const geos=[],mats=[skin,patchMat];
 const G=(g,m,x,y,z,rx=0,rz=0,sx=1,sy=1,sz=1)=>{const mesh=new THREE.Mesh(g,m);mesh.position.set(x,y,z);mesh.rotation.x=rx;mesh.rotation.z=rz;mesh.scale.set(sx,sy,sz);fig.add(mesh);geos.push(g);return mesh};
 const sph=(r,w=24,h=18)=>new THREE.SphereGeometry(r,w,h);
 const cap=(r,l)=>new THREE.CapsuleGeometry(r,l,6,16);
 // head, neck, torso, pelvis
 G(sph(.3),skin,0,2.92,0,0,0,1,1.16,1);
 G(new THREE.CylinderGeometry(.11,.13,.26,16),skin,0,2.56,0);
 const pts=[];[[.26,0],[.29,.25],[.36,.55],[.44,.85],[.44,1.1],[.28,1.28]].forEach(p=>pts.push(new THREE.Vector2(p[0],p[1])));
 G(new THREE.LatheGeometry(pts,28),skin,0,1.32,0,0,0,1,1,.82);
 G(sph(.33),skin,0,1.34,0,0,0,1.15,.78,.9);
 // delts, arms, hands
 const parts={arms:[],legs:[],chest:[],back:[]};
 [-1,1].forEach(s=>{
  G(sph(.17),skin,s*.5,2.42,0);
  parts.arms.push(G(cap(.115,.5),patchMat,s*.63,2.02,0,0,s*.14));
  parts.arms.push(G(cap(.095,.46),patchMat,s*.71,1.42,0,0,s*.05));
  G(cap(.10,.5),skin,s*.63,2.02,0,0,s*.14);G(cap(.085,.46),skin,s*.71,1.42,0,0,s*.05);
  G(sph(.105),skin,s*.73,1.1,0);
  G(cap(.15,.55),skin,s*.2,.92,0);G(cap(.11,.5),skin,s*.22,.34,0);
  parts.legs.push(G(cap(.16,.55),patchMat,s*.2,.92,0));parts.legs.push(G(cap(.12,.5),patchMat,s*.22,.34,0));
  G(sph(.13),skin,s*.23,.07,.09,0,0,1,.5,1.9);
 });
 parts.chest.push(G(sph(.34),patchMat,0,2.18,.30,0,0,1.05,.85,.55));
 parts.back.push(G(sph(.34),patchMat,0,2.18,-.30,0,0,1.05,.85,.55));
 three={patchMat,parts};
 // interaction
 let targetY=0,dragging=false,lastX=0,auto=false,raf=0,visible=true,inView=true;
 three.turnForRegion=r=>{targetY=r==='back'?Math.PI:0};
 canvas.addEventListener('pointerdown',e=>{dragging=true;lastX=e.clientX;canvas.setPointerCapture(e.pointerId)});
 canvas.addEventListener('pointermove',e=>{if(!dragging)return;targetY+=(e.clientX-lastX)*.012;lastX=e.clientX});
 canvas.addEventListener('pointerup',()=>dragging=false);
 canvas.addEventListener('pointercancel',()=>dragging=false);
 canvas.addEventListener('lostpointercapture',()=>dragging=false);
 canvas.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight')e.preventDefault();if(e.key==='ArrowLeft')targetY-=.3;if(e.key==='ArrowRight')targetY+=.3});
 canvas.tabIndex=0;
 $$('#stage-controls [data-turn]').forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.turn;
  if(k==='front')targetY=0;if(k==='back')targetY=Math.PI;if(k==='left')targetY-=Math.PI/2;if(k==='right')targetY+=Math.PI/2;if(k==='reset')targetY=0}));
 $('#autorotate').addEventListener('change',e=>{auto=e.target.checked&&!reduced});
 $('#autorotate').addEventListener('focus',()=>{if(auto){auto=false;$('#autorotate').checked=false}});
 function resize(){const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);cam.aspect=w/h;
  const t=Math.tan(cam.fov*Math.PI/360);const d=Math.max(1.75/t,1.0/(t*cam.aspect))+.7;
  cam.position.set(0,1.7,d);cam.lookAt(0,1.6,0);cam.updateProjectionMatrix()}
 const resizeObserver=new ResizeObserver(resize);resizeObserver.observe(stage);resize();
 function loop(){raf=requestAnimationFrame(loop);if(reduced)fig.rotation.y=targetY;else fig.rotation.y+=(targetY-fig.rotation.y)*.12;
  if(auto)targetY+=.005;renderer.render(scene,cam)}
 function play(){if(!raf&&visible&&inView)loop()}
 function stop(){cancelAnimationFrame(raf);raf=0}
 document.addEventListener('visibilitychange',()=>{visible=!document.hidden;visible?play():stop()});
 const intersectionObserver=new IntersectionObserver(en=>{inView=en[0].isIntersecting;inView?play():stop()});intersectionObserver.observe(stage);
 window.addEventListener('pagehide',()=>{stop();resizeObserver.disconnect();intersectionObserver.disconnect();geos.forEach(g=>g.dispose());floor.geometry.dispose();floor.material.dispose();mats.forEach(m=>m.dispose());renderer.dispose();three=null},{once:true});
 requestAnimationFrame(()=>{play();applyRegion(selectedRegion);applyRegionCounts()});
}
function applyRegion(r){selectedRegion=r;
 $$('.region-btns .chip').forEach(c=>c.setAttribute('aria-pressed',String(c.dataset.region===r)));
 const fb=$('#athlete-fallback');if(!fb.hidden)fb.dataset.region=r;
 if(three){Object.entries(three.parts).forEach(([k,meshes])=>meshes.forEach(m=>m.visible=k===r));three.turnForRegion?.(r)}}
function applyRegionCounts(){if(!three)return;const counts={};store.saved.forEach(s=>counts[s.region]=(counts[s.region]||0)+1);
 Object.entries(three.parts).forEach(([k,meshes])=>{const sc=1+Math.min((counts[k]||0)*.03,.15);meshes.forEach(m=>{const b=m.userData.base||(m.userData.base=m.scale.clone());m.scale.set(b.x*sc,b.y,b.z*sc)})})}
$$('.region-btns .chip').forEach(c=>c.addEventListener('click',()=>{const k=ORDER.find(x=>EXERCISES[x].region===c.dataset.region);if(k)selectExercise(k);applyRegion(c.dataset.region)}));

/* ---------- analyse ---------- */
let currentEx='curl',currentScenario='example',fileURL=null;
const grid=$('#ex-grid');
$('#choose-file').addEventListener('click',()=>$('#file-input').click());
ORDER.forEach(k=>{const ex=EXERCISES[k];const b=document.createElement('button');b.type='button';b.className='ex-card';b.dataset.ex=k;b.setAttribute('role','radio');b.setAttribute('aria-checked',String(k===currentEx));
 const t=document.createElement('strong');t.textContent=ex.name;const d=document.createElement('span');d.textContent=ex.desc;b.append(t,d);
 b.addEventListener('click',()=>selectExercise(k));grid.append(b)});
function setGuidance(){$('#ex-guidance').textContent=EXERCISES[currentEx].guidance}
function selectExercise(k){currentEx=k;$$('.ex-card').forEach(x=>x.setAttribute('aria-checked',String(x.dataset.ex===k)));applyRegion(EXERCISES[k].region);setGuidance();updateHomeMeta()}
function revokeFile(){if(fileURL){URL.revokeObjectURL(fileURL);fileURL=null;const v=$('#file-video');v.removeAttribute('src');v.load();$('#file-preview').hidden=true}}
$('#file-input').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;revokeFile();
 fileURL=URL.createObjectURL(f);const v=$('#file-video');v.src=fileURL;$('#file-preview').hidden=false;
 $('#file-note').textContent='Local preview only — this file is not uploaded or analysed.';
 v.onloadedmetadata=()=>{if(v.duration>60)$('#file-note').textContent='This clip is over 60 seconds. Shorter clips (up to 60s) work best. Still local only — nothing is uploaded.'}});
$('#file-clear').addEventListener('click',()=>{revokeFile();$('#file-input').value=''});
window.addEventListener('pagehide',revokeFile);
$('#scenario-select').addEventListener('change',e=>{currentScenario=e.target.value;$('#banner-scenario').value=currentScenario;stopPlay()});
$('#banner-scenario').addEventListener('change',e=>{currentScenario=e.target.value;$('#scenario-select').value=currentScenario;stopPlay();
 if(!$('#view-results').hidden)renderResults()});
let procTimer=0;
$('#preview-example').addEventListener('click',()=>{const p=$('#processing');p.hidden=false;$('#show-result').hidden=true;
 const start=performance.now();clearInterval(procTimer);
 procTimer=setInterval(()=>{const el=(performance.now()-start)/1000;$('#elapsed').textContent=el.toFixed(1)+'s';
  if(el>=1.8){clearInterval(procTimer);$('#show-result').hidden=false}},100)});
$('#show-result').addEventListener('click',()=>{renderResults();location.hash='results'});
$('#save-example').addEventListener('click',saveExampleSet);
$$('[data-demo]').forEach(a=>a.addEventListener('click',()=>{currentScenario='example';$('#scenario-select').value='example'}));

/* ---------- results ---------- */
const REPS=[{s:0,e:1.2,l:'Rep 1'},{s:1.2,e:2.4,l:'Rep 2'},{s:2.4,e:3.6,l:'Rep 3'},{s:3.6,e:4.8,l:'Rep 4'},{s:4.8,e:5.4,l:'Partial'}];
const DUR=5.4;let replayT=0,playing=false,playRaf=0;
function poseAngles(k,t){const inRep=t<4.8;const p=inRep?(t%1.2)/1.2:(t-4.8)/1.2;const d=Math.sin(Math.PI*Math.min(p,1))*(inRep?1:.5);
 if(k==='squat')return{L:.1+.5*d,K:.15+1.55*d,C:.1+1.25*d,A:1.1,E:.25};
 if(k==='lat')return{L:.06+.14*d,K:.06,C:.04,A:2.7-1.7*d,E:.35+.85*d};
 if(k==='press')return{L:.05,K:.05,C:.03,A:1.5,E:1.7-1.35*d};
 return{L:.05,K:.05,C:.03,A:.12,E:.15+1.9*d}}
function drawPose(k,t){const a=poseAngles(k,t),hip={x:100,y:158},TL=66,TH=52,CL=52,UA=42,FA=40;
 const sh={x:hip.x+TL*Math.sin(a.L),y:hip.y-TL*Math.cos(a.L)};
 const kn={x:hip.x+TH*Math.sin(a.K),y:hip.y+TH*Math.cos(a.K)};
 const an={x:kn.x+CL*Math.sin(a.C),y:kn.y+CL*Math.cos(a.C)};
 const el={x:sh.x+UA*Math.sin(a.A),y:sh.y+UA*Math.cos(a.A)};
 const wr={x:el.x+FA*Math.sin(a.A+a.E),y:el.y+FA*Math.cos(a.A+a.E)};
 const set=(id,p,q)=>{const n=$(id);n.setAttribute('x1',p.x);n.setAttribute('y1',p.y);n.setAttribute('x2',q.x);n.setAttribute('y2',q.y)};
 set('#rj-torso',hip,sh);set('#rj-uarm',sh,el);set('#rj-farm',el,wr);set('#rj-thigh',hip,kn);set('#rj-calf',kn,an);
 const hd=$('#rj-head');hd.setAttribute('cx',sh.x+16*Math.sin(a.L));hd.setAttribute('cy',sh.y-16*Math.cos(a.L))}
function setReplayTime(t){replayT=Math.max(0,Math.min(DUR,t));$('#replay-range').value=replayT;
 $('#replay-time').textContent=replayT.toFixed(1)+'s / '+DUR.toFixed(1)+'s';drawPose(currentEx,replayT)}
function stopPlay(){playing=false;cancelAnimationFrame(playRaf);$('#replay-play').textContent='Play'}
$('#replay-play').addEventListener('click',()=>{if(playing){stopPlay();return}playing=true;$('#replay-play').textContent='Pause';
 let last=performance.now();const step=n=>{if(!playing)return;replayT+=(n-last)/1000;last=n;
  if(replayT>=DUR){setReplayTime(DUR);stopPlay();return}setReplayTime(replayT);playRaf=requestAnimationFrame(step)};playRaf=requestAnimationFrame(step)});
$('#replay-range').addEventListener('input',e=>{stopPlay();setReplayTime(+e.target.value)});
$('#replay-moment').addEventListener('click',()=>{stopPlay();setReplayTime(REPS[2].s+.6)});
REPS.forEach(r=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=r.l;
 b.addEventListener('click',()=>{stopPlay();setReplayTime(r.s)});$('#rep-btns').append(b)});

function renderResults(){const sc=currentScenario,ex=EXERCISES[currentEx];stopPlay();
 const empty=sc==='empty';
 $('#results-empty').hidden=!empty;$('#results-body').hidden=empty;
 if(empty)return;
 $('#results-exercise').textContent=ex.name;
 const failed=sc==='failed';
 $('#results-body h1').textContent=failed?'We couldn’t read this set.':sc==='limited'?'A partial view of your set.':'Your set, understood.';
 $('#failed-panel').hidden=!failed;
 const metricsPanel=$('#metrics-list').closest('.panel');
 [$('.replay-panel'),$('.obs-panel'),metricsPanel,$('.details-panel'),$('#save-panel')].forEach(p=>{if(p)p.hidden=failed});
 if(failed)return;
 const hasMetrics=sc==='example'||sc==='expired'||sc==='coach-down';
 const limited=sc==='limited';
 // replay
 const replayDead=sc==='expired'||limited;
 $('#replay-wrap').hidden=replayDead;
 $('#replay-controls').hidden=replayDead;
 $('#rep-btns').hidden=replayDead;
 $('#replay-unavailable').textContent=limited?'This example has insufficient visibility to reconstruct a complete movement.':'Video expired in this example. The saved measurements remain available.';
 $('#replay-svg').style.opacity=replayDead?.35:1;
 $('#replay-unavailable').hidden=!replayDead;
 $$('#replay-controls button, #replay-controls input, #rep-btns button, #replay-moment').forEach(c=>c.disabled=replayDead);
 // observation
 const coachDown=sc==='coach-down';
 const obsOff=coachDown||limited;
 $('#obs-content').hidden=obsOff;$('#obs-unavailable').hidden=!obsOff;
 if(limited)$('#obs-unavailable').textContent='Visibility was too limited to pick a reliable observation. Your partial measurements are kept below.';
 else if(coachDown)$('#obs-unavailable').textContent='Coaching cues aren’t available for this analysis. Your measurements are kept as recorded, without an accuracy validation.';
 $('#obs-text').textContent=ex.obs;$('#cue-text').textContent=ex.cue;$('#why-text').textContent='Why: '+ex.why;
 // metrics
 const list=$('#metrics-list');list.textContent='';
 const rows=hasMetrics?ex.metrics:limited?[[ex.metrics[0][0],'Unavailable — insufficient visibility']]:[];
 rows.forEach(m=>{const li=document.createElement('li');const a=document.createElement('span');a.textContent=m[0];const b=document.createElement('span');b.textContent=m[1];li.append(a,b);list.append(li)});
 $('#visibility-note').hidden=!(hasMetrics||limited);
 $('#visibility-note').textContent=limited?'Measurement visibility: 41% of frames usable — too low for full cycles.':'Measurement visibility: 92% of frames usable.';
 $('#no-cycles').hidden=!limited;
 $('#no-cycles').textContent='No complete movements measured — no penalty. Rest up and try again when you’re ready.';
 // details
 $('#ref-score').textContent=limited?'Unavailable':'79 / 100';
 $('#prov-cycles').textContent=limited?'No complete movements measured':'4 completed movements · 1 partial';
 $('#prov-missing').textContent=limited?'Completed-cycle measurements unavailable; visibility was insufficient.':'Not assessed: muscle activation, technique safety and camera-view compatibility.';
 updateSaveButton();
 setReplayTime(0)}

/* ---------- recognition ---------- */
const SAVEABLE=['example','coach-down','expired'];
function updateSaveButton(){const b=$('#save-example');if(!b)return;
 const dup=store.saved.some(s=>s.analysisId==='fixture-'+currentEx+'-v1');
 b.disabled=!SAVEABLE.includes(currentScenario)||dup;
 $('#save-status').textContent=dup?'Already saved':b.disabled?'':'Not saved yet'}
function saveExampleSet(){if(!SAVEABLE.includes(currentScenario))return;
 const ex=EXERCISES[currentEx],id='fixture-'+currentEx+'-v1';
 if(store.saved.some(s=>s.analysisId===id)){updateSaveButton();return}
 const entry={analysisId:id,exercise:currentEx,region:ex.region,date:new Date().toISOString().slice(0,10)};
 const next={...store,saved:[...store.saved,entry]};
 try{persist(next)}catch(e){toast('Couldn’t save this set — nothing was added.');return}
 store=next;$('#save-status').textContent='Saved';updateSaveButton();
 toast(ex.regionLabel+' · one analysed set added');renderProgress();updateHomeMeta();applyRegionCounts()}

/* ---------- progress & home meta ---------- */
function renderProgress(){const grid=$('#region-grid');grid.textContent='';
 const counts={};store.saved.forEach(s=>counts[s.region]=(counts[s.region]||0)+1);
 ORDER.forEach(k=>{const ex=EXERCISES[k],c=counts[ex.region]||0;const card=document.createElement('div');card.className='region-card';
  const h=document.createElement('h2');h.textContent=ex.regionLabel+' · '+ex.short;
  const n=document.createElement('p');n.className='count';n.textContent=c;
  const m=document.createElement('p');m.className='meta';
  const next=MILESTONES.find(x=>x>c);
  m.textContent=c===0?'No analysed sets yet.':next?c+' analysed set'+(c>1?'s':'')+' · next milestone at '+next:'Milestone reached — nice consistency.';
  card.append(h,n,m);grid.append(card)});
 const hist=$('#history-list');hist.textContent='';$('#history-empty').hidden=store.saved.length>0;
 [...store.saved].reverse().forEach(s=>{const li=document.createElement('li');
  const a=document.createElement('span');a.textContent=EXERCISES[s.exercise].name;
  const b=document.createElement('span');b.className='meta';b.textContent=s.date+' · example · recognition earned';
  li.append(a,b);hist.append(li)})}
function updateHomeMeta(){const now=new Date().toISOString().slice(0,10);
 const week=store.saved.filter(s=>s.date>=new Date(Date.now()-6*864e5).toISOString().slice(0,10)).length;
 $('#week-summary').textContent=week?week+' analysed set'+(week>1?'s':'')+' this week (examples).':'No analysed sets yet this week.';
 const last=store.saved[store.saved.length-1];
 $('#latest-result').textContent=last?EXERCISES[last.exercise].name+' · '+last.date+' · example result':'Nothing yet — analyse a set or explore the example.';
 $('#focus-name').textContent=EXERCISES[currentEx].name;$('#focus-guidance').textContent=EXERCISES[currentEx].guidance;
 $('#focus-cue').textContent='Example cue: '+EXERCISES[currentEx].cue}
function resetDraft(){try{localStorage.removeItem(LS_KEY)}catch(e){toast('Couldn’t clear saved data — your current view is unchanged.');return}
 store=freshStore();applyAccent(store.appearance);
 renderProgress();updateHomeMeta();applyRegionCounts();toast('Draft reset — example history cleared.')}
$('#banner-reset').addEventListener('click',resetDraft);
$('#clear-history').addEventListener('click',resetDraft);

/* ---------- init ---------- */
applyAccent(store.appearance);setGuidance();renderProgress();updateHomeMeta();route();initAthlete();
