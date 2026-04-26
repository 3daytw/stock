from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import anthropic
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

app = FastAPI(title="AI Stock Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
FINMIND_API = "https://api.finmindtrade.com/api/v4/data"

AI_STOCKS = [
    {"id": "2330", "name": "台積電",   "category": "晶片製造"},
    {"id": "2454", "name": "聯發科",   "category": "IC設計"},
    {"id": "2382", "name": "廣達",     "category": "AI伺服器"},
    {"id": "3231", "name": "緯創",     "category": "AI伺服器"},
    {"id": "6669", "name": "緯穎",     "category": "AI伺服器"},
    {"id": "2356", "name": "英業達",   "category": "AI伺服器"},
    {"id": "2317", "name": "鴻海",     "category": "AI製造"},
    {"id": "3661", "name": "世芯-KY",  "category": "ASIC設計"},
    {"id": "3443", "name": "創意",     "category": "IC設計"},
    {"id": "3035", "name": "智原",     "category": "IC設計"},
    {"id": "3017", "name": "奇鋐",     "category": "散熱"},
    {"id": "2421", "name": "建準",     "category": "散熱"},
    {"id": "4977", "name": "眾達-KY",  "category": "散熱"},
    {"id": "2376", "name": "技嘉",     "category": "AI硬體"},
    {"id": "2357", "name": "華碩",     "category": "AI硬體"},
    {"id": "2377", "name": "微星",     "category": "AI硬體"},
    {"id": "2379", "name": "瑞昱",     "category": "IC設計"},
    {"id": "3034", "name": "聯詠",     "category": "IC設計"},
    {"id": "3529", "name": "力旺",     "category": "IP設計"},
    {"id": "6533", "name": "晶心科",   "category": "AI晶片IP"},
    {"id": "2345", "name": "智邦",     "category": "AI網路"},
    {"id": "8299", "name": "群聯",     "category": "儲存IC"},
    {"id": "2303", "name": "聯電",     "category": "晶片製造"},
    {"id": "2308", "name": "台達電",   "category": "電源供應"},
    {"id": "3706", "name": "神達",     "category": "AI伺服器"},
    # 散熱
    {"id": "3324", "name": "雙鴻",     "category": "散熱"},
    {"id": "3338", "name": "泰碩",     "category": "散熱"},
    {"id": "2354", "name": "鴻準",     "category": "散熱"},
    {"id": "6664", "name": "群翊",     "category": "散熱"},
    # PCB／基板
    {"id": "3189", "name": "景碩",     "category": "PCB"},
    {"id": "3037", "name": "欣興",     "category": "PCB"},
    {"id": "8046", "name": "南電",     "category": "PCB"},
    {"id": "3044", "name": "健鼎",     "category": "PCB"},
    {"id": "2383", "name": "台光電",   "category": "PCB"},
    {"id": "4958", "name": "臻鼎-KY",  "category": "PCB"},
    {"id": "2368", "name": "金像電",   "category": "PCB"},
    # PCB 材料
    {"id": "6274", "name": "台燿",     "category": "PCB材料"},
    {"id": "1802", "name": "台玻",     "category": "PCB材料"},
    # 連接器
    {"id": "8110", "name": "華東",     "category": "連接器"},
    {"id": "3533", "name": "嘉澤",     "category": "連接器"},
    {"id": "2392", "name": "正崴",     "category": "連接器"},
    # ETF 配息型
    {"id": "0056",   "name": "元大高股息",       "category": "ETF配息"},
    {"id": "00878",  "name": "國泰永續高股息",   "category": "ETF配息"},
    {"id": "00919",  "name": "群益台灣精選高息", "category": "ETF配息"},
    {"id": "00929",  "name": "復華台灣科技優息", "category": "ETF配息"},
    {"id": "00940",  "name": "元大台灣價值高息", "category": "ETF配息"},
    # ETF 主動型
    {"id": "00981A", "name": "統一台股增長",     "category": "ETF主動"},
    {"id": "00982A", "name": "凱基台灣優選成長", "category": "ETF主動"},
    {"id": "00985A", "name": "元大台灣卓越成長", "category": "ETF主動"},
    {"id": "00992A", "name": "富邦台灣核心競爭力","category": "ETF主動"},
    {"id": "00994A", "name": "國泰台灣大數據",   "category": "ETF主動"},
    # ETF 指數型
    {"id": "0050",   "name": "元大台灣50",   "category": "ETF指數"},
    {"id": "00631L", "name": "元大台灣50正2", "category": "ETF指數"},
    {"id": "00692",  "name": "富邦公司治理",  "category": "ETF指數"},
    {"id": "00733",  "name": "富邦臺灣中小",  "category": "ETF指數"},
    {"id": "0051",   "name": "元大中型100",   "category": "ETF指數"},
]


@app.get("/api/stocks")
async def get_stocks():
    return AI_STOCKS


@app.get("/api/stock/{stock_id}/price")
async def get_stock_price(stock_id: str, start_date: str = None, end_date: str = None):
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(FINMIND_API, params={
                "dataset": "TaiwanStockPrice",
                "data_id": stock_id,
                "start_date": start_date,
                "end_date": end_date,
                "token": FINMIND_TOKEN,
            })
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != 200:
                raise HTTPException(status_code=400, detail=data.get("msg", "FinMind API error"))
            return data.get("data", [])
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"FinMind API unavailable: {str(e)}")


@app.get("/api/stock/{stock_id}/minutes")
async def get_stock_minutes(stock_id: str, days: int = 1):
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days * 3 + 5)  # buffer for weekends
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(FINMIND_API, params={
                "dataset": "TaiwanStockPriceMinute",
                "data_id": stock_id,
                "start_date": start_dt.strftime("%Y-%m-%d"),
                "end_date": end_dt.strftime("%Y-%m-%d"),
                "token": FINMIND_TOKEN,
            })
            resp.raise_for_status()
            result = resp.json()
            if result.get("status") != 200:
                raise HTTPException(status_code=400, detail=result.get("msg", "FinMind API error"))
            raw = result.get("data", [])
            if not raw:
                return []
            trading_days = sorted(set(d["date"][:10] for d in raw))
            recent = set(trading_days[-days:])
            return [d for d in raw if d["date"][:10] in recent]
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=str(e))


class QueryRequest(BaseModel):
    question: str
    stock_id: str = None
    stock_name: str = None


@app.post("/api/ai/query")
async def ai_query(req: QueryRequest):
    context = ""

    if req.stock_id:
        try:
            start = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            end = datetime.now().strftime("%Y-%m-%d")
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(FINMIND_API, params={
                    "dataset": "TaiwanStockPrice",
                    "data_id": req.stock_id,
                    "start_date": start,
                    "end_date": end,
                    "token": FINMIND_TOKEN,
                })
                price_data = resp.json().get("data", [])
                if price_data:
                    recent = price_data[-20:]
                    context = f"\n【{req.stock_name}（{req.stock_id}）近期股價資料】\n"
                    for d in recent:
                        context += f"  {d['date']}: 開{d['open']} 高{d['max']} 低{d['min']} 收{d['close']} 量{d.get('Trading_Volume', '-')}\n"
                    closes = [float(d["close"]) for d in price_data]
                    if len(closes) > 1:
                        latest = closes[-1]
                        month_ago = closes[max(0, len(closes) - 22)]
                        pct = (latest - month_ago) / month_ago * 100
                        context += f"\n近一個月漲跌幅：{pct:+.2f}%\n"
                        context += f"近期最高：{max(closes[-22:]):.1f}，最低：{min(closes[-22:]):.1f}\n"
        except Exception:
            pass

    try:
        ai_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        system_prompt = (
            "你是一位專業的台灣股市分析師，專精於AI相關概念股分析。\n"
            "請用繁體中文回答，語氣專業但易懂，提供具體有洞察力的分析。\n"
            "回答要有條理，可以使用重點條列。\n"
            "重要提示：你的分析僅供參考，不構成具體投資建議，投資需自行評估風險。"
        )
        user_msg = req.question + (context if context else "")
        message = ai_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        return {"answer": message.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")


@app.get("/api/stock/{stock_id}/revenue")
async def get_stock_revenue(stock_id: str):
    start = (datetime.now() - timedelta(days=760)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(FINMIND_API, params={
                "dataset": "TaiwanStockMonthRevenue",
                "data_id": stock_id,
                "start_date": start,
                "end_date": end,
                "token": FINMIND_TOKEN,
            })
            resp.raise_for_status()
            result = resp.json()
            if result.get("status") != 200:
                return []
            return result.get("data", [])
        except Exception:
            return []


@app.get("/api/stock/{stock_id}/financials")
async def get_stock_financials(stock_id: str):
    start = (datetime.now() - timedelta(days=760)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(FINMIND_API, params={
                "dataset": "TaiwanStockFinancialStatements",
                "data_id": stock_id,
                "start_date": start,
                "end_date": end,
                "token": FINMIND_TOKEN,
            })
            resp.raise_for_status()
            result = resp.json()
            if result.get("status") != 200:
                return []
            keep = {"EPS", "GrossProfit", "Revenue", "IncomeAfterTaxes"}
            return [r for r in result.get("data", []) if r.get("type") in keep]
        except Exception:
            return []


@app.get("/api/stock/{stock_id}/per")
async def get_stock_per(stock_id: str):
    start = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(FINMIND_API, params={
                "dataset": "TaiwanStockPER",
                "data_id": stock_id,
                "start_date": start,
                "end_date": end,
                "token": FINMIND_TOKEN,
            })
            resp.raise_for_status()
            result = resp.json()
            if result.get("status") != 200:
                return []
            return result.get("data", [])
        except Exception:
            return []


# Static files — must be mounted last
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")
