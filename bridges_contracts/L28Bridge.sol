// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title L28 Bridge Contract
 * @notice Locks/unlocks L28 for cross-chain transfers
 */
contract L28Bridge {
    address public owner;
    mapping(address => uint256) public lockedBalances;
    mapping(bytes32 => bool) public processedTransactions;
    
    event TokensLocked(address indexed user, uint256 amount, string targetChain, bytes32 txHash);
    event TokensUnlocked(address indexed user, uint256 amount, bytes32 sourceTxHash);
    
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @notice Lock L28 tokens to bridge to another chain
     * @param amount Amount to lock
     * @param targetChain Target blockchain (e.g., "polygon", "arbitrum")
     */
    function lockTokens(uint256 amount, string memory targetChain) external {
        require(amount > 0, "Amount must be > 0");
        
        // Transfer tokens from user to contract
        // (assumes L28 ERC20 token exists)
        
        lockedBalances[msg.sender] += amount;
        
        bytes32 txHash = keccak256(abi.encodePacked(msg.sender, amount, block.timestamp));
        
        emit TokensLocked(msg.sender, amount, targetChain, txHash);
    }
    
    /**
     * @notice Unlock tokens when bridging back from another chain
     * @param user User address
     * @param amount Amount to unlock
     * @param sourceTxHash Transaction hash from source chain
     */
    function unlockTokens(address user, uint256 amount, bytes32 sourceTxHash) external {
        require(msg.sender == owner, "Only owner");
        require(!processedTransactions[sourceTxHash], "Already processed");
        require(lockedBalances[user] >= amount, "Insufficient locked balance");
        
        processedTransactions[sourceTxHash] = true;
        lockedBalances[user] -= amount;
        
        // Transfer tokens back to user
        
        emit TokensUnlocked(user, amount, sourceTxHash);
    }
    
    function getLockedBalance(address user) external view returns (uint256) {
        return lockedBalances[user];
    }
}
