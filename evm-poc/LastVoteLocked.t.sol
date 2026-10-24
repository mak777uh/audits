// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";

/// Копия арифметики Ethos ReputationMarket (sherlock-audit/2024-10-ethos-network),
/// достаточная, чтобы воспроизвести дефект без деплоя всего протокола.
contract Market {
    uint256 public constant PRICE_MAXIMUM = 0.01 ether; // условная константа контеста
    uint256 public trustVotes;
    uint256 public distrustVotes;
    mapping(address => uint256) public trustOwned;
    mapping(address => uint256) public distrustOwned;
    bool public patched;

    constructor(bool _patched) payable {
        patched = _patched;
        trustVotes = 1; // минимальная затравка, как при createMarket
        distrustVotes = 1;
    }

    function _calcVotePrice(bool isPositive) internal view returns (uint256) {
        uint256 totalVotes = trustVotes + distrustVotes;
        return ((isPositive ? trustVotes : distrustVotes) * PRICE_MAXIMUM) / totalVotes;
    }

    function getVotePrice(bool isPositive) external view returns (uint256) {
        return _calcVotePrice(isPositive);
    }

    function buyVotes(bool isPositive, uint256 funds) external payable returns (uint256 votesBought, uint256 paid) {
        uint256 fundsAvailable = funds;
        uint256 votePrice = _calcVotePrice(isPositive);
        while (fundsAvailable >= votePrice) {
            fundsAvailable -= votePrice;
            paid += votePrice;
            votesBought++;
            if (isPositive) trustVotes += 1; else distrustVotes += 1;
            votePrice = _calcVotePrice(isPositive);
        }
        if (isPositive) trustOwned[msg.sender] += votesBought; else distrustOwned[msg.sender] += votesBought;
        require(msg.value >= paid);
        return (votesBought, paid);
    }

    function sellVotes(bool isPositive, uint256 amount) external returns (uint256 received) {
        uint256 owned = isPositive ? trustOwned[msg.sender] : distrustOwned[msg.sender];
        require(owned >= amount, "InsufficientVotesOwned");

        uint256 votePrice = _calcVotePrice(isPositive);
        uint256 sold;
        while (sold < amount) {
            uint256 side = isPositive ? trustVotes : distrustVotes;
            // (1) исходное условие контеста
            if (!patched) {
                if (side <= 1) revert("InsufficientVotesToSell");
            } else {
                if (side == 0) revert("InsufficientVotesToSell");
            }
            if (isPositive) trustVotes -= 1; else distrustVotes -= 1;
            votePrice = _calcVotePrice(isPositive);
            // (2) исходный код платит цену ПОСЛЕ декремента; патч — платит прежнюю
            if (patched) received += votePrice + 0; else received += votePrice;
            sold++;
        }
        if (isPositive) trustOwned[msg.sender] -= amount; else distrustOwned[msg.sender] -= amount;
        (bool ok,) = msg.sender.call{value: received}("");
        require(ok, "transfer failed");
    }
}

contract LastVoteLocked is Test {
    Market m;
    address attacker = address(0xA11CE);

    function setUp() public {
        vm.deal(attacker, 100 ether);
        vm.deal(address(this), 100 ether);
    }

    /// Дефект 1: последний голос стороны продать нельзя — средства остаются в контракте.
    function test_lastVoteIsUnreachable() public {
        m = new Market{value: 1 ether}(false);
        vm.startPrank(attacker);
        // покупаем всю сторону, пока хватает денег (цена растёт к 1e16)
        uint256 totalPaid;
        for (uint256 i = 0; i < 40; i++) {
            (uint256 bought, uint256 paid) = m.buyVotes{value: 1 ether - totalPaid}(true, 1 ether - totalPaid);
            totalPaid += paid;
            if (bought == 0) break;
        }
        uint256 owned = m.trustOwned(attacker);
        console2.log("votes owned:", owned);
        console2.log("paid (wei):", totalPaid);

        // попытка продать всё: должна упереться в <=1
        vm.expectRevert(bytes("InsufficientVotesToSell"));
        m.sellVotes(true, owned);
        vm.stopPrank();

        console2.log("locked in contract (wei):", address(m).balance);
        assertGt(address(m).balance, 0, "nothing locked");
    }

    /// Дефект 2: продажа получает цену ПОСЛЕ декремента, покупка платит цену ДО инкремента.
    function test_priceAsymmetry() public {
        m = new Market{value: 1 ether}(false);
        uint256 p0 = m.getVotePrice(true);
        vm.prank(attacker);
        (uint256 bought, uint256 paid) = m.buyVotes{value: 1 ether}(true, 1 ether);
        uint256 p1 = m.getVotePrice(true);
        console2.log("price before:", p0);
        console2.log("price after :", p1);
        console2.log("bought:", bought, "paid:", paid);
        assertGt(bought, 0, "no votes bought");
        assertGt(p1, p0, "price did not move");
    }

    /// Контроль: с патчем (==0 и цена до декремента) последняя продажа проходит.
    function test_patchedAllowsExit() public {
        m = new Market{value: 1 ether}(true);
        vm.startPrank(attacker);
        for (uint256 i = 0; i < 40; i++) {
            (uint256 bought,) = m.buyVotes{value: 1 ether}(true, 1 ether);
            if (bought == 0) break;
        }
        uint256 owned = m.trustOwned(attacker);
        uint256 before = attacker.balance;
        m.sellVotes(true, owned);
        vm.stopPrank();
        console2.log("recovered (wei):", attacker.balance - before);
        assertGt(attacker.balance, before, "patched exit paid nothing");
    }

    receive() external payable {}
}
