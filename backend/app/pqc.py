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

def scan(files:dict[str,str]):
    """Use installed QoreScan CLI if explicitly configured; otherwise label heuristic output."""
    import json
    import os
    import subprocess
    import tempfile
    from pathlib import Path
    executable=os.getenv('QORESCAN_BIN','').strip()
    if not executable:return analyze_source(files)
    with tempfile.TemporaryDirectory(prefix='qs-pqc-') as base:
        src=Path(base)/'sources';src.mkdir()
        for name,body in files.items():
            # Ingestion already validates paths. Defend again at tool boundary.
            p=(src/name).resolve()
            if not p.is_relative_to(src.resolve()):raise ValueError('Unsafe source filename')
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8')
        output=Path(base)/'scan.json'
        result=subprocess.run([executable,'solidity',str(src),'--out',str(output)],
                              capture_output=True,text=True,timeout=45,check=False)
        if result.returncode!=0:raise RuntimeError('QoreScan failed (check server logs)')
        cbom=json.loads(output.read_text(encoding='utf-8'))
    if cbom.get('bomFormat')!='CycloneDX':raise RuntimeError('QoreScan did not return CycloneDX')
    return {'status':'completed','method':'qorescan-cli','cbom':cbom,'components':len(cbom.get('components',[])),
            'evidence':[],'limitations':'Cryptographic inventory only; not a certification of quantum safety.'}
