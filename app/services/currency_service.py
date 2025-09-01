import httpx
from typing import Optional

class CurrencyService:
    def __init__(self) -> None:
        self.client = httpx.Client(timeout=5.0, headers={"User-Agent": "Andreia32/1.0"})

    def get_dollar_to_real_rate(self) -> float:
        try:
            rate = self._fetch_from_api()
            if rate and rate > 0:
                return rate
            # fallback conservador
            return 5.00
        except Exception:
            return 5.00

    def _fetch_from_api(self) -> Optional[float]:
        try:
            resp = self.client.get("https://economia.awesomeapi.com.br/last/USD-BRL")
            data = resp.json()
            bid = data.get("USDBRL", {}).get("bid")
            return float(bid) if bid else None
        except Exception:
            return None

    def convert_dollar_to_real(self, dollar_amount: float) -> float:
        rate = self.get_dollar_to_real_rate()
        return dollar_amount * rate

    def format_real(self, value: float) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

