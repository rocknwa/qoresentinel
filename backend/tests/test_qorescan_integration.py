"""Official QoreScan integration boundary tests. No network or external binary is run."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

FIXTURE={
  "bomFormat":"CycloneDX","specVersion":"1.6","version":1,
  "components":[
    {"type":"cryptographic-asset","name":"ECDSA secp256k1",
     "properties":[{"name":"qorescan:classification","value":"quantum-vulnerable"},
                   {"name":"qorescan:transition","value":"NIST transition review"}],
     "evidence":{"occurrences":[{"location":"Contract.sol","line":7,
                 "additionalContext":"ecrecover signature check"}]}},
    {"type":"cryptographic-asset","name":"Keccak-256",
     "properties":[{"name":"qorescan:classification","value":"symmetric"}],
     "evidence":{"occurrences":[{"location":"Contract.sol","line":8,
                 "additionalContext":"keccak256 hash"}]}}
  ]
}

def test_qorescan_cli_cbom_report_and_risk(monkeypatch):
    from app import pqc
    monkeypatch.setenv('QORESCAN_BIN','/opt/bin/qorescan')
    commands=[]
    def fake_run(args,**kwargs):
        commands.append(args)
        output=Path(args[-1]);output.parent.mkdir(parents=True,exist_ok=True)
        if args[1]=='solidity':
            output.write_text(json.dumps(FIXTURE),encoding='utf-8')
        elif args[1]=='report':
            output.write_text('# Migration review\n',encoding='utf-8')
        else:raise AssertionError(args)
        assert kwargs['check'] is False and kwargs['timeout']<=70
        return SimpleNamespace(returncode=0,stdout='',stderr='')
    import subprocess
    monkeypatch.setattr(subprocess,'run',fake_run)
    result=pqc.scan({'Contract.sol':'contract A { function f() public { keccak256(""); } }'})
    assert result['method']=='qorescan-0.1.0-solidity'
    assert result['components']==2
    assert result['risk_summary']=={'quantum-vulnerable':1,'symmetric':1}
    assert result['evidence'][0]['file']=='Contract.sol'
    assert result['report_markdown'].startswith('# Migration review')
    assert len(commands)==2 and commands[0][1]=='solidity'
    assert '--out' in commands[0] and '--cbom' in commands[1]

def test_invalid_source_path_rejected_before_scanner(monkeypatch):
    from app import pqc
    monkeypatch.setenv('QORESCAN_BIN','/opt/bin/qorescan')
    with pytest.raises(ValueError):
        pqc.scan({'../private.sol':'contract Private {}'})

def test_scanner_error_does_not_silently_become_heuristic(monkeypatch):
    from app import pqc
    import subprocess
    monkeypatch.setenv('QORESCAN_BIN','/opt/bin/qorescan')
    monkeypatch.setattr(subprocess,'run',lambda *args,**kw:SimpleNamespace(returncode=2))
    with pytest.raises(RuntimeError):
        pqc.scan({'Contract.sol':'contract C {}'})

def test_absent_binary_reports_heuristic_method(monkeypatch):
    from app import pqc
    import shutil
    monkeypatch.delenv('QORESCAN_BIN',raising=False)
    monkeypatch.setattr(shutil,'which',lambda x:None)
    result=pqc.scan({'Contract.sol':'contract C { function f() public { keccak256(""); } }'})
    assert result['method']=='source-heuristic'
    assert 'not a QoreScan run' in result['limitations']
