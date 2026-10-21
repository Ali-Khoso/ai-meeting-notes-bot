export class AppError extends Error { constructor(message, status=400) { super(message); this.status=status; } }
export function recordingId(value) {
  const id=String(value ?? '');
  if (!/^[1-9][0-9]{0,19}$/.test(id)) throw new AppError('Select a valid recording.');
  return id;
}
export function transcript(raw) {
  if (!Array.isArray(raw?.transcript) || !raw.transcript.length) throw new AppError('Transcript is not ready. Try again after Fathom finishes processing.');
  const rows=raw.transcript.map((r,i)=> {
    if(typeof r.text!=='string' || typeof r.timestamp!=='string') throw new AppError('Invalid transcript received.');
    return {id:i, speaker:String(r.speaker?.display_name || 'Unknown speaker'), timestamp:r.timestamp, text:r.text};
  }).filter(r=>r.text.trim());
  if(!rows.length) throw new AppError('No spoken transcript available.');
  if(Buffer.byteLength(JSON.stringify(rows))>2000000) throw new AppError('Transcript exceeds the 2 MB import limit.');
  return rows;
}
export function createService(env, fetcher=fetch) {
  const base=(env.SUPABASE_URL||'').replace(/\/$/,'');
  if(!/^https:\/\/[a-z0-9.-]+$/.test(base) || !env.SUPABASE_ANON_KEY || !env.ALLOWED_USER_ID) throw new AppError('Server setup is incomplete. Follow cloud/README.md.',503);
  async function request(url,options={},label='Service') {
    let response;
    try { response=await fetcher(url,{...options,redirect:'error',signal:AbortSignal.timeout(15000)}); }
    catch {throw new AppError(`${label} is unavailable. Please retry.`,502);}
    if(!response.ok) throw new AppError(`${label} request failed (${response.status}).`,response.status===401?401:502);
    if(response.status===204) return null;
    const body=await response.text();
    if(!body) return null;
    if(Buffer.byteLength(body)>4000000) throw new AppError(`${label} response exceeds the import limit.`,502);
    try{return JSON.parse(body);}catch{throw new AppError(`${label} returned invalid data.`,502);}
  }
  const headers=token=>({apikey:env.SUPABASE_ANON_KEY,Authorization:`Bearer ${token}`,'Content-Type':'application/json'});
  async function user(token) {
    if(!token) throw new AppError('Please sign in.',401);
    const u=await request(`${base}/auth/v1/user`,{headers:headers(token)},'Sign-in');
    if(u.id!==env.ALLOWED_USER_ID) throw new AppError('This dashboard is private.',403);
    return u;
  }
  async function fathom(path) {
    if(!env.FATHOM_API_KEY) throw new AppError('FATHOM_API_KEY is missing on the server.',503);
    return request(`https://api.fathom.ai/external/v1${path}`,{headers:{'X-Api-Key':env.FATHOM_API_KEY}},'Fathom');
  }
  return async function execute(action,body,token) {
    if(action==='login') {
      if(typeof body.email!=='string'||typeof body.password!=='string'||body.email.length>320||body.password.length>1024) throw new AppError('Enter your email and password.');
      const session=await request(`${base}/auth/v1/token?grant_type=password`,{method:'POST',headers:{apikey:env.SUPABASE_ANON_KEY,'Content-Type':'application/json'},body:JSON.stringify({email:body.email,password:body.password})},'Sign-in');
      await user(session.access_token);
      return {access_token:session.access_token}; // Memory-only session; no refresh token in browser storage.
    }
    const u=await user(token);
    const db=(query,options={})=>request(`${base}/rest/v1/meetings${query}`,{...options,headers:{...headers(token),...options.headers}},'Database');
    const owner=`owner_id=eq.${encodeURIComponent(u.id)}`;
    if(action==='list') return db(`?${owner}&select=recording_id,title,imported_at&order=imported_at.desc&limit=100`);
    if(action==='read') return db(`?${owner}&recording_id=eq.${recordingId(body.id)}&select=*`);
    if(action==='delete') {await db(`?${owner}&recording_id=eq.${recordingId(body.id)}`,{method:'DELETE'});return {ok:true};}
    if(action==='recordings') {
      const cursor=body.cursor||'';
      if(typeof cursor!=='string'||cursor.length>2000) throw new AppError('Invalid cursor.');
      const data=await fathom(`/meetings${cursor?'?cursor='+encodeURIComponent(cursor):''}`);
      if(!Array.isArray(data.items)) throw new AppError('Invalid Fathom recording list.',502);
      return {items:data.items.map(r=>({recording_id:recordingId(r.recording_id),title:String(r.title||r.meeting_title||'Untitled meeting')})),next_cursor:data.next_cursor||null};
    }
    if(action==='import') {
      const id=recordingId(body.id);
      const rows=transcript(await fathom(`/recordings/${id}/transcript`));
      let summary='',warning=null;
      try {const s=await fathom(`/recordings/${id}/summary`);summary=s.summary?.markdown_formatted||'';if(typeof summary!=='string') throw new Error();}
      catch {warning='Transcript saved; Fathom summary is not available yet.';}
      const record={owner_id:u.id,recording_id:id,title:String(body.title||'Untitled meeting').slice(0,300),transcript:rows,summary,imported_at:new Date().toISOString()};
      await db('?on_conflict=owner_id,recording_id',{method:'POST',headers:{Prefer:'resolution=merge-duplicates,return=minimal'},body:JSON.stringify(record)});
      return {ok:true,warning};
    }
    throw new AppError('Unknown action.',404);
  };
}
