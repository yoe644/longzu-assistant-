import os
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
import httpx

# ---------- 数据库配置（使用 SQLite，简单可靠） ----------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "longzu.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------- 数据库模型 ----------
class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    rarity = Column(String, default="SSR")
    role_type = Column(String, default="输出")
    attributes = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    description = Column(Text, default="")
    plain_analysis = Column(Text, default="")
    pve_rating = Column(Float, default=5.0)
    pvp_rating = Column(Float, default=5.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skills = relationship("Skill", back_populates="character", cascade="all, delete")

class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"))
    name = Column(String)
    official_desc = Column(Text, default="")
    plain_desc = Column(Text, default="")
    mechanics = Column(JSON, default=list)
    pve_score = Column(Float, default=5.0)
    pvp_score = Column(Float, default=5.0)

    character = relationship("Character", back_populates="skills")

class Synergy(Base):
    __tablename__ = "synergies"
    id = Column(Integer, primary_key=True, index=True)
    source_character_id = Column(Integer, ForeignKey("characters.id"))
    target_character_id = Column(Integer, ForeignKey("characters.id"))
    trigger_condition = Column(Text, default="")
    buff_effect = Column(Text, default="")
    synergy_score = Column(Float, default=5.0)
    description = Column(Text, default="")

class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"
    id = Column(Integer, primary_key=True, index=True)
    term = Column(String, unique=True, index=True)
    category = Column(String, default="通用")
    explanation = Column(Text, default="")
    related_to = Column(JSON, default=list)

class AIModule(Base):
    __tablename__ = "ai_modules"
    id = Column(Integer, primary_key=True, index=True)
    module_name = Column(String)
    unlock_condition = Column(String, default="")
    battle_effect = Column(Text, default="")
    upgrade_path = Column(Text, default="")
    best_synergy = Column(JSON, default=list)
    description = Column(Text, default="")

class DataVersion(Base):
    __tablename__ = "data_versions"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True, index=True)
    update_time = Column(DateTime, default=datetime.utcnow)
    change_log = Column(Text, default="")
    affected_tables = Column(JSON, default=list)

# ---------- 创建表并插入初始数据 ----------
def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # 检查是否已有数据
    if db.query(Character).count() == 0:
        # 插入示例角色
        char1 = Character(
            name="楚子航",
            rarity="SSR",
            role_type="输出",
            attributes=["火", "刀"],
            tags=["高爆发", "单体"],
            description="狮心会会长，言灵·君焰。",
            plain_analysis="强力火系输出，大招能造成大量单体伤害，适合作为主C培养。",
            pve_rating=9.0,
            pvp_rating=8.5
        )
        char2 = Character(
            name="夏弥",
            rarity="SSR",
            role_type="辅助",
            attributes=["风", "龙"],
            tags=["增伤", "控制"],
            description="神秘少女，真实身份为大地与山之王。",
            plain_analysis="风系辅助，能为队友增加伤害，并有一定控制能力。",
            pve_rating=8.0,
            pvp_rating=9.0
        )
        db.add_all([char1, char2])
        db.flush()

        # 插入技能
        skill1 = Skill(
            character_id=char1.id,
            name="君焰",
            official_desc="造成300%攻击力的火属性伤害，并点燃目标。",
            plain_desc="打一下很痛，还能让敌人持续掉血。",
            mechanics=["点燃", "高倍率"],
            pve_score=9.5,
            pvp_score=8.5
        )
        skill2 = Skill(
            character_id=char2.id,
            name="风王之瞳",
            official_desc="提升全体队友20%攻击力，持续2回合。",
            plain_desc="全队攻击力上升，持续两回合。",
            mechanics=["群体增益"],
            pve_score=8.5,
            pvp_score=9.0
        )
        db.add_all([skill1, skill2])

        # 插入联动
        synergy = Synergy(
            source_character_id=char1.id,
            target_character_id=char2.id,
            trigger_condition="楚子航与夏弥同时上场时触发。",
            buff_effect="楚子航暴击率提升15%，夏弥技能冷却减少1回合。",
            synergy_score=9.0,
            description="两人配合默契，输出和辅助相得益彰。"
        )
        db.add(synergy)

        # 插入术语
        term1 = GlossaryTerm(
            term="言灵",
            category="战斗",
            explanation="角色特有的超自然能力，相当于技能。",
            related_to=["所有角色"]
        )
        term2 = GlossaryTerm(
            term="血统",
            category="角色",
            explanation="角色的血脉等级，影响基础属性。",
            related_to=["角色养成"]
        )
        db.add_all([term1, term2])

        # 插入AI模块
        ai_module = AIModule(
            module_name="诺玛",
            unlock_condition="完成主线第二章解锁",
            battle_effect="对局内自动分析敌方弱点，提升全队破甲效率。",
            upgrade_path="使用AI核心升级，提升分析速度。",
            best_synergy=["楚子航", "夏弥"],
            description="游戏内人工智能辅助系统，可在战斗中提供战术建议。"
        )
        db.add(ai_module)

        # 插入版本号
        version = DataVersion(
            version="1.0.0",
            update_time=datetime.utcnow(),
            change_log="初始版本，包含示例角色数据。",
            affected_tables=["characters", "skills", "synergies", "glossary_terms", "ai_modules"]
        )
        db.add(version)

        db.commit()
    db.close()

init_db()

# ---------- FastAPI 应用 ----------
app = FastAPI(title="龙族卡塞尔之门智能百科")

# 挂载静态文件（前端页面）
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ---------- Pydantic 模型 ----------
class ChatRequest(BaseModel):
    question: str

# ---------- 辅助函数 ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- 首页 ----------
@app.get("/")
def read_root():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "前端页面尚未创建，请先创建 backend/static/index.html"}

# ---------- API：角色列表 ----------
@app.get("/api/characters")
def list_characters(db: Session = Depends(get_db)):
    characters = db.query(Character).all()
    result = []
    for c in characters:
        result.append({
            "id": c.id,
            "name": c.name,
            "rarity": c.rarity,
            "role_type": c.role_type,
            "tags": c.tags,
            "plain_analysis": c.plain_analysis,
            "pve_rating": c.pve_rating,
            "pvp_rating": c.pvp_rating
        })
    return result

# ---------- API：角色详情 ----------
@app.get("/api/characters/{character_id}")
def get_character(character_id: int, db: Session = Depends(get_db)):
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="角色不存在")
    skills = db.query(Skill).filter(Skill.character_id == character_id).all()
    synergies = db.query(Synergy).filter(
        (Synergy.source_character_id == character_id) | (Synergy.target_character_id == character_id)
    ).all()
    skill_list = [{
        "id": s.id,
        "name": s.name,
        "official_desc": s.official_desc,
        "plain_desc": s.plain_desc,
        "mechanics": s.mechanics,
        "pve_score": s.pve_score,
        "pvp_score": s.pvp_score
    } for s in skills]
    synergy_list = []
    for syn in synergies:
        other_id = syn.target_character_id if syn.source_character_id == character_id else syn.source_character_id
        other_char = db.query(Character).filter(Character.id == other_id).first()
        synergy_list.append({
            "id": syn.id,
            "other_character_name": other_char.name if other_char else "未知",
            "trigger_condition": syn.trigger_condition,
            "buff_effect": syn.buff_effect,
            "synergy_score": syn.synergy_score,
            "description": syn.description
        })
    return {
        "character": {
            "id": character.id,
            "name": character.name,
            "rarity": character.rarity,
            "role_type": character.role_type,
            "attributes": character.attributes,
            "tags": character.tags,
            "description": character.description,
            "plain_analysis": character.plain_analysis,
            "pve_rating": character.pve_rating,
            "pvp_rating": character.pvp_rating,
            "updated_at": character.updated_at
        },
        "skills": skill_list,
        "synergies": synergy_list
    }

# ---------- API：术语列表 ----------
@app.get("/api/glossary")
def list_glossary(db: Session = Depends(get_db)):
    terms = db.query(GlossaryTerm).all()
    return [{
        "id": t.id,
        "term": t.term,
        "category": t.category,
        "explanation": t.explanation,
        "related_to": t.related_to
    } for t in terms]

# ---------- API：AI模块列表 ----------
@app.get("/api/ai_modules")
def list_ai_modules(db: Session = Depends(get_db)):
    modules = db.query(AIModule).all()
    return [{
        "id": m.id,
        "module_name": m.module_name,
        "unlock_condition": m.unlock_condition,
        "battle_effect": m.battle_effect,
        "upgrade_path": m.upgrade_path,
        "best_synergy": m.best_synergy,
        "description": m.description
    } for m in modules]

# ---------- API：版本信息 ----------
@app.get("/api/version/latest")
def get_latest_version(db: Session = Depends(get_db)):
    version = db.query(DataVersion).order_by(DataVersion.update_time.desc()).first()
    if not version:
        return {"version": "0.0.0", "update_time": datetime.utcnow(), "change_log": ""}
    return {
        "version": version.version,
        "update_time": version.update_time,
        "change_log": version.change_log
    }

# ---------- API：AI 问答（使用 DeepSeek，需设置环境变量 DEEPSEEK_API_KEY） ----------
@app.post("/api/chat")
async def chat(request: ChatRequest):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        # 没有配置AI密钥时，返回简单提示
        return {"answer": "AI 问答功能尚未配置。请在后端设置 DEEPSEEK_API_KEY 环境变量后使用。", "sources": []}
    
    question = request.question
    # 可选的：先检索数据库相关内容（这里简化，直接调用AI）
    # 实际生产环境建议做RAG，此处先直接调用AI模型
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是《龙族：卡塞尔之门》的攻略助手，请基于你的知识回答用户问题，如果不知道就说不知道。"},
                        {"role": "user", "content": question}
                    ],
                    "temperature": 0.7
                },
                timeout=30
            )
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return {"answer": answer, "sources": []}
    except Exception as e:
        return {"answer": f"AI 调用失败：{str(e)}", "sources": []}
