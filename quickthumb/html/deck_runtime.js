(function(){
  var stages=Array.prototype.slice.call(document.querySelectorAll('.qt-stage'));
  if(!stages.length)return;
  var fit={{ responsive }};
  function syncPath(){
    return window.location.pathname==='/presenter'?'/':window.location.pathname;
  }
  function stateKey(){
    return 'quickthumb:slide:'+window.location.origin+syncPath();
  }
  function readSavedCurrent(){
    try{
      var value=window.localStorage&&window.localStorage.getItem(stateKey());
      if(value===null||value==='')return null;
      var index=Number(value);
      return Number.isInteger(index)&&index>=0&&index<stages.length?index:null;
    }catch(error){return null;}
  }
  function saveCurrent(){
    try{
      if(window.localStorage)window.localStorage.setItem(stateKey(),String(current));
    }catch(error){}
  }
  var savedCurrent=readSavedCurrent();
  var current=savedCurrent===null?0:savedCurrent;
  var hideTimer,autoTimer,transitioning=false,timelineBusy=false,applyingRemote=false;
  var timelines=stages.map(function(s){return new qtTimeline(s);});
  var presenter=presenterRequested();
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
        '<header class="qt-presenter-heading"><span>Current slide</span><span data-qt-current></span></header>'+
        '<div class="qt-presenter-current"></div>'+
      '</section>'+
      '<aside class="qt-presenter-sidebar">'+
        '<header class="qt-presenter-heading"><span>Next slide</span><span data-qt-next></span></header>'+
        '<div class="qt-presenter-next"></div>'+
        '<div class="qt-presenter-heading qt-presenter-notes-label"><span>Speaker notes</span></div>'+
        '<div class="qt-presenter-notes" aria-live="polite"></div>'+
        '<div><div class="qt-presenter-status">'+
          '<span data-qt-progress></span><button class="qt-presenter-timer" type="button" '+
          'title="Reset timer" data-qt-presenter-control>00:00</button></div>'+
          '<nav class="qt-presenter-controls" aria-label="Slide controls">'+
            '<button class="qt-presenter-control" type="button" data-qt-previous '+
            'data-qt-presenter-control>Previous</button>'+
            '<button class="qt-presenter-control" type="button" data-qt-forward '+
            'data-qt-presenter-control>Next</button>'+
            '<a class="qt-presenter-audience" target="_blank" rel="noopener" '+
            'data-qt-audience data-qt-presenter-control>Open audience view</a>'+
          '</nav></div>'+
      '</aside>';
    document.body.appendChild(shell);
    shell.querySelector('.qt-presenter-current').appendChild(frame);
    var ui={
      shell:shell,
      nextFrame:shell.querySelector('.qt-presenter-next'),
      notes:shell.querySelector('.qt-presenter-notes'),
      currentLabel:shell.querySelector('[data-qt-current]'),
      nextLabel:shell.querySelector('[data-qt-next]'),
      progress:shell.querySelector('[data-qt-progress]'),
      timer:shell.querySelector('.qt-presenter-timer'),
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
    var started=Date.now();
    function updateTimer(){
      var elapsed=Math.floor((Date.now()-started)/1000);
      var minutes=String(Math.floor(elapsed/60)).padStart(2,'0');
      var seconds=String(elapsed%60).padStart(2,'0');
      ui.timer.textContent=minutes+':'+seconds;
    }
    ui.timer.addEventListener('click',function(e){
      e.stopPropagation();started=Date.now();updateTimer();
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
    var channel=new window.BroadcastChannel('quickthumb:'+window.location.origin+syncPath());
    channel.addEventListener('message',function(event){
      var message=event.data||{};
      if(presenter){
        if(message.action==='ready')channel.postMessage({action:'go',index:current});
        return;
      }
      applyingRemote=true;
      if(message.action==='advance')advance();
      else if(message.action==='go')go(Number(message.index),Number(message.index)<current);
      applyingRemote=false;
    });
    return channel;
  }
  function sendSync(message){
    if(presenter&&sync&&!applyingRemote)sync.postMessage(message);
  }
  function updatePresenter(){
    if(!presenterUi)return;
    presenterUi.currentLabel.textContent=(current+1)+' / '+stages.length;
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
        if(element)element.style.visibility=node.a==='entrance'?'visible':'hidden';
      });
    });
    return clone;
  }
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
    updatePresenter();
    scheduleAuto();
    if(needsInitialSync&&sync){
      needsInitialSync=false;
      sync.postMessage({action:'ready'});
    }
  }
  function reverse(anim){return anim?anim+' reverse':'';}
  function go(i,backward){
    if(transitioning||timelineBusy||i<0||i>=stages.length||i===current)return;
    clearAuto();
    transitioning=true;
    var out=stages[current],inc=stages[i];
    var source=backward?out:inc;
    current=i;
    saveCurrent();
    sendSync({action:'go',index:i});
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
    updatePresenter();
    var dur=parseFloat(source.getAttribute('data-qt-dur'))||0;
    clearTimeout(hideTimer);hideTimer=setTimeout(settle,dur*1000+60);
  }
  function advance(){
    if(transitioning||timelineBusy)return;
    clearAuto();
    if(timelines[current].hasNext()){
      sendSync({action:'advance'});
      timelineBusy=true;
      timelines[current].advance().then(function(){
        timelineBusy=false;updatePresenter();scheduleAuto();
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
  if(savedCurrent!==null){
    stages.forEach(function(stage,j){
      if(j!==current){stage.style.display='none';stage.hidden=true;}
    });
    stages[current].hidden=false;stages[current].style.display='block';
    finishTimeline(current);
    settle();
  }else{
    if(fit)qtFit(stages[current]);
    updatePresenter();
    transitioning=true;
    stages[current].hidden=false;
    stages[current].style.display='block';
    stages[current].style.willChange='transform,opacity,clip-path';
    stages[current].style.animation=stages[current].getAttribute('data-qt-transition')||'';
    runTimeline(current);
    var d0=parseFloat(stages[current].getAttribute('data-qt-dur'))||0;
    hideTimer=setTimeout(settle,d0*1000+60);
  }
})();
