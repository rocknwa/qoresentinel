"""Source-only cryptographic inventory with file/line evidence and CycloneDX output.
Not a certification and not a replacement for QoreScan.
"""
import re
import uuid
from datetime import datetime,timezone

RULES=[
 ('ecrecover',r'\becrecover\s*\(','ECDSA secp256k1','classical','signature'),
 ('ECDSA import',r'\b(?:ECDSA|SignatureChecker)\b','ECDSA secp256k1','classical','signature'),
 ('P-256',r'\b(?:P256|p256Verify|secp256r1)\b','ECDSA P-256','classical','signature'),
 ('RSA',r'\b(?:RSA|RS256)\b','RSA','classical','signature'),
 ('keccak256',r'\bkeccak256\s*\(','Keccak-256','classical','hash'),
 ('sha256',r'\bsha256\s*\(','SHA-256','classical','hash'),
 ('ripemd160',r'\bripemd160\s*\(','RIPEMD-160','classical','hash'),
 ('ML-DSA',r'\b(?:ML[_-]?DSA|Dilithium)\b','ML-DSA (claimed reference)','unknown','signature'),
 ('ML-KEM',r'\b(?:ML[_-]?KEM|Kyber)\b','ML-KEM (claimed reference)','unknown','kem'),
 ('Qore PQC API',r'\b(?:IQorePQC|pqcVerify|pqcKeyStatus)\b','QoreChain PQC API reference','unknown','other'),
]

def analyze_source(files:dict[str,str]):
    matches=[];components={}
    for file,code in sorted(files.items()):
        for line_idx,line in enumerate(code.splitlines(),1):
            if re.match(r'^\s*(//|\*)',line):continue
            for label,pattern,algorithm,classification,kind in RULES:
                if re.search(pattern,line,re.I):
                    evidence={'file':file,'line':line_idx,'excerpt':line.strip()[:180],'rule':label,'algorithm':algorithm,'classification':classification,'confidence':'source-reference-only'}
                    matches.append(evidence)
                    components[(algorithm,classification,kind)]=True
    cbom={'bomFormat':'CycloneDX','specVersion':'1.6','serialNumber':'urn:uuid:'+str(uuid.uuid4()),'version':1,
       'metadata':{'timestamp':datetime.now(timezone.utc).isoformat(),'component':{'type':'application','name':'QoreSentinel source heuristic','version':'0.2'},'properties':[{'name':'qoresentinel:scan-method','value':'heuristic-source-reference-only'}]},
       'components':[{'type':'cryptographic-asset','bom-ref':'source:'+re.sub('[^a-zA-Z0-9]','-',name), 'name':name,'cryptoProperties':{'assetType':'algorithm','algorithmProperties':{'primitive':kind,'cryptoFunctions':[]}}, 'properties':[{'name':'qoresentinel:classification','value':classification}]} for name,classification,kind in components],
       'dependencies':[]}
    return {'status':'completed','method':'source-heuristic','evidence':matches,'components':len(components),'cbom':cbom,
       'limitations':'Source references only. This is not a QoreScan run, cryptographic validation, or proof of quantum safety. Imports may be unresolved.'}

def summarize_cbom(cbom:dict)->dict:
    """Preserve QoreScan classification and source occurrences without claiming a security audit."""
    categories={}
    evidence=[]
    for item in cbom.get('components',[]):
        if not isinstance(item,dict) or item.get('type')!='cryptographic-asset':
            continue
        props={p['name']:p.get('value','') for p in item.get('properties',[])
               if isinstance(p,dict) and isinstance(p.get('name'),str)}
        classification=props.get('qorescan:classification','unknown')
        categories[classification]=categories.get(classification,0)+1
        name=item.get('name','Unnamed asset')
        for occ in (item.get('evidence') or {}).get('occurrences',[]):
            if not isinstance(occ,dict):continue
            evidence.append({'file':str(occ.get('location') or 'network'),
                'line':int(occ.get('line') or 0),
                'excerpt':str(occ.get('additionalContext') or occ.get('symbol') or '')[:300],
                'algorithm':name,'classification':classification,
                'confidence':'scanner-observation','standard':props.get('qorescan:standard',''),
                'transition':props.get('qorescan:transition','')})
    return {'risk_summary':categories,'evidence':evidence[:250],
            'evidence_truncated':len(evidence)>250}

def scan(files:dict[str,str]):
    """Run the official QoreScan 0.1.0 CLI when installed, never execute submitted Solidity."""
    import json
    import os
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path
    executable=os.getenv('QORESCAN_BIN','').strip() or shutil.which('qorescan')
    if not executable:
        return analyze_source(files)
    if not files:raise ValueError('No Solidity source provided')
    with tempfile.TemporaryDirectory(prefix='qs-pqc-') as base:
        src=Path(base)/'sources';src.mkdir()
        for name,body in files.items():
            target=(src/name).resolve()
            if not target.is_relative_to(src.resolve()) or target.suffix.lower()!='.sol':
                raise ValueError('Invalid Solidity source path')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(body,encoding='utf-8')
        output=Path(base)/'qorescan.cbom.json'
        network=os.getenv('QORE_QORESCAN_NETWORK','').lower().strip()
        if network not in ('','testnet'):raise ValueError('Unsupported QoreScan network')
        cmd=([executable,'scan','--network','testnet','--solidity',str(src)]
             if network=='testnet' else [executable,'solidity',str(src)])
        cmd+=['--out',str(output)]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=70,check=False)
        if result.returncode!=0:
            raise RuntimeError('QoreScan scan failed')
        if not output.exists() or output.stat().st_size>12_000_000:
            raise RuntimeError('Invalid QoreScan CBOM')
        cbom=json.loads(output.read_text(encoding='utf-8'))
        if (not isinstance(cbom,dict) or cbom.get('bomFormat')!='CycloneDX'
                or cbom.get('specVersion')!='1.6' or not isinstance(cbom.get('components'),list)):
            raise RuntimeError('QoreScan produced an invalid CycloneDX CBOM')
        report=Path(base)/'qorescan-report.md'
        markdown=''
        report_cmd=[executable,'report','--framework','nis','--cbom',str(output),'--out',str(report)]
        try:
            report_run=subprocess.run(report_cmd,capture_output=True,text=True,timeout=20,check=False)
            if report_run.returncode==0 and report.exists() and report.stat().st_size<2_000_000:
                markdown=report.read_text(encoding='utf-8')
        except (OSError,subprocess.TimeoutExpired):
            pass
    summary=summarize_cbom(cbom)
    return {'status':'completed','method':'qorescan-0.1.0'+('-diana' if network else '-solidity'),
            'cbom':cbom,'components':len(cbom.get('components',[])),
            'evidence':summary['evidence'],'risk_summary':summary['risk_summary'],
            'evidence_truncated':summary['evidence_truncated'],'report_markdown':markdown,
            'limitations':'QoreScan inventory and risk classification are indicators, not a full audit or certification. Uploaded dependencies may be unresolved.'}
