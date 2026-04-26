from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import anthropic
import asyncio
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
    {"id": "6664", "name": "群翊",     "category": "PCB"},
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


BROAD_SCREEN_STOCKS = [
    # 金融
    {"id":"2882","name":"國泰金"},{"id":"2886","name":"兆豐金"},{"id":"2884","name":"玉山金"},
    {"id":"2891","name":"中信金"},{"id":"2892","name":"第一金"},{"id":"2881","name":"富邦金"},
    {"id":"2885","name":"元大金"},{"id":"2887","name":"台新金"},{"id":"2890","name":"永豐金"},
    {"id":"5876","name":"上海商銀"},{"id":"5880","name":"合庫金"},{"id":"2883","name":"開發金"},
    {"id":"2801","name":"彰銀"},{"id":"2809","name":"京城銀"},
    # 電信
    {"id":"2412","name":"中華電"},{"id":"4904","name":"遠傳"},{"id":"3045","name":"台灣大"},
    # 石化
    {"id":"1301","name":"台塑"},{"id":"1303","name":"南亞"},{"id":"1326","name":"台化"},
    {"id":"6505","name":"台塑化"},
    # 鋼鐵
    {"id":"2002","name":"中鋼"},{"id":"2006","name":"東和鋼鐵"},{"id":"2015","name":"豐興"},
    # 食品/零售
    {"id":"1216","name":"統一"},{"id":"2912","name":"統一超"},{"id":"1210","name":"大成"},
    {"id":"1234","name":"黑松"},{"id":"2915","name":"潤泰全"},
    # 紡織/化工
    {"id":"1402","name":"遠東新"},{"id":"1434","name":"福懋"},{"id":"1717","name":"長興"},
    # 製造/工業
    {"id":"1504","name":"東元"},{"id":"9933","name":"中鼎"},{"id":"9910","name":"豐泰"},
    {"id":"9914","name":"美利達"},{"id":"1605","name":"華新"},
    # 汽車
    {"id":"2207","name":"和泰車"},{"id":"2227","name":"裕日車"},{"id":"2201","name":"裕隆"},
    # 航運
    {"id":"2603","name":"長榮"},{"id":"2615","name":"萬海"},{"id":"2609","name":"陽明"},
    {"id":"2610","name":"華航"},{"id":"2618","name":"長榮航"},
    # 建設
    {"id":"2520","name":"冠德"},{"id":"5522","name":"遠雄"},{"id":"2501","name":"國建"},
    # 其他科技
    {"id":"2353","name":"宏碁"},{"id":"2352","name":"佳世達"},{"id":"2347","name":"聯強"},
    {"id":"2360","name":"致茂"},{"id":"3711","name":"日月光投控"},{"id":"2049","name":"上銀"},
    {"id":"4938","name":"和碩"},{"id":"2474","name":"可成"},{"id":"2327","name":"國巨"},
    {"id":"3008","name":"大立光"},{"id":"2388","name":"威盛"},{"id":"6415","name":"矽力-KY"},
    {"id":"2449","name":"京元電子"},{"id":"6669","name":"緯穎"},{"id":"3231","name":"緯創"},
]

@app.get("/api/screen")
async def screen_stocks():
    """Scan broad market for value stocks in 特價/便宜/合理 zones."""
    today = datetime.now()
    end_str   = today.strftime("%Y-%m-%d")
    per_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    eps_start = (today - timedelta(days=760)).strftime("%Y-%m-%d")
    p3y_start = (today - timedelta(days=365*3)).strftime("%Y-%m-%d")

    # Build deduplicated screen list (exclude ETFs already in AI_STOCKS)
    seen: set[str] = set()
    screen_list = []
    for s in BROAD_SCREEN_STOCKS + [
        x for x in AI_STOCKS if not x["category"].startswith("ETF")
    ]:
        if s["id"] not in seen:
            seen.add(s["id"])
            screen_list.append(s)

    async with httpx.AsyncClient(timeout=25) as client:

        # ── Phase 1: fetch latest P/E for all candidates (batches of 10) ──
        async def _get_cur_per(sid: str):
            try:
                r = await client.get(FINMIND_API, params={
                    "dataset": "TaiwanStockPER", "data_id": sid,
                    "start_date": per_start, "end_date": end_str,
                    "token": FINMIND_TOKEN,
                })
                rows = r.json().get("data", [])
                return sid, rows[-1] if rows else None
            except Exception:
                return sid, None

        per_map: dict = {}
        for i in range(0, len(screen_list), 10):
            batch = screen_list[i:i + 10]
            results = await asyncio.gather(*[_get_cur_per(s["id"]) for s in batch])
            for sid, row in results:
                if row:
                    per_map[sid] = row
            await asyncio.sleep(0.25)

        # ── Filter: reasonable P/E + positive yield ──
        candidates = [
            s for s in screen_list
            if s["id"] in per_map
            and 3 < float(per_map[s["id"]].get("PER") or 0) < 25
            and float(per_map[s["id"]].get("dividend_yield") or 0) > 0
        ]

        # ── Phase 2: fetch EPS + 3yr PER history for candidates ──
        async def _get_eps_per(sid: str):
            try:
                eps_r, p3_r = await asyncio.gather(
                    client.get(FINMIND_API, params={
                        "dataset": "TaiwanStockFinancialStatements",
                        "data_id": sid, "start_date": eps_start,
                        "end_date": end_str, "token": FINMIND_TOKEN,
                    }),
                    client.get(FINMIND_API, params={
                        "dataset": "TaiwanStockPER",
                        "data_id": sid, "start_date": p3y_start,
                        "end_date": end_str, "token": FINMIND_TOKEN,
                    }),
                )
                eps_rows = [x for x in eps_r.json().get("data", []) if x.get("type") == "EPS"]
                per_hist = p3_r.json().get("data", [])
                return sid, eps_rows, per_hist
            except Exception:
                return sid, [], []

        scored = []
        name_map = {s["id"]: s["name"] for s in screen_list}

        for i in range(0, len(candidates), 5):
            batch = candidates[i:i + 5]
            results = await asyncio.gather(*[_get_eps_per(s["id"]) for s in batch])
            for s, (sid, eps_list, per_hist) in zip(batch, results):
                try:
                    eps_sorted = sorted(eps_list, key=lambda x: x["date"])
                    if len(eps_sorted) < 4:
                        continue
                    ttm = sum(float(e["value"]) for e in eps_sorted[-4:])
                    if ttm <= 0:
                        continue
                    valid_pers = sorted([
                        float(x["PER"]) for x in per_hist
                        if 0 < float(x.get("PER") or 0) < 300
                    ])
                    if len(valid_pers) < 20:
                        continue
                    n = len(valid_pers)
                    pe15 = valid_pers[int(n * 0.15)]
                    pe30 = valid_pers[int(n * 0.30)]
                    pe50 = valid_pers[int(n * 0.50)]
                    pe80 = valid_pers[int(n * 0.80)]
                    cur_per = float(per_map[sid].get("PER") or 0)
                    if cur_per <= pe15:
                        zone = "特價"
                    elif cur_per <= pe30:
                        zone = "便宜"
                    elif cur_per <= pe50:
                        zone = "合理"
                    else:
                        continue  # above fair value — skip
                    scored.append({
                        "id": sid,
                        "name": name_map.get(sid, sid),
                        "zone": zone,
                        "per": round(cur_per, 1),
                        "ttm_eps": round(ttm, 2),
                        "dy": round(float(per_map[sid].get("dividend_yield") or 0), 2),
                        "pbr": round(float(per_map[sid].get("PBR") or 0), 2),
                        "cheap_price": round(pe30 * ttm, 1),
                        "fair_price":  round(pe50 * ttm, 1),
                        "exp_price":   round(pe80 * ttm, 1),
                    })
                except Exception:
                    pass
            await asyncio.sleep(0.25)

    zone_order = {"特價": 0, "便宜": 1, "合理": 2}
    scored.sort(key=lambda x: (zone_order.get(x["zone"], 9), -x.get("dy", 0)))
    return scored[:20]


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
