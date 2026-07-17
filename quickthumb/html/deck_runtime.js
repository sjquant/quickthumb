(function(){
  var stages=Array.prototype.slice.call(document.querySelectorAll('.qt-stage'));
  if(!stages.length)return;
  var fit={{ responsive }};
  function syncPath(){
    return window.location.pathname==='/presenter'?'/':window.location.pathname;
  }
  function documentId(){
    var body=document.body;
    return body&&body.getAttribute('data-qt-state-id')||'default';
  }
  function stateKey(){
    return 'quickthumb:state:'+window.location.origin+syncPath()+':'+documentId();
  }
  function readSavedState(){
    try{
      var value=window.localStorage&&window.localStorage.getItem(stateKey());
      if(value===null||value==='')return null;
      return JSON.parse(value);
    }catch(error){return null;}
  }
  var timelines=stages.map(function(s){return new qtTimeline(s);});
  function normalizeState(state){
    if(!state||typeof state!=='object')return null;
    var slide=Number(state.slide),timeline=Number(state.timeline);
    return Number.isInteger(slide)&&slide>=0&&slide<stages.length&&
      Number.isInteger(timeline)&&timeline>=0&&timeline<=timelines[slide].length()
      ?{slide:slide,timeline:timeline}:null;
  }
  var presenter=presenterRequested();
  var savedState=presenter?normalizeState(readSavedState()):null;
  var current=savedState?savedState.slide:0;
  function snapshot(){
    return {slide:current,timeline:timelines[current].position()};
  }
  function saveState(state){
    if(!presenter)return;
    try{
      if(window.localStorage)window.localStorage.setItem(stateKey(),JSON.stringify(state));
    }catch(error){}
  }
  var hideTimer,autoTimer,transitioning=false,timelineBusy=false,applyingRemote=false;
  var pendingRemoteState=null,pendingRemoteAdvance=null;
  var presenterUi=presenter?createPresenter():null;
  var needsInitialSync=!presenter;
  var sync=createSync();
  if(presenter)fit=true;
  if(fit){var refit=function(){
      qtFit(stages[current]);
      if(presenterUi&&presenterUi.preview)qtFit(presenterUi.preview);
    };
    if(window.ResizeObserver){
      var observer=new ResizeObserver(refit);
      observer.observe(stages[0].parentElement);
      if(presenterUi)observer.observe(presenterUi.nextFrame);
    }
    else{window.addEventListener('resize',refit);}}

  function presenterRequested(){
    if(!window.location)return false;
    if(window.location.pathname==='/presenter')return true;
    var value=new URLSearchParams(window.location.search).get('presenter');
    return value!==null&&value!=='0'&&value!=='false';
  }
  function createPresenter(){
    document.body.classList.add('qt-presenter');
    var frame=stages[0].parentElement;
    if(frame===document.body){
      frame=document.createElement('div');frame.className='qt'+'-frame';
      stages.forEach(function(stage){frame.appendChild(stage);});
    }
    var shell=document.createElement('main');shell.className='qt-presenter-shell';
    shell.setAttribute('aria-label','Presenter view');
    shell.innerHTML=
      '<section class="qt-presenter-main">'+
        '<div class="qt-presenter-status">'+
          '<div class="qt-presenter-status-meta">'+
            '<span class="qt-presenter-status-kicker">Presentation</span>'+
            '<span data-qt-progress></span>'+
          '</div>'+
          '<div class="qt-presenter-timer-group">'+
            '<button class="qt-presenter-timer" type="button" data-qt-timer-toggle '+
            'data-qt-presenter-control aria-pressed="true" data-running="true">'+
              '<span class="qt-presenter-timer-icon" data-qt-timer-icon aria-hidden="true">Ⅱ</span>'+
              '<span class="qt-presenter-timer-value" data-qt-timer-value>00:00</span>'+
              '<span class="qt-presenter-timer-label" data-qt-timer-label>Pause</span>'+
            '</button>'+
            '<button class="qt-presenter-timer-reset" type="button" '+
              'title="Reset timer" aria-label="Reset timer" data-qt-reset-timer '+
              'data-qt-presenter-control><svg class="qt-presenter-timer-reset-icon" '+
              'viewBox="0 0 24 24" aria-hidden="true" focusable="false">'+
              '<path d="M20 11a8 8 0 0 0-14.9-4L3 9m0 0V4m0 5h5M4 13a8 8 0 0 0 14.9 4L21 15m0 0v5m0-5h-5"/>'+
              '</svg></button>'+
          '</div>'+
        '</div>'+
        '<div class="qt-presenter-current"></div>'+
      '</section>'+
      '<aside class="qt-presenter-sidebar">'+
        '<header class="qt-presenter-heading qt-presenter-next-label"><span>Next slide</span><span data-qt-next></span></header>'+
        '<div class="qt-presenter-next"></div>'+
        '<div class="qt-presenter-heading qt-presenter-notes-label"><span>Speaker notes</span></div>'+
        '<div class="qt-presenter-notes" aria-live="polite"></div>'+
        '<nav class="qt-presenter-controls" aria-label="Slide controls">'+
            '<button class="qt-presenter-control" type="button" data-qt-previous '+
            'data-qt-presenter-control>Previous</button>'+
            '<button class="qt-presenter-control" type="button" data-qt-forward '+
            'data-qt-presenter-control>Next</button>'+
            '<a class="qt-presenter-audience" target="_blank" rel="noopener" '+
            'data-qt-audience data-qt-presenter-control>Open audience view</a>'+
        '</nav>'+
      '</aside>';
    document.body.appendChild(shell);
    shell.querySelector('.qt-presenter-current').appendChild(frame);
    var ui={
      shell:shell,
      nextFrame:shell.querySelector('.qt-presenter-next'),
      notes:shell.querySelector('.qt-presenter-notes'),
      nextLabel:shell.querySelector('[data-qt-next]'),
      progress:shell.querySelector('[data-qt-progress]'),
      timer:shell.querySelector('.qt-presenter-timer'),
      timerIcon:shell.querySelector('[data-qt-timer-icon]'),
      timerValue:shell.querySelector('[data-qt-timer-value]'),
      timerLabel:shell.querySelector('[data-qt-timer-label]'),
      resetTimer:shell.querySelector('[data-qt-reset-timer]'),
      previous:shell.querySelector('[data-qt-previous]'),
      forward:shell.querySelector('[data-qt-forward]'),
      preview:null
    };
    ui.shell.querySelector('[data-qt-audience]').href=audienceUrl();
    ui.previous.addEventListener('click',function(e){
      e.stopPropagation();if(current>0)go(current-1,true);
    });
    ui.forward.addEventListener('click',function(e){
      e.stopPropagation();if(canClick())advance();
    });
    var timerElapsed=0,timerStartedAt=Date.now(),timerRunning=true;
    function updateTimer(){
      var elapsed=Math.floor((timerElapsed+(timerRunning?Date.now()-timerStartedAt:0))/1000);
      var minutes=String(Math.floor(elapsed/60)).padStart(2,'0');
      var seconds=String(elapsed%60).padStart(2,'0');
      ui.timerValue.textContent=minutes+':'+seconds;
      ui.timer.setAttribute('aria-pressed',timerRunning?'true':'false');
      ui.timer.setAttribute('data-running',timerRunning?'true':'false');
      ui.timerIcon.textContent=timerRunning?'Ⅱ':'▶';
      ui.timerLabel.textContent=timerRunning?'Pause':'Resume';
    }
    ui.timer.addEventListener('click',function(e){
      e.stopPropagation();
      if(timerRunning){timerElapsed+=Date.now()-timerStartedAt;timerRunning=false;}
      else{timerStartedAt=Date.now();timerRunning=true;}
      updateTimer();
    });
    ui.resetTimer.addEventListener('click',function(e){
      e.stopPropagation();timerElapsed=0;timerStartedAt=Date.now();timerRunning=true;updateTimer();
    });
    setInterval(updateTimer,1000);
    return ui;
  }
  function audienceUrl(){
    var url=new URL(window.location.href);
    if(url.pathname==='/presenter')url.pathname='/';
    url.searchParams.delete('presenter');
    return url.toString();
  }
  function createSync(){
    if(!window.BroadcastChannel||!window.location)return null;
    var channel=new window.BroadcastChannel(stateKey());
    channel.addEventListener('message',function(event){
      var message=event.data||{};
      if(presenter){
        if(message.action==='ready')channel.postMessage({action:'state',state:snapshot()});
        return;
      }
      applyingRemote=true;
      if(message.action==='advance')applyRemoteAdvance(message.state);
      else if(message.action==='state')applyRemoteState(message.state);
      applyingRemote=false;
    });
    return channel;
  }
  function sendSync(message){
    if(presenter&&sync&&!applyingRemote)sync.postMessage(message);
  }
  function publishState(){
    if(!presenter)return;
    var state=snapshot();saveState(state);sendSync({action:'state',state:state});
  }
  function updatePresenter(){
    if(!presenterUi)return;
    presenterUi.progress.textContent='Slide '+(current+1)+' of '+stages.length;
    presenterUi.previous.disabled=current===0;
    presenterUi.forward.disabled=!canClick()||(
      current===stages.length-1&&!timelines[current].hasNext()
    );
    var notes=stages[current].getAttribute('data-qt-notes')||'';
    presenterUi.notes.textContent=notes||'No speaker notes for this slide.';
    presenterUi.notes.setAttribute('data-empty',notes?'false':'true');
    presenterUi.nextFrame.replaceChildren();
    presenterUi.preview=null;
    if(current>=stages.length-1){
      presenterUi.nextLabel.textContent='End';
      var empty=document.createElement('div');empty.className='qt-presenter-empty';
      empty.textContent='End of deck';presenterUi.nextFrame.appendChild(empty);
      return;
    }
    presenterUi.nextLabel.textContent=(current+2)+' / '+stages.length;
    var preview=previewStage(stages[current+1]);
    presenterUi.nextFrame.appendChild(preview);presenterUi.preview=preview;
    if(fit)window.requestAnimationFrame(function(){qtFit(preview);});
  }
  function previewStage(stage){
    var clone=stage.cloneNode(true);
    clone.hidden=false;clone.style.display='block';clone.style.animation='';
    clone.style.zIndex='';clone.style.willChange='';clone.style.pointerEvents='none';
    var nodes=JSON.parse(clone.getAttribute('data-qt-timeline')||'[]');
    nodes.forEach(function(node){
      node.t.forEach(function(id){
        var element=clone.querySelector('#'+CSS.escape(id));
        if(element&&node.a==='entrance')element.style.visibility='visible';
      });
    });
    return clone;
  }
  function runTimeline(i){timelines[i].reset();return timelines[i].start();}
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
  function settle(restoredCursor){
    clearTimeout(hideTimer);
    transitioning=false;
    stages.forEach(function(s,j){
      s.style.animation='';s.style.zIndex='';s.style.willChange='';
      if(j!==current){s.style.display='none';s.hidden=true;}
      else{s.hidden=false;}
    });
    if(restoredCursor!==undefined)timelines[current].setPosition(restoredCursor);
    if(fit)qtFit(stages[current]);
    updatePresenter();
    scheduleAuto();
    publishState();
    if(needsInitialSync&&sync){
      needsInitialSync=false;
      sync.postMessage({action:'ready'});
    }
    flushPendingRemoteAdvance();
    flushPendingRemoteState();
  }
  function flushPendingRemoteAdvance(){
    if(!pendingRemoteAdvance||transitioning||timelineBusy)return;
    var next=pendingRemoteAdvance;pendingRemoteAdvance=null;
    if(next.slide!==current||!timelines[current].hasNext())return;
    timelines[current].setPosition(next.timeline);
    advance();
  }
  function flushPendingRemoteState(){
    if(!pendingRemoteState||transitioning||timelineBusy)return;
    var next=pendingRemoteState;pendingRemoteState=null;applyRemoteState(next);
  }
  function applyRemoteState(state){
    var next=normalizeState(state);
    if(!next)return;
    if(transitioning||timelineBusy){pendingRemoteState=next;return;}
    if(next.slide===current){
      timelines[current].setPosition(next.timeline);
      updatePresenter();scheduleAuto();
      return;
    }
    go(next.slide,next.slide<current,next.timeline);
  }
  function applyRemoteAdvance(state){
    var next=normalizeState(state);
    if(!next||next.slide!==current)return;
    if(transitioning||timelineBusy){pendingRemoteAdvance=next;return;}
    timelines[current].setPosition(next.timeline);
    advance();
  }
  function reverse(anim){return anim?anim+' reverse':'';}
  function go(i,backward,restoreCursor){
    if(transitioning||timelineBusy||i<0||i>=stages.length||i===current)return;
    clearAuto();
    transitioning=true;
    var out=stages[current],inc=stages[i];
    var source=backward?out:inc;
    current=i;
    if(backward){
      timelines[i].setPosition(
        restoreCursor===undefined?timelines[i].length():restoreCursor,
      );
    }else{
      timelines[i].reset();
    }
    publishState();
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
    if(!backward){
      var timelineRun=runTimeline(i);
      Promise.resolve(timelineRun).then(function(){
        if(current===i&&!transitioning){updatePresenter();publishState();}
      });
    }
    updatePresenter();
    var dur=parseFloat(source.getAttribute('data-qt-dur'))||0;
    clearTimeout(hideTimer);hideTimer=setTimeout(function(){settle(restoreCursor);},dur*1000+60);
  }
  function advance(){
    if(transitioning||timelineBusy)return;
    clearAuto();
    if(timelines[current].hasNext()){
      timelineBusy=true;
      sendSync({action:'advance',state:snapshot()});
      timelines[current].advance().then(function(){
        timelineBusy=false;updatePresenter();scheduleAuto();publishState();
        flushPendingRemoteAdvance();
        flushPendingRemoteState();
      });
    }
    else if(current<stages.length-1)go(current+1,false);
  }
  document.addEventListener('click',function(e){
    if(e&&e.target&&e.target.closest&&e.target.closest('[data-qt-presenter-control]'))return;
    if(canClick())advance();
  });
  document.addEventListener('keydown',function(e){
    if(e.target&&e.target.closest&&e.target.closest('[data-qt-presenter-control]'))return;
    if(e.key==='ArrowRight'||e.key===' '){if(canClick())advance();}
    else if(e.key==='ArrowLeft'){if(current>0)go(current-1,true);}
  });
  // First load plays slide 0's enter transition. A refresh restores the last
  // controlled slide in its settled state so presenter and audience views do
  // not diverge while one tab is reloading.
  if(savedState){
    stages.forEach(function(stage,j){
      if(j!==current){stage.style.display='none';stage.hidden=true;}
    });
    stages[current].hidden=false;stages[current].style.display='block';
    timelines[current].setPosition(savedState.timeline);
    settle();
  }else{
    if(fit)qtFit(stages[current]);
    updatePresenter();
    transitioning=true;
    stages[current].hidden=false;
    stages[current].style.display='block';
    stages[current].style.willChange='transform,opacity,clip-path';
    stages[current].style.animation=stages[current].getAttribute('data-qt-transition')||'';
    var initialTimeline=runTimeline(current);
    Promise.resolve(initialTimeline).then(function(){
      if(current===0){updatePresenter();publishState();}
    });
    var d0=parseFloat(stages[current].getAttribute('data-qt-dur'))||0;
    hideTimer=setTimeout(settle,d0*1000+60);
  }
})();
