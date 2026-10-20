const $ = id => document.getElementById(id);
let meetings = [], selected = null, tab = 'transcript', loading = false;
let cursor = null;
const stages = {importing:'Fetching the transcript and summary from Fathom.',imported:'Imported. Transcript and Fathom summary are ready; local pain-point analysis is optional.',analyzing:'Extracting evidence-linked notes with Ollama on this computer.',completed:'Notes ready. Verify important details against the transcript.',failed:'The last operation failed. Saved notes remain available.',interrupted:'The previous operation was interrupted; import or analyze again.'};
function notice(text) {$('notice').textContent=text;}
function el(tag,text,cls) {const n=document.createElement(tag); n.textContent=text; if(cls)n.className=cls;return n;}
function time(n){return new Date(Math.max(0,n)*1000).toISOString().slice(11,19);}
async function api(path,data) {const r=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});const v=await r.json();if(!r.ok)throw new Error(v.error||'Request failed');return v;}
async function refresh(){if(loading)return;loading=true;try{meetings=await api('/api/meetings');if(!selected&&meetings.length)selected=meetings[0].id;render();}catch(e){notice('Cannot reach the app: '+e.message);}finally{loading=false;}}
function render(){
 $('count').textContent=meetings.length; $('history').replaceChildren();
 if(!meetings.length)$('history').append(el('p','No meetings yet.','small'));
 for(const m of meetings){const b=el('button','',m.id===selected?'history selected':'history');b.append(el('strong',m.title),el('span',new Date(m.created).toLocaleString()+' · '+m.status));b.onclick=()=>{selected=m.id;render();};$('history').append(b);}
 const m=meetings.find(x=>x.id===selected);$('empty').hidden=!!m;$('meeting').hidden=!m;if(!m)return;
 $('meetingTitle').textContent=m.title;$('status').textContent=m.status;$('stage').textContent=(stages[m.status]||m.status)+(m.error?' '+m.error:'')+(m.warning?' '+m.warning:'');
 $('reimport').hidden=!m.recording_id; $('retry').hidden=!m.segments.length||['importing','analyzing'].includes(m.status);$('export').hidden=!m.segments.length;$('export').href=`/api/meetings/${m.id}/export`;
 $('content').replaceChildren();document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('selected',b.dataset.tab===tab));
 if(tab==='transcript'){
  $('content').append(el('p','Transcript from Fathom · Speaker names are shown when supplied.','small'));
  for(const s of m.segments){const row=el('div','', 'segment');row.append(el('time',time(s.start)),el('p',(s.speaker?s.speaker+': ':'')+s.text));$('content').append(row);}
  if(!m.segments.length)$('content').append(el('p','The transcript will appear after a successful import.','placeholder'));
 }else if(!m.report){if(tab==='summary')showFathom(m);else $('content').append(el('p','Click Analyze pain points after installing Ollama and downloading the model. Transcript and Fathom summary do not require Ollama.','placeholder'));}
 else{
  if(tab==='summary')showFathom(m);
  const categories=tab==='summary'?['summary','actions']:['pain_points'];
  for(const cat of categories){$('content').append(el('h3',cat==='summary'?'Key discussion points':cat==='actions'?'Action items':'Problems raised'));
   const rows=m.report[cat]||[];if(!rows.length)$('content').append(el('p','No supported items extracted.','small'));
   for(const row of rows){const card=el('div','','note');card.append(el('p',row.text));if(cat==='actions')card.append(el('p',`Owner: ${row.owner} · Due: ${row.deadline}`,'small'));card.append(el('blockquote',`[${time(row.start)}] “${row.quote}”`));$('content').append(card);}
  }
  $('content').append(el('p','AI-generated notes: matching quotes support review but do not guarantee every interpretation is correct.','small'));
  if(m.report.rejected_items)$('content').append(el('p',`${m.report.rejected_items} model entries were omitted because their evidence could not be matched.`,'small'));
 }
}
function showFathom(m){$('content').append(el('h3','Fathom summary'));$('content').append(el('div',m.fathom_summary||'Fathom has not returned a summary yet. Refresh the recording later.','fathom-summary'));}
async function importRecording(rid,title){notice('');try{const m=await api('/api/fathom/import',{recording_id:rid,title});selected=m.id;await refresh();}catch(e){notice(e.message);}}
async function loadRemote(more=false){$('load').disabled=true;$('more').disabled=true;try{const page=await api('/api/fathom/meetings',{cursor:more?cursor:''});if(!more)$('remote').replaceChildren();for(const m of page.items){const row=el('div','','remote-row');const label=el('div');label.append(el('strong',m.title),el('p',`${m.created} · ${m.recorded_by}`,'small'));const btn=el('button','Import','secondary');btn.onclick=async()=>{btn.disabled=true;try{await importRecording(m.recording_id,m.title);}finally{btn.disabled=false;}};row.append(label,btn);$('remote').append(row);}cursor=page.next_cursor;$('more').hidden=!cursor;if(!page.items.length&&!more)$('remote').append(el('p','No recordings found. Finish a Fathom recording first.','small'));notice('');}catch(e){notice(e.message);}finally{$('load').disabled=false;$('more').disabled=false;}}
$('load').onclick=()=>loadRemote();$('more').onclick=()=>loadRemote(true);
$('reimport').onclick=()=>{const m=meetings.find(x=>x.id===selected);if(m)importRecording(m.recording_id,m.title);};
for(const [id,action] of [['retry','analyze'],['delete','delete']])$(id).onclick=async()=>{if(action==='delete'&&!confirm('Delete the local copy of this meeting? The original in Fathom will remain.'))return;$(id).disabled=true;try{await api(`/api/meetings/${selected}/${action}`,{});if(action==='delete')selected=null;notice('');await refresh();}catch(e){notice(e.message);}finally{$(id).disabled=false;}};
api('/api/health').then(h=>{$('connection').textContent=h.fathom_configured?'API key configured locally. Load recordings to test the connection.':'Add FATHOM_API_KEY to .env and restart the app. Never paste it into chat or GitHub.';}).catch(e=>notice(e.message));
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;render();});
refresh();setInterval(refresh,4000);
