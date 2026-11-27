'use client';
import {useEffect,useRef,useState} from 'react';
import {usePathname} from 'next/navigation';
import {VIEW_PATHS,viewFromPathname,auditIdFromPathname,auditReportPath,type View} from '@/lib/routes';
import {Activity,ArrowRight,Bell,BookOpen,CheckCircle2,ChevronDown,CircleAlert,Clock3,CloudUpload,Code2,CreditCard,Download,FileCode2,FileSearch,FileText,Fingerprint,FolderOpen,HelpCircle,Hexagon,LayoutDashboard,LockKeyhole,Menu,MessageSquareText,Plus,Radio,RefreshCcw,Search,Settings2,Shield,ShieldAlert,ShieldCheck,Sparkles,Upload,Wallet, X} from 'lucide-react';
import {api,setAccessToken,type Audit,type AttestationStatus,type AttestationRequest,type AuditSummary,type AuditMessage,type ChainTx,type Project,type PqcScan,type TxEvidence,type PaymentIntent,type PendingPaymentIntent,type PlanQuote,type UsageWindow} from '@/lib/api';
import {connectQoreX,loginProof,nativeSend,sendHybridProof,requestQoreXUnlock,FAUCET_URL,QOREX_CHROME_URL,QOREX_FIREFOX_URL,QOREX_NETWORK_GUIDE,hasQoreXNative,classifyQoreXError,type QoreXConnectIssue} from '@/lib/wallet';

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
 const pathname=usePathname();
 const [view,setView]=useState<View>(()=>viewFromPathname(pathname));
 const [menuOpen,setMenuOpen]=useState(false);
 // Keep workspace state mounted while browser Back/Forward changes the section.
 useEffect(()=>{
   if(window.location.pathname==='/'){
     window.history.replaceState(window.history.state,'',VIEW_PATHS.overview);
   }
   setView(viewFromPathname(window.location.pathname));
 },[pathname]);
 const [backend,setBackend]=useState<'checking'|'online'|'offline'>('checking');
 const [projectName,setProjectName]=useState('My Solidity Project');const [project,setProject]=useState<Project|null>(null);const [recentProjects,setRecentProjects]=useState<Project[]>([]);
 const [source,setSource]=useState('// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n\ncontract MyContract {\n    // Paste your Solidity code here\n}');
 const [files,setFiles]=useState<File[]>([]);const [mode,setMode]=useState<'paste'|'upload'>('paste');
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const [audit,setAudit]=useState<Audit|null>(null);const [attestation,setAttestation]=useState<AttestationStatus|null>(null);const [attestationRequest,setAttestationRequest]=useState<AttestationRequest|null>(null);const [attestationBusy,setAttestationBusy]=useState(false);const [attestationError,setAttestationError]=useState('');const [agentExpanded,setAgentExpanded]=useState(false);
 const fileRef=useRef<HTMLInputElement>(null);
 const [nativeAddress,setNativeAddress]=useState('');const [signedIn,setSignedIn]=useState(false);
 const [gasBalance,setGasBalance]=useState<string|null>(null);
 const [pendingLogin,setPendingLogin]=useState<{address:string;challenge_id:string;tx_hash:string}|null>(null);
 const [needsFaucet,setNeedsFaucet]=useState(false);
 const [walletIssue,setWalletIssue]=useState<QoreXConnectIssue|null>(null);
 const [walletMessage,setWalletMessage]=useState('');
 const [jobId,setJobId]=useState('');const [agentDone,setAgentDone]=useState(0);
 const [pqcScan,setPqcScan]=useState<PqcScan|null>(null);
 const [pqcInputMode,setPqcInputMode]=useState<'project'|'paste'|'upload'>('project');
 const [pqcProjectId,setPqcProjectId]=useState('');
 const [pqcSource,setPqcSource]=useState('');
 const [pqcUploads,setPqcUploads]=useState<File[]>([]);
 const [pqcWalletLocked,setPqcWalletLocked]=useState(false);
 const pqcFileRef=useRef<HTMLInputElement>(null);
 const [txHash,setTxHash]=useState('');const [hybridSendStatus,setHybridSendStatus]=useState('');const [txEvidence,setTxEvidence]=useState<TxEvidence|null>(null);
 const [paymentIntent,setPaymentIntent]=useState<PaymentIntent|null>(null);
 const [pendingPayments,setPendingPayments]=useState<PendingPaymentIntent[]>([]);
 const [pendingPaymentLoading,setPendingPaymentLoading]=useState(false);
 const [pendingPaymentError,setPendingPaymentError]=useState('');
 const [manualPaymentHash,setManualPaymentHash]=useState('');
 const [paymentHash,setPaymentHash]=useState('');const [paymentResult,setPaymentResult]=useState('');
 const [funding,setFunding]=useState<{quote:PlanQuote;fusdRaw:string;qorRaw:string}|null>(null);
 const [fundingLoading,setFundingLoading]=useState(false);
 const [fundingMessage,setFundingMessage]=useState('');
 const [fundingError,setFundingError]=useState('');
 function displayUnits(raw:string){
   const digits=raw.padStart(7,'0');const decimals=digits.slice(-6).replace(/0+$/,'');
   return digits.slice(0,-6)+(decimals?'.'+decimals:'');
 }

 const [subscription,setSubscription]=useState<{plan:string;expires_at:number|null}|null>(null);
 const [usage,setUsage]=useState<UsageWindow|null>(null);
 async function refreshPendingPayments(){
   if(!signedIn)return;
   setPendingPaymentLoading(true);setPendingPaymentError('');
   try{
     const response=await api.pendingIntents();setPendingPayments(response.intents);
   }catch(err){setPendingPaymentError(err instanceof Error?err.message:'Could not retrieve pending payments');}
   finally{setPendingPaymentLoading(false);}
 }
 function resumePayment(p:PendingPaymentIntent){
   setPaymentIntent({...p,notice:'Pending testnet payment — verify the transaction on-chain before activating Pro.'});
   setPaymentHash(p.tx_hash||'');setManualPaymentHash(p.tx_hash||'');
   setPaymentResult(p.tx_hash?'Transaction recorded; verification is still required.':'Payment intent restored. Approve the transfer only if you have not already sent it.');
   setFundingError('');setError('');
 }
 async function storePaymentHash(){
   if(!paymentIntent||!manualPaymentHash.trim())return;
   setBusy(true);setError('');
   try{
     const result=await api.broadcastPayment(paymentIntent.id,manualPaymentHash.trim());
     setPaymentHash(result.tx_hash);
     setManualPaymentHash(result.tx_hash);
     setPaymentResult('Transaction hash saved. It is not yet verified or credited.');
     await refreshPendingPayments();
   }catch(err){setError(err instanceof Error?err.message:'Could not save transaction hash');}
   finally{setBusy(false);}
 }

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
     setAudit(loaded);setAttestation(null);setAttestationRequest(null);setAttestationError('');
     if(loaded.status==='completed'){
       api.attestationRequest(jobId).then(setAttestationRequest).catch(()=>{});
       api.attestation(jobId).then(setAttestation).catch(e=>setAttestationError(e instanceof Error?e.message:'Attestation unavailable'));
     }
     setSelectedAuditId(jobId);setAuditQuestion('');setAuditMessages([]);
     const messages=await api.auditMessages(jobId);
     setAuditMessages(messages.messages);
     if(loaded.status==='queued'||loaded.status==='running'){
       setJobId(jobId);setAgentDone(loaded.completed_agents);navigateAudit(jobId,'audit-progress');
     }else navigateAudit(jobId);
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
 function loadWalletWorkspace(){
   api.subscription().then(setSubscription).catch(()=>{});
   api.usage().then(setUsage).catch(()=>{});
   api.pendingIntents().then(x=>setPendingPayments(x.intents)).catch(()=>{});
   api.listProjects().then(x=>setRecentProjects(x.projects)).catch(()=>{});
   api.audits().then(x=>{setAllAudits(x.audits);setMoreAudits(x.has_more)}).catch(()=>{});
   api.transactions().then(x=>{setTransactions(x.transactions);setMoreTransactions(x.has_more)}).catch(()=>{});
 }
 function afterLogin(token:string){
   setWalletIssue(null);setWalletMessage('');setAccessToken(token);setSignedIn(true);setPendingLogin(null);setNeedsFaucet(false);
   setNotice('QoreX native wallet authenticated on Diana testnet.');
   loadWalletWorkspace();
 }
 useEffect(()=>{
   let active=true;
   api.session().then(session=>{
     if(!active)return;
     setNativeAddress(session.wallet);setSignedIn(true);setWalletIssue(null);setWalletMessage('');
     loadWalletWorkspace();
   }).catch(()=>{});
   return ()=>{active=false};
 },[]);
 useEffect(()=>{
   const id=auditIdFromPathname(pathname);
   if(!id||!signedIn||audit?.id===id)return;
   let active=true;
   const load=async()=>{
     setLoadingHistory(true);
     try{
       const result=await api.audit(id);
       const [messages,storedProject]=await Promise.all([
         api.auditMessages(id),api.getProject(result.project_id).catch(()=>null)
       ]);
       if(!active)return;
       setAudit(result);setAttestation(null);setAttestationRequest(null);setAttestationError('');
        if(result.status==='completed')api.attestationRequest(id).then(setAttestationRequest).catch(()=>{});
        if(result.status==='completed')api.attestation(id).then(setAttestation).catch(e=>setAttestationError(e instanceof Error?e.message:'Attestation unavailable'));
        setSelectedAuditId(id);setAuditMessages(messages.messages);
       setProject(storedProject||{id:result.project_id,name:allAudits.find(x=>x.id===id)?.project_name||'Saved audit'});
       if(result.status==='queued'||result.status==='running'){
         setJobId(id);setAgentDone(result.completed_agents);setView('audit-progress');
       }else setView('audit-results');
       setLoadHistoryError('');
     }catch(e){if(active)setLoadHistoryError(e instanceof Error?e.message:'Audit not found or access denied');}
     finally{if(active)setLoadingHistory(false);}
   };
   void load();
   return()=>{active=false};
 },[pathname,signedIn,audit?.id]);
 useEffect(()=>{
   if(!audit?.id||!signedIn||!attestationRequest||!['queued','processing','submitted'].includes(attestationRequest.status))return;
   let active=true;
   const timer=setInterval(()=>{
     void Promise.all([api.attestationRequest(audit.id),api.attestation(audit.id)])
       .then(([request,status])=>{if(active){setAttestationRequest(request);setAttestation(status);}})
       .catch(()=>{});
   },6000);
   return()=>{active=false;clearInterval(timer);};
 },[audit?.id,signedIn,attestationRequest?.status]);
 async function refreshGas(address:string){
   const balance=await api.nativeBalance(address);
   setGasBalance(balance.amount_raw);
   setNeedsFaucet(balance.low_gas);
   return balance;
 }
 async function signInNative(){
   setBusy(true);setError('');setNotice('');setWalletIssue(null);setWalletMessage('');try{
     if(!hasQoreXNative()){
       setWalletIssue('missing');setWalletMessage('QoreX is not detected in this browser. Install or enable the extension, then retry.');return;
     }
     const address=await connectQoreX();setNativeAddress(address);setWalletIssue(null);
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
   }catch(e){
     const issue=classifyQoreXError(e);
     if(issue){setWalletIssue(issue.issue);setWalletMessage(issue.message);setError('');}
     else setError(e instanceof Error?e.message:'QoreX sign-in failed');
   }finally{setBusy(false);}
 }
 async function verifyPendingLogin(){
   if(!pendingLogin)return;setBusy(true);setError('');try{
     const session=await api.nativeVerify(pendingLogin.address,pendingLogin.challenge_id,pendingLogin.tx_hash);
     afterLogin(session.access_token);
   }catch(e){setError(e instanceof Error?e.message:'Native login verification pending');}
   finally{setBusy(false);}
 }
 async function logout(){
   try{await api.logout();}catch(e){setError(e instanceof Error?e.message:'Could not sign out');return;}
   setWalletIssue(null);setWalletMessage('');setSignedIn(false);setNativeAddress('');setGasBalance(null);setPendingLogin(null);
   setNeedsFaucet(false);setAccessToken('');setSubscription(null);setUsage(null);setRecentProjects([]);
   setProject(null);setAudit(null);setAttestation(null);setAttestationRequest(null);setAttestationError('');setPqcScan(null);setPqcWalletLocked(false);setPqcProjectId('');setPqcInputMode('project');setPqcSource('');setPqcUploads([]);setPaymentIntent(null);setPaymentHash('');setFunding(null);setFundingMessage('');setFundingError('');
   setAllAudits([]);setTransactions([]);setMoreAudits(false);setMoreTransactions(false);setAuditMessages([]);setSelectedAuditId('');
   setPendingPayments([]);setPendingPaymentError('');setManualPaymentHash('');
 }
 useEffect(()=>{if(!jobId||!signedIn)return;
   let closed=false;
   const poll=async()=>{try{const status=await api.audit(jobId);if(closed)return;
     setAgentDone(status.completed_agents);
     if(status.status==='completed'){setAudit(status);setAttestation(null);setAttestationRequest(null);setAttestationError('');api.attestationRequest(status.id).then(setAttestationRequest).catch(()=>{});api.attestation(status.id).then(setAttestation).catch(e=>setAttestationError(e instanceof Error?e.message:'Attestation unavailable'));setSelectedAuditId(status.id);setAuditMessages([]);setBusy(false);setJobId('');navigateAudit(status.id);api.audits().then(x=>{setAllAudits(x.audits);setMoreAudits(x.has_more)}).catch(()=>{});}
     if(status.status==='failed'){setBusy(false);setJobId('');setError(status.error||'Audit failed.');}
   }catch(e){if(!closed){setBusy(false);setJobId('');setError(e instanceof Error?e.message:'Audit status unavailable');}}};
   void poll();const ticker=setInterval(poll,4000);return()=>{closed=true;clearInterval(ticker)};
 },[jobId,signedIn]);
 async function runPqc(){
   setBusy(true);setError('');setNotice('');setPqcScan(null);
   try{
     let result:PqcScan;
     if(pqcInputMode==='project'){
       const id=pqcProjectId||project?.id;
       if(!id)throw new Error('Select a saved Solidity project first.');
       result=await api.pqc(id);
     }else if(pqcInputMode==='paste'){
       if(!pqcSource.trim())throw new Error('Paste Solidity source to scan.');
       result=await api.pqcPaste(pqcSource);
     }else{
       if(!pqcUploads.length)throw new Error('Choose .sol files or one ZIP archive first.');
       result=await api.pqcFiles(pqcUploads);
     }
     setPqcScan(result);
     setNotice('Cryptographic inventory completed. No paid audit credits were used or PQC scan history saved.');
   }catch(e){setError(e instanceof Error?e.message:'PQC scan failed');}
   finally{setBusy(false);}
 }
 async function inspectHybridEvidence(hash:string){
   const evidence=await api.inspectTx(hash);
   setTxEvidence(evidence);
   if(!evidence.found){
     setNotice('Transaction was broadcast but is not indexed yet. Use Inspect transaction again after the next block.');
     return;
   }
   if(!evidence.chain_reports_verified){
     setNotice('Transaction found, but chain-reported hybrid verification is not confirmed. Inspect its events before relying on this proof.');
     return;
   }
   setHybridSendStatus('Hybrid signature verified on-chain');
   if(signedIn){
     try{
       await api.registerHybrid(hash);
       api.transactions().then(x=>{setTransactions(x.transactions);setMoreTransactions(x.has_more)}).catch(()=>{});
       setNotice('Hybrid proof verified and recorded in Transaction History.');
     }catch(e){
       setNotice('Hybrid proof verified on-chain, but could not be added to this wallet history: '+(e instanceof Error?e.message:'registration unavailable'));
     }
   }else{
     setNotice('Hybrid proof verified on-chain. Sign in with QoreX to save it to your activity history.');
   }
 }
 async function makeHybridProof(){if(!nativeAddress)return;setBusy(true);setError('');setNotice('');
   let broadcastHash='';
   try{
     // Ask QoreX to wake its unlock UI directly from the user's click,
     // before asynchronous network balance checks lose user activation.
     await requestQoreXUnlock(nativeAddress);
     setPqcWalletLocked(false);
     const balance=await refreshGas(nativeAddress);
     if(balance.low_gas){setError('Testnet QOR below 10. Claim tokens from the faucet before sending proof.');return;}
     const proof=await sendHybridProof(nativeAddress);
     broadcastHash=proof.txHash;
     setHybridSendStatus(`Wallet broadcast: ${proof.shield}`);
     setTxHash(proof.txHash);
     await inspectHybridEvidence(proof.txHash);
   }catch(e){
     const detail=e instanceof Error?e.message:'Transaction verification unavailable';
     if(broadcastHash){
       setNotice('QoreX broadcast the transaction. Its hash is preserved above; the on-chain lookup failed. Use Inspect transaction to retry without sending another transaction.');
       setError('Inspector unavailable: '+detail);
     }else{
       const issue=classifyQoreXError(e);
       if(issue?.issue==='locked'){
         setPqcWalletLocked(true);setError('');
         setHybridSendStatus('QoreX did not open an unlock prompt. Update your QoreX extension or unlock it manually, then retry. Source scanning remains available.');
       }else if(issue?.issue==='wrong-network'){
         setPqcWalletLocked(false);setError(issue.message);
       }else setError(detail);
     }
   }finally{setBusy(false);}
 }
 async function inspectTx(){if(!txHash.trim())return;setBusy(true);setError('');setNotice('');
   try{await inspectHybridEvidence(txHash.trim());}
   catch(e){setError(e instanceof Error?e.message:'Transaction lookup failed');}
   finally{setBusy(false);}
 }

 async function refreshFunding(){
   if(!signedIn||!nativeAddress)return null;
   setFundingLoading(true);setFundingError('');
   try{
     const quote=await api.planQuote('pro');
     const [gas,fusd]=await Promise.all([
       api.nativeBalance(nativeAddress),
       api.nativeBalance(nativeAddress,quote.denom)
     ]);
     const balance={quote,fusdRaw:fusd.amount_raw,qorRaw:gas.amount_raw};
     setFunding(balance);setGasBalance(gas.amount_raw);setNeedsFaucet(gas.low_gas);
     const missing=BigInt(fusd.amount_raw)<BigInt(quote.amount_raw);
     const reason=[
       missing?'Insufficient fUSD. Available '+displayUnits(fusd.amount_raw)+' fUSD; Pro requires '+quote.amount_fusd+' fUSD.':'',
       gas.low_gas?'QOR balance is below 10 QOR; additional gas funding is required.':'',
       missing||gas.low_gas?'Claim test tokens from the faucet, then refresh balances before checkout.':''
     ].filter(Boolean).join(' ');
     setFundingMessage(reason);
     return {quote,ready:!missing&&!gas.low_gas};
   }catch(err){
     setFunding(null);
     setFundingMessage('');
     setFundingError(err instanceof Error?err.message:'Could not check testnet balances');
     throw err;
   }finally{setFundingLoading(false);}
 }
 useEffect(()=>{
   if(view!=='billing'||!signedIn||!nativeAddress)return;
   void refreshFunding().catch(()=>{});
   // Refresh on entry or wallet change. Checkout also rechecks immediately.
   // eslint-disable-next-line react-hooks/exhaustive-deps
 },[view,signedIn,nativeAddress]);
 async function checkout(plan:'pro'){
   if(!signedIn||!nativeAddress){setError('Sign in using your QoreX native wallet first.');return;}
   if(paymentHash){setFundingError('A transaction is already pending verification. Verify it before starting another checkout.');return;}
   setBusy(true);setError('');setFundingError('');
   try{
     const balance=await refreshFunding();
     if(!balance?.ready){setPaymentIntent(null);return;}
     const intent=await api.intent(plan);
     if(intent.amount_raw!==balance.quote.amount_raw||intent.denom!==balance.quote.denom){
       setPaymentIntent(null);setFundingError('The plan price changed during checkout. Refresh and try again.');return;
     }
     setPaymentResult('');setPaymentIntent(intent);setManualPaymentHash('');
     await refreshPendingPayments();
     setNotice('Payment details created. Review the recipient and approve the native fUSD transfer.');
   }catch(err){setFundingError(err instanceof Error?err.message:'Checkout unavailable');}
   finally{setBusy(false);}
 }
 async function sendPayment(){
   if(!paymentIntent||!nativeAddress||paymentHash)return;
   setBusy(true);setError('');setFundingError('');
   try{
     const balance=await refreshFunding();
     if(!balance?.ready)return;
     if(balance.quote.amount_raw!==paymentIntent.amount_raw||balance.quote.denom!==paymentIntent.denom){
       setFundingError('Payment details no longer match the configured plan. Start a new checkout.');return;
     }
     const result=await nativeSend(nativeAddress,paymentIntent.recipient,paymentIntent.denom,paymentIntent.amount_raw,paymentIntent.memo);
     setPaymentHash(result.txHash);setManualPaymentHash(result.txHash);
     setPaymentResult('Transaction broadcast. Saving its hash and checking confirmation…');
     try{
       await api.broadcastPayment(paymentIntent.id,result.txHash);
       await refreshPendingPayments();
       setPaymentResult('Transaction broadcast and saved. Verify it on-chain to activate Pro.');
     }catch(saveErr){
       setPaymentResult('Transaction broadcast, but the server could not save its hash. Copy the hash below and use Save transaction hash to retry.');
       setError(saveErr instanceof Error?saveErr.message:'Could not persist transaction hash');
     }
   }catch(err){setError(err instanceof Error?err.message:'Wallet declined or payment failed');}
   finally{setBusy(false);}
 }
 async function confirmPayment(){if(!paymentIntent||!paymentHash)return;setBusy(true);setError('');
   try{const result=await api.verifyPayment(paymentIntent.id,paymentHash);
     setPaymentResult(result.status==='paid'?'Payment verified. Your testnet plan is active.':`Awaiting chain confirmation: ${result.reason||'pending'}`);
     if(result.status==='paid'){setSubscription(await api.subscription());api.usage().then(setUsage).catch(()=>{});refreshTransactions();setPendingPayments(prev=>prev.filter(x=>x.id!==paymentIntent.id));}
   }catch(e){setError(e instanceof Error?e.message:'Transfer verification failed');}finally{setBusy(false);}}
 async function askSecurityAssistant(){if(!project||!question.trim())return;setBusy(true);setError('');
   try{setAssistantAnswer((await api.ask(project.id,question)).answer);}catch(e){setError(e instanceof Error?e.message:'Assistant unavailable');}finally{setBusy(false);}}

 useEffect(()=>{api.health().then(()=>setBackend('online')).catch(()=>setBackend('offline'))},[]);
 function navigateAudit(jobId:string,stage:'audit-results'|'audit-progress'='audit-results'){
   if(window.location.pathname!==auditReportPath(jobId)){
     window.history.pushState({audit:jobId},'',auditReportPath(jobId));
   }
   setView(stage);setMenuOpen(false);setError('');
 }
 function navigate(next:View){
   const destination=VIEW_PATHS[next];
   if(window.location.pathname!==destination){
     window.history.pushState({section:next},'',destination);
   }
   setView(next);setMenuOpen(false);setError('');setNotice('');setLoadHistoryError('');
   if(next==='audit-history')refreshAuditHistory();
   if(next==='transaction-history'||next==='settings'||next==='overview')refreshTransactions();
   if(next==='billing'){void refreshPendingPayments();api.usage().then(setUsage).catch(()=>{});}}
 async function submitAudit(){setError('');setNotice('');if(!signedIn){setError('Sign in with QoreX Native to submit an audit.');return;}
 setBusy(true);setAudit(null);setAttestation(null);setAttestationRequest(null);setAttestationError('');setSelectedAuditId('');setAuditMessages([]);setAgentDone(0);navigate('audit-progress');try{
  const created=await api.createProject(projectName.trim()||'Untitled project');setProject(created);setRecentProjects(prev=>[created,...prev]);
  if(mode==='paste')await api.pasteSource(created.id,source);else{if(!files.length)throw new Error('Select at least one .sol file or a ZIP project.');await api.upload(created.id,files);}
  const job=await api.runAudit(created.id);setJobId(job.id);navigateAudit(job.id,'audit-progress');
  setNotice('Your source was accepted. The twelve-agent security audit is queued.');
 }catch(e){setBusy(false);setError(e instanceof Error?e.message:'Unexpected audit error');}}
 async function refreshAttestation(){
  if(!audit||audit.status!=='completed')return;
  try{
    setAttestationError('');
    const [status,request]=await Promise.all([api.attestation(audit.id),api.attestationRequest(audit.id)]);
    setAttestation(status);setAttestationRequest(request);
  }catch(e){setAttestationError(e instanceof Error?e.message:'Attestation verification unavailable');}
}
async function requestAttestationFromUI(){
  if(!audit||audit.status!=='completed'||attestationBusy)return;
  setAttestationBusy(true);setAttestationError('');
  try{
    const request=await api.requestAttestation(audit.id);
    setAttestationRequest(request);
    const status=await api.attestation(audit.id);
    setAttestation(status);
  }catch(e){setAttestationError(e instanceof Error?e.message:'Attestation request failed');}
  finally{setAttestationBusy(false);}
}
function renderAuditAttestation(){if(!audit||audit.status!=='completed')return null;return <section className="panel" style={{marginTop:16,padding:18}}>
  <div className="panel-head"><div><span className="eyebrow">ON-CHAIN EVIDENCE</span><h2>Audit report attestation</h2></div>
  <button className="secondary" onClick={()=>void refreshAttestation()} disabled={attestationBusy}>Refresh</button></div>
  {attestationError?<p className="help-text" role="alert">{attestationError}</p>:null}
  {!attestation?<p className="help-text">Checking Diana testnet attestation…</p>:
  <div className="service-list">
   <div><span>On-chain report status</span><strong>{attestation.status==='attested'?'Verified on Diana':attestation.status==='not_configured'?'Not configured':'Not attested yet'}</strong></div>
   <div><span>SHA-256 (report bytes)</span><code style={{overflowWrap:'anywhere'}}>{attestation.report_sha256}</code></div>
   {attestation.contract_address?<div><span>Contract (Diana EVM 9800)</span><code style={{overflowWrap:'anywhere'}}>{attestation.contract_address}</code></div>:null}
   {attestation.attested_at?<div><span>Published at (UTC)</span><span>{attestation.attested_at}</span></div>:null}
   {attestationRequest?<div><span>Publication request</span><strong>{attestationRequest.status.replace('_',' ')}</strong></div>:null}
   {attestationRequest?.tx_hash?<div><span>Transaction</span><code style={{overflowWrap:'anywhere'}}>{attestationRequest.tx_hash}</code></div>:null}
   <p className="help-text">Only the publisher can anchor the SHA-256 digest. This verifies report publication, not accuracy of the AI findings.</p>
   {attestation.status!=='attested' && attestation.status!=='not_configured' &&
    (!attestationRequest||['not_requested','queued','failed'].includes(attestationRequest.status))?
    <button className="primary" disabled={attestationBusy||(attestationRequest?.status==='failed'&&Boolean(attestationRequest.tx_hash))} onClick={()=>void requestAttestationFromUI()}>
     <ShieldCheck size={16}/>{attestationBusy?'Requesting…':attestationRequest?.status==='queued'?'Retry publishing queued request':'Request on-chain attestation'}
    </button>:null}
   {attestationRequest?.status==='failed'?<p className="help-text">Attestation could not be published. Contact support before retrying.</p>:null}
   {attestationRequest&&['queued','processing','submitted'].includes(attestationRequest.status)?
    <p className="help-text">Publication is pending. Use Refresh to check confirmations; this may take a short while.</p>:null}
  </div>}
</section>}
  function saveReport(){if(!audit?.report_markdown)return;const url=URL.createObjectURL(new Blob([audit.report_markdown],{type:'text/markdown'}));const a=document.createElement('a');a.href=url;a.download=`qoresentinel-audit-${project?.id||'report'}.md`;a.click();URL.revokeObjectURL(url)}
 return <div className="shell">
 <aside className={`sidebar ${menuOpen?'open':''}`}>
  <div className="brand"><div className="brand-mark"><Hexagon size={24}/><ShieldCheck size={14} className="brand-shield"/></div><div><strong>QoreSentinel</strong><small>SECURITY OPERATIONS</small></div><button className="mobile-close" aria-label="Close menu" onClick={()=>setMenuOpen(false)}><X size={18}/></button></div>
  <div className="workspace"><div className="workspace-logo">QS</div><div><strong>Personal Workspace</strong><span>Developer workspace</span></div><ChevronDown size={14}/></div>
  <nav>{['WORKSPACE','SECURITY','MANAGEMENT'].map(group=><div key={group} className="nav-group"><span className="nav-label">{group}</span>{menu.filter(item=>item.group===group).map(({id,name,icon:Icon})=><a key={id} href={VIEW_PATHS[id]} aria-current={view===id?'page':undefined} className={`nav-item ${view===id?'active':''}`} onClick={event=>{if(event.button!==0||event.ctrlKey||event.metaKey||event.altKey||event.shiftKey)return;event.preventDefault();navigate(id);}}><Icon size={17}/>{name}{id==='audit-results'&&audit?<span className="nav-dot"/>:null}</a>)}</div>)}</nav>
  <div className="sidebar-bottom"><div className="sidebar-footnote"><Shield size={17}/><div>QORECHAIN TESTNET<small>{nativeAddress?`${nativeAddress.slice(0,9)}…`:'qorechain-diana'}</small></div></div><div className="profile"><div className="avatar">QS</div><div><strong>Developer</strong><span>Local workspace</span></div><Settings2 size={15}/></div></div>
 </aside>
 {menuOpen&&<button className="scrim" onClick={()=>setMenuOpen(false)} aria-label="Close navigation"/>}
 <div className="main-area"><header className="topbar"><div className="topbar-left"><button className="mobile-open" onClick={()=>setMenuOpen(true)} aria-label="Open navigation"><Menu size={21}/></button><span>Workspace</span><span className="slash">/</span><strong>{menu.find(item=>item.id===view)?.name}</strong></div><div className="topbar-actions"><span className={`connection ${backend}`}><span className="connection-dot"/>{backend==='online'?'API Connected':backend==='checking'?'Checking API':'API Offline'}</span><a className="wallet-connect" href={FAUCET_URL} target="_blank" rel="noreferrer" title="Claim testnet QOR or fUSD">Faucet</a><button className="wallet-connect" disabled={busy} onClick={signedIn?logout:pendingLogin?verifyPendingLogin:signInNative} title={signedIn?'Sign out':'Authenticate using a wallet-approved native transaction'}><Wallet size={14}/>{signedIn?`${nativeAddress.slice(0,9)}… Sign out`:pendingLogin?'Verify login transaction':busy?'Connecting…':'Sign in with QoreX'}</button><button className="new-audit-top" onClick={()=>navigate('new-audit')}><Plus size={16}/> New Audit</button></div></header>
 <main className="page">
 {!signedIn&&walletIssue&&<section className="wallet-onboarding" role="alert" aria-live="polite">
  <div className="wallet-onboarding-heading"><Wallet size={19}/><div><strong>{walletIssue==='missing'?'Install QoreX to continue':walletIssue==='wrong-network'?'Switch QoreX to Diana Testnet':walletIssue==='locked'?'Unlock your QoreX wallet':'QoreX connection cancelled'}</strong><p>{walletMessage}</p></div></div>
  {walletIssue==='wrong-network'&&<p className="wallet-onboarding-guide">Open QoreX, unlock it, tap the extension version number seven times to reveal testnet controls, then select <strong>Switch to testnet (diana)</strong>. Return here and retry.</p>}
  {walletIssue==='missing'&&<p className="wallet-onboarding-guide">Install QoreX only from the official extension listing. Enable it for this site, then reload or retry the connection. Never share your recovery phrase.</p>}
  <div className="wallet-onboarding-actions">
   {walletIssue==='missing'&&<><a className="secondary" href={QOREX_CHROME_URL} target="_blank" rel="noopener noreferrer">Install for Chrome / Edge <ArrowRight size={14}/></a><a className="secondary" href={QOREX_FIREFOX_URL} target="_blank" rel="noopener noreferrer">Install for Firefox <ArrowRight size={14}/></a></>}
   {walletIssue==='wrong-network'&&<a className="secondary" href={QOREX_NETWORK_GUIDE} target="_blank" rel="noopener noreferrer">Network switching guide <ArrowRight size={14}/></a>}
   <button className="primary" disabled={busy} onClick={signInNative}><RefreshCcw size={14}/>{busy?'Connecting…':'Retry connection'}</button>
  </div>
 </section>}
 {!signedIn&&<div className={`native-login-banner ${needsFaucet?'low-gas':''}`}>
  <div><strong>{needsFaucet?'Low testnet QOR balance':'QoreX Native authentication'}</strong>
   <p>{needsFaucet?'Get test QOR before signing in. A first-time PQC key registration and the login transaction both require gas.':'Connect a qor1 wallet and approve a one-time hybrid-signed self-transfer to authenticate.'}</p>
   {nativeAddress&&<span className="mono-address">{nativeAddress}</span>}
   {gasBalance!==null&&<span className="native-balance">{(Number(gasBalance)/1_000_000).toLocaleString(undefined,{maximumFractionDigits:6})} test QOR available</span>}
  </div><div className="native-login-actions">{needsFaucet&&<><a className="secondary" href={FAUCET_URL} target="_blank" rel="noreferrer">Open testnet faucet <ArrowRight size={14}/></a><button className="secondary" onClick={()=>navigator.clipboard.writeText(FAUCET_URL)}>Copy faucet link</button></>}{pendingLogin&&<button className="primary" onClick={verifyPendingLogin} disabled={busy}>Verify pending login</button>}</div>
 </div>}
 {view==='overview'&&<><Header kicker="OVERVIEW / WORKSPACE" title="Security at a glance" sub="Manage code submissions, run audits, and track your security workflow." action={<button className="primary" onClick={()=>navigate('new-audit')}><Plus size={16}/> New Security Audit</button>}/><div className="stats"><div className="stat"><div className="stat-label">PROJECTS CREATED <FolderOpen size={16}/></div><strong>{recentProjects.length||'—'}</strong><span>Wallet projects</span></div><div className="stat"><div className="stat-label">AUDITS COMPLETED <CheckCircle2 size={16}/></div><strong>{allAudits.filter(x=>x.status==='completed').length||'—'}</strong><span>Saved audit reports</span></div><div className="stat"><div className="stat-label">SECURITY FINDINGS <ShieldAlert size={16}/></div><strong>{audit?.findings_status==='structured_parsing_not_implemented'?'—':audit?audit.findings.length:'—'}</strong><span>Structured results pending</span></div><div className="stat"><div className="stat-label">PQC READINESS <Fingerprint size={16}/></div><strong>{pqcScan?.components??'—'}</strong><span>{pqcScan?.method||'No source inventory yet'}</span></div></div><div className="dashboard-grid"><section className="panel large"><div className="panel-head"><div><span className="eyebrow">ACTIVITY</span><h2>Security Operations</h2></div><button className="secondary" onClick={()=>navigate('audit-history')}>View audit history <ArrowRight size={14}/></button></div>{project?<div className="activity-row"><span className="square-icon"><FileCode2 size={18}/></span><div><strong>{project.name}</strong><p>{audit?'Audit response received':'Project created; audit not completed'}</p></div><Status tone={audit?'good':'neutral'}>{audit?'Completed':'In progress'}</Status></div>:<Empty icon={Activity} title="No audit activity yet" desc="Your submitted projects and recent audits will appear here." action={<button className="secondary" onClick={()=>navigate('new-audit')}>Start your first audit <ArrowRight size={14}/></button>}/>}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">SYSTEM STATUS</span><h2>Services & Integrations</h2></div></div><div className="service-list"><div><span><Radio size={16}/> FastAPI service</span><Status tone={backend==='online'?'good':'warn'}>{backend}</Status></div><div><span><Sparkles size={16}/> Multi-agent audit</span><Status tone={signedIn?"cyan":"neutral"}>{signedIn?"Ready for requests":"Wallet login"}</Status></div><div><span><Fingerprint size={16}/> QoreScan</span><Status tone="cyan">Source inventory</Status></div><div><span><Wallet size={16}/> QoreChain testnet</span><Status tone={nativeAddress?"good":"neutral"}>{nativeAddress?"Connected":"Diana testnet"}</Status></div></div></section></div><section className="panel"><div className="panel-head"><div><span className="eyebrow">MY PROJECTS</span><h2>Recent projects</h2></div></div>{recentProjects.length?<div className="service-list">{recentProjects.slice(0,8).map(item=><div key={item.id}><span><FolderOpen size={16}/>{item.name}</span><button className="secondary" onClick={async()=>{setProject(item);setPqcScan(null);setAudit(null);setError('');navigate('pqc');}}>Open <ArrowRight size={14}/></button></div>)}</div>:<p className="help-text">Sign in to see your existing projects.</p>}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">QUICK ACTIONS</span><h2>Start investigating</h2></div></div><div className="quick-grid"><button onClick={()=>navigate('new-audit')}><FileCode2/><strong>Analyze smart contract</strong><span>Paste Solidity or upload project files</span><ArrowRight size={16}/></button><button onClick={()=>navigate('audit-history')}><ShieldAlert/><strong>Review findings</strong><span>Open saved audit reports and evidence</span><ArrowRight size={16}/></button><button onClick={()=>navigate('pqc')}><Fingerprint/><strong>Quantum readiness</strong><span>View upcoming cryptographic inventory tools</span><ArrowRight size={16}/></button></div></section></>}
 {view==='audit-history'&&<><Header kicker="SECURITY / AUDIT HISTORY" title="Audit history" sub="Every submitted audit remains available under its original job ID. Reports can be reopened without running another audit." action={<button className="secondary" onClick={refreshAuditHistory}><RefreshCcw size={15}/> Refresh</button>}/>
 {loadHistoryError&&<div role="alert" className="alert">{loadHistoryError}</div>}
 <section className="panel"><div className="panel-head"><h2>Saved audits</h2><Status tone="cyan">{allAudits.length} loaded</Status></div>
 {!signedIn?<Empty icon={LockKeyhole} title="Connect your wallet" desc="Sign in with your original QoreX address to view past audits."/>:!allAudits.length?<Empty icon={BookOpen} title="No saved audits yet" desc="Completed and pending audits associated with this wallet will appear here."/>:
 <div className="history-list">{allAudits.map(item=><div className="history-item" key={item.id}>
 <div><strong>{item.project_name}</strong><p>{new Date(item.created_at).toLocaleString()} · Job {item.id.slice(0,8)}…</p></div>
 <Status tone={item.status==='completed'?'good':item.status==='failed'?'warn':'cyan'}>{item.status}</Status>
 <a className="secondary" href={auditReportPath(item.id)} onClick={event=>{if(event.button!==0||event.ctrlKey||event.metaKey||event.altKey||event.shiftKey)return;event.preventDefault();void openAudit(item.id);}}>{item.status==='completed'?'Open report & discussion':'View audit'} <ArrowRight size={14}/></a>
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
 {view==='audit-results'&&<>{renderAuditAttestation()}<Header kicker="SECURITY / AUDIT RESULTS" title="Audit findings & evidence" sub="Review the report returned by the real backend audit engine." action={audit?.report_markdown?<div className="audit-link-actions"><button className="secondary" onClick={()=>navigator.clipboard.writeText(window.location.origin+auditReportPath(audit.id))}>Copy audit link</button><button className="primary" onClick={saveReport}><Download size={16}/> Download Markdown</button></div>:undefined}/>{audit?<><div className="stats small-stats"><div className="stat"><div className="stat-label">AUDIT STATUS</div><strong className="stat-word">{audit.status}</strong><span>Backend-reported</span></div><div className="stat"><div className="stat-label">AI-REPORTED FINDINGS</div><strong>{audit.findings_status==='structured_parsing_not_implemented'?'—':audit.findings.length}</strong><span>Extracted from report, not verified</span></div><div className="stat"><div className="stat-label">PROJECT</div><strong className="stat-word">{project?.name||'Unknown'}</strong><span>{project?.id||'No project ID'}</span></div></div>{audit.findings.length>0&&<section className="panel"><div className="panel-head"><div><span className="eyebrow">AI-REPORTED FINDINGS</span><h2>Finding summaries</h2></div><Status tone="warn">Unverified</Status></div>
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
 </section></>:<section className="panel"><Empty icon={ShieldAlert} title={loadingHistory?'Loading audit report':!signedIn&&auditIdFromPathname(pathname)?'Sign in to view this audit':'No audit selected'} desc={loadHistoryError||(!signedIn&&auditIdFromPathname(pathname)?'Authenticate with your QoreX wallet to load this private report.':'Open a saved report from Audit History without running another audit.')} action={!signedIn?<button className="primary" onClick={signInNative}>Sign in with QoreX</button>:<button className="primary" onClick={()=>navigate('audit-history')}>Open audit history <ArrowRight size={16}/></button>}/></section>}</>}
 {view==='assistant'&&<><Header kicker="SECURITY / AI ASSISTANT" title="AI security assistant" sub="Discuss submitted Solidity source and audit evidence."/><section className="panel"><div className="panel-head"><h2>Project security analysis</h2><Status tone={project?'cyan':'neutral'}>{project?.name||'Select a project'}</Status></div>{project?<><label className="field-label" htmlFor="assistant-question">Your question</label><textarea id="assistant-question" className="field" rows={4} maxLength={2000} placeholder="Which access-control assumptions should I verify?" value={question} onChange={e=>setQuestion(e.target.value)}/><button className="primary" disabled={busy||!question.trim()} onClick={askSecurityAssistant}><MessageSquareText size={16}/> Ask assistant</button>{assistantAnswer&&<><div className="section-separator"/><pre className="report">{assistantAnswer}</pre><p className="help-text">AI-generated response grounded in supplied files; verify any claims independently.</p></>}</>:<Empty icon={MessageSquareText} title="Submit a contract to begin" desc="The assistant uses source files from your workspace. Open a project first." action={<button className="secondary" onClick={()=>navigate('new-audit')}>Submit source <ArrowRight size={16}/></button>}/>}</section></>}
 {view==='pqc'&&<><Header kicker="QUANTUM RESILIENCE / INVENTORY" title="Post-Quantum Readiness" sub="Inspect source-level cryptographic references and QoreChain hybrid-signature evidence."/><div className="stats small-stats"><div className="stat"><div className="stat-label">CRYPTO COMPONENTS</div><strong>{pqcScan?.components??'—'}</strong><span>{pqcScan?.method||'No scan yet'}</span></div><div className="stat"><div className="stat-label">HYBRID PROOF</div><strong className="stat-word">{txEvidence?.chain_reports_verified?'CHAIN VERIFIED':'—'}</strong><span>{txEvidence?.found?'QoreChain testnet evidence':'No inspected transaction'}</span></div><div className="stat"><div className="stat-label">CBOM</div><strong className="stat-word">{pqcScan?.cbom?'AVAILABLE':'—'}</strong><span>CycloneDX inventory</span></div></div><div className="settings-grid"><section className="panel"><div className="panel-head"><h2>Cryptographic inventory</h2><Status tone="cyan">SOLIDITY SOURCE</Status></div><p className="plain-copy">Scan Solidity without starting a paid AI audit. PQC scans are not saved to history; download the CBOM or report if you want to retain a result.</p>
<div className="tab-row pqc-mode-tabs" role="group" aria-label="PQC source type">
  <button className={pqcInputMode==='project'?'selected':''} onClick={()=>{setPqcInputMode('project');setPqcScan(null);}}><FolderOpen size={15}/> Saved project</button>
  <button className={pqcInputMode==='paste'?'selected':''} onClick={()=>{setPqcInputMode('paste');setPqcScan(null);}}><Code2 size={15}/> Paste Solidity</button>
  <button className={pqcInputMode==='upload'?'selected':''} onClick={()=>{setPqcInputMode('upload');setPqcScan(null);}}><Upload size={15}/> Upload files / ZIP</button>
</div>
{pqcInputMode==='project'&&<div className="pqc-source-input">
 <label className="field-label" htmlFor="pqc-project">Choose your saved project</label>
 <select id="pqc-project" className="field" value={pqcProjectId||project?.id||''} onChange={e=>{setPqcProjectId(e.target.value);setPqcScan(null);}}>
 <option value="">Select a project</option>
 {recentProjects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
 {project&&!recentProjects.some(p=>p.id===project.id)&&<option value={project.id}>{project.name}</option>}
 </select>
 {!recentProjects.length&&!project&&<p className="help-text">No saved projects yet. Paste Solidity or upload source files instead.</p>}
 </div>}
{pqcInputMode==='paste'&&<div className="pqc-source-input">
 <label className="field-label" htmlFor="pqc-pasted-source">Solidity source</label>
 <textarea id="pqc-pasted-source" className="code-editor pqc-editor" spellCheck={false} placeholder={"// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\ncontract Example {}"} value={pqcSource} onChange={e=>{setPqcSource(e.target.value);setPqcScan(null);}}/>
 <p className="help-text">Source is scanned for cryptographic references and discarded after the request. No project is created.</p>
 </div>}
{pqcInputMode==='upload'&&<div className="pqc-source-input">
 <input ref={pqcFileRef} type="file" accept=".sol,.zip" multiple hidden onChange={e=>{const next=Array.from(e.target.files||[]);setPqcUploads(next);setPqcScan(null);}}/>
 <button className="upload-box" onClick={()=>pqcFileRef.current?.click()}><CloudUpload size={24}/><strong>Choose Solidity files or a ZIP</strong><span>ZIP archives must be uploaded alone.</span></button>
 {pqcUploads.length>0&&<p className="help-text">{pqcUploads.map(f=>f.name).join(', ')}</p>}
 <p className="help-text">Files are scanned in memory and discarded after scanning. No saved project or PQC history.</p>
 </div>}
<button className="primary" disabled={busy||!signedIn||(pqcInputMode==='project'&&!(pqcProjectId||project?.id))||(pqcInputMode==='paste'&&!pqcSource.trim())||(pqcInputMode==='upload'&&!pqcUploads.length)} onClick={runPqc}><Fingerprint size={16}/>{busy?'Scanning source…':'Analyze source — free'}</button>
{!signedIn&&<p className="help-text">Sign in with QoreX to use the scanner; no wallet transaction is required for each scan and no audit credits are consumed.</p>} {pqcScan&&<><div className="section-separator"/><p className="help-text">{pqcScan.limitations}</p><p className="help-text">Scanner: <strong>{pqcScan.method}</strong></p>{pqcScan.risk_summary&&<div className="pqc-risk-summary">{Object.entries(pqcScan.risk_summary).map(([kind,count])=><div className="pqc-risk-count" key={kind}><strong>{count}</strong><span>{kind==='quantum-vulnerable'?'Quantum migration review':kind==='post-quantum'?'Post-quantum references':kind==='symmetric'?'Hashes / symmetric':kind}</span></div>)}</div>}<div className="service-list">{pqcScan.evidence.slice(0,30).map((e,i)=><div key={i}><span><Code2 size={14}/>{e.algorithm} — {e.file}{e.line?':'+e.line:''}</span><Status tone={e.classification==='quantum-vulnerable'?'warn':e.classification==='post-quantum'?'good':'neutral'}>{e.classification}</Status></div>)}</div><button className="secondary" onClick={()=>{const a=document.createElement('a');const url=URL.createObjectURL(new Blob([JSON.stringify(pqcScan.cbom,null,2)],{type:'application/json'}));a.href=url;a.download='qoresentinel-cbom.json';a.click();URL.revokeObjectURL(url);}}><Download size={16}/> Export CBOM</button>{pqcScan.report_markdown&&<button className="secondary" onClick={()=>{const a=document.createElement('a');const url=URL.createObjectURL(new Blob([pqcScan.report_markdown!],{type:'text/markdown'}));a.href=url;a.download='qorescan-readiness-report.md';a.click();URL.revokeObjectURL(url);}}><Download size={16}/> Download QoreScan report</button>}</>}</section><section className="panel"><div className="panel-head"><h2>QoreChain hybrid-signature evidence</h2><Status tone="cyan">DIANA TESTNET</Status></div><div className="info-note"><ShieldCheck size={16}/>A hybrid proof sends 1 uqor (0.000001 testnet QOR) from your QoreX native address back to itself. Network fees apply. Your wallet will request approval.</div><button className="secondary" disabled={!nativeAddress||busy} onClick={makeHybridProof}><ShieldCheck size={15}/> Send hybrid testnet proof</button>{pqcWalletLocked&&<div className="wallet-onboarding pqc-unlock" role="alert"><div className="wallet-onboarding-heading"><LockKeyhole size={18}/><div><strong>QoreX is locked</strong><p>QoreSentinel requested QoreX to open its unlock prompt. If your extension did not open a popup, update QoreX or unlock it from your browser toolbar and retry. Source scanning is unaffected.</p></div></div><button className="secondary" disabled={busy} onClick={makeHybridProof}><RefreshCcw size={15}/> Retry QoreX prompt</button></div>}{hybridSendStatus&&<p className="help-text">{hybridSendStatus}</p>}<div className="section-separator"/><label className="field-label" htmlFor="proof-hash">Native transaction hash</label><input id="proof-hash" className="field" value={txHash} onChange={e=>setTxHash(e.target.value)} placeholder="0x… (64 hex characters)"/><button className="secondary" disabled={busy||!txHash.trim()} onClick={inspectTx}><Search size={15}/> Inspect transaction</button>{txEvidence&&<div className="service-list"><div><span>Found on chain</span><Status tone={txEvidence.found?'good':'warn'}>{txEvidence.found?'Yes':'No'}</Status></div>{txEvidence.found&&<><div><span>Hybrid layer present</span><Status tone={txEvidence.hybrid_layer_present?'good':'warn'}>{txEvidence.hybrid_layer_present?'Yes':'No'}</Status></div><div><span>Chain-reported verification</span><Status tone={txEvidence.chain_reports_verified?'good':'warn'}>{txEvidence.chain_reports_verified?'Verified':'Not verified'}</Status></div><p className="help-text">{txEvidence.verification_method}</p></>}</div>}</section></div></>}
 {view==='billing'&&<><Header kicker="MANAGEMENT / BILLING & USAGE" title="Subscriptions & usage" sub="Purchase audit plans using QoreX native fUSD bank transfers. All payments require on-chain confirmation."/><div className="stats small-stats"><div className="stat"><div className="stat-label">CURRENT PLAN</div><strong className="stat-word">{subscription?.plan?.toUpperCase()||'FREE'}</strong><span>{subscription?.expires_at?`Expires ${new Date(subscription.expires_at*1000).toLocaleDateString()}`:'No paid entitlement'}</span><span>{usage?`${usage.audits.remaining} of ${usage.audits.limit} audits remaining (24h)`:'Checking usage…'}</span></div><div className="stat"><div className="stat-label">NETWORK</div><strong className="stat-word">DIANA</strong><span>QoreChain 9800 · Test tokens only</span></div><div className="stat"><div className="stat-label">CHECKOUT</div><strong className="stat-word">{paymentResult?'IN PROGRESS':'—'}</strong><span>Backend verifies native bank transfers</span></div></div><section className="panel"><div className="panel-head"><h2>Testnet fUSD checkout</h2><Status tone="cyan">NO REAL MONETARY VALUE</Status></div><p className="plain-copy">Approve a native QoreX bank transfer. Access activates only after the backend verifies the sender, recipient, exact fUSD amount, memo, hybrid signature and confirmations.</p>
 {signedIn&&<div className="checkout-funding" aria-live="polite">
   <div className="checkout-funding-head"><strong>Wallet balance check</strong><button className="secondary" disabled={busy||fundingLoading} onClick={()=>void refreshFunding().catch(()=>{})}><RefreshCcw size={14}/>{fundingLoading?'Checking…':'Refresh balances'}</button></div>
   {funding&&<div className="checkout-funding-data">
     <div><span>Available fUSD</span><strong>{displayUnits(funding.fusdRaw)} fUSD</strong></div>
     <div><span>Pro — 30 days</span><strong>{funding.quote.amount_fusd} fUSD</strong></div>
     <div><span>QOR for gas</span><strong>{displayUnits(funding.qorRaw)} QOR</strong></div>
   </div>}
   {!funding&&fundingLoading&&<p className="help-text">Checking fUSD and QOR balances on Diana testnet…</p>}
   {fundingError&&<p role="alert" className="checkout-funding-error">{fundingError}</p>}
   {fundingMessage&&<div className="checkout-funding-warning" role="status"><CircleAlert size={17}/><p>{fundingMessage}</p><div className="checkout-funding-actions"><a className="secondary" href={FAUCET_URL} target="_blank" rel="noreferrer">Open faucet <ArrowRight size={14}/></a><button className="secondary" onClick={()=>void navigator.clipboard.writeText(FAUCET_URL)}>Copy faucet link</button></div></div>}
 </div>}{signedIn&&<section className="checkout-recovery">
  <div className="checkout-funding-head"><strong>Recover pending payment</strong><button className="secondary" onClick={()=>void refreshPendingPayments()} disabled={busy||pendingPaymentLoading}><RefreshCcw size={14}/>{pendingPaymentLoading?'Loading…':'Refresh pending payments'}</button></div>
  <p className="help-text">Previously created checkout records are saved under your QoreX address. A recorded transaction is not counted as paid until verified on-chain.</p>
  {pendingPaymentError&&<p role="alert" className="checkout-funding-error">{pendingPaymentError}</p>}
  {pendingPayments.length>0?<div className="history-list">{pendingPayments.map(p=><div className="history-item" key={p.id}><div><strong>Pro · {p.amount_fusd} fUSD</strong><p>Expires {new Date(p.expires_at*1000).toLocaleString()} · {p.tx_hash?'Broadcast hash saved':'No broadcast hash saved'}</p></div><button className="secondary" disabled={busy} onClick={()=>resumePayment(p)}>Resume checkout <ArrowRight size={14}/></button></div>)}</div>:<p className="help-text">No open checkout records found.</p>}
 </section>}{!signedIn?<button className="primary" onClick={signInNative}><Wallet size={16}/> Sign in with QoreX</button>:<><div className="quick-grid"><button disabled={busy||fundingLoading||Boolean(paymentHash)||!funding||Boolean(fundingMessage)||Boolean(fundingError)} onClick={()=>checkout('pro')}><ShieldCheck/><strong>Pro — 30 days</strong><span>View and approve a testnet payment</span><ArrowRight size={15}/></button></div>{paymentIntent&&<div className="checkout-details"><div className="section-separator"/><div className="service-list"><div><span>Amount (fUSD)</span><strong>{paymentIntent.amount_fusd}</strong></div><div><span>Chain</span><strong>{paymentIntent.network}</strong></div><div><span>Recipient</span><span className="mono-address">{paymentIntent.recipient}</span></div><div><span>Payment window</span><span>{new Date(paymentIntent.expires_at*1000).toLocaleTimeString()}</span></div></div><button className="primary" disabled={busy||fundingLoading||Boolean(paymentHash)||Boolean(fundingMessage)||Boolean(fundingError)} onClick={sendPayment}><Wallet size={16}/> Approve native fUSD transfer</button><div className="section-separator"/><label className="field-label" htmlFor="recover-payment-hash">Native transaction hash</label><input className="field" id="recover-payment-hash" placeholder="Paste a QoreX transaction hash if you already sent payment" value={manualPaymentHash} onChange={e=>setManualPaymentHash(e.target.value)}/><button className="secondary" disabled={busy||!manualPaymentHash.trim()} onClick={storePaymentHash}>Save transaction hash</button>{paymentHash&&<><p className="help-text">Transaction: {paymentHash}</p><button className="secondary" disabled={busy} onClick={confirmPayment}><CheckCircle2 size={16}/> Verify payment on-chain</button></>}{paymentResult&&<div className="info-note"><Clock3 size={16}/>{paymentResult}</div>}</div>}</>}</section></>}
 {view==='settings'&&<><Header kicker="MANAGEMENT / SETTINGS" title="Wallet & privacy" sub="Connected identities, security preferences, and data access."/><div className="settings-grid"><section className="panel"><div className="panel-head"><h2>Wallet connections</h2></div><div className="service-list"><div><span>QoreX Native</span><Status tone={nativeAddress?'good':'neutral'}>{nativeAddress?nativeAddress.slice(0,14)+'…':'Not connected'}</Status></div><div><span>QoreX authenticated session</span><Status tone={signedIn?'good':'neutral'}>{signedIn?nativeAddress.slice(0,14)+'…':'Not signed in'}</Status></div></div><button className="secondary" onClick={signedIn?logout:pendingLogin?verifyPendingLogin:signInNative}><LockKeyhole size={15}/>{signedIn?'Sign out of wallet session':pendingLogin?'Verify pending login':'Authenticate QoreX Native wallet'}</button></section><section className="panel"><div className="panel-head"><h2>Privacy & security</h2></div><p className="plain-copy">Never disclose recovery phrases or private keys. Security findings are AI-assisted and should be verified independently. Testnet tokens have no real monetary value.</p><button className="secondary" onClick={()=>navigate('transaction-history')}><Activity size={16}/> View transaction history</button><div className="service-list"><div><span>Service health</span><Status tone={backend==='online'?'good':'warn'}>{backend}</Status></div><div><span>Session</span><Status tone={signedIn?'good':'neutral'}>{signedIn?'Wallet signed in':'Signed out'}</Status></div></div></section></div></>}
 {error&&view!=='audit-progress'&&<div role="alert" className="floating-error"><CircleAlert size={18}/><span>{error}</span><button onClick={()=>setError('')} aria-label="Dismiss error"><X size={16}/></button></div>}
 </main></div></div>
}
