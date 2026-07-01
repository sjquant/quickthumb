(function(){
  var stage=document.querySelector('.qt-stage');
  if(!stage)return;
  var fit={{ responsive }};
  if(fit){function r(){qtFit(stage);}
    if(window.ResizeObserver){new ResizeObserver(r).observe(stage.parentElement);}
    else{window.addEventListener('resize',r);}r();}
  var tl=new qtTimeline(stage);
  tl.start();
  document.addEventListener('click',function(){if(tl.hasNext())tl.advance();});
})();
