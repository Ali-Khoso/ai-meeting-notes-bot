import {createService,AppError} from '../lib/service.js';
export default async function handler(req,res) {
  res.setHeader('Cache-Control','no-store');
  if(req.method!=='POST') return res.status(405).json({error:'Use POST.'});
  if(!req.headers['content-type']?.startsWith('application/json')) return res.status(415).json({error:'Use JSON.'});
  // No cross-origin access and no cookie authentication.
  if(req.headers['sec-fetch-site']==='cross-site') return res.status(403).json({error:'Cross-site request rejected.'});
  try {
    const body=typeof req.body==='string'?JSON.parse(req.body):req.body;
    if(!body||Buffer.byteLength(JSON.stringify(body))>12000) throw new AppError('Invalid request.');
    const token=req.headers.authorization?.match(/^Bearer (.+)$/)?.[1];
    const result=await createService(process.env)(body.action,body,token);
    return res.status(200).json(result);
  } catch(e) {return res.status(e instanceof AppError?e.status:500).json({error:e instanceof AppError?e.message:'Request failed. Please retry.'});}
}
