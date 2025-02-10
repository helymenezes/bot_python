import logging

class TraderOrder:
    @staticmethod
    def create_order(client, _symbol, _side, _type, _quantity, _timeInForce=None, _limit_price=None, _stop_price=None):
        print(f"[create_order] _symbol: '{_symbol}',_side: '{_side}',_type: '{_type}',_quantity: '{_quantity}',_timeInForce: '{_timeInForce}',_limit_price: '{_limit_price}',_stop_price: '{_stop_price}'")
        
        params = {
            "symbol": _symbol,
            "side": _side,
            "type": _type,
            "quantity": _quantity
        }
        if _timeInForce:
            params["timeInForce"] = _timeInForce
        if _limit_price:
            params["price"] = _limit_price
        if _stop_price:
            params["stopPrice"] = _stop_price
        
        try:
            order = client.create_order(**params)
            return order
        except Exception as e:
            print(f"Erro ao criar ordem: {e}")
            logging.error(f"[create_order][ERROR] Erro ao enviar ordem: {e}")
            return None