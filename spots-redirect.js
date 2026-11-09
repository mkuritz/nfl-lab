(function(){'use strict';
try{
 const p=new URLSearchParams(location.search);
 const view=p.get('view');p.delete('view');
 const qs=p.toString();
 const hash='#spots'+(view?'/'+view:'');
 window.__spotsRedirect='index.html'+(qs?'?'+qs:'')+hash;
 location.replace(window.__spotsRedirect);
}catch(e){window.__spotsRedirect='index.html#spots'}
})();
