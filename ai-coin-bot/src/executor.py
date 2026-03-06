"""
Solana Transaction Executor
Handles buyback execution on the Solana blockchain.
"""

import os
import base58
import logging
from typing import Optional

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solders.message import Message
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed


class SolanaExecutor:
    """Executes buyback transactions on Solana."""

    # PumpFun program addresses
    PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
    RAYDIUM_AMM_PROGRAM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

    def __init__(self, config: dict, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.logger = logging.getLogger("SolanaExecutor")

        # Initialize RPC client
        self.rpc_url = config.get("rpc_url") or os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
        self.client = AsyncClient(self.rpc_url)

        # Load wallet
        self.keypair = self._load_keypair()
        self.coin_address = config.get("coin_address") or os.getenv("COIN_ADDRESS")

    def _load_keypair(self) -> Optional[Keypair]:
        """Load the wallet keypair from environment."""
        private_key = os.getenv("SOLANA_PRIVATE_KEY")

        if not private_key:
            self.logger.warning("No private key configured, running in read-only mode")
            return None

        try:
            # Handle different private key formats
            if private_key.startswith("["):
                # JSON array format
                import json
                key_bytes = bytes(json.loads(private_key))
            else:
                # Base58 format
                key_bytes = base58.b58decode(private_key)

            return Keypair.from_bytes(key_bytes)

        except Exception as e:
            self.logger.error(f"Failed to load keypair: {e}")
            return None

    async def get_rewards_balance(self) -> float:
        """Get the creator rewards balance available for buyback."""
        if not self.keypair:
            return 0.0

        try:
            response = await self.client.get_balance(self.keypair.pubkey())
            balance_lamports = response.value
            balance_sol = balance_lamports / 1e9

            self.logger.debug(f"Wallet balance: {balance_sol:.4f} SOL")
            return balance_sol

        except Exception as e:
            self.logger.error(f"Failed to get balance: {e}")
            return 0.0

    async def execute_buyback(self, amount_sol: float) -> Optional[str]:
        """
        Execute a buyback transaction.

        Args:
            amount_sol: Amount of SOL to spend on buyback

        Returns:
            Transaction signature if successful, None otherwise
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would execute buyback of {amount_sol:.4f} SOL")
            return "DRY_RUN_TX_" + os.urandom(16).hex()

        if not self.keypair:
            self.logger.error("No keypair loaded, cannot execute transaction")
            return None

        try:
            # For PumpFun tokens, we need to use their specific swap mechanism
            # This is a simplified version - production would use Jupiter or Raydium
            tx_signature = await self._execute_swap(amount_sol)
            return tx_signature

        except Exception as e:
            self.logger.error(f"Buyback execution failed: {e}")
            return None

    async def _execute_swap(self, amount_sol: float) -> Optional[str]:
        """Execute a swap transaction through an AMM."""
        try:
            # In production, you would:
            # 1. Get quote from Jupiter API
            # 2. Build the swap transaction
            # 3. Sign and submit

            # Using Jupiter API for best routing
            quote = await self._get_jupiter_quote(amount_sol)
            if not quote:
                self.logger.error("Failed to get swap quote")
                return None

            # Get swap transaction
            swap_tx = await self._get_jupiter_swap_tx(quote)
            if not swap_tx:
                self.logger.error("Failed to get swap transaction")
                return None

            # Sign and send transaction
            signature = await self._sign_and_send(swap_tx)
            return signature

        except Exception as e:
            self.logger.error(f"Swap execution error: {e}")
            return None

    async def _get_jupiter_quote(self, amount_sol: float) -> Optional[dict]:
        """Get swap quote from Jupiter aggregator."""
        import httpx

        try:
            # SOL mint address
            sol_mint = "So11111111111111111111111111111111111111112"
            amount_lamports = int(amount_sol * 1e9)

            url = "https://quote-api.jup.ag/v6/quote"
            params = {
                "inputMint": sol_mint,
                "outputMint": self.coin_address,
                "amount": amount_lamports,
                "slippageBps": 500,  # 5% slippage
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            self.logger.error(f"Jupiter quote error: {e}")
            return None

    async def _get_jupiter_swap_tx(self, quote: dict) -> Optional[bytes]:
        """Get swap transaction from Jupiter."""
        import httpx

        try:
            url = "https://quote-api.jup.ag/v6/swap"
            payload = {
                "quoteResponse": quote,
                "userPublicKey": str(self.keypair.pubkey()),
                "wrapAndUnwrapSol": True,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": "auto"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Decode the transaction
                swap_tx = base58.b58decode(data["swapTransaction"])
                return swap_tx

        except Exception as e:
            self.logger.error(f"Jupiter swap tx error: {e}")
            return None

    async def _sign_and_send(self, tx_bytes: bytes) -> Optional[str]:
        """Sign and send a transaction."""
        try:
            from solders.transaction import VersionedTransaction

            # Deserialize the versioned transaction
            tx = VersionedTransaction.from_bytes(tx_bytes)

            # Sign the transaction
            tx.sign([self.keypair])

            # Send transaction
            response = await self.client.send_transaction(
                tx,
                opts={"skip_preflight": False, "preflight_commitment": Confirmed}
            )

            signature = str(response.value)
            self.logger.info(f"Transaction sent: {signature}")

            # Wait for confirmation
            await self.client.confirm_transaction(signature, commitment=Confirmed)
            self.logger.info(f"Transaction confirmed: {signature}")

            return signature

        except Exception as e:
            self.logger.error(f"Transaction send error: {e}")
            return None

    async def close(self):
        """Close the RPC client connection."""
        await self.client.close()
