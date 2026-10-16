import pandas as pd
import numpy as np
import talib
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class PocketOptionSignalEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def analyze_market(self) -> Dict[str, Any]:
        close = self.df['close'].values
        open_p = self.df['open'].values
        high_p = self.df['high'].values
        low_p = self.df['low'].values

        # Indicators
        rsi = talib.RSI(close, timeperiod=14)[-1]
        macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        upper, middle, lower = talib.BBANDS(close, timeperiod=20)
        ema_fast = talib.EMA(close, timeperiod=9)[-1]
        ema_slow = talib.EMA(close, timeperiod=21)[-1]

        # Candlestick Patterns
        engulfing = talib.CDLENGULFING(open_p, high_p, low_p, close_p)[-1]
        hammer = talib.CDLHAMMER(open_p, high_p, low_p, close_p)[-1]
        shooting_star = talib.CDLSHOOTINGSTAR(open_p, high_p, low_p, close_p)[-1]

        # Signal Logic
        call_score = 0
        put_score = 0

        # RSI logic
        if rsi < 30: call_score += 2
        elif rsi > 70: put_score += 2

        # EMA Trend
        if ema_fast > ema_slow: call_score += 1
        else: put_score += 1

        # MACD Crossover
        if macdhist[-1] > 0: call_score += 1
        else: put_score += 1

        # Bollinger Bands
        if close[-1] <= lower[-1]: call_score += 2
        elif close[-1] >= upper[-1]: put_score += 2

        # Pattern scoring
        if engulfing == 100 or hammer == 100: call_score += 2
        elif engulfing == -100 or shooting_star == -100: put_score += 2

        # Action Decision
        if call_score >= 4 and call_score > put_score:
            signal = "CALL (BUY)"
            confidence = min(60 + (call_score * 5), 92)
        elif put_score >= 4 and put_score > call_score:
            signal = "PUT (SELL)"
            confidence = min(60 + (put_score * 5), 92)
        else:
            signal = "HOLD / NEUTRAL"
            confidence = 50.0

        return {
            "signal": signal,
            "confidence": f"{confidence}%",
            "rsi": round(rsi, 2),
            "trend": "BULLISH" if ema_fast > ema_slow else "BEARISH",
            "recommended_position": "3% of account balance"
        }

app = FastAPI(title="Pocket Option AI Signal Bot")

class Candle(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float = 0

class CandleRequest(BaseModel):
    symbol: str
    timeframe: str  # e.g., "15s" or "1m"
    candles: List[Candle]

@app.post("/analyze")
async def analyze(data: CandleRequest):
    if len(data.candles) < 30:
        raise HTTPException(status_code=400, detail="Kam az kam 30 candles ki ururat hai.")

    df = pd.DataFrame([c.dict() for c in data.candles])
    engine = PocketOptionSignalEngine(df)
    result = engine.analyze_market()
    result["symbol"] = data.symbol
    result["timeframe"] = data.timeframe

    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
      
