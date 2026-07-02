(function(){
  var stages=Array.prototype.slice.call(document.querySelectorAll('.qt-stage'));
  if(!stages.length)return;
  var fit={{ responsive }};
  var current=0,hideTimer,autoTimer,transitioning=false,timelineBusy=false;
  var timelines=stages.map(function(s){return new qtTimeline(s);});
  if(fit){var refit=function(){qtFit(stages[current]);};
    if(window.ResizeObserver){new ResizeObserver(refit).observe(stages[0].parentElement);}
    else{window.addEventListener('resize',refit);}}
  function runTimeline(i){timelines[i].reset();timelines[i].start();}
  function finishTimeline(i){timelines[i].reset();timelines[i].finish();}
  function clearAuto(){if(autoTimer){clearTimeout(autoTimer);autoTimer=null;}}
  function canClick(){return stages[current].getAttribute('data-qt-click')!=='0';}
  function scheduleAuto(){
    clearAuto();
    var raw=stages[current].getAttribute('data-qt-after');
    if(!raw||current>=stages.length-1)return;
    var after=parseFloat(raw);
    if(isNaN(after))return;
    autoTimer=setTimeout(function(){
      if(!transitioning&&!timelineBusy&&!timelines[current].hasNext())go(current+1,false);
    },after*1000);
  }
  // Once a transition has run, drop the off-screen slides and clear the
  // transient transition styles (animation/z-index/will-change) so nothing
  // stays GPU-promoted longer than needed.
  function settle(){
    clearTimeout(hideTimer);
    transitioning=false;
    stages.forEach(function(s,j){
      s.style.animation='';s.style.zIndex='';s.style.willChange='';
      if(j!==current){s.style.display='none';s.hidden=true;}
      else{s.hidden=false;}
    });
    if(fit)qtFit(stages[current]);
    scheduleAuto();
  }
  function reverse(anim){return anim?anim+' reverse':'';}
  function go(i,backward){
    if(transitioning||timelineBusy||i<0||i>=stages.length||i===current)return;
    clearAuto();
    transitioning=true;
    var out=stages[current],inc=stages[i];
    var source=backward?out:inc;
    current=i;
    var under=source.getAttribute('data-qt-z')==='under';
    var enter=source.getAttribute('data-qt-transition')||'';
    var exit=source.getAttribute('data-qt-exit')||'';
    var reverseIncomingOver=backward&&!enter&&exit;
    // Keep the outgoing slide on screen (static, or sliding out) under/over the
    // incoming one; will-change lifts both onto their own compositor layer so
    // the move is GPU-driven rather than a main-thread repaint.
    out.hidden=false;out.style.display='block';out.style.zIndex=backward?(reverseIncomingOver?'1':'2'):(under?'2':'1');
    out.style.willChange='transform,opacity';if(fit)qtFit(out);
    out.style.animation=backward?reverse(enter):exit;
    inc.hidden=false;inc.style.display='block';inc.style.zIndex=backward?(reverseIncomingOver?'2':'1'):(under?'1':'2');
    inc.style.willChange='transform,opacity,clip-path';if(fit)qtFit(inc);
    inc.style.animation=backward?reverse(exit):enter;
    if(backward)finishTimeline(i);else runTimeline(i);
    var dur=parseFloat(source.getAttribute('data-qt-dur'))||0;
    clearTimeout(hideTimer);hideTimer=setTimeout(settle,dur*1000+60);
  }
  function advance(){
    if(transitioning||timelineBusy)return;
    clearAuto();
    if(timelines[current].hasNext()){
      timelineBusy=true;
      timelines[current].advance().then(function(){timelineBusy=false;scheduleAuto();});
    }
    else if(current<stages.length-1)go(current+1,false);
  }
  document.addEventListener('click',function(){if(canClick())advance();});
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowRight'||e.key===' '){if(canClick())advance();}
    else if(e.key==='ArrowLeft'){if(current>0)go(current-1,true);}
  });
  // First slide plays its own enter transition, then settles like any other.
  if(fit)qtFit(stages[0]);
  transitioning=true;
  stages[0].hidden=false;
  stages[0].style.willChange='transform,opacity,clip-path';
  stages[0].style.animation=stages[0].getAttribute('data-qt-transition')||'';
  runTimeline(0);
  var d0=parseFloat(stages[0].getAttribute('data-qt-dur'))||0;
  hideTimer=setTimeout(settle,d0*1000+60);
})();
