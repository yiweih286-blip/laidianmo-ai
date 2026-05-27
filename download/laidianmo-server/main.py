"""来点墨AI客服 - 后端（FastAPI + z-ai大模型）"""
import os, sys
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import subprocess

# ========== 数据库 ==========
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "laidianmo.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    sort_order = Column(Integer, default=0)

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    age_range = Column(String(50))
    level = Column(String(50))
    duration = Column(String(50))
    total_sessions = Column(Integer)
    price = Column(Float)
    price_unit = Column(String(30), default="元/期")
    max_students = Column(Integer)
    highlights = Column(Text)
    is_active = Column(Boolean, default=True)

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    title = Column(String(100))
    specialties = Column(Text)
    experience = Column(String(50))
    education = Column(String(100))
    awards = Column(Text)
    bio = Column(Text)
    is_active = Column(Boolean, default=True)

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_name = Column(String(100), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(String(20), nullable=False)
    end_time = Column(String(20), nullable=False)
    teacher_name = Column(String(50))
    campus_name = Column(String(100))
    current_students = Column(Integer, default=0)
    max_students = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)

class Campus(Base):
    __tablename__ = "campuses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    address = Column(Text)
    phone = Column(String(30))
    business_hours = Column(String(100))
    transportation = Column(Text)
    is_active = Column(Boolean, default=True)

class FAQ(Base):
    __tablename__ = "faqs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50))
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

class Promotion(Base):
    __tablename__ = "promotions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    discount_value = Column(String(200))
    start_date = Column(String(20))
    end_date = Column(String(20))
    conditions = Column(Text)
    is_active = Column(Boolean, default=True)

class OrgInfo(Base):
    __tablename__ = "org_info"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), default="来点墨书法艺术培训中心")
    slogan = Column(String(200))
    intro = Column(Text)
    phone = Column(String(30))
    wechat = Column(String(100))
    philosophy = Column(Text)

class TrialBooking(Base):
    __tablename__ = "trial_bookings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_name = Column(String(50))
    phone = Column(String(20))
    child_name = Column(String(50))
    child_age = Column(Integer)
    preferred_time = Column(String(100))
    remark = Column(Text)
    status = Column(String(20), default="待确认")
    created_at = Column(DateTime, default=datetime.now)

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _obj(model):
    if not model: return {}
    return {c.name: getattr(model, c.name) for c in model.__table__.columns}

# ========== 鉴权 ==========
import hashlib, secrets, jwt as pyjwt

SECRET = "laidianmo_jwt_2026"

def hash_pw(pw): 
    salt = secrets.token_hex(16)
    return f"{salt}${hashlib.sha256((salt+pw).encode()).hexdigest()}"

def verify_pw(pw, h):
    try:
        salt, hsh = h.split("$")
        return hashlib.sha256((salt+pw).encode()).hexdigest() == hsh
    except: return False

def make_token(data):
    from datetime import timedelta
    data["exp"] = datetime.utcnow() + timedelta(hours=24)
    return pyjwt.encode(data, SECRET, algorithm="HS256")

def check_token(auth: str = Header(None)):
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    try:
        return pyjwt.decode(auth[7:], SECRET, algorithms=["HS256"])
    except: raise HTTPException(401, "登录过期")

# ========== 检索 ==========
DAY = {1:"周一",2:"周二",3:"周三",4:"周四",5:"周五",6:"周六",7:"周日"}

def retrieve(db, query):
    q = f"%{query}%"
    parts = []

    org = db.query(OrgInfo).first()
    if org:
        s = f"【机构】{org.name}"
        if org.slogan: s += f" | {org.slogan}"
        if org.phone: s += f" | 电话：{org.phone}"
        if org.wechat: s += f" | 微信：{org.wechat}"
        if org.intro: s += f"\n{org.intro}"
        parts.append(s)

    courses = db.query(Course).filter(Course.is_active==True).filter(
        Course.name.like(q)|Course.description.like(q)|Course.age_range.like(q)|Course.level.like(q)
    ).limit(6).all()
    if not courses:
        courses = db.query(Course).filter(Course.is_active==True).limit(6).all()
    if courses:
        lines = ["【课程】"]
        for c in courses:
            cat = db.query(Category).filter(Category.id==c.category_id).first()
            line = f"- {c.name}"
            if cat: line += f"（{cat.name}）"
            if c.age_range: line += f" | 适合{c.age_range}"
            if c.level: line += f" | {c.level}"
            if c.price: line += f" | {c.price}{c.price_unit}"
            if c.duration: line += f" | {c.duration}"
            if c.total_sessions: line += f" | 共{c.total_sessions}次"
            if c.max_students: line += f" | ≤{c.max_students}人"
            if c.description: line += f"\n  {c.description}"
            lines.append(line)
        parts.append("\n".join(lines))

    teachers = db.query(Teacher).filter(Teacher.is_active==True).filter(
        Teacher.name.like(q)|Teacher.specialties.like(q)
    ).limit(4).all()
    if not teachers:
        teachers = db.query(Teacher).filter(Teacher.is_active==True).limit(4).all()
    if teachers:
        lines = ["【教师】"]
        for t in teachers:
            line = f"- {t.name}（{t.title or ''}）"
            if t.specialties: line += f" | 擅长：{t.specialties}"
            if t.experience: line += f" | {t.experience}"
            if t.education: line += f" | {t.education}"
            if t.awards: line += f"\n  获奖：{t.awards}"
            lines.append(line)
        parts.append("\n".join(lines))

    schedules = db.query(Schedule).filter(Schedule.is_active==True).limit(8).all()
    if schedules:
        lines = ["【课表】"]
        for s in schedules:
            line = f"- {s.course_name} | {DAY.get(s.day_of_week,'')} {s.start_time}-{s.end_time}"
            if s.teacher_name: line += f" | {s.teacher_name}"
            if s.campus_name: line += f" | {s.campus_name}"
            line += f" | {s.current_students}/{s.max_students}人"
            lines.append(line)
        parts.append("\n".join(lines))

    campuses = db.query(Campus).filter(Campus.is_active==True).filter(
        Campus.name.like(q)|Campus.address.like(q)
    ).limit(3).all()
    if not campuses:
        campuses = db.query(Campus).filter(Campus.is_active==True).limit(3).all()
    if campuses:
        lines = ["【校区】"]
        for c in campuses:
            line = f"- {c.name}"
            if c.address: line += f" | {c.address}"
            if c.phone: line += f" | {c.phone}"
            if c.business_hours: line += f" | {c.business_hours}"
            lines.append(line)
        parts.append("\n".join(lines))

    faqs = db.query(FAQ).filter(FAQ.is_active==True).filter(
        FAQ.question.like(q)|FAQ.answer.like(q)|FAQ.category.like(q)
    ).limit(5).all()
    if faqs:
        lines = ["【FAQ】"]
        for f in faqs:
            lines.append(f"- Q：{f.question}\n  A：{f.answer}")
        parts.append("\n".join(lines))

    promos = db.query(Promotion).filter(Promotion.is_active==True).limit(3).all()
    if promos:
        lines = ["【优惠】"]
        for p in promos:
            line = f"- {p.title} | {p.discount_value or ''}"
            if p.conditions: line += f" | 条件：{p.conditions}"
            lines.append(line)
        parts.append("\n".join(lines))

    return "\n\n".join(parts) if parts else "（暂无数据）"

# ========== LLM ==========
SYSTEM_PROMPT = """你是"来点墨书法艺术培训中心"的售前AI客服，名叫"小墨"。

## 角色
专业、亲切、耐心的书法培训顾问，服务咨询课程的家长。

## 原则
1. 以数据库真实数据为准，不编造信息
2. 语气温暖自然，像贴心教育顾问
3. 家长问题模糊时，主动询问孩子年龄、基础、兴趣
4. 数据库没有的信息，坦诚告知并建议联系校区
5. 适时推荐体验课

## 格式
- 简体中文，简洁有力
- 价格明确标注
- 推荐课程说明理由

## 数据库信息
{CONTEXT}

---
基于以上数据库信息回答。信息不足时建议家长联系校区。"""

def call_llm(user_msg, db_context, history):
    system = SYSTEM_PROMPT.replace("{CONTEXT}", db_context[:3000] or "（暂无数据）")
    messages = []
    if history:
        for m in history[-8:]:
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_msg})

    try:
        import asyncio
        from z_ai_web_dev_sdk import ZAI
        async def _chat():
            zai = await ZAI.create()
            completion = await zai.chat.completions.create(
                messages=[{"role": "assistant", "content": system}] + messages,
                thinking={"type": "disabled"}
            )
            return completion.choices[0].message.content
        reply = asyncio.run(_chat())
        if reply and reply.strip():
            return reply.strip()
    except Exception as e:
        print(f"LLM error: {e}")

    if db_context:
        return f"感谢咨询！根据我们的信息：\n\n{db_context[:500]}\n\n如需更多详情，建议联系校区咨询。"
    return "抱歉，暂时无法获取信息。请拨打校区电话咨询！"

# ========== FastAPI ==========
app = FastAPI(title="来点墨AI客服")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

FRONTEND = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(FRONTEND, exist_ok=True)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(Admin).first():
        db.add(Admin(username="admin", hashed_password=hash_pw("admin123")))
    if not db.query(OrgInfo).first():
        db.add(OrgInfo(name="来点墨书法艺术培训中心", slogan="以墨养心，以书育人",
                       intro="来点墨书法艺术培训中心是一家专注于书法艺术教育的专业培训机构。",
                       phone="400-888-6688", wechat="laidianmo_art"))
    db.commit()
    db.close()

# 前端页面
@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))

@app.get("/admin")
async def admin():
    return FileResponse(os.path.join(FRONTEND, "admin.html"))

# ========== 公开接口 ==========
class ChatReq(BaseModel):
    message: str
    history: list = []

@app.post("/api/chat")
async def chat(req: ChatReq, db: Session = Depends(get_db)):
    ctx = retrieve(db, req.message)
    reply = call_llm(req.message, ctx, req.history)
    return {"success": True, "reply": reply}

@app.get("/api/courses")
async def list_courses(db: Session = Depends(get_db)):
    return {"data": [_obj(c) for c in db.query(Course).filter(Course.is_active==True).all()]}

@app.get("/api/campuses")
async def list_campuses(db: Session = Depends(get_db)):
    return {"data": [_obj(c) for c in db.query(Campus).filter(Campus.is_active==True).all()]}

@app.post("/api/trial-booking")
async def book(data: dict, db: Session = Depends(get_db)):
    b = TrialBooking(**{k: data.get(k) for k in ["parent_name","phone","child_name","child_age","preferred_time","remark"] if data.get(k)})
    db.add(b); db.commit(); db.refresh(b)
    return {"success": True, "id": b.id}

# ========== 管理接口 ==========
@app.post("/api/admin/login")
async def login(data: dict, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username==data.get("username")).first()
    if not admin or not verify_pw(data.get("password",""), admin.hashed_password):
        raise HTTPException(401, "用户名或密码错误")
    return {"success": True, "token": make_token({"sub": admin.username, "id": admin.id}), "username": admin.username}

@app.post("/api/admin/change-password")
async def change_pw(data: dict, admin=Depends(check_token), db: Session = Depends(get_db)):
    a = db.query(Admin).filter(Admin.username==admin["sub"]).first()
    if not verify_pw(data.get("old_password",""), a.hashed_password):
        raise HTTPException(400, "当前密码错误")
    a.hashed_password = hash_pw(data["new_password"])
    db.commit()
    return {"success": True}

# 通用CRUD
TABLES = {
    "categories": Category, "courses": Course, "teachers": Teacher,
    "schedules": Schedule, "campuses": Campus, "faqs": FAQ,
    "promotions": Promotion, "org_info": OrgInfo
}

@app.get("/api/admin/{table}")
async def list_items(table: str, admin=Depends(check_token), db: Session = Depends(get_db)):
    if table not in TABLES: raise HTTPException(404)
    return {"data": [_obj(i) for i in db.query(TABLES[table]).all()]}

@app.post("/api/admin/{table}")
async def add_item(table: str, data: dict, admin=Depends(check_token), db: Session = Depends(get_db)):
    if table not in TABLES: raise HTTPException(404)
    obj = TABLES[table](**data)
    db.add(obj); db.commit(); db.refresh(obj)
    return {"success": True, "id": obj.id}

@app.put("/api/admin/{table}/{item_id}")
async def update_item(table: str, item_id: int, data: dict, admin=Depends(check_token), db: Session = Depends(get_db)):
    if table not in TABLES: raise HTTPException(404)
    obj = db.query(TABLES[table]).filter(TABLES[table].id==item_id).first()
    if not obj: raise HTTPException(404)
    for k, v in data.items():
        if hasattr(obj, k): setattr(obj, k, v)
    db.commit()
    return {"success": True}

@app.delete("/api/admin/{table}/{item_id}")
async def delete_item(table: str, item_id: int, admin=Depends(check_token), db: Session = Depends(get_db)):
    if table not in TABLES: raise HTTPException(404)
    obj = db.query(TABLES[table]).filter(TABLES[table].id==item_id).first()
    if not obj: raise HTTPException(404)
    if hasattr(obj, "is_active"): obj.is_active = False
    else: db.delete(obj)
    db.commit()
    return {"success": True}

@app.get("/api/admin/bookings/list")
async def list_bookings(admin=Depends(check_token), db: Session = Depends(get_db)):
    return {"data": [_obj(b) for b in db.query(TrialBooking).order_by(TrialBooking.id.desc()).all()]}

@app.put("/api/admin/bookings/{bid}")
async def update_booking(bid: int, data: dict, admin=Depends(check_token), db: Session = Depends(get_db)):
    b = db.query(TrialBooking).filter(TrialBooking.id==bid).first()
    if not b: raise HTTPException(404)
    if "status" in data: b.status = data["status"]
    db.commit()
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
