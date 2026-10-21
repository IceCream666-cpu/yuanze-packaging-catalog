import test from 'node:test';
import assert from 'node:assert/strict';
import {createCarouselMotion,horizontalWheel,wheelSnap} from '../src/carousel-motion.js';

function harness(initial=0,length=8) {
 let time=0,id=0;const frames=new Map(),painted=[],selected=[];
 const motion=createCarouselMotion({initial,length,now:()=>time,requestFrame:fn=>{frames.set(++id,fn);return id;},cancelFrame:id=>frames.delete(id),paint:(p,m)=>painted.push([p,m]),select:i=>selected.push(i)});
 function frame(dt=1000/60){time+=dt;const jobs=[...frames.values()];frames.clear();jobs.forEach(fn=>fn(time));}
 function settle(){for(let i=0;i<180&&frames.size;i++)frame();assert.equal(frames.size,0,'motion must settle');}
 return {motion,frames,painted,selected,frame,settle};
}

test('continuous horizontal deltas and rapid reversals are never locked or dropped',()=>{
 const h=harness();let expected=0;
 // 240 input events, with no quiet gap: four fast strokes and their reverse strokes.
 for(let i=0;i<240;i++){
  const dx=i<120?12:-9;expected+=dx/300;h.motion.moveTo(h.motion.state.position+dx/300);
  if(i%4===3)h.frame();
  assert.ok(Math.abs(h.motion.state.position-expected)<1e-9);
 }
 assert.equal(h.painted.length,60,'one paint per display frame, not per input event');
 h.motion.settle(wheelSnap(expected,0));h.settle();assert.equal(h.motion.state.position,1);
});

test('rapid next commands preserve all steps and selection echo cannot restart or reverse travel',()=>{
 const h=harness();for(let i=0;i<5;i++) {h.motion.advance(1);h.frame(30);h.motion.selectIndex((i+1)%8);}
 assert.deepEqual(h.selected,[1,2,3,4,5]);h.settle();assert.equal(h.motion.state.position,5);
 for(let i=0;i<5;i++){h.motion.advance(-1);h.frame(30);}h.settle();assert.equal(h.motion.state.position,0);
 h.motion.advance(-1);h.settle();assert.equal(h.motion.state.position,7);
});

test('new targets retain velocity instead of restarting easing from a standstill',()=>{
 const h=harness();h.motion.advance(1);h.frame(40);h.frame(40);
 const before={...h.motion.state};h.motion.advance(1);
 assert.equal(h.motion.state.position,before.position);assert.equal(h.motion.state.velocity,before.velocity);
 h.frame();assert.ok(h.motion.state.position>before.position);h.settle();assert.equal(h.motion.state.position,2);
});

test('pointer or wheel can take over an active snap, reverse and release without a jump',()=>{
 const h=harness();h.motion.advance(1);h.frame(60);const start=h.motion.state.position;
 h.motion.moveTo(start-.3);h.frame();assert.equal(h.motion.state.position,start-.3);
 h.motion.settle(-1);h.settle();assert.equal(h.motion.state.position,7);
 assert.equal(h.painted.at(-1)[1],false);
});

test('reduced motion snaps immediately; disposal clears the outstanding frame',()=>{
 const h=harness();h.motion.advance(4);h.frame(30);h.motion.setReduced(true);
 assert.equal(h.frames.size,0);assert.equal(h.motion.state.position,4);
 h.motion.advance(1);assert.equal(h.motion.state.position,5);assert.equal(h.frames.size,0);
 h.motion.setReduced(false);h.motion.moveTo(5.2);assert.equal(h.frames.size,1);h.motion.dispose();assert.equal(h.frames.size,0);
});

test('wheel normalization respects vertical scroll, pinch zoom, shift, line and page units',()=>{
 const e={deltaX:12,deltaY:1,deltaMode:0};assert.equal(horizontalWheel(e,300),12);
 assert.equal(horizontalWheel({...e,deltaY:30},300),0);
 assert.equal(horizontalWheel({...e,ctrlKey:true},300),0);
 assert.equal(horizontalWheel({...e,metaKey:true},300),0);
 assert.equal(horizontalWheel({...e,deltaX:0,deltaY:3,shiftKey:true,deltaMode:1},300),48);
 assert.equal(horizontalWheel({...e,deltaX:-1,deltaY:0,deltaMode:2},300),-300);
 assert.equal(horizontalWheel({...e,deltaX:NaN},300),0);
});

test('short intentional swipes, tiny tails, long drags and circular seams snap predictably',()=>{
 for(const [position,start,expected] of [[.17,0,1],[-.17,0,-1],[.03,0,0],[2.65,0,3],[8.2,7.9,9],[7.98,8,8]])assert.equal(wheelSnap(position,start),expected);
});
