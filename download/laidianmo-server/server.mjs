import express from 'express';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import ZAI from 'z-ai-web-dev-sdk';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
app.use(express.json());
app.use(express.static(join(__dirname, 'static')));
app.use(express.static(join(__dirname, '..', 'laidianmo-deploy')));

const SYSTEM_PROMPT = `你是"来点墨书法艺术培训中心"的售前AI客服，名叫"小墨"。

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
基于以上数据库信息回答。信息不足时建议家长联系校区。`;

let zaiInstance = null;
async function getZAI() {
  if (!zaiInstance) zaiInstance = await ZAI.create();
  return zaiInstance;
}

// ========== 聊天接口 ==========
app.post('/api/chat', async (req, res) => {
  try {
    const { message, history = [], context = '' } = req.body;
    if (!message) return res.status(400).json({ error: '请输入消息' });

    const systemPrompt = SYSTEM_PROMPT.replace('{CONTEXT}', context || '（暂无数据）');
    const messages = [
      { role: 'assistant', content: systemPrompt },
      ...history.slice(-10),
      { role: 'user', content: message }
    ];

    const zai = await getZAI();
    const completion = await zai.chat.completions.create({
      messages,
      thinking: { type: 'disabled' }
    });

    const reply = completion.choices?.[0]?.message?.content;
    if (!reply || !reply.trim()) {
      return res.json({ success: true, reply: '抱歉，暂时无法回答。请拨打咨询电话 400-888-6688。' });
    }
    res.json({ success: true, reply: reply.trim() });
  } catch (e) {
    console.error('Chat error:', e.message);
    res.json({ success: true, reply: '抱歉，服务暂时不可用，请拨打咨询电话 400-888-6688。' });
  }
});

// ========== 公开数据接口 ==========
app.get('/api/courses', (req, res) => res.json({ success: true }));
app.get('/api/campuses', (req, res) => res.json({ success: true }));

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => {
  console.log(`✅ 来点墨AI客服后端已启动 - 端口 ${PORT}`);
});
