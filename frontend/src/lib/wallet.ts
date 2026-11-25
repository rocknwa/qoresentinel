import { getQorexNative } from '@qorechain/qorex-types';

/* QoreX Native supports read/connect + wallet-approved hybrid native transactions.
   QoreX EVM currently does NOT support personal_sign or eth_sendTransaction.
   For fUSD ERC-20 checkout use a compatible EVM wallet on Diana testnet. */
export type Eip1193={request:(args:{method:string;params?:unknown[]|object})=>Promise<unknown>;
  on?:(event:string,fn:(...args:unknown[])=>void)=>void};
declare global { interface Window { ethereum?: Eip1193 } }
export const DIANA_CHAIN='0x2648';
export function getEvm():Eip1193|null{
  // MetaMask is preferable for fUSD payments, since QoreX EVM signing is unsupported.
  if(typeof window==='undefined')return null;
  return window.ethereum||null;
}
export async function connectQoreX():Promise<string>{
  const native=getQorexNative();
  if(!native)throw new Error('QoreX native wallet was not detected. Unlock its extension and select Diana testnet.');
  if(native.enable)await native.enable('qorechain-diana');
  const key=await native.getKey('qorechain-diana');
  if(!/^qor1[a-z0-9]{20,}$/i.test(key.bech32Address))throw new Error('QoreX did not return a valid native address');
  return key.bech32Address;
}
export async function connectEvm():Promise<{provider:Eip1193;address:string}>{
  const provider=getEvm();if(!provider)throw new Error('No EVM wallet detected. Install MetaMask for signed authentication and fUSD payments.');
  const accounts=await provider.request({method:'eth_requestAccounts'}) as string[];
  if(!Array.isArray(accounts)||!accounts[0]||!/^0x[0-9a-fA-F]{40}$/.test(accounts[0]))throw new Error('Wallet did not return an EVM account');
  let chain=await provider.request({method:'eth_chainId'});
  if(chain!==DIANA_CHAIN){
    try{await provider.request({method:'wallet_switchEthereumChain',params:[{chainId:DIANA_CHAIN}]});}
    catch{
      // EIP-3085: offer MetaMask users a trusted QoreChain Diana configuration.
      try{await provider.request({method:'wallet_addEthereumChain',params:[{
        chainId:DIANA_CHAIN,chainName:'QoreChain Diana Testnet',
        nativeCurrency:{name:'QOR',symbol:'QOR',decimals:18},
        rpcUrls:['https://evm-testnet.qore.host'],
        blockExplorerUrls:['https://explore.qore.network']
      }]});}catch{throw new Error('Please add QoreChain Diana testnet (chain ID 9800) in your EVM wallet.');}
    }
    chain=await provider.request({method:'eth_chainId'});
    if(chain!==DIANA_CHAIN)throw new Error('Wrong wallet network: QoreChain Diana testnet required');
  }
  return {provider,address:accounts[0].toLowerCase()};
}
export async function signLogin(provider:Eip1193,address:string,message:string):Promise<string>{
  const hex='0x'+Array.from(new TextEncoder().encode(message)).map(b=>b.toString(16).padStart(2,'0')).join('');
  try{return String(await provider.request({method:'personal_sign',params:[hex,address]}));}
  catch{throw new Error('This wallet cannot sign a login message. QoreX EVM signing is not yet supported; use a compatible EVM wallet.');}
}
export async function transferFusd(provider:Eip1193,address:string,token:string,receiver:string,amount:string){
  if((await provider.request({method:'eth_chainId'}))!==DIANA_CHAIN)throw new Error('QoreChain Diana testnet must be selected');
  if(!/^0x[0-9a-fA-F]{40}$/.test(receiver)||!/^\d+$/.test(amount))throw new Error('Invalid payment details');
  const data='0xa9059cbb'+receiver.slice(2).toLowerCase().padStart(64,'0')+BigInt(amount).toString(16).padStart(64,'0');
  return String(await provider.request({method:'eth_sendTransaction',params:[{from:address,to:token,data,value:'0x0'}]}));
}

export async function sendHybridProof(nativeAddress:string):Promise<{txHash:string;code:number;shield:string}>{
  if(!nativeAddress.startsWith('qor1'))throw new Error('Connect QoreX on Diana testnet first');
  // Official QoreX kits hand the protobuf MsgSend bytes to the wallet for
  // wallet-approved secp256k1 + ML-DSA signing. Private keys never enter the app.
  const {MsgSend}=await import('cosmjs-types/cosmos/bank/v1beta1/tx.js');
  const {qorexSignAndBroadcast}=await import('@qorechain/qorex-types');
  const msg={fromAddress:nativeAddress,toAddress:nativeAddress,amount:[{denom:'uqor',amount:'1000000'}]};
  const result=await qorexSignAndBroadcast({chainId:'qorechain-diana',
    messages:[{typeUrl:'/cosmos.bank.v1beta1.MsgSend',value:MsgSend.encode(msg).finish()}],
    memo:'QoreSentinel hybrid-signature testnet proof'});
  if(Number(result.code)!==0)throw new Error('QoreX rejected or failed the testnet transaction');
  return {txHash:String(result.txHash),code:Number(result.code),shield:String(result.shield)};
}
