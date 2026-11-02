"""
Demo Services & Repositories for Graph-RAG Call Chain Tracing
"""

import uuid
import time

class PaymentService:
    """支付网关服务"""
    
    def charge(self, user_id: str, amount: float) -> str:
        """执行扣款调用底层接口"""
        self._verify_balance(user_id, amount)
        return self._execute_bank_api(user_id, amount)

    def _verify_balance(self, user_id: str, amount: float) -> bool:
        return True

    def _execute_bank_api(self, user_id: str, amount: float) -> str:
        return f"tx_{uuid.uuid4().hex[:8]}"


class NotificationService:
    """消息通知服务"""
    
    def send_email(self, user_id: str, content: str):
        print(f"[Email] Sending to {user_id}: {content}")


class OrderRepository:
    """订单数据库持久化仓储"""
    
    def save_order(self, user_id: str, amount: float, tx_id: str) -> str:
        order_id = f"ord_{int(time.time())}"
        print(f"[DB] Saving order {order_id} (tx: {tx_id}) to database")
        return order_id
