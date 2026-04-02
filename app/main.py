from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.db import engine, SessionLocal, Base
from app.telephony.twilio_handler import router as twilio_router
from app.telephony.stream_handler import router as stream_router
from app.vision.upload_handler import router as upload_router
import app.scheduling.models  # noqa: F401 — registers models with Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from app.scheduling.seed import seed_database
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Sears Home Services Voice Agent", lifespan=lifespan)
app.include_router(twilio_router)
app.include_router(stream_router)
app.include_router(upload_router)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@app.get("/info", response_class=__import__("fastapi").responses.HTMLResponse)
async def info():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sears Voice Agent — О проекте</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #222; }
  .hero { background: #003399; color: white; padding: 32px 20px 24px; }
  .hero h1 { font-size: 22px; font-weight: 700; margin-bottom: 8px; }
  .hero p { font-size: 15px; opacity: 0.85; line-height: 1.5; }
  .section { background: white; margin: 12px 16px; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  .section h2 { font-size: 17px; font-weight: 700; color: #003399; margin-bottom: 14px; border-bottom: 2px solid #e8eef8; padding-bottom: 8px; }
  .section h3 { font-size: 15px; font-weight: 600; margin: 16px 0 8px; }
  .section p { font-size: 14px; line-height: 1.6; color: #444; margin-bottom: 10px; }
  .badge { display: inline-block; background: #e8eef8; color: #003399; font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 20px; margin-bottom: 10px; }
  .tier { border-left: 3px solid #003399; padding-left: 14px; margin-bottom: 16px; }
  .tier.t2 { border-color: #0066cc; }
  .tier.t3 { border-color: #0099ff; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
  th { background: #f0f4ff; color: #003399; text-align: left; padding: 8px 10px; font-size: 12px; }
  td { padding: 8px 10px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
  .chat { background: #f9f9f9; border-radius: 10px; padding: 14px; font-size: 13px; line-height: 1.7; }
  .chat .agent { color: #003399; font-weight: 600; }
  .chat .user { color: #333; }
  .flow { display: flex; flex-direction: column; gap: 6px; }
  .flow-step { background: #f0f4ff; border-radius: 8px; padding: 10px 14px; font-size: 13px; display: flex; align-items: center; gap: 10px; }
  .flow-step .num { background: #003399; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
  .arrow { text-align: center; color: #aaa; font-size: 18px; }
  .test-case { border: 1px solid #e8eef8; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
  .test-case .label { font-size: 12px; font-weight: 700; color: #003399; margin-bottom: 4px; }
  .test-case .desc { font-size: 13px; color: #444; line-height: 1.5; }
  .benefit-row { display: flex; gap: 10px; margin-bottom: 8px; align-items: flex-start; }
  .benefit-row .icon { font-size: 18px; flex-shrink: 0; }
  .benefit-row .text { font-size: 13px; color: #444; line-height: 1.5; }
  .phone-box { background: #003399; color: white; border-radius: 12px; padding: 20px; text-align: center; margin: 12px 16px; }
  .phone-box .num { font-size: 28px; font-weight: 700; letter-spacing: 1px; margin: 8px 0; }
  .phone-box p { font-size: 13px; opacity: 0.8; }
  footer { text-align: center; padding: 24px 16px; font-size: 12px; color: #aaa; }
</style>
</head>
<body>

<div class="hero">
  <h1>Sears Home Services<br>Голосовой AI Агент</h1>
  <p>Умный голосовой помощник для диагностики бытовой техники и записи к технику — без ожидания, без кнопок.</p>
</div>

<div class="phone-box">
  <p>Позвонить и протестировать</p>
  <div class="num">+1 (662) 591-9049</div>
  <p>Отвечает мгновенно, 24/7</p>
</div>

<div class="section">
  <h2>Что это такое?</h2>
  <p>AI агент который разговаривает как живой человек — слушает что ты говоришь, понимает проблему с техникой, помогает её решить пошагово. Если не получается — записывает к технику прямо во время звонка.</p>
  <p>Никакого ожидания оператора. Никакого «нажмите 1, нажмите 2».</p>
</div>

<div class="section">
  <h2>Пример разговора</h2>
  <div class="chat">
    <p><span class="agent">Alex:</span> Hi, this is Alex from Sears Home Services! How can I help you today?</p>
    <p><span class="user">Ты:</span> My washing machine stopped draining</p>
    <p><span class="agent">Alex:</span> I'm sorry to hear that! First, can you check if the drain hose at the back is kinked?</p>
    <p><span class="user">Ты:</span> I checked, it looks fine</p>
    <p><span class="agent">Alex:</span> Let's try a spin-only cycle — does the machine make any unusual sounds?</p>
    <p><span class="user">Ты:</span> Yes, it hums but water doesn't drain</p>
    <p><span class="agent">Alex:</span> Sounds like the drain pump. Would you like me to schedule a technician?</p>
    <p><span class="user">Ты:</span> Yes please, my zip is 60601</p>
    <p><span class="agent">Alex:</span> Marcus Rivera is available Tuesday at 9 AM or Thursday at 1 PM — which works?</p>
    <p><span class="user">Ты:</span> Tuesday please, I'm John Smith, 312-555-1234</p>
    <p><span class="agent">Alex:</span> Done! Marcus Rivera is scheduled for Tuesday at 9 AM. Is there anything else?</p>
  </div>
</div>

<div class="section">
  <h2>Три уровня возможностей</h2>

  <div class="tier">
    <span class="badge">Tier 1 — Базовый</span>
    <h3>Диагностика голосом</h3>
    <p>Агент определяет прибор, собирает симптомы и ведёт через шаги диагностики. Помнит весь разговор — не переспрашивает.</p>
  </div>

  <div class="tier t2">
    <span class="badge">Tier 2 — Запись</span>
    <h3>Технические визиты</h3>
    <p>Находит техников по zip code и специализации, показывает свободные слоты, записывает и подтверждает визит.</p>
  </div>

  <div class="tier t3">
    <span class="badge">Tier 3 — Визуальный</span>
    <h3>Анализ фотографий</h3>
    <p>Запрашивает email прямо в разговоре, присылает ссылку для загрузки фото, GPT-4o Vision анализирует снимок и уточняет диагноз — пока ты ещё на линии.</p>
  </div>
</div>

<div class="section">
  <h2>Как работает изнутри</h2>
  <div class="flow">
    <div class="flow-step"><div class="num">1</div><div>Twilio принимает звонок на реальный номер</div></div>
    <div class="arrow">↓</div>
    <div class="flow-step"><div class="num">2</div><div>Deepgram переводит речь в текст за ~0.2 сек</div></div>
    <div class="arrow">↓</div>
    <div class="flow-step"><div class="num">3</div><div>GPT-4o думает, отвечает или вызывает инструмент (поиск техника, запись)</div></div>
    <div class="arrow">↓</div>
    <div class="flow-step"><div class="num">4</div><div>OpenAI TTS озвучивает ответ живым голосом</div></div>
    <div class="arrow">↓</div>
    <div class="flow-step"><div class="num">5</div><div>Ты слышишь ответ через ~1.5 сек</div></div>
  </div>
</div>

<div class="section">
  <h2>Польза для клиента</h2>
  <div class="benefit-row"><div class="icon">⏱️</div><div class="text"><strong>Мгновенный ответ</strong> — никакого ожидания в очереди</div></div>
  <div class="benefit-row"><div class="icon">🎙️</div><div class="text"><strong>Живой разговор</strong> — говоришь как с человеком</div></div>
  <div class="benefit-row"><div class="icon">🔧</div><div class="text"><strong>Экспертная диагностика</strong> — знает все приборы и поломки</div></div>
  <div class="benefit-row"><div class="icon">📅</div><div class="text"><strong>Запись прямо в звонке</strong> — не надо перезванивать</div></div>
  <div class="benefit-row"><div class="icon">📷</div><div class="text"><strong>Видит проблему</strong> — анализ фото во время разговора</div></div>
  <div class="benefit-row"><div class="icon">🌙</div><div class="text"><strong>24/7</strong> — работает в любое время</div></div>
</div>

<div class="section">
  <h2>Тест-кейсы</h2>

  <div class="test-case">
    <div class="label">✅ Тест 1 — Базовый разговор</div>
    <div class="desc">Назови прибор и симптом. Агент должен дать конкретные советы именно для этого прибора.</div>
  </div>
  <div class="test-case">
    <div class="label">✅ Тест 2 — Память</div>
    <div class="desc">Скажи сразу всё в одном предложении. Агент не должен переспрашивать уже сказанное.</div>
  </div>
  <div class="test-case">
    <div class="label">✅ Тест 3 — Запись к технику</div>
    <div class="desc">Дойди до записи. Назови zip 60601 — агент найдёт техников и запишет.</div>
  </div>
  <div class="test-case">
    <div class="label">✅ Тест 4 — Загрузка фото</div>
    <div class="desc">Дай email во время звонка. Открой ссылку, загрузи фото, скажи агенту — он опишет что видит.</div>
  </div>
  <div class="test-case">
    <div class="label">✅ Тест 5 — Разные приборы</div>
    <div class="desc">Позвони несколько раз с разными приборами — холодильник, духовка, кондиционер. Каждый раз разные советы.</div>
  </div>
  <div class="test-case">
    <div class="label">✅ Тест 6 — Нет техников</div>
    <div class="desc">Назови zip 99999 — агент корректно скажет что нет техников в этой зоне.</div>
  </div>
</div>

<div class="section">
  <h2>Что хранится в базе данных</h2>
  <table>
    <tr><th>Таблица</th><th>Что внутри</th></tr>
    <tr><td><strong>technicians</strong></td><td>10 техников, имена, контакты</td></tr>
    <tr><td><strong>service_areas</strong></td><td>Zip codes Чикаго которые обслуживает каждый</td></tr>
    <tr><td><strong>specialties</strong></td><td>Какие приборы умеет чинить каждый техник</td></tr>
    <tr><td><strong>availability_slots</strong></td><td>Расписание на 7 дней вперёд</td></tr>
    <tr><td><strong>appointments</strong></td><td>Подтверждённые записи клиентов</td></tr>
    <tr><td><strong>image_requests</strong></td><td>Токены для загрузки фото + результаты анализа</td></tr>
  </table>
</div>

<footer>Sears Home Services Voice Agent · Take-home project</footer>

</body>
</html>"""
