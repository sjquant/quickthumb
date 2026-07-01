function qtFit(stage){
  var f=stage.parentElement;
  var s=Math.min(
    f.clientWidth/parseInt(stage.style.width),
    f.clientHeight/parseInt(stage.style.height)
  );
  // Expose the scale as a custom property so transform-based slide transitions
  // can compose with it; transitions that don't touch transform keep this.
  stage.style.setProperty('--qt-stage-x','-50%');
  stage.style.setProperty('--qt-stage-y','-50%');
  stage.style.setProperty('--qt-scale', s);
  stage.style.transform='translate(var(--qt-stage-x),var(--qt-stage-y)) scale('+s+')';
}

function qtTimeline(stage){
  var nodes=JSON.parse(stage.getAttribute('data-qt-timeline')||'[]');
  var cursor=0;
  // Cache element references and animation inline state once at construction.
  // Avoids repeated querySelector in the per-frame animation hot path.
  var elMap={};
  var origClips={};
  var origOpacity={};
  nodes.forEach(function(node){
    var isEntrance=node.a==='entrance';
    node.t.forEach(function(id){
      if(!elMap[id]){var el=stage.querySelector('#'+CSS.escape(id));if(el)elMap[id]=el;}
      if(elMap[id]&&!(id in origOpacity)){
        origOpacity[id]=elMap[id].style.opacity;
        elMap[id].style.setProperty('--qt-opacity',origOpacity[id]||'1');
      }
      if(isEntrance&&elMap[id]&&!(id in origClips)){
        origClips[id]=elMap[id].style.clipPath;
      }
    });
  });
  function resetElements(){
    nodes.forEach(function(node){
      if(node.a==='entrance'){
        node.t.forEach(function(id){
          var el=elMap[id];
          if(el){
            el.style.visibility='hidden';el.style.animation='';
            el.style.clipPath=origClips[id]||'';el.style.opacity=origOpacity[id]||'';
          }
        });
      }
    });
  }
  function play(node){
    return new Promise(function(res){
      var dur=0;
      node.t.forEach(function(id){
        var el=elMap[id];
        if(!el)return;
        var origClip=origClips[id]||'';
        var origOp=origOpacity[id]||'';
        el.style.willChange='clip-path,opacity';
        el.style.visibility='visible';
        el.style.animation=node.k+' '+node.d+'s ease both '+node.delay+'s';
        function settle(){
          el.style.willChange='';
          el.style.animation='';
          if(node.a==='entrance'){el.style.clipPath=origClip;el.style.opacity=origOp;}
          else{el.style.visibility='hidden';}
        }
        el.addEventListener('animationend',settle,{once:true});
        dur=Math.max(dur,(node.d+node.delay)*1000);
      });
      setTimeout(res,dur);
    });
  }
  function withCompanions(i){
    var group=[nodes[i]];var j=i+1;
    while(j<nodes.length&&nodes[j].tr==='with_previous'){group.push(nodes[j]);j++;}
    return {group:group,next:j};
  }
  async function runGroup(i){
    var gc=withCompanions(i);
    await Promise.all(gc.group.map(play));
    cursor=gc.next;
    while(cursor<nodes.length&&nodes[cursor].tr==='after_previous'){
      var ac=withCompanions(cursor);
      await Promise.all(ac.group.map(play));
      cursor=ac.next;
    }
  }
  async function autoLead(){
    while(cursor<nodes.length&&nodes[cursor].tr==='after_previous'){await runGroup(cursor);}
  }
  function finishElements(){
    nodes.forEach(function(node){
      node.t.forEach(function(id){
        var el=elMap[id];
        if(!el)return;
        el.style.animation='';
        el.style.willChange='';
        if(node.a==='entrance'){
          el.style.visibility='visible';
          el.style.clipPath=origClips[id]||'';el.style.opacity=origOpacity[id]||'';
        }else{
          el.style.visibility='hidden';
        }
      });
    });
  }
  this.hasNext=function(){return cursor<nodes.length;};
  this.advance=function(){if(cursor<nodes.length)return runGroup(cursor);return Promise.resolve();};
  this.reset=function(){cursor=0;resetElements();};
  this.finish=function(){finishElements();cursor=nodes.length;};
  this.start=autoLead;
}
