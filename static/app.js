const $ = id => document.getElementById(id);
let meetings = [], selected = null, tab = 'transcript', loading = false;
const stages = {starting:'Opening the meeting. This can take about a minute.',waiting:'Waiting for you to admit the bot in Google Meet.',recording:'Recording meeting audio. Click Stop & generate notes when finished.',transcribing:'Transcribing locally. The first run downloads the speech model; CPU processing may take time.',analyzing:'Preparing evidence-linked notes with your local model.',completed:'Notes ready. Check important details against the transcript.',failed:'The job could not finish. Any saved transcript is still available.',interrupted:'The previous job was interrupted.',cancelled:'Cancelled before recording.',no_speech:'No speech detected.'};
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
 $('meetingTitle').textContent=m.title;$('status').textContent=m.status;$('stage').textContent=(stages[m.status]||m.status)+(m.error?' '+m.error:'');
 $('stop').hidden=!['starting','waiting','recording'].includes(m.status);$('retry').hidden=!m.segments.length||['starting','waiting','recording','transcribing','analyzing'].includes(m.status);$('export').hidden=!m.segments.length;$('export').href=`/api/meetings/${m.id}/export`;
 $('content').replaceChildren();document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('selected',b.dataset.tab===tab));
 if(tab==='transcript'){
  $('content').append(el('p','Audio transcript · Speaker identities are not detected in this version.','small'));
  for(const s of m.segments){const row=el('div','', 'segment');row.append(el('time',time(s.start)),el('p',s.text));$('content').append(row);}
  if(!m.segments.length)$('content').append(el('p','The full transcript will appear after recording and transcription.','placeholder'));
 }else if(!m.report){$('content').append(el('p','Notes will appear after local analysis finishes.','placeholder'));}
 else{
  const categories=tab==='summary'?['summary','actions']:['pain_points'];
  for(const cat of categories){$('content').append(el('h3',cat==='summary'?'Key discussion points':cat==='actions'?'Action items':'Problems raised'));
   const rows=m.report[cat]||[];if(!rows.length)$('content').append(el('p','No supported items extracted.','small'));
   for(const row of rows){const card=el('div','','note');card.append(el('p',row.text));if(cat==='actions')card.append(el('p',`Owner: ${row.owner} · Due: ${row.deadline}`,'small'));card.append(el('blockquote',`[${time(row.start)}] “${row.quote}”`));$('content').append(card);}
  }
  $('content').append(el('p','AI-generated notes: matching quotes support review but do not guarantee every interpretation is correct.','small'));
  if(m.report.rejected_items)$('content').append(el('p',`${m.report.rejected_items} model entries were omitted because their evidence could not be matched.`,'small'));
 }
}
$('join').onsubmit=async e=>{e.preventDefault();$('joinBtn').disabled=true;notice('');try{const m=await api('/api/meetings',{title:$('title').value,url:$('url').value,consent:$('consent').checked});selected=m.id;await refresh();}catch(e){notice(e.message);}finally{$('joinBtn').disabled=false;}};
for(const [id,action] of [['stop','stop'],['retry','analyze'],['delete','delete']])$(id).onclick=async()=>{if(action==='delete'&&!confirm('Delete this meeting, its audio and notes from this computer?'))return;$(id).disabled=true;try{await api(`/api/meetings/${selected}/${action}`,{});if(action==='delete')selected=null;notice(action==='stop'?'Stopping the bot. Notes will be generated next.':'');await refresh();}catch(e){notice(e.message);}finally{$(id).disabled=false;}};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;render();});
refresh();setInterval(refresh,4000);
