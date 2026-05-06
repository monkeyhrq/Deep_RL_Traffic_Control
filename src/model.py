"""
model.py - DQN 神經網路定義

架構：
    Input (5維) → FC(128) → ReLU → FC(64) → ReLU → Output (2維)

Input：  狀態向量 [Q_N, Q_E, Q_S, Q_W, φₜ]
Output： Q(s, Keep), Q(s, Change)
"""

import torch
import torch.nn as nn


class QNetwork(nn.Module):
    """
    Deep Q-Network 神經網路

    用來估計每個動作的 Q 值（長期累積獎勵期望值）
    選擇 Q 值最大的動作就是最優決策

    Args:
        state_dim:  輸入維度（狀態向量大小，預設 5）
        action_dim: 輸出維度（動作數量，預設 2）
        hidden1:    第一隱藏層神經元數（預設 128）
        hidden2:    第二隱藏層神經元數（預設 64）
    """

    def __init__(self,
                 state_dim:  int = 5,
                 action_dim: int = 2,
                 hidden1:    int = 128,
                 hidden2:    int = 64):
        super(QNetwork, self).__init__()

        # 建立神經網路層
        self.network = nn.Sequential(
            # 第一層：輸入層 → 隱藏層 1
            nn.Linear(state_dim, hidden1),
            nn.ReLU(),

            # 第二層：隱藏層 1 → 隱藏層 2
            nn.Linear(hidden1, hidden2),
            nn.ReLU(),

            # 第三層：隱藏層 2 → 輸出層
            # 注意：輸出層不加激勵函數（Linear 輸出）
            nn.Linear(hidden2, action_dim),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        前向傳播：輸入狀態，輸出每個動作的 Q 值

        Args:
            state: 狀態張量，shape = (batch_size, state_dim)

        Returns:
            q_values: Q 值張量，shape = (batch_size, action_dim)
                      q_values[:, 0] = Q(s, Keep)
                      q_values[:, 1] = Q(s, Change)
        """
        return self.network(state)

    def get_action(self, state: torch.Tensor) -> int:
        """
        根據狀態選擇 Q 值最大的動作（貪婪策略）

        Args:
            state: 狀態張量，shape = (1, state_dim)

        Returns:
            action: 整數，0=Keep 或 1=Change
        """
        with torch.no_grad():
            q_values = self.forward(state)
            action = q_values.argmax(dim=1).item()
        return action
