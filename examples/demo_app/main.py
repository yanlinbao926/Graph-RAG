"""
Demo Codebase for Graph-RAG
Demonstrating multi-tier architectures: Gateway -> Controller -> Service -> Repository
"""

from .services import PaymentService, NotificationService, OrderRepository

class OrderController:
    """订单控制器，负责接收请求并调度业务处理"""
    
    def __init__(self):
        self.payment_service = PaymentService()
        self.notifier = NotificationService()
        self.repo = OrderRepository()

    def create_order(self, user_id: str, amount: float) -> str:
        """创建订单、执行扣款、发送提醒并持久化"""
        print(f"Creating order for user {user_id} with amount {amount}")
        tx_id = self.payment_service.charge(user_id, amount)
        order_id = self.repo.save_order(user_id, amount, tx_id)
        self.notifier.send_email(user_id, f"Order {order_id} created successfully")
        return order_id


def main():
    controller = OrderController()
    controller.create_order("user_1001", 99.9)

if __name__ == "__main__":
    main()
