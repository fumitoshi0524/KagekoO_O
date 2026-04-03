"""Agent Reinforcement Learning framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


RewardFunction = Callable[[str, str], float]  # (action, outcome) -> reward


@dataclass(slots=True, kw_only=True)
class Episode:
    """RL episode capturing state-action-reward trajectory."""

    state: str
    action: str
    reward: float
    next_state: str


@dataclass(slots=True, kw_only=True)
class AgentPolicy:
    """Policy for action selection with exploration/exploitation."""

    epsilon: float = 0.1  # exploration rate
    q_table: dict[tuple[str, str], float] = field(default_factory=dict)

    def select_action(self, state: str, available_actions: list[str]) -> str:
        """Select action using epsilon-greedy policy."""
        import random

        if random.random() < self.epsilon:
            return random.choice(available_actions)
        best_action = max(
            available_actions,
            key=lambda a: self.q_table.get((state, a), 0.0),
        )
        return best_action

    def update(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        alpha: float = 0.1,
        gamma: float = 0.9,
    ) -> None:
        """Update Q-value using temporal difference learning."""
        current_q = self.q_table.get((state, action), 0.0)
        next_actions = [a for (s, a), q in self.q_table.items() if s == next_state]

        max_next_q = max(
            (self.q_table.get((next_state, a), 0.0) for a in next_actions),
            default=0.0,
        )
        new_q = current_q + alpha * (reward + gamma * max_next_q - current_q)
        self.q_table[(state, action)] = new_q


@dataclass(slots=True, kw_only=True)
class RLAgent:
    """RL-enabled agent wrapper with reward collection and policy updates."""

    policy: AgentPolicy
    reward_function: RewardFunction
    episodes: list[Episode] = field(default_factory=list)

    def record_episode(
        self, state: str, action: str, outcome: str, next_state: str
    ) -> None:
        """Record episode and update policy."""
        reward = self.reward_function(action, outcome)
        episode = Episode(
            state=state, action=action, reward=reward, next_state=next_state
        )
        self.episodes.append(episode)
        self.policy.update(state, action, reward, next_state)

    def get_average_reward(self, n: int = 100) -> float:
        """Calculate average reward over last n episodes."""
        if not self.episodes:
            return 0.0
        recent = self.episodes[-n:]
        return sum(ep.reward for ep in recent) / len(recent)
