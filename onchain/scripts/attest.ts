/**
 * Publish a SHA-256 of the exact exported Markdown report bytes.
 * Requires the publisher's live, hybrid-opened EVM authorization window.
 * Usage: npm run attest -- ./report.md [--read]
 */
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { createPublicClient, createWalletClient, defineChain, http, parseAbi, type Address, type Hex } from "viem";
import { privateKeyToAccount } from "viem/accounts";

try { process.loadEnvFile(); } catch { /* read-only mode can use environment */ }
const path = process.argv[2];
const readOnly = process.argv.includes("--read");
if (!path || !existsSync(path)) throw new Error("Pass a readable Markdown report path: npm run attest -- ./report.md [--read]");
const contract = process.env.QORE_ATTESTATION_CONTRACT as Address | undefined;
if (!contract || !/^0x[a-fA-F0-9]{40}$/.test(contract)) throw new Error("Set QORE_ATTESTATION_CONTRACT to the deployed contract address in .env");
const digest = ("0x" + createHash("sha256").update(readFileSync(path)).digest("hex")) as Hex;
const chain = defineChain({ id: 9800, name: "QoreChain Diana Testnet", nativeCurrency: {name:"QOR",symbol:"QOR",decimals:18}, rpcUrls: {default:{http:["https://evm-testnet.qore.host"]}}, blockExplorers:{default:{name:"QoreChain Explorer",url:"https://explore.qore.network"}} });
const abi = parseAbi([
  "function publisher() view returns (address)",
  "function attestedAt(bytes32) view returns (uint64)",
  "function attest(bytes32 reportDigest)",
]);
const publicClient = createPublicClient({chain,transport:http()});
if (await publicClient.getChainId() !== 9800) throw new Error("Not connected to Diana EVM chain 9800");
if (!await publicClient.getBytecode({address:contract})) throw new Error("Attestation contract is not deployed at this address");
const at = await publicClient.readContract({address:contract,abi,functionName:"attestedAt",args:[digest]});
console.log("Report SHA-256:",digest);
console.log("Contract:",contract);
console.log("Previously attested:", at ? new Date(Number(at)*1000).toISOString() : "no");
if (!readOnly && !at) {
  const key = process.env.PRIVATE_KEY as Hex | undefined;
  if (!key || !/^0x[0-9a-fA-F]{64}$/.test(key)) throw new Error("Set PRIVATE_KEY locally; do not put it in GitHub or the browser");
  const account=privateKeyToAccount(key);
  const publisher=await publicClient.readContract({address:contract,abi,functionName:"publisher"});
  if (publisher.toLowerCase() !== account.address.toLowerCase()) throw new Error("Only the deployment publisher may attest; use the publisher account");
  const wallet=createWalletClient({account,chain,transport:http()});
  const gas=await publicClient.estimateContractGas({address:contract,abi,functionName:"attest",args:[digest],account});
  const tx=await wallet.writeContract({address:contract,abi,functionName:"attest",args:[digest],gas:gas*13n/10n});
  console.log("Attestation tx:", tx);
  const receipt=await publicClient.waitForTransactionReceipt({hash:tx});
  if (receipt.status!=="success") throw new Error("Attestation transaction reverted");
  console.log("Confirmed at block",receipt.blockNumber.toString());
}
