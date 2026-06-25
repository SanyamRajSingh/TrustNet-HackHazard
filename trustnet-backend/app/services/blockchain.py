"""
Blockchain Service - Base (Sepolia) Integration
Smart contract interaction for on-chain scam registry.
"""

import asyncio
import os
from typing import Any, Dict, Optional

import structlog
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from web3 import Web3
except ImportError:
    Account = None
    encode_defunct = None
    Web3 = None

from config import settings

logger = structlog.get_logger()

# TrustNetRegistry.sol ABI
TRUSTNET_REGISTRY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "entityHash", "type": "bytes32"},
            {"name": "entityType", "type": "uint8"},
            {"name": "trustScore", "type": "uint32"},
            {"name": "timestamp", "type": "uint64"},
        ],
        "name": "EntityFlagged",
        "type": "event",
    },
    {
        "inputs": [
            {"name": "entityHash", "type": "bytes32"},
            {"name": "entityType", "type": "uint8"},
            {"name": "trustScore", "type": "uint32"},
            {"name": "reportCount", "type": "uint32"},
            {"name": "signature", "type": "bytes"},
        ],
        "name": "flagEntity",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "entityHash", "type": "bytes32"}],
        "name": "checkEntity",
        "outputs": [
            {
                "components": [
                    {"name": "entityHash", "type": "bytes32"},
                    {"name": "entityType", "type": "uint8"},
                    {"name": "trustScore", "type": "uint32"},
                    {"name": "reportCount", "type": "uint32"},
                    {"name": "firstFlaggedAt", "type": "uint64"},
                    {"name": "lastUpdatedAt", "type": "uint64"},
                    {"name": "isActive", "type": "bool"},
                ],
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "_backendSigner", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {
        "inputs": [],
        "name": "backendSigner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "", "type": "bytes32"}],
        "name": "registry",
        "outputs": [
            {"name": "entityHash", "type": "bytes32"},
            {"name": "entityType", "type": "uint8"},
            {"name": "trustScore", "type": "uint32"},
            {"name": "reportCount", "type": "uint32"},
            {"name": "firstFlaggedAt", "type": "uint64"},
            {"name": "lastUpdatedAt", "type": "uint64"},
            {"name": "isActive", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

TYPE_MAP = {"domain": 1, "email": 2, "phone": 3, "company": 4}


class BlockchainService:
    """Base blockchain service for scam registry operations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.enabled = settings.BLOCKCHAIN_ENABLED
        if not self.enabled:
            logger.warning("blockchain.disabled")
            return
        self.w3 = Web3(Web3.HTTPProvider(settings.BASE_SEPOLIA_RPC))
        self.private_key = settings.BACKEND_WALLET_PRIVATE_KEY
        self.account = Account.from_key(self.private_key)
        self.contract_address = Web3.to_checksum_address(settings.TRUSTNET_CONTRACT_ADDRESS)
        self.contract = self.w3.eth.contract(
            address=self.contract_address, abi=TRUSTNET_REGISTRY_ABI
        )
        self._initialized = True

    def _get_entity_hash(self, entity_type: str, entity_value: str) -> bytes:
        """Generate keccak256 hash of entity type + value."""
        return self.w3.keccak(text=f"{entity_type}:{entity_value}")

    def _sign_message(self, entity_hash: bytes, entity_type_int: int,
                      trust_score: int, report_count: int) -> str:
        """Sign message for smart contract verification."""
        msg_hash = self.w3.keccak(
            entity_hash +
            entity_type_int.to_bytes(1, "big") +
            trust_score.to_bytes(4, "big") +
            report_count.to_bytes(4, "big")
        )
        message = encode_defunct(msg_hash)
        signed = Account.sign_message(message, private_key=self.private_key)
        return signed.signature.hex()

    async def flag_entity(
        self,
        entity_type: str,
        entity_value: str,
        trust_score: int,
        report_count: int = 1,
    ) -> Optional[str]:
        """
        Write flagged entity to blockchain registry.
        Returns transaction hash or None if disabled/failed.
        """
        if not self.enabled:
            return None

        try:
            entity_hash = self._get_entity_hash(entity_type, entity_value)
            entity_type_int = TYPE_MAP.get(entity_type, 0)
            signature = self._sign_message(
                entity_hash, entity_type_int, trust_score, report_count
            )

            # Build transaction
            tx = self.contract.functions.flagEntity(
                entity_hash,
                entity_type_int,
                trust_score,
                report_count,
                bytes.fromhex(signature[2:]) if signature.startswith("0x") else bytes.fromhex(signature),
            ).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 200000,
                "gasPrice": self.w3.eth.gas_price,
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            tx_hash_hex = tx_hash.hex() if isinstance(tx_hash, bytes) else tx_hash
            logger.info("blockchain.entity_flagged",
                        entity_type=entity_type,
                        entity_value=entity_value,
                        tx_hash=tx_hash_hex)
            return tx_hash_hex

        except Exception as e:
            logger.error("blockchain.flag_error", error=str(e))
            return None

    async def check_entity(
        self, entity_type: str, entity_value: str
    ) -> Dict[str, Any]:
        """Check if entity is on-chain."""
        if not self.enabled:
            return {"on_chain": False, "reason": "Blockchain disabled"}

        try:
            entity_hash = self._get_entity_hash(entity_type, entity_value)
            result = self.contract.functions.checkEntity(entity_hash).call()
            return {
                "on_chain": result[6],  # isActive
                "entity_hash": entity_hash.hex(),
                "entity_type": result[1],
                "trust_score": result[2],
                "report_count": result[3],
                "first_flagged_at": result[4],
                "last_updated_at": result[5],
                "is_active": result[6],
            }
        except Exception as e:
            logger.error("blockchain.check_error", error=str(e))
            return {"on_chain": False, "error": str(e)}
