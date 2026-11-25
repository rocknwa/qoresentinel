'use client';
import {useEffect,useRef,useState} from 'react';
import {Activity,ArrowRight,Bell,BookOpen,CheckCircle2,ChevronDown,CircleAlert,Clock3,CloudUpload,Code2,CreditCard,Download,FileCode2,FileSearch,FileText,Fingerprint,FolderOpen,HelpCircle,Hexagon,LayoutDashboard,LockKeyhole,Menu,MessageSquareText,Plus,Radio,RefreshCcw,Search,Settings2,Shield,ShieldAlert,ShieldCheck,Sparkles,Upload,Wallet, X} from 'lucide-react';
import {api,setAccessToken,type Audit,type AuditSummary,type AuditMessage,type ChainTx,type Project,type PqcScan,type TxEvidence,type PaymentIntent} from '@/lib/api';
import {connectQoreX,loginProof,nativeSend,sendHybridProof,FAUCET_URL} from '@/lib/wallet';

type View='overview'|'new-audit'|'audit-progress'|'audit-results'|'audit-history'|'transaction-history'|'assistant'|'pqc'|'billing'|'settings';
const agentNames=['Access Control','Asymmetry','Boundary','Economic Security','Execution Trace','First Principles','Flow Gap','Invariant','Math Precision','Numerical Gap','Periphery','Trust Gap'];
const menu:{id:View;name:string;icon:typeof Shield;group:string}[]=[
 {id:'overview',name:'Overview',icon:LayoutDashboard,group:'WORKSPACE'},
 {id:'new-audit',name:'New Audit',icon:FileSearch,group:'WORKSPACE'},
 {id:'audit-progress',name:'Audit Progress',icon:Activity,group:'SECURITY'},
 {id:'audit-results',name:'Audit Results',icon:ShieldAlert,group:'SECURITY'},
 {id:'audit-history',name:'Audit History',icon:BookOpen,group:'SECURITY'},
 {id:'transaction-history',name:'Transaction History',icon:Activity,group:'MANAGEMENT'},
 {id:'assistant',name:'AI Assistant',icon:MessageSquareText,group:'SECURITY'},
 {id:'pqc',name:'PQC Readiness',icon:Fingerprint,group:'SECURITY'},
 {id:'billing',name:'Billing & Usage',icon:CreditCard,group:'MANAGEMENT'},
 {id:'settings',name:'Settings',icon:Settings2,group:'MANAGEMENT'},
];
function Status({tone='neutral',children}:{tone?:'neutral'|'good'|'warn'|'cyan';children:React.ReactNode}){return <span className={`status ${tone}`}>{children}</span>}
function Empty({icon:Icon=FolderOpen,title,desc,action}:{icon?:typeof Shield;title:string;desc:string;action?:React.ReactNode}){return <div className="empty"><Icon size={28}/><h3>{title}</h3><p>{desc}</p>{action}</div>}
function Header({title,kicker,sub,action}:{title:string;kicker:string;sub:string;action?:React.ReactNode}){return <div className="page-heading"><div><div className="eyebrow">{kicker}</div><h1>{title}</h1><p>{sub}</p></div>{action}</div>}
export default function Home(){
 const [view,setView]=useState<View>('overview');const [menuOpen,setMenuOpen]=useState(false);
 const [backend,setBackend]=useState<'checking'|'online'|'offline'>('checking');
 const [projectName,setProjectName]=useState('My Solidity Project');const [project,setProject]=useState<Project|null>(null);const [recentProjects,setRecentProjects]=useState<Project[]>([]);
 const [source,setSource]=useState('// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n\ncontract MyContract {\n    // Paste your Solidity code here\n}');
 const [files,setFiles]=useState<File[]>([]);const [mode,setMode]=useState<'paste'|'upload'>('paste');
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const [audit,setAudit]=useState<Audit|null>(null);const [agentExpanded,setAgentExpanded]=useState(false);
 const fileRef=useRef<HTMLInputElement>(null);
 const [nativeAddress,setNativeAddress]=useState('');const [signedIn,setSignedIn]=useState(false);
 const [gasBalance,setGasBalance]=useState<string|null>(null);
 const [pendingLogin,setPendingLogin]=useState<{address:string;challenge_id:string;tx_hash:string}|null>(null);
 const [needsFaucet,setNeedsFaucet]=useState(false);
 const [jobId,setJobId]=useState('');const [agentDone,setAgentDone]=useState(0);
 const [pqcScan,setPqcScan]=useState<PqcScan|null>(null);
 const [txHash,setTxHash]=useState('');const [hybridSendStatus,setHybridSendStatus]=useState('');const [txEvidence,setTxEvidence]=useState<TxEvidence|null>(null);
 const [paymentIntent,setPaymentIntent]=useState<PaymentIntent|null>(null);
 const [paymentHash,setPaymentHash]=useState('');const [paymentResult,setPaymentResult]=useState('');
 const [subscription,setSubscription]=useState<{plan:string;expires_at:number|null}|null>(null);
 const [question,setQuestion]=useState('');const [assistantAnswer,setAssistantAnswer]=useState('');
 const [allAudits,setAllAudits]=useState<AuditSummary[]>([]);
 const [moreAudits,setMoreAudits]=useState(false);
 const [moreTransactions,setMoreTransactions]=useState(false);
 const [transactions,setTransactions]=useState<ChainTx[]>([]);
 const [auditMessages,setAuditMessages]=useState<AuditMessage[]>([]);
 const [auditQuestion,setAuditQuestion]=useState('');
 const [chatBusy,setChatBusy]=useState(false);
 const [selectedAuditId,setSelectedAuditId]=useState('');
 const [loadingHistory,setLoadingHistory]=useState(false);
 const [loadHistoryError,setLoadHistoryError]=useState('');
 function refreshAuditHistory(){
   if(!signedIn)return;
   api.audits().then(x=>{setAllAudits(x.audits);setMoreAudits(x.has_more)}).catch(e=>setLoadHistoryError(e instanceof Error?e.message:'Could not load audits'));
 }
 function refreshTransactions(){
   if(!signedIn)return;
   api.transactions().then(x=>{setTransactions(x.transactions);setMoreTransactions(x.has_more)}).catch(e=>setLoadHistoryError(e instanceof Error?e.message:'Could not load transactions'));
 }
 async function openAudit(jobId:string){
   if(!signedIn)return;
   setLoadingHistory(true);setError('');setLoadHistoryError('');
   try{
     const loaded=await api.audit(jobId);
     const matching=allAudits.find(x=>x.id===jobId);
     const existing=recentProjects.find(x=>x.id===loaded.project_id);
     setProject(existing||{id:loaded.project_id,name:matching?.project_name||'Saved audit'});
     setAudit(loaded);setSelectedAuditId(jobId);setAuditQuestion('');setAuditMessages([]);
     const messages=await api.auditMessages(jobId);
     setAuditMessages(messages.messages);setView('audit-results');
   }catch(e){setLoadHistoryError(e instanceof Error?e.message:'Could not open saved audit');}
   finally{setLoadingHistory(false);}
 }
 async function askAuditQuestion(){
   if(!audit||!auditQuestion.trim()||!selectedAuditId)return;
   setChatBusy(true);setError('');const question=auditQuestion.trim();
   try{
     await api.auditQuestion(selectedAuditId,question);
     const messages=await api.auditMessages(selectedAuditId);
     setAuditMessages(messages.messages);setAuditQuestion('');
   }catch(e){setError(e instanceof Error?e.message:'Could not save audit discussion');}
   finally{setChatBusy(false);}
 }
 async function loadMoreAudits(){
   if(loadingHistory)return;setLoadingHistory(true);
   try{const page=await api.audits(allAudits.length);setAllAudits(prev=>[...prev,...page.audits]);setMoreAudits(page.has_more);}
   catch(e){setLoadHistoryError(e instanceof Error?e.message:'Could not load more audits');}
   finally{setLoadingHistory(false);}
 }
 async function loadMoreTransactions(){
   if(loadingHistory)return;setLoadingHistory(true);
   try{const page=await api.transactions(transactions.length);setTransactions(prev=>[...prev,...page.transactions]);setMoreTransactions(page.has_more);}
   catch(e){setLoadHistoryError(e instanceof Error?e.message:'Could not load more transactions');}
   finally{setLoadingHistory(false);}
 }
 function afterLogin(token:string){
   setAccessToken(token);setSignedIn(true);setPendingLogin(null);setNeedsFaucet(false);
   setNotice('QoreX native wallet authenticated on Diana testnet.');
   api.subscription().then(setSubscription).catch(()=>{});
   api.listProjects().then(x=>setRecentProjects(x.projects)).catch(()=>{});
   api.audits().then(x=>{setAllAudits(x.audits);setMoreAudits(x.has_more)}).catch(()=>{});
   api.transactions().then(x=>{setTransactions(x.transactions);setMoreTransactions(x.has_more)}).catch(()=>{});
 }
 async function refreshGas(address:string){
   const balance=await api.nativeBalance(address);
   setGasBalance(balance.amount_raw);
   setNeedsFaucet(balance.low_gas);
   return balance;
 }
 async function signInNative(){
   setBusy(true);setError('');setNotice('');try{
     const address=await connectQoreX();setNativeAddress(address);
     const balance=await refreshGas(address);
     if(balance.low_gas){
       setNotice('Your testnet QOR balance is low. Claim gas from the faucet, then connect again.');return;
     }
     const challenge=await api.nativeChallenge(address);
     const result=await loginProof(address,challenge.memo);
     setPendingLogin({address,challenge_id:challenge.challenge_id,tx_hash:result.txHash});
     try{const session=await api.nativeVerify(address,challenge.challenge_id,result.txHash);afterLogin(session.access_token);}
     catch(e){setNotice('Transaction submitted. Use Verify login transaction after it is indexed.');
       setError(e instanceof Error?e.message:'Transaction confirmation pending');}
   }catch(e){const msg=e instanceof Error?e.message:'QoreX sign-in failed';
     setError(/wallet is locked/i.test(msg)?'Unlock the QoreX extension, then try connecting again.':msg);}
   finally{setBusy(false);}
 }
 async function verifyPendingLogin(){
   if(!pendingLogin)return;setBusy(true);setError('');try{
     const session=await api.nativeVerify(pendingLogin.address,pendingLogin.challenge_id,pendingLogin.tx_hash);
     afterLogin(session.access_token);
   }catch(e){setError(e instanceof Error?e.message:'Native login verification pending');}
   finally{setBusy(false);}
 }
 function logout(){setSignedIn(false);setNativeAddress('');setGasBalance(null);setPendingLogin(null);
   setNeedsFaucet(false);setAccessToken('');setSubscription(null);setRecentProjects([]);
   setProject(null);setAudit(null);setPqcScan(null);setPaymentIntent(null);setPaymentHash('');
   setAllAudits([]);setTransactions([]);setMoreAudits(false);setMoreTransactions(false);setAuditMessages([]);setSelectedAuditId('');}
 useEffect(()=>{if(!jobId||!signedIn)return;
   let closed=false;
   const poll=async()=>{try{const status=await api.audit(jobId);if(closed)return;
     setAgentDone(status.completed_agents);
     if(status.status==='completed'){setAudit(status);setSelectedAuditId(status.id);setAuditMessages([]);setBusy(false);setJobId('');setView('audit-results');api.audits().then(x=>{setAllAudits(x.audits);setMoreAudits(x.has_more)}).catch(()=>{});}
     if(status.status==='failed'){setBusy(false);setJobId('');setError(status.error||'Audit failed.');}
   }catch(e){if(!closed){setBusy(false);setJobId('');setError(e instanceof Error?e.message:'Audit status unavailable');}}};
   void poll();const ticker=setInterval(poll,4000);return()=>{closed=true;clearInterval(ticker)};
 },[jobId,signedIn]);
 async function runPqc(){if(!project){setError('Submit a project first.');return;}setBusy(true);setError('');
   try{const scan=await api.pqc(project.id);setPqcScan(scan);setNotice('Source inventory complete.');}
   catch(e){setError(e instanceof Error?e.message:'PQC scan failed');}finally{setBusy(false);}}
 async function makeHybridProof(){if(!nativeAddress)return;setBusy(true);setError('');try{
    const balance=await refreshGas(nativeAddress);
    if(balance.low_gas){setError('Testnet QOR below 10. Claim tokens from the faucet before sending proof.');return;}
    const proof=await sendHybridProof(nativeAddress);
    setHybridSendStatus(`Wallet broadcast: ${proof.shield}`);setTxHash(proof.txHash);
    setTxEvidence(await api.inspectTx(proof.txHash));
    await api.registerHybrid(proof.txHash);
    api.transactions().then(x=>{setTransactions(x.transactions);setMoreTransactions(x.has_more)}).catch(()=>{});
  }catch(e){setError(e instanceof Error?e.message:'Hybrid proof transaction failed');}
  finally{setBusy(false);}}
 async function inspectTx(){if(!txHash.trim())return;setBusy(true);setError('');
   try{setTxEvidence(await api.inspectTx(txHash.trim()));}catch(e){setError(e instanceof Error?e.message:'Transaction lookup failed');}finally{setBusy(false);}}
 async function checkout(plan:'pro'){
   if(!signedIn||!nativeAddress){setError('Sign in using your QoreX native wallet first.');return;}
   setBusy(true);setError('');setPaymentResult('');setPaymentHash('');try{
     const intent=await api.intent(plan);setPaymentIntent(intent);
     setNotice('Payment intent created. A QoreX native fUSD transfer requires your approval.');
   }catch(e){setError(e instanceof Error?e.message:'Checkout unavailable');}finally{setBusy(false);}}
 async function sendPayment(){if(!paymentIntent||!nativeAddress)return;
   setBusy(true);setError('');try{
     const gas=await refreshGas(nativeAddress);
     if(gas.low_gas)throw new Error('Low testnet QOR. Claim gas from the faucet before paying.');
     const funds=await api.nativeBalance(nativeAddress,paymentIntent.denom);
     if(BigInt(funds.amount_raw)<BigInt(paymentIntent.amount_raw))throw new Error('Insufficient native fUSD. Claim test tokens from the faucet.');
     const result=await nativeSend(nativeAddress,paymentIntent.recipient,paymentIntent.denom,paymentIntent.amount_raw,paymentIntent.memo);
     setPaymentHash(result.txHash);setPaymentResult('Transaction submitted. Verify it on-chain to activate your plan.');
   }catch(e){setError(e instanceof Error?e.message:'Wallet declined or payment failed');}finally{setBusy(false);}}
 async function confirmPayment(){if(!paymentIntent||!paymentHash)return;setBusy(true);setError('');
   try{const result=await api.verifyPayment(paymentIntent.id,paymentHash);
     setPaymentResult(result.status==='paid'?'Payment verified. Your testnet plan is active.':`Awaiting chain confirmation: ${result.reason||'pending'}`);
     if(result.status==='paid'){setSubscription(await api.subscription());refreshTransactions();}
   }catch(e){setError(e instanceof Error?e.message:'Transfer verification failed');}finally{setBusy(false);}}
 async function askSecurityAssistant(){if(!project||!question.trim())return;setBusy(true);setError('');
   try{setAssistantAnswer((await api.ask(project.id,question)).answer);}catch(e){setError(e instanceof Error?e.message:'Assistant unavailable');}finally{setBusy(false);}}

 useEffect(()=>{api.health().then(()=>setBackend('online')).catch(()=>setBackend('offline'))},[]);
 function navigate(next:View){setView(next);setMenuOpen(false);setError('');setNotice('');setLoadHistoryError('');
   if(next==='audit-history')refreshAuditHistory();
   if(next==='transaction-history'||next==='settings'||next==='overview')refreshTransactions();}
 async function submitAudit(){setError('');setNotice('');if(!signedIn){setError('Sign in with QoreX Native to submit an audit.');return;}
 setBusy(true);setAudit(null);setSelectedAuditId('');setAuditMessages([]);setAgentDone(0);setView('audit-progress');try{
  const created=await api.createProject(projectName.trim()||'Untitled project');setProject(created);setRecentProjects(prev=>[created,...prev]);
  if(mode==='paste')await api.pasteSource(created.id,source);else{if(!files.length)throw new Error('Select at least one .sol file or a ZIP project.');await api.upload(created.id,files);}
  const job=await api.runAudit(created.id);setJobId(job.id);
  setNotice('Your source was accepted. The twelve-agent security audit is queued.');
 }catch(e){setBusy(false);setError(e instanceof Error?e.message:'Unexpected audit error');}}
 function saveReport(){if(!audit?.report_markdown)return;const url=URL.createObjectURL(new Blob([audit.report_markdown],{type:'text/markdown'}));const a=document.createElement('a');a.href=url;a.download=`qoresentinel-audit-${project?.id||'report'}.md`;a.click();URL.revokeObjectURL(url)}
 return <div className="shell">
 <aside className={`sidebar ${menuOpen?'open':''}`}>
  <div className="brand"><div className="brand-mark"><Hexagon size={24}/><ShieldCheck size={14} className="brand-shield"/></div><div><strong>QoreSentinel</strong><small>SECURITY OPERATIONS</small></div><button className="mobile-close" aria-label="Close menu" onClick={()=>setMenuOpen(false)}><X size={18}/></button></div>
  <div className="workspace"><div className="workspace-logo">QS</div><div><strong>Personal Workspace</strong><span>Developer workspace</span></div><ChevronDown size={14}/></div>
  <nav>{['WORKSPACE','SECURITY','MANAGEMENT'].map(group=><div key={group} className="nav-group"><span className="nav-label">{group}</span>{menu.filter(item=>item.group===group).map(({id,name,icon:Icon})=><button key={id} className={`nav-item ${view===id?'active':''}`} onClick={()=>navigate(id)}><Icon size={17}/>{name}{id==='audit-results'&&audit?<span className="nav-dot"/>:null}</button>)}</div>)}</nav>
  <div className="sidebar-bottom"><div className="sidebar-footnote"><Shield size={17}/><div>QORECHAIN TESTNET<small>{nativeAddress?`${nativeAddress.slice(0,9)}…`:'qorechain-diana'}</small></div></div><div className="profile"><div className="avatar">QS</div><div><strong>Developer</strong><span>Local workspace</span></div><Settings2 size={15}/></div></div>
 </aside>
 {menuOpen&&<button className="scrim" onClick={()=>setMenuOpen(false)} aria-label="Close navigation"/>}
 <div className="main-area"><header className="topbar"><div className="topbar-left"><button className="mobile-open" onClick={()=>setMenuOpen(true)} aria-label="Open navigation"><Menu size={21}/></button><span>Workspace</span><span className="slash">/</span><strong>{menu.find(item=>item.id===view)?.name}</strong></div><div className="topbar-actions"><span className={`connection ${backend}`}><span className="connection-dot"/>{backend==='online'?'API Connected':backend==='checking'?'Checking API':'API Offline'}</span>{needsFaucet&&<a className="wallet-connect" href={FAUCET_URL} target="_blank" rel="noreferrer" title="Claim testnet QOR">Faucet</a>}<button className="wallet-connect" disabled={busy} onClick={signedIn?logout:pendingLogin?verifyPendingLogin:signInNative} title={signedIn?'Sign out':'Authenticate using a wallet-approved native transaction'}><Wallet size={14}/>{signedIn?`${nativeAddress.slice(0,9)}… Sign out`:pendingLogin?'Verify login transaction':busy?'Connecting…':'Sign in with QoreX'}</button><button className="new-audit-top" onClick={()=>navigate('new-audit')}><Plus size={16}/> New Audit</button></div></header>
 <main className="page">
 {!signedIn&&<div className={`native-login-banner ${needsFaucet?'low-gas':''}`}>
  <div><strong>{needsFaucet?'Low testnet QOR balance':'QoreX Native authentication'}</strong>
   <p>{needsFaucet?'Get test QOR before signing in. A first-time PQC key registration and the login transaction both require gas.':'Connect a qor1 wallet and approve a one-time hybrid-signed self-transfer to authenticate.'}</p>
   {nativeAddress&&<span className="mono-address">{nativeAddress}</span>}
   {gasBalance!==null&&<span className="native-balance">{(Number(gasBalance)/1_000_000).toLocaleString(undefined,{maximumFractionDigits:6})} test QOR available</span>}
  </div><div className="native-login-actions">{needsFaucet&&<><a className="secondary" href={FAUCET_URL} target="_blank" rel="noreferrer">Open testnet faucet <ArrowRight size={14}/></a><button className="secondary" onClick={()=>navigator.clipboard.writeText(FAUCET_URL)}>Copy faucet link</button></>}{pendingLogin&&<button className="primary" onClick={verifyPendingLogin} disabled={busy}>Verify pending login</button>}</div>
 </div>}
 {view==='overview'&&<><Header kicker="OVERVIEW / WORKSPACE" title="Security at a glance" sub="Manage code submissions, run audits, and track your security workflow." action={<button className="primary" onClick={()=>navigate('new-audit')}><Plus size={16}/> New Security Audit</button>}/><div className="stats"><div className="stat"><div className="stat-label">PROJECTS CREATED <FolderOpen size={16}/></div><strong>{recentProjects.length||'—'}</strong><span>Wallet projects</span></div><div className="stat"><div className="stat-label">AUDITS COMPLETED <CheckCircle2 size={16}/></div><strong>{allAudits.filter(x=>x.status==='completed').length||'—'}</strong><span>Saved audit reports</span></div><div className="stat"><div className="stat-label">SECURITY FINDINGS <ShieldAlert size={16}/></div><strong>{audit?.findings_status==='structured_parsing_not_implemented'?'—':audit?audit.findings.length:'—'}</strong><span>Structured results pending</span></div><div className="stat"><div className="stat-label">PQC READINESS <Fingerprint size={16}/></div><strong>{pqcScan?.components??'—'}</strong><span>{pqcScan?.method||'No source inventory yet'}</span></div></div><div className="dashboard-grid"><section className="panel large"><div className="panel-head"><div><span className="eyebrow">ACTIVITY</span><h2>Security Operations</h2></div><button className="secondary" onClick={()=>navigate('audit-history')}>View audit history <ArrowRight size={14}/></button></div>{project?<div className="activity-row"><span className="square-icon"><FileCode2 size={18}/></span><div><strong>{project.name}</strong><p>{audit?'Audit response received':'Project created; audit not completed'}</p></div><Status tone={audit?'good':'neutral'}>{audit?'Completed':'In progress'}</Status></div>:<Empty icon={Activity} title="No audit activity yet" desc="Your submitted projects and recent audits will appear here." action={<button className="secondary" onClick={()=>navigate('new-audit')}>Start your first audit <ArrowRight size={14}/></button>}/>}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">SYSTEM STATUS</span><h2>Services & Integrations</h2></div></div><div className="service-list"><div><span><Radio size={16}/> FastAPI service</span><Status tone={backend==='online'?'good':'warn'}>{backend}</Status></div><div><span><Sparkles size={16}/> Multi-agent audit</span><Status tone={signedIn?"cyan":"neutral"}>{signedIn?"Ready for requests":"Wallet login"}</Status></div><div><span><Fingerprint size={16}/> QoreScan</span><Status tone="cyan">Source inventory</Status></div><div><span><Wallet size={16}/> QoreChain testnet</span><Status tone={nativeAddress?"good":"neutral"}>{nativeAddress?"Connected":"Diana testnet"}</Status></div></div></section></div><section className="panel"><div className="panel-head"><div><span className="eyebrow">MY PROJECTS</span><h2>Recent projects</h2></div></div>{recentProjects.length?<div className="service-list">{recentProjects.slice(0,8).map(item=><div key={item.id}><span><FolderOpen size={16}/>{item.name}</span><button className="secondary" onClick={async()=>{setProject(item);setPqcScan(null);setAudit(null);setError('');setView('pqc');}}>Open <ArrowRight size={14}/></button></div>)}</div>:<p className="help-text">Sign in to see your existing projects.</p>}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">QUICK ACTIONS</span><h2>Start investigating</h2></div></div><div className="quick-grid"><button onClick={()=>navigate('new-audit')}><FileCode2/><strong>Analyze smart contract</strong><span>Paste Solidity or upload project files</span><ArrowRight size={16}/></button><button onClick={()=>navigate('audit-history')}><ShieldAlert/><strong>Review findings</strong><span>Open saved audit reports and evidence</span><ArrowRight size={16}/></button><button onClick={()=>navigate('pqc')}><Fingerprint/><strong>Quantum readiness</strong><span>View upcoming cryptographic inventory tools</span><ArrowRight size={16}/></button></div></section></>}
 {view==='audit-history'&&<><Header kicker="SECURITY / AUDIT HISTORY" title="Audit history" sub="Every submitted audit remains available under its original job ID. Reports can be reopened without running another audit." action={<button className="secondary" onClick={refreshAuditHistory}><RefreshCcw size={15}/> Refresh</button>}/>
 {loadHistoryError&&<div role="alert" className="alert">{loadHistoryError}</div>}
 <section className="panel"><div className="panel-head"><h2>Saved audits</h2><Status tone="cyan">{allAudits.length} loaded</Status></div>
 {!signedIn?<Empty icon={LockKeyhole} title="Connect your wallet" desc="Sign in with your original QoreX address to view past audits."/>:!allAudits.length?<Empty icon={BookOpen} title="No saved audits yet" desc="Completed and pending audits associated with this wallet will appear here."/>:
 <div className="history-list">{allAudits.map(item=><div className="history-item" key={item.id}>
 <div><strong>{item.project_name}</strong><p>{new Date(item.created_at).toLocaleString()} · Job {item.id.slice(0,8)}…</p></div>
 <Status tone={item.status==='completed'?'good':item.status==='failed'?'warn':'cyan'}>{item.status}</Status>
 <button className="secondary" disabled={loadingHistory} onClick={()=>openAudit(item.id)}>{item.status==='completed'?'Open report & discussion':'View audit'} <ArrowRight size={14}/></button>
 </div>)}</div>}
 {moreAudits&&<button className="secondary history-load-more" disabled={loadingHistory} onClick={loadMoreAudits}>Load more audits</button>}
 </section></>}
 {view==='transaction-history'&&<><Header kicker="WALLET / ACTIVITY" title="Transaction history" sub="Confirmed QoreSentinel login, hybrid-proof, and subscription transactions linked to this wallet." action={<button className="secondary" onClick={refreshTransactions}><RefreshCcw size={15}/> Refresh</button>}/>
 {loadHistoryError&&<div role="alert" className="alert">{loadHistoryError}</div>}
 <section className="panel"><div className="panel-head"><h2>Verified on-chain activity</h2><Status tone="cyan">{transactions.length} records</Status></div>
 {!signedIn?<Empty icon={Wallet} title="Wallet authentication required" desc="Connect QoreX to view app transaction history."/>:!transactions.length?<Empty icon={Activity} title="No verified activity" desc="Verified logins, hybrid proofs, and subscription transfers will appear here. Older wallet transfers are not imported."/>:
 <div className="history-list">{transactions.map(tx=><div className="history-item" key={tx.kind+tx.tx_hash}><div><strong>{tx.kind==='login'?'Wallet authentication':tx.kind==='hybrid-proof'?'Hybrid-signature proof':tx.kind==='subscription'?'Subscription payment':tx.kind}</strong><p>{new Date(tx.created_at).toLocaleString()} · {tx.denom} · {tx.amount_raw} base units</p><p className="tx-hash">{tx.tx_hash}</p></div><Status tone="good">{tx.status}</Status><button className="secondary" onClick={()=>navigator.clipboard.writeText(tx.tx_hash)}>Copy hash</button></div>)}</div>}
 {moreTransactions&&<button className="secondary history-load-more" disabled={loadingHistory} onClick={loadMoreTransactions}>Load more transactions</button>}
 </section></>}
 {view==='new-audit'&&<><Header kicker="SECURITY / NEW AUDIT" title="Submit smart contract for audit" sub="Inspect Solidity source with QoreSentinel's specialist auditing workflow."/><div className="audit-grid"><section className="panel"><div className="panel-head"><div><span className="eyebrow">01 / PROJECT DETAILS</span><h2>Submission Workspace</h2></div><Status tone="cyan">SOLIDITY</Status></div><label className="field-label" htmlFor="project-name">Project name</label><input id="project-name" className="field" value={projectName} onChange={e=>setProjectName(e.target.value)} maxLength={120} placeholder="e.g. My DeFi Protocol"/><div className="section-separator"/><div className="tab-row"><button className={mode==='paste'?'selected':''} onClick={()=>setMode('paste')}><Code2 size={16}/> Paste source</button><button className={mode==='upload'?'selected':''} onClick={()=>setMode('upload')}><Upload size={16}/> Upload files / ZIP</button></div>{mode==='paste'?<><div className="editor-toolbar"><span><FileCode2 size={14}/> Contract.sol</span><Status>Solidity</Status></div><textarea spellCheck={false} className="code-editor" aria-label="Solidity source code" value={source} onChange={e=>setSource(e.target.value)}/><p className="help-text">Source code is sent to your configured backend for analysis. Do not submit secrets or private keys.</p></>:<><input ref={fileRef} type="file" accept=".sol,.zip" multiple hidden onChange={e=>setFiles(Array.from(e.target.files||[]))}/><button className="upload-box" onClick={()=>fileRef.current?.click()}><CloudUpload size={32}/><strong>Choose Solidity files or ZIP project</strong><span>Supports .sol files or one .zip archive (submitted separately)</span></button><div className="file-list">{files.length?files.map((f,i)=><div key={i}><FileText size={15}/><span>{f.name}</span><button aria-label={`Remove ${f.name}`} onClick={()=>setFiles(files.filter((_,j)=>i!==j))}><X size={15}/></button></div>):<span>No files selected</span>}</div></> }</section><aside className="panel right-panel"><div className="panel-head"><div><span className="eyebrow">02 / AUDIT CONFIGURATION</span><h2>Analysis Settings</h2></div></div><div className="settings-option"><ShieldCheck size={20}/><div><strong>12 specialist agents</strong><p>Parallel vulnerability investigation with final judge consolidation.</p></div><Status tone="cyan">ENGINE</Status></div><div className="settings-option"><LockKeyhole size={20}/><div><strong>Private source handling</strong><p>Runs through your backend; credentials must stay server-side.</p></div></div><div className="settings-option"><FileSearch size={20}/><div><strong>Evidence-first reporting</strong><p>Agent responses are consolidated into a report with source attribution where supported.</p></div></div><button disabled={busy||!signedIn||!projectName.trim()||(mode==='paste'?!source.trim():!files.length)} className="primary full" onClick={submitAudit}>{busy?'Preparing audit...':signedIn?'Initiate Security Audit':'Sign in to start audit'} <ArrowRight size={16}/></button></aside></div></>}
 {view==='audit-progress'&&<><Header kicker="SECURITY / AUDIT IN PROGRESS" title="Multi-agent audit pipeline" sub="Follow your queued audit through the specialist pipeline and final report."/><section className="panel"><div className="panel-head"><div><span className="eyebrow">EXECUTION STATUS</span><h2>{busy?'Analyzing source files…':audit?'Audit completed':'No active audit'}</h2></div><Status tone={busy?'cyan':'neutral'}>{busy?'RUNNING':audit?'COMPLETE':'IDLE'}</Status></div>{error&&<div role="alert" className="alert"><CircleAlert size={17}/>{error}</div>}{notice&&<div className="info-note"><Activity size={17}/>{notice}</div>}<div className="agent-grid">{agentNames.map((name,i)=><div key={name} className="agent-tile"><span className="agent-index">{String(i+1).padStart(2,'0')}</span><Shield size={16}/><div><strong>{name}</strong><small>{busy?(i<agentDone?'Completed':i===agentDone?'Analyzing':'Queued'):'Not running'}</small></div><span className={`tiny-dot ${busy?'pulse':''}`}/></div>)}</div><div className="judge-row"><Sparkles size={18}/><div><strong>Final judge & report synthesis</strong><p>Deduplicates agent findings when the configured engine finishes</p></div><Status>{busy?`${agentDone}/12 specialists done`:'Not running'}</Status></div>{!busy&&<button className="secondary" onClick={()=>navigate('new-audit')}><Plus size={16}/> Start new audit</button>}</section></>}
 {view==='audit-results'&&<><Header kicker="SECURITY / AUDIT RESULTS" title="Audit findings & evidence" sub="Review the report returned by the real backend audit engine." action={audit?.report_markdown?<button className="primary" onClick={saveReport}><Download size={16}/> Download Markdown</button>:undefined}/>{audit?<><div className="stats small-stats"><div className="stat"><div className="stat-label">AUDIT STATUS</div><strong className="stat-word">{audit.status}</strong><span>Backend-reported</span></div><div className="stat"><div className="stat-label">AI-REPORTED FINDINGS</div><strong>{audit.findings_status==='structured_parsing_not_implemented'?'—':audit.findings.length}</strong><span>Extracted from report, not verified</span></div><div className="stat"><div className="stat-label">PROJECT</div><strong className="stat-word">{project?.name||'Unknown'}</strong><span>{project?.id||'No project ID'}</span></div></div>{audit.findings.length>0&&<section className="panel"><div className="panel-head"><div><span className="eyebrow">AI-REPORTED FINDINGS</span><h2>Finding summaries</h2></div><Status tone="warn">Unverified</Status></div>
 <p className="help-text">Extracted from the saved report. Confirm each claim against the source and compile/test results before acting on it.</p>
 <div className="history-list">{audit.findings.map((finding,index)=><div className="finding-item" key={index}>
 <div className="finding-meta"><Status tone={finding.severity.toLowerCase()==='high'||finding.severity.toLowerCase()==='critical'?'warn':'neutral'}>{finding.severity}</Status><strong>{finding.title}</strong></div>
 <pre>{finding.evidence}</pre></div>)}</div></section>}
 <section className="panel"><div className="panel-head"><div><span className="eyebrow">FULL REPORT</span><h2>Audit report</h2></div><Status tone="cyan">BACKEND OUTPUT</Status></div><div className="info-note"><CircleAlert size={17}/>AI-generated security analysis; validate findings independently. Severity labels are assertions from the report.</div><pre className="report">{audit.report_markdown||'The backend returned no Markdown report.'}</pre><button className="text-button" onClick={()=>setAgentExpanded(!agentExpanded)}>{agentExpanded?'Hide':'Show'} raw agent results <ChevronDown size={14}/></button>{agentExpanded&&<pre className="report">{JSON.stringify(audit.agents,null,2)}</pre>}</section>
 <section className="panel audit-discussion"><div className="panel-head"><div><span className="eyebrow">AUDIT WORKSPACE</span><h2>Discussion history</h2></div><Status tone="cyan">{selectedAuditId?'Saved per audit':'Select an audit'}</Status></div>
 <p className="help-text">Questions and replies are saved against this audit, so you can return later without running another analysis.</p>
 <div className="conversation-log">{auditMessages.length?auditMessages.map(message=><div key={message.id} className={`conversation-message ${message.role}`}><strong>{message.role==='user'?'You':'QoreSentinel'}</strong><pre>{message.body}</pre></div>):<p className="help-text">No questions yet for this report.</p>}</div>
 <label className="field-label" htmlFor="audit-question">Ask about this audit</label>
 <textarea id="audit-question" className="field" rows={3} maxLength={2000} value={auditQuestion} onChange={e=>setAuditQuestion(e.target.value)} placeholder="Which findings should I prioritize, and what evidence supports them?"/>
 <button className="primary" disabled={!signedIn||!selectedAuditId||chatBusy||!auditQuestion.trim()} onClick={askAuditQuestion}><MessageSquareText size={16}/>{chatBusy?'Analyzing…':'Send question'}</button>
 </section></>:<section className="panel"><Empty icon={ShieldAlert} title="No audit selected" desc="Open a saved report from Audit History without running another audit." action={<button className="primary" onClick={()=>navigate('audit-history')}>Open audit history <ArrowRight size={16}/></button>}/></section>}</>}
 {view==='assistant'&&<><Header kicker="SECURITY / AI ASSISTANT" title="AI security assistant" sub="Discuss submitted Solidity source and audit evidence."/><section className="panel"><div className="panel-head"><h2>Project security analysis</h2><Status tone={project?'cyan':'neutral'}>{project?.name||'Select a project'}</Status></div>{project?<><label className="field-label" htmlFor="assistant-question">Your question</label><textarea id="assistant-question" className="field" rows={4} maxLength={2000} placeholder="Which access-control assumptions should I verify?" value={question} onChange={e=>setQuestion(e.target.value)}/><button className="primary" disabled={busy||!question.trim()} onClick={askSecurityAssistant}><MessageSquareText size={16}/> Ask assistant</button>{assistantAnswer&&<><div className="section-separator"/><pre className="report">{assistantAnswer}</pre><p className="help-text">AI-generated response grounded in supplied files; verify any claims independently.</p></>}</>:<Empty icon={MessageSquareText} title="Submit a contract to begin" desc="The assistant uses source files from your workspace. Open a project first." action={<button className="secondary" onClick={()=>navigate('new-audit')}>Submit source <ArrowRight size={16}/></button>}/>}</section></>}
 {view==='pqc'&&<><Header kicker="QUANTUM RESILIENCE / INVENTORY" title="Post-Quantum Readiness" sub="Inspect source-level cryptographic references and QoreChain hybrid-signature evidence."/><div className="stats small-stats"><div className="stat"><div className="stat-label">CRYPTO COMPONENTS</div><strong>{pqcScan?.components??'—'}</strong><span>{pqcScan?.method||'No scan yet'}</span></div><div className="stat"><div className="stat-label">HYBRID PROOF</div><strong className="stat-word">{txEvidence?.chain_reports_verified?'CHAIN VERIFIED':'—'}</strong><span>{txEvidence?.found?'QoreChain testnet evidence':'No inspected transaction'}</span></div><div className="stat"><div className="stat-label">CBOM</div><strong className="stat-word">{pqcScan?.cbom?'AVAILABLE':'—'}</strong><span>CycloneDX inventory</span></div></div><div className="settings-grid"><section className="panel"><div className="panel-head"><h2>Cryptographic inventory</h2><Status tone="cyan">SOLIDITY SOURCE</Status></div>{project?<><p className="plain-copy">{project.name}</p><button className="primary" disabled={busy} onClick={runPqc}><Fingerprint size={16}/> Analyze source</button></>:<Empty icon={FileCode2} title="No submitted project" desc="Run a source submission to begin cryptographic inventory." action={<button className="secondary" onClick={()=>navigate('new-audit')}>Open new audit</button>}/>} {pqcScan&&<><div className="section-separator"/><p className="help-text">{pqcScan.limitations}</p><div className="service-list">{pqcScan.evidence.slice(0,30).map((e,i)=><div key={i}><span><Code2 size={14}/>{e.algorithm} — {e.file}:{e.line}</span><Status>{e.classification}</Status></div>)}</div><button className="secondary" onClick={()=>{const a=document.createElement('a');const url=URL.createObjectURL(new Blob([JSON.stringify(pqcScan.cbom,null,2)],{type:'application/json'}));a.href=url;a.download='qoresentinel-cbom.json';a.click();URL.revokeObjectURL(url);}}><Download size={16}/> Export CBOM</button></>}</section><section className="panel"><div className="panel-head"><h2>QoreChain hybrid-signature evidence</h2><Status tone="cyan">DIANA TESTNET</Status></div><div className="info-note"><ShieldCheck size={16}/>A hybrid proof sends 1 testnet QOR from your QoreX native address back to itself. Network fees apply. Your wallet will request approval.</div><button className="secondary" disabled={!nativeAddress||busy} onClick={makeHybridProof}><ShieldCheck size={15}/> Send hybrid testnet proof</button>{hybridSendStatus&&<p className="help-text">{hybridSendStatus}</p>}<div className="section-separator"/><label className="field-label" htmlFor="proof-hash">Native transaction hash</label><input id="proof-hash" className="field" value={txHash} onChange={e=>setTxHash(e.target.value)} placeholder="0x… (64 hex characters)"/><button className="secondary" disabled={busy||!txHash.trim()} onClick={inspectTx}><Search size={15}/> Inspect transaction</button>{txEvidence&&<div className="service-list"><div><span>Found on chain</span><Status tone={txEvidence.found?'good':'warn'}>{txEvidence.found?'Yes':'No'}</Status></div>{txEvidence.found&&<><div><span>Hybrid layer present</span><Status tone={txEvidence.hybrid_layer_present?'good':'warn'}>{txEvidence.hybrid_layer_present?'Yes':'No'}</Status></div><div><span>Chain-reported verification</span><Status tone={txEvidence.chain_reports_verified?'good':'warn'}>{txEvidence.chain_reports_verified?'Verified':'Not verified'}</Status></div><p className="help-text">{txEvidence.verification_method}</p></>}</div>}</section></div></>}
 {view==='billing'&&<><Header kicker="MANAGEMENT / BILLING & USAGE" title="Subscriptions & usage" sub="Purchase audit plans using QoreX native fUSD bank transfers. All payments require on-chain confirmation."/><div className="stats small-stats"><div className="stat"><div className="stat-label">CURRENT PLAN</div><strong className="stat-word">{subscription?.plan?.toUpperCase()||'FREE'}</strong><span>{subscription?.expires_at?`Expires ${new Date(subscription.expires_at*1000).toLocaleDateString()}`:'No paid entitlement'}</span></div><div className="stat"><div className="stat-label">NETWORK</div><strong className="stat-word">DIANA</strong><span>QoreChain 9800 · Test tokens only</span></div><div className="stat"><div className="stat-label">CHECKOUT</div><strong className="stat-word">{paymentResult?'IN PROGRESS':'—'}</strong><span>Backend verifies native bank transfers</span></div></div><section className="panel"><div className="panel-head"><h2>Testnet fUSD checkout</h2><Status tone="cyan">NO REAL MONETARY VALUE</Status></div><p className="plain-copy">Approve a native QoreX bank transfer. Access activates only after the backend verifies the sender, recipient, exact fUSD amount, memo, hybrid signature and confirmations.</p>{!signedIn?<button className="primary" onClick={signInNative}><Wallet size={16}/> Sign in with QoreX</button>:<><div className="quick-grid"><button disabled={busy} onClick={()=>checkout('pro')}><ShieldCheck/><strong>Pro — 30 days</strong><span>View and approve a testnet payment</span><ArrowRight size={15}/></button></div>{paymentIntent&&<div className="checkout-details"><div className="section-separator"/><div className="service-list"><div><span>Amount (fUSD)</span><strong>{paymentIntent.amount_fusd}</strong></div><div><span>Chain</span><strong>{paymentIntent.network}</strong></div><div><span>Recipient</span><span className="mono-address">{paymentIntent.recipient}</span></div><div><span>Payment window</span><span>{new Date(paymentIntent.expires_at*1000).toLocaleTimeString()}</span></div></div><button className="primary" disabled={busy||Boolean(paymentHash)} onClick={sendPayment}><Wallet size={16}/> Approve native fUSD transfer</button>{paymentHash&&<><p className="help-text">Transaction: {paymentHash}</p><button className="secondary" disabled={busy} onClick={confirmPayment}><CheckCircle2 size={16}/> Verify payment on-chain</button></>}{paymentResult&&<div className="info-note"><Clock3 size={16}/>{paymentResult}</div>}</div>}</>}</section></>}
 {view==='settings'&&<><Header kicker="MANAGEMENT / SETTINGS" title="Wallet & privacy" sub="Connected identities, security preferences, and data access."/><div className="settings-grid"><section className="panel"><div className="panel-head"><h2>Wallet connections</h2></div><div className="service-list"><div><span>QoreX Native</span><Status tone={nativeAddress?'good':'neutral'}>{nativeAddress?nativeAddress.slice(0,14)+'…':'Not connected'}</Status></div><div><span>QoreX authenticated session</span><Status tone={signedIn?'good':'neutral'}>{signedIn?nativeAddress.slice(0,14)+'…':'Not signed in'}</Status></div></div><button className="secondary" onClick={signedIn?logout:pendingLogin?verifyPendingLogin:signInNative}><LockKeyhole size={15}/>{signedIn?'Sign out of wallet session':pendingLogin?'Verify pending login':'Authenticate QoreX Native wallet'}</button></section><section className="panel"><div className="panel-head"><h2>Privacy & security</h2></div><p className="plain-copy">Never disclose recovery phrases or private keys. Security findings are AI-assisted and should be verified independently. Testnet tokens have no real monetary value.</p><button className="secondary" onClick={()=>navigate('transaction-history')}><Activity size={16}/> View transaction history</button><div className="service-list"><div><span>Service health</span><Status tone={backend==='online'?'good':'warn'}>{backend}</Status></div><div><span>Session</span><Status tone={signedIn?'good':'neutral'}>{signedIn?'Wallet signed in':'Signed out'}</Status></div></div></section></div></>}
 {error&&view!=='audit-progress'&&<div role="alert" className="floating-error"><CircleAlert size={18}/><span>{error}</span><button onClick={()=>setError('')} aria-label="Dismiss error"><X size={16}/></button></div>}
 </main></div></div>
}
