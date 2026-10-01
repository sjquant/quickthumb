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
  var generation=0;
  var activeTransforms={};
  // Cache element references and animation inline state once at construction.
  // Avoids repeated querySelector in the per-frame animation hot path.
  var elMap={};
  var origClips={};
  var origOpacity={};
  function transformValues(el,values){
    Object.keys(values||{}).forEach(function(name){el.style.setProperty(name,values[name]);});
  }
  function cancelTransform(id){
    if(activeTransforms[id])activeTransforms[id]();
  }
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
  function setInitialElements(){
    var seen={};
    nodes.forEach(function(node){
      node.t.forEach(function(id){
        var el=elMap[id];
        if(!el||seen[id])return;
        seen[id]=true;
        cancelTransform(id);
        el.style.animation='';el.style.willChange='';
        if(node.a==='transform'){
          transformValues(el,node.initial);el.style.visibility='visible';
        }else if(node.a==='entrance'){
          el.style.visibility='hidden';
          el.style.clipPath=origClips[id]||'';el.style.opacity=origOpacity[id]||'';
        }else{
          el.style.visibility='visible';
        }
      });
    });
  }
  function play(node,run){
    return new Promise(function(res){
      var dur=0;
      var transformSettlers=[];
      node.t.forEach(function(id){
        var el=elMap[id];
        if(!el)return;
        var origClip=origClips[id]||'';
        var origOp=origOpacity[id]||'';
        el.style.willChange=node.a==='transform'?'transform,opacity':'clip-path,opacity';
        el.style.visibility='visible';
        if(node.a==='transform'){
          cancelTransform(id);
          el.style.animation='';
          // Commit the cleared animation before replaying the same keyframes.
          void el.offsetWidth;
        }
        el.style.animation=node.k+' '+node.d+'s '+(node.e||'ease')+
          (node.a==='transform'?' forwards ':' both ')+node.delay+'s';
        var cancelled=false;
        function cancel(){
          cancelled=true;
          el.removeEventListener('animationend',settle);
          delete activeTransforms[id];
        }
        function settle(){
          if(node.a==='transform'){
            if(cancelled||run!==generation)return;
            transformValues(el,node.final);
            cancel();
          }
          el.style.willChange='';
          el.style.animation='';
          if(node.a==='entrance'){el.style.clipPath=origClip;el.style.opacity=origOp;}
          else if(node.a!=='transform'){el.style.visibility='hidden';}
        }
        el.addEventListener('animationend',settle,{once:true});
        if(node.a==='transform'){
          activeTransforms[id]=cancel;transformSettlers.push(settle);
        }
        dur=Math.max(dur,(node.d+node.delay)*1000);
      });
      setTimeout(function(){transformSettlers.forEach(function(settle){settle();});res();},dur);
    });
  }
  function withCompanions(i){
    var group=[nodes[i]];var j=i+1;
    while(j<nodes.length&&nodes[j].tr==='with_previous'){group.push(nodes[j]);j++;}
    return {group:group,next:j};
  }
  async function runGroup(i,run){
    var gc=withCompanions(i);
    await Promise.all(gc.group.map(function(node){return play(node,run);}));
    if(run!==generation)return;
    cursor=gc.next;
    while(cursor<nodes.length&&nodes[cursor].tr==='after_previous'){
      var ac=withCompanions(cursor);
      await Promise.all(ac.group.map(function(node){return play(node,run);}));
      if(run!==generation)return;
      cursor=ac.next;
    }
  }
  async function autoLead(){
    var run=generation;
    while(run===generation&&cursor<nodes.length&&nodes[cursor].tr==='after_previous'){
      await runGroup(cursor,run);
    }
  }
  function finishElements(){
    nodes.forEach(function(node){
      node.t.forEach(function(id){
        var el=elMap[id];
        if(!el)return;
        cancelTransform(id);
        el.style.animation='';
        el.style.willChange='';
        if(node.a==='transform'){
          transformValues(el,node.final);el.style.visibility='visible';
        }else if(node.a==='entrance'){
          el.style.visibility='visible';
          el.style.clipPath=origClips[id]||'';el.style.opacity=origOpacity[id]||'';
        }else{
          el.style.visibility='hidden';
        }
      });
    });
  }
  function setElementsAt(position){
    setInitialElements();
    nodes.forEach(function(node,index){
      if(index>=position)return;
      node.t.forEach(function(id){
        var el=elMap[id];
        if(!el)return;
        if(node.a==='transform'){
          transformValues(el,node.final);el.style.visibility='visible';
        }else if(node.a==='entrance'){
          el.style.visibility='visible';
          el.style.clipPath=origClips[id]||'';el.style.opacity=origOpacity[id]||'';
        }else{
          el.style.visibility='hidden';
        }
      });
    });
  }
  this.hasNext=function(){return cursor<nodes.length;};
  this.length=function(){return nodes.length;};
  this.position=function(){return cursor;};
  this.setPosition=function(position){
    generation++;
    var next=Math.max(0,Math.min(nodes.length,Number(position)||0));
    setElementsAt(next);cursor=next;
  };
  this.advance=function(){if(cursor<nodes.length)return runGroup(cursor,generation);return Promise.resolve();};
  this.reset=function(){generation++;cursor=0;setInitialElements();};
  this.finish=function(){generation++;finishElements();cursor=nodes.length;};
  this.start=autoLead;
}
