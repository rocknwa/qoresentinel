import { getQorexNative, qorexSignAndBroadcast } from '@qorechain/qorex-types';

export const NATIVE_CHAIN = 'qorechain-diana';
export const FAUCET_URL = 'https://dashboard.qorechain.io/faucet';

export async function connectQoreX(): Promise<string> {
  const native = getQorexNative();
  if (!native) throw new Error('QoreX was not detected. Unlock the wallet and switch to Diana testnet.');
  await native.enable(NATIVE_CHAIN);
  const key = await native.getKey(NATIVE_CHAIN);
  if (!/^qor1[023456789acdefghjklmnpqrstuvwxyz]{38}$/.test(key.bech32Address)) {
    throw new Error('QoreX did not provide a valid native address.');
  }
  return key.bech32Address;
}

export async function nativeSend(fromAddress: string, toAddress: string, denom: string, amount: string, memo: string) {
  if (!/^qor1[023456789acdefghjklmnpqrstuvwxyz]{38}$/.test(fromAddress) ||
      !/^qor1[023456789acdefghjklmnpqrstuvwxyz]{38}$/.test(toAddress) ||
      !/^\d+$/.test(amount) || BigInt(amount) <= BigInt(0) || !denom || new TextEncoder().encode(memo).length > 256) {
    throw new Error('Invalid QoreChain native transaction details.');
  }
  const native = getQorexNative();
  if (!native) throw new Error('QoreX is disconnected. Reconnect before approving the transaction.');
  const key = await native.getKey(NATIVE_CHAIN);
  if (key.bech32Address !== fromAddress) throw new Error('The active QoreX wallet has changed. Reconnect your original address.');
  const { MsgSend } = await import('cosmjs-types/cosmos/bank/v1beta1/tx.js');
  const result = await qorexSignAndBroadcast({
    chainId: NATIVE_CHAIN,
    messages: [{ typeUrl: '/cosmos.bank.v1beta1.MsgSend', value: MsgSend.encode({
      fromAddress, toAddress, amount: [{ denom, amount }]
    }).finish() }],
    memo
  });
  if (Number(result.code) !== 0) throw new Error('The native transaction was not successful.');
  const txHash = String(result.txHash ?? '').trim().replace(/^0x/i, '').toUpperCase();
  if (!/^[0-9A-F]{64}$/.test(txHash)) {
    throw new Error('QoreX broadcast the transaction but returned an unexpected hash. Check wallet activity before sending another transaction.');
  }
  return { txHash, shield: String(result.shield) };
}

export async function loginProof(address: string, memo: string) {
  return nativeSend(address, address, 'uqor', '1', memo);
}

export async function sendHybridProof(nativeAddress: string) {
  return nativeSend(nativeAddress, nativeAddress, 'uqor', '1', 'QoreSentinel hybrid-signature testnet proof');
}
