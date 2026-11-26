import { getQorexNative, qorexSignAndBroadcast } from '@qorechain/qorex-types';

export const NATIVE_CHAIN = 'qorechain-diana';
export const FAUCET_URL = 'https://dashboard.qorechain.io/faucet';
export const QOREX_CHROME_URL = 'https://chromewebstore.google.com/detail/qorex/cflpnggbnnifibblifgbeobogdpfjpcg';
export const QOREX_FIREFOX_URL = 'https://addons.mozilla.org/en-US/firefox/addon/qorex/';
export const QOREX_NETWORK_GUIDE = 'https://docs.qorechain.io/qorex/testnet-features/';

export type QoreXConnectIssue = 'missing' | 'wrong-network' | 'locked' | 'rejected';

export class QoreXConnectError extends Error {
  constructor(readonly issue: QoreXConnectIssue, message: string) {
    super(message);
    this.name = 'QoreXConnectError';
  }
}

export function hasQoreXNative(): boolean {
  return typeof window !== 'undefined' && Boolean(getQorexNative());
}

export function classifyQoreXError(error: unknown): QoreXConnectError | null {
  if (error instanceof QoreXConnectError) return error;
  const message = error instanceof Error ? error.message : String(error ?? '');
  const code = typeof error === 'object' && error !== null && 'code' in error
    ? String((error as {code?: unknown}).code) : '';
  if (/chain\s+\S+\s+does not match the active network|switch the network in QoreX|network mismatch|qorechain-vladi|wrong network/i.test(message)) {
    return new QoreXConnectError('wrong-network', 'QoreX is on a different network. Switch to Diana Testnet inside QoreX, then retry.');
  }
  if (/wallet is locked|unlock (?:the )?wallet/i.test(message)) {
    return new QoreXConnectError('locked', 'Unlock QoreX, then retry the connection.');
  }
  if (code === '4001' || /signature rejected|user rejected|user denied|request rejected/i.test(message)) {
    return new QoreXConnectError('rejected', 'Connection was cancelled in QoreX. Try again when ready.');
  }
  return null;
}

export async function connectQoreX(): Promise<string> {
  const native = getQorexNative();
  if (!native) {
    throw new QoreXConnectError('missing', 'QoreX is not detected in this browser. Install or enable the extension, then retry.');
  }
  let key: Awaited<ReturnType<typeof native.getKey>>;
  try {
    await native.enable(NATIVE_CHAIN);
    key = await native.getKey(NATIVE_CHAIN);
  } catch (error) {
    throw classifyQoreXError(error) ?? error;
  }
  if (!/^qor1[023456789acdefghjklmnpqrstuvwxyz]{38}$/.test(key.bech32Address)) {
    throw new Error('QoreX did not provide a valid native address.');
  }
  return key.bech32Address;
}

/**
 * Trigger QoreX's own access/unlock prompt from an explicit user interaction.
 * Recent QoreX extensions wake the vault for enable/getKey while locked.
 * Older extensions may reject instead; the caller must show manual guidance.
 * This never signs or broadcasts a transaction.
 */
export async function requestQoreXUnlock(expectedAddress: string): Promise<void> {
  const native = getQorexNative();
  if (!native) throw new QoreXConnectError('missing', 'Install or enable QoreX to continue.');
  try {
    await native.enable(NATIVE_CHAIN);
    const key = await native.getKey(NATIVE_CHAIN);
    if (key.bech32Address.toLowerCase() !== expectedAddress.toLowerCase()) {
      throw new Error('The active QoreX wallet has changed. Reconnect your original address.');
    }
  } catch (error) {
    throw classifyQoreXError(error) ?? error;
  }
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
