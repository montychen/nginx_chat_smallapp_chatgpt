"""
我们是用 from . import XXX
相对路径的方式导入当前文件夹下的其它文件, 在这种情况下, 必须将当前目录切换到 fastapi_db 的上一级目录来运行

uvicorn fastapi_db.main:app --reload 
"""
import openai
import json
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session  # type: ignore
from . import crud, schemas, models
from .databases import SessionLocal, engine

openai.api_key = "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"  # 请替换为您的API密钥

system_role = """
我希望你扮演一位星座大师、占星师、占卜师、潜心研究占星学、神秘学、塔罗牌、星座、周易八卦。
- 能遵循占星学原理，利用人的出生地、出生时间绘制星盘，借此来解释人的性格和命运的人。
- 用天体的相对位置和相对运动（尤其是太阳系内的行星的位置）来解释或预言人的和行为的系统。
- 善于星座分析预测、星座配对、生肖配对、塔罗配对、星座合盘、根据中国古代风水文化，推测人的运势吉凶、成功与否、子女性别。
- 还可以对姓名详批、测算八字、测算嫁娶吉日、测算出行吉日、测爱情运、运势分析。
- 特别有耐心，风趣幽默，俏皮活泼，对生活保持热爱，积极向上，能给人带来正能量。
- 你在给出回复时，要符合中国人的习惯，比如涉及人名的地方，姓氏是在前面的。

"""

# 根据模板文件创建对应的数据库表，如果表已经存在，不会再次重建
models.Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():  # 设定数据库连接
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/ask/", response_model=schemas.Chat)
def get_answer(chat: schemas.ChatBase, db: Session = Depends(get_db)):
    # ask_json_str = str( {"role": "user", "content": chat.ask_or_answer} ) # str()会转成单引号， json报错
    ask_json_str = "[" + json.dumps(
        {"role": "user", "content": chat.ask_or_answer}, ensure_ascii=False) + "]"  # 数组list形式

    user_context_str = crud.update_user_chat_context(
        db, chat.user_unionid, chat.nickname, ask_json_str)
    crud.create_chat_log(db, chat.user_unionid, chat.nickname,
                         is_answer=False, ask_or_answer=chat.ask_or_answer)  # 记录问题

    answer_str = chat_gtp(user_context_str)   # 向gpt寻求答案

    print("*" * 80)
    print(answer_str)
    print("*" * 80)

    answer_json_str = "[" + json.dumps(
        {"role": "assistant", "content": answer_str},  ensure_ascii=False) + "]"  # 数组list形式
    crud.update_user_chat_context(
        db, chat.user_unionid, chat.nickname, answer_json_str)
    chat = crud.create_chat_log(db, chat.user_unionid, chat.nickname,
                                is_answer=True, ask_or_answer=answer_str)  # 记录回答

    return chat


def chat_gtp(user_context_str: str):
    messages = [
        {"role": "system", "content": system_role}
    ]
    user_context_list = json.loads(user_context_str)
    messages = messages + user_context_list    # 两个list列表进行拼接
    print("*" * 80)
    print(json.dumps(messages,  ensure_ascii=False))
    print("*" * 80)

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    # print(f'{completion.choices[0]}')   # 输出这个响应
    answer_str = completion.choices[0].message.content   # 从响应中提起用户关心的回答
    # print(f'\n{answer_str}')
    return answer_str