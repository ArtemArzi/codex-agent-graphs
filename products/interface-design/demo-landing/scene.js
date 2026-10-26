import * as THREE from './vendor/three.module.js';

// One progressively enhanced scene. Product controls live independently in app.js.
const hero = document.querySelector('.hero-cinematic');
const canvas = document.querySelector('[data-cloth-canvas]');
const photo = document.querySelector('[data-scene-background]');
const planner = document.querySelector('#planner');
const toggle = document.querySelector('[data-motion-toggle]');
const windInput = document.querySelector('[data-wind]');
const controls = document.querySelector('[data-scene-controls]');
const motionQuery = matchMedia('(prefers-reduced-motion: reduce)');
const coarseQuery = matchMedia('(pointer: coarse)');
const state = {ready:false,running:false,failed:false,disposed:false,inView:true,suspended:false,
  userPaused:false,reduced:motionQuery.matches,frames:0,automaticFrames:0,manualFrames:0,
  phase:0.62,lastTime:0,lastDraw:0,wind:0.82,pointerX:0,pointerY:0,viewX:0,viewY:0,
  width:0,height:0,dpr:1,fpsCap:40,maxDrawMs:0,totalDrawMs:0,reason:'loading'};
let renderer, scene, camera, cloth, position, geometry, texture;
let resizeObserver, intersectionObserver, plannerObserver;
let barycentric = [];
const resources = new Set();
const bindings = new AbortController();
const introAnimations = [];
let introStarted = false;
const loadStarted = performance.now();

export function getSceneDiagnostics() {
  return {...state,threeRevision:THREE.REVISION,averageDrawMs:state.frames ? state.totalDrawMs/state.frames : 0,
    activeGeometryVertices:barycentric.length,resourceCount:resources.size,initializationMs:state.ready ? state.initializationMs : null};
}

function wanted() {
  return state.ready && !state.failed && !state.disposed && !state.suspended && state.inView &&
    document.visibilityState === 'visible' && !planner.open && !state.userPaused && !state.reduced;
}
function setCameraView(x,y) {
  const transform = `translate3d(${x}px,${y}px,0) scale(1.035)`;
  photo.style.transform = transform;
  canvas.style.transform = transform;
}
function updateControlLabels() {
  toggle.disabled = state.reduced;
  toggle.setAttribute('aria-pressed',String(state.userPaused || state.reduced));
  toggle.setAttribute('aria-label',state.reduced ? 'Движение отключено настройкой устройства' : state.userPaused ? 'Продолжить движение сцены' : 'Приостановить движение сцены');
  toggle.querySelector('span').textContent = state.reduced ? 'Без движения' : state.userPaused ? 'Продолжить' : 'Пауза';
  hero.dataset.motion = state.reduced ? 'reduced' : state.userPaused ? 'paused' : 'active';
}
function synchronize() {
  if (!renderer || state.disposed) return;
  const run = wanted();
  if (!run && introStarted) finishIntro();
  if (run && !state.running) {
    state.lastTime = 0;
    state.lastDraw = 0;
    state.running = true;
    renderer.setAnimationLoop(frame);
  } else if (!run && state.running) {
    renderer.setAnimationLoop(null);
    state.running = false;
  }
  if (toggle) updateControlLabels();
}

function makeFabricTexture() {
  state.brandedFabric = hero.getBoundingClientRect().width > 700;
  const plate = document.createElement('canvas');
  plate.width = plate.height = 1024;
  const ctx = plate.getContext('2d');
  if (!ctx) throw new Error('Texture canvas unavailable');
  ctx.fillStyle = '#e95b28';
  ctx.fillRect(0,0,1024,1024);
  ctx.lineWidth = 1;
  for (let n=0;n<1024;n+=4) {
    ctx.strokeStyle = n%12 ? 'rgba(89,29,8,0.025)' : 'rgba(255,228,179,0.05)';
    ctx.beginPath();ctx.moveTo(n,0);ctx.lineTo(n,1024);ctx.stroke();
    ctx.beginPath();ctx.moveTo(0,n);ctx.lineTo(1024,n);ctx.stroke();
  }
  if (state.brandedFabric) {
  ctx.fillStyle = '#21362c';
  ctx.textAlign = 'center';
  ctx.font = '700 148px Unbounded';
  ctx.fillText('КРАЙ',690,375);
  ctx.textAlign = 'left';
  ctx.font = '500 23px "Golos Text"';
  ctx.fillText('ПОЛЕВЫЕ ПРОГУЛКИ',463,430);
  ctx.lineWidth = 2;ctx.strokeStyle = '#21362c';
  ctx.beginPath();ctx.moveTo(470,460);ctx.lineTo(945,460);ctx.stroke();
  }
  const result = new THREE.CanvasTexture(plate);
  result.colorSpace = THREE.SRGBColorSpace;
  result.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(),4);
  resources.add(result);
  return result;
}

function makeCloth() {
  const divisions = 48, coordinates=[], uvs=[], indices=[], rows=[];
  for(let i=0;i<=divisions;i++) {
    rows.push(coordinates.length/3);
    for(let j=0;j<=divisions-i;j++) {
      const b=i/divisions,c=j/divisions,a=1-b-c;
      barycentric.push({a,b,c});coordinates.push(0,0,0);uvs.push(b+c,1-c);
    }
  }
  for(let i=0;i<divisions;i++) for(let j=0;j<divisions-i;j++) {
    const a=rows[i]+j,b=rows[i+1]+j,c=rows[i]+j+1;
    indices.push(a,b,c);
    if(j<divisions-i-1) indices.push(b,rows[i+1]+j+1,c);
  }
  geometry = new THREE.BufferGeometry();
  position = new THREE.Float32BufferAttribute(coordinates,3).setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute('position',position);
  geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));
  geometry.setIndex(indices);
  texture = makeFabricTexture();
  const material = new THREE.MeshStandardMaterial({map:texture,side:THREE.DoubleSide,roughness:0.83,metalness:0.02});
  cloth = new THREE.Mesh(geometry,material);
  cloth.frustumCulled = false;
  scene.add(cloth);
  resources.add(geometry);resources.add(material);
}

function positionScene() {
  const bounds=hero.getBoundingClientRect();
  state.width=Math.max(1,bounds.width);state.height=Math.max(1,bounds.height);
  const mobile=state.width<=700;
  if (state.brandedFabric === mobile) {
    resources.delete(texture);texture.dispose();
    texture=makeFabricTexture();cloth.material.map=texture;cloth.material.needsUpdate=true;
  }
  state.dpr=Math.min(devicePixelRatio,mobile?1.2:1.5);
  state.fpsCap=mobile?30:40;
  renderer.setPixelRatio(state.dpr);
  renderer.setSize(state.width,state.height,false);
  camera.left=-state.width/2;camera.right=state.width/2;
  camera.top=state.height/2;camera.bottom=-state.height/2;
  camera.updateProjectionMatrix();
  const layout=mobile ? {ax:.49,ay:.39,bx:.87,by:.28,cy:.60} : {ax:.66,ay:.32,bx:.91,by:.20,cy:.66};
  state.layout=layout;
  draw(false);
}

function deform() {
  const {width:w,height:h,phase:t,layout:l}=state;
  const a={x:l.ax*w-w/2,y:h/2-l.ay*h};
  const b={x:l.bx*w-w/2,y:h/2-l.by*h};
  const c={x:l.bx*w-w/2,y:h/2-l.cy*h};
  const strength=Math.min(w,h)*.085*(.24+state.wind*.94);
  for(let i=0;i<barycentric.length;i++) {
    const q=barycentric[i];
    const envelope=1-Math.pow(Math.max(q.a,q.b,q.c),4);
    const wave=Math.sin(q.b*10.5+t*1.8+state.pointerX*.55)+Math.sin(q.c*23.6-t*2.9)*.23;
    const z=envelope*strength*wave;
    position.setXYZ(i,q.a*a.x+q.b*b.x+q.c*c.x+envelope*strength*.13*Math.sin(t*2+q.c*8),
      q.a*a.y+q.b*b.y+q.c*c.y+envelope*strength*.075*Math.cos(q.b*12-t*1.7),z);
  }
  position.needsUpdate=true;
  geometry.computeVertexNormals();
}

function draw(automatic) {
  if(!renderer||!state.layout||state.failed||state.disposed) return;
  const before=performance.now();
  deform();renderer.render(scene,camera);
  const cost=performance.now()-before;
  state.frames++;state.totalDrawMs+=cost;state.maxDrawMs=Math.max(state.maxDrawMs,cost);
  if(automatic) state.automaticFrames++; else state.manualFrames++;
}

function frame(now) {
  if(!wanted()) {synchronize();return;}
  // A small tolerance avoids skipping a whole refresh on timestamp rounding.
  if(state.lastDraw && now-state.lastDraw<1000/state.fpsCap-1) return;
  const dt=state.lastTime?Math.min((now-state.lastTime)/1000,.075):0;
  state.lastDraw=state.lastTime=now;
  state.phase+=dt;
  const maxX=coarseQuery.matches?0:14,maxY=coarseQuery.matches?0:9;
  state.viewX+=(state.pointerX*maxX-state.viewX)*.045;
  state.viewY+=(state.pointerY*maxY-state.viewY)*.045;
  setCameraView(state.viewX,state.viewY);
  draw(true);
}

function finishIntro() {for(const animation of introAnimations) {try{animation.finish();}catch(_){}}}
function playIntro() {
  if(introStarted||state.reduced||planner.open||document.visibilityState!=='visible') return;
  introStarted=true;
  const letters=[...hero.querySelectorAll('.hero-letter')];
  for(let i=0;i<letters.length;i++) {
    introAnimations.push(letters[i].animate([{transform:'translateY(115%) rotateX(-72deg)',opacity:0},{transform:'translateY(0) rotateX(0)',opacity:1}],
      {duration:1050,delay:Math.min(i*24,300),easing:'cubic-bezier(.16,1,.3,1)',fill:'backwards'}));
  }
}

function stopAndDispose(reason) {
  if(state.disposed) return;
  state.running=false;state.disposed=true;state.reason=reason;
  renderer?.setAnimationLoop(null);
  resizeObserver?.disconnect();intersectionObserver?.disconnect();plannerObserver?.disconnect();
  bindings.abort();finishIntro();
  for(const resource of resources)resource.dispose();
  resources.clear();renderer?.dispose();
}
function fallback(reason) {
  state.failed=true;state.reason=reason;
  hero.dataset.sceneReady='false';hero.dataset.sceneState='fallback';
  controls.hidden=true;
  stopAndDispose(reason);
  photo.style.transform='none';
}

async function boot() {
  if(!hero||!canvas) return;
  if(new URLSearchParams(location.search).has('no3d')) {fallback('explicit-static');return;}
  await Promise.all([document.fonts.ready,photo.decode()]);
  renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,premultipliedAlpha:false,powerPreference:'low-power'});
  renderer.setClearColor(0x000000,0);
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.05;
  scene=new THREE.Scene();camera=new THREE.OrthographicCamera(-1,1,1,-1,.1,4000);camera.position.z=1600;
  scene.add(new THREE.AmbientLight(0xffffff,1.65));
  const sun=new THREE.DirectionalLight(0xffeed9,3.7);sun.position.set(-300,650,1200);scene.add(sun);
  const fill=new THREE.DirectionalLight(0xb9cfdd,.8);fill.position.set(500,-200,700);scene.add(fill);
  makeCloth();
  positionScene();
  state.ready=true;state.reason='ready';state.initializationMs=performance.now()-loadStarted;
  hero.dataset.sceneReady='true';hero.dataset.sceneState='ready';controls.hidden=false;
  resizeObserver=new ResizeObserver(()=>positionScene());resizeObserver.observe(hero);
  intersectionObserver=new IntersectionObserver(entries=>{state.inView=entries[0].isIntersecting;synchronize();},{threshold:0});intersectionObserver.observe(hero);
  plannerObserver=new MutationObserver(synchronize);plannerObserver.observe(planner,{attributes:true,attributeFilter:['open']});
  const options={signal:bindings.signal};
  document.addEventListener('visibilitychange',synchronize,options);
  hero.addEventListener('pointermove',event=>{if(state.reduced||state.userPaused||coarseQuery.matches)return;const r=hero.getBoundingClientRect();state.pointerX=(event.clientX-r.left)/r.width*2-1;state.pointerY=(event.clientY-r.top)/r.height*2-1;},{...options,passive:true});
  hero.addEventListener('pointerleave',()=>{state.pointerX=state.pointerY=0;},options);
  toggle.addEventListener('click',()=>{state.userPaused=!state.userPaused;if(state.userPaused)finishIntro();synchronize();},options);
  windInput.addEventListener('input',()=>{state.wind=Number(windInput.value);if(!state.running)draw(false);},options);
  motionQuery.addEventListener('change',event=>{state.reduced=event.matches;if(state.reduced){state.phase=.62;state.pointerX=state.pointerY=0;finishIntro();setCameraView(0,0);draw(false);}synchronize();},options);
  canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();fallback('context-lost');},options);
  window.addEventListener('pagehide',event=>{if(event.persisted){state.suspended=true;synchronize();}else stopAndDispose('pagehide');},options);
  window.addEventListener('pageshow',event=>{if(event.persisted){state.suspended=false;synchronize();}},options);
  playIntro();synchronize();
}

boot().catch(()=>fallback('initialization-unavailable'));
