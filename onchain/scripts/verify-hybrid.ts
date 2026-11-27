/**
 * Verifies Diana REST evidence for an EVM window-opening hybrid transaction.
 * Usage: npm run verify:hybrid -- <native-tx-hash>
 */
const hash=(process.argv[2]??"").replace(/^0x/i,"").toUpperCase();
if (!/^[0-9A-F]{64}$/.test(hash)) throw new Error("Pass a 64-hex-character native transaction hash");
const response=await fetch(`https://api-testnet.qore.host/cosmos/tx/v1beta1/txs/${hash}`);
if (!response.ok) throw new Error(`Diana REST transaction lookup HTTP ${response.status}`);
const record=await response.json() as {
  tx?: {body?: {extension_options?: Array<Record<string,string>>;non_critical_extension_options?: Array<Record<string,string>>}};
  tx_response?: {code?: number|string;events?: Array<{type?:string;attributes?: Array<{key?:string;value?:string}>}>;height?:string};
};
const result=record.tx_response;
const options=[...(record.tx?.body?.extension_options??[]),...(record.tx?.body?.non_critical_extension_options??[])];
const hybrid=options.some(ext=>String(ext["@type"]??"").includes("PQCHybridSignature"));
function decode(value:string|undefined):string {
  if (!value) return "";
  if (/^(status|verified)$/i.test(value)) return value;
  try { return Buffer.from(value,"base64").toString("utf8"); } catch { return value; }
}
const verified=(result?.events??[]).some(event=>event.type==="pqc_hybrid_verify"&&(event.attributes??[]).some(attr=>decode(attr.key)==="status"&&decode(attr.value)==="verified"));
const success=Number(result?.code??1)===0 && Number(result?.height??0)>0;
console.log(JSON.stringify({network:"qorechain-diana",hash,success,hybrid_extension_present:hybrid,chain_verified_event:verified,confirmed:success&&hybrid&&verified},null,2));
if (!(success&&hybrid&&verified)) process.exitCode=1;
