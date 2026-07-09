"""紙上模擬券商(Paper Trading)。

這是一個「完整可用」的券商實作 —— 不碰真錢,但會真的模擬撮合、
計算持倉與損益。交易者可以用它把整套交易程式跑到滿意為止,
再考慮是否要換成真實券商。

這是設計上的核心安全策略:預設值就是安全的。
"""

from __future__ import annotations

from .base import (
    AccountInfo,
    BrokerAdapter,
    Order,
    OrderResult,
    OrderSide,
    OrderType,
    Position,
)


class PaperBroker(BrokerAdapter):
    """以記憶體模擬的紙上券商。

    預設只支援『做多』(買進後賣出平倉):賣出超過持倉會直接拒單。
    若要模擬放空,明確傳入 allow_short=True —— 此時採 naive 現金會計:
    開空/回補的損益方向正確,但**不含**借券費、融資利息、資金費率、
    保證金鎖定與強制平倉。這是刻意的取捨:與其給出「半真」的保證金模型
    讓人誤以為已建模成本,不如誠實標明這是簡化模型(見 SHORT_DISCLAIMER)。

    Args:
        cash:        起始資金
        fee_rate:    每筆成交的手續費率(模擬交易成本)
        slippage:    市價單的模擬滑價率
        price_feed:  可選的報價函式 symbol -> price;未提供時需用 set_price 餵價
        allow_short: 是否允許裸放空(預設 False)。開啟後為簡化模型,估值偏樂觀。
    """

    name = "paper"
    is_live = False

    #: 開啟 allow_short 時,對使用者顯示的免責說明(刻意冗長,逼你讀完)
    SHORT_DISCLAIMER = (
        "⚠️ 放空為『簡化模型』:未計入借券費 / 融券手續費 / 融資利息 / "
        "資金費率 / 保證金鎖定 / 維持率與強制平倉。估值偏樂觀,"
        "僅供方向性損益驗證,不可當作真實放空的績效預期。"
    )

    def __init__(
        self,
        cash: float = 1_000_000.0,
        *,
        fee_rate: float = 0.001,
        slippage: float = 0.0005,
        currency: str = "USD",
        price_feed=None,
        allow_short: bool = False,
    ) -> None:
        super().__init__()
        self._cash = cash
        self._fee_rate = fee_rate
        self._slippage = slippage
        self._currency = currency
        self._price_feed = price_feed
        # 預設 False:賣出超過持倉直接拒單。設為 True 時允許裸放空,
        # 但採 naive 現金會計(見 SHORT_DISCLAIMER),不假裝已建模借券成本。
        self._allow_short = allow_short
        self._prices: dict[str, float] = {}
        self._positions: dict[str, Position] = {}
        self._order_seq = 0
        self.fills: list[OrderResult] = []   # 成交紀錄,方便事後分析

    # ── 報價 ──────────────────────────────────────────────
    def set_price(self, symbol: str, price: float) -> None:
        """手動餵入最新報價(回測 / 模擬時逐根餵價)。"""
        self._prices[symbol] = price
        if symbol in self._positions:
            self._positions[symbol].market_price = price

    def get_price(self, symbol: str) -> float:
        if self._price_feed is not None:
            price = self._price_feed(symbol)
            self.set_price(symbol, price)
            return price
        if symbol not in self._prices:
            raise ValueError(
                f"PaperBroker 沒有 {symbol} 的報價。請先 set_price() 或提供 price_feed。"
            )
        return self._prices[symbol]

    # ── 帳戶 / 持倉 ───────────────────────────────────────
    def connect(self) -> None:
        # 紙上模擬無需連線
        pass

    def get_account(self) -> AccountInfo:
        equity = self._cash + sum(
            p.quantity * self._prices.get(p.symbol, p.avg_price)
            for p in self._positions.values()
        )
        return AccountInfo(cash=self._cash, equity=equity, currency=self._currency)

    def get_positions(self) -> list[Position]:
        return [p for p in self._positions.values() if p.quantity != 0]

    # ── 下單(模擬撮合)────────────────────────────────────
    def place_order(self, order: Order) -> OrderResult:
        self._guard_live()   # PaperBroker is_live=False,永遠放行;保留以示範正確用法
        order.validate()

        ref_price = self.get_price(order.symbol)
        # 市價單套用滑價,限價單以限價成交
        if order.order_type == OrderType.MARKET:
            slip = self._slippage if order.side == OrderSide.BUY else -self._slippage
            fill_price = ref_price * (1 + slip)
        else:
            fill_price = order.limit_price or ref_price

        notional = fill_price * order.quantity
        fee = abs(notional) * self._fee_rate

        signed_qty = order.quantity if order.side == OrderSide.BUY else -order.quantity

        if order.side == OrderSide.BUY:
            # 買進:扣現金(含手續費)
            cost = notional + fee
            if cost > self._cash:
                return OrderResult(
                    ok=False, message=f"資金不足:需 {cost:,.2f},現金 {self._cash:,.2f}"
                )
        else:
            # 賣出。預設(allow_short=False)只支援做多:賣出不得超過持倉。
            # 裸放空牽涉保證金、借券費、強制平倉,正確建模太複雜;
            # 與其給出錯誤的現金/權益數字,預設誠實拒單。
            held = self._positions.get(order.symbol)
            held_qty = held.quantity if held else 0.0
            if not self._allow_short and order.quantity > held_qty + 1e-9:
                return OrderResult(
                    ok=False,
                    message=(
                        f"賣出數量 {order.quantity:g} 超過持有部位 {held_qty:g}。"
                        "本紙上模擬預設只支援做多;要模擬放空請用 "
                        "PaperBroker(allow_short=True)(簡化模型,不含借券費)。"
                    ),
                )
            # 平多倉 / (allow_short 時)開空:回收賣出金額,扣手續費
            cost = -notional + fee

        self._cash -= cost
        self._apply_fill(order.symbol, signed_qty, fill_price)

        # 若這筆成交讓部位變成淨空單,附上放空的簡化模型免責說明
        pos_after = self._positions.get(order.symbol)
        msg = "paper fill"
        if pos_after is not None and pos_after.quantity < 0:
            msg = f"paper fill / {self.SHORT_DISCLAIMER}"

        self._order_seq += 1
        result = OrderResult(
            ok=True,
            order_id=f"PAPER-{self._order_seq:06d}",
            filled_quantity=order.quantity,
            avg_price=fill_price,
            message=msg,
            raw={"fee": fee, "tag": order.client_tag},
        )
        self.fills.append(result)
        return result

    def _apply_fill(self, symbol: str, signed_qty: float, price: float) -> None:
        """更新持倉的加權平均成本。

        正確處理四種情形:
          1. 無部位 / 部位已平 → 直接建立新部位
          2. 同向加碼 → 加權平均成本
          3. 反向減碼(未超量)→ 數量減少,均價不變
          4. 反向超量(平舊倉並反手)→ 剩餘數量以「本次成交價」建立反向新部位
             (這是先前的 bug:超量翻倉時若沿用舊均價,未實現損益與
              停損停利會全部以錯誤的均價計算)
        """
        pos = self._positions.get(symbol)
        if pos is None or pos.quantity == 0:
            self._positions[symbol] = Position(symbol, signed_qty, price, price)
            return

        new_qty = pos.quantity + signed_qty

        # 完全平倉
        if new_qty == 0:
            pos.quantity = 0
            pos.market_price = price
            return

        same_direction = (pos.quantity > 0) == (signed_qty > 0)
        if same_direction:
            # 情形 2:同向加碼 → 加權平均
            total_cost = pos.avg_price * pos.quantity + price * signed_qty
            pos.avg_price = total_cost / new_qty
        elif (new_qty > 0) == (pos.quantity > 0):
            # 情形 3:反向減碼但未超量(方向不變)→ 均價維持原值
            pass
        else:
            # 情形 4:反向超量(方向翻轉)→ 剩餘部位以本次成交價為新均價
            pos.avg_price = price

        pos.quantity = new_qty
        pos.market_price = price

    def cancel_order(self, order_id: str) -> bool:
        # 紙上模擬為立即成交,無掛單可取消
        return False
