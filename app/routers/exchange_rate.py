from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ..services.currency_service import CurrencyService

router = APIRouter()

@router.get("/exchange-rate")
async def exchange_rate():
    try:
        service = CurrencyService()
        rate = service.get_dollar_to_real_rate()
        return JSONResponse(content={
            "success": True,
            "rate": rate,
            "formatted_rate": f"{rate:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "currency": "BRL"
        })
    except Exception:
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "Erro ao obter taxa de câmbio",
            "rate": 5.00
        })

