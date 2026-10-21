const $=id=>document.getElementById(id);
let token='',cursor=null,selected=null,busy=false;
const status=text=>{$('status').textContent=text;};
async function api(action,data={}) {
  const r=await fetch('/api/meetings',{method:'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},body:JSON.stringify({action,...data})});
  const result=await r.json();
  if(!r.ok){if(r.status===401)signOut();throw new Error(result.error||'Request failed.');}return result;
}
async function run(fn) {
  if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);status('Working…');
  try{await fn();}catch(e){status(e.message||'Please retry.');}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);}
}
function signOut(){token='';selected=null;cursor=null;$('workspace').hidden=true;$('login').hidden=false;$('remote').replaceChildren();$('saved').replaceChildren();$('content').textContent='';$('details').hidden=true;$('title').textContent='Select a saved meeting';$('date').textContent='';}
function row(container,label,buttonText,fn){const div=document.createElement('div');div.className='row';const span=document.createElement('span');span.textContent=label;const b=document.createElement('button');b.textContent=buttonText;b.onclick=()=>run(fn);div.append(span,b);container.append(div);}
async function saved(){const data=await api('list');$('saved').replaceChildren();if(!data.length)$('saved').textContent='No meetings saved yet.';data.forEach(m=>row($('saved'),m.title,'Open',async()=>{const rows=await api('read',{id:m.recording_id});if(!rows.length)throw new Error('Meeting no longer exists.');selected=rows[0];$('title').textContent=selected.title;$('date').textContent='Imported '+new Date(selected.imported_at).toLocaleString();$('details').hidden=false;showTranscript();status('Loaded from your database.');}));}
function showTranscript(){$('content').textContent=selected?.transcript.map(r=>`[${r.timestamp}] ${r.speaker}: ${r.text}`).join('\n\n')||'';}
async function recordings(more=false){const data=await api('recordings',{cursor:more?cursor:null});if(!more)$('remote').replaceChildren();data.items.forEach(m=>row($('remote'),m.title,'Import',async()=>{const result=await api('import',{id:m.recording_id,title:m.title});await saved();status(result.warning||'Transcript and summary saved to your database.');}));cursor=data.next_cursor;$('more').hidden=!cursor;status(data.items.length?'Choose a recording to import.':'No recordings found.');}
$('login').onsubmit=e=>{e.preventDefault();run(async()=>{const result=await api('login',{email:$('email').value,password:$('password').value});token=result.access_token;$('password').value='';$('login').hidden=true;$('workspace').hidden=false;await saved();status('Signed in.');});};
$('load').onclick=()=>run(()=>recordings());$('more').onclick=()=>run(()=>recordings(true));$('refresh').onclick=()=>run(async()=>{await saved();status('Saved meetings refreshed.');});$('logout').onclick=()=>{signOut();status('Signed out on this page.');};
$('transcriptTab').onclick=showTranscript;$('summaryTab').onclick=()=>{$('content').textContent=selected?.summary||'Summary not available. Try importing again later.';};
$('delete').onclick=()=>{if(!selected||!confirm('Delete this database copy? The original stays in Fathom.'))return;run(async()=>{await api('delete',{id:selected.recording_id});selected=null;$('details').hidden=true;$('title').textContent='Select a saved meeting';$('date').textContent='';$('content').textContent='';await saved();status('Database copy deleted.');});};
$('export').onclick=()=>{if(!selected)return;const text=selected.title+'\n\n'+selected.transcript.map(r=>`[${r.timestamp}] ${r.speaker}: ${r.text}`).join('\n\n')+'\n\nSUMMARY\n'+selected.summary;const url=URL.createObjectURL(new Blob([text],{type:'text/plain'}));const a=document.createElement('a');a.href=url;a.download='meeting-'+selected.recording_id+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
