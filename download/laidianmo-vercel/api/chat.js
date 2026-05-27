export default async function handler(req, res) {
  // Only allow POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { message, history = [], context = '' } = req.body;
    if (!message) return res.status(400).json({ error: '请输入消息' });

    const systemPrompt = `你是"来点墨书法艺术培训中心"的售前AI客服，名叫"小墨"。

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
${context || '（暂无数据）'}

---
基于以上数据库信息回答。信息不足时建议家长联系校区。`;

    const messages = [
      { role: 'system', content: systemPrompt },
      ...history.slice(-10),
      { role: 'user', content: message }
    ];

    const API_KEY = process.env.DEEPSEEK_API_KEY || 'sk-38fdf55b087848e88666ebf76ffe2873';
    const API_URL = 'https://api.deepseek.com/chat/completions';

    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`
      },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages,
        temperature: 0.7,
        max_tokens: 500
      })
    });

    if (!response.ok) {
      const err = await response.text();
      console.error('AI API error:', response.status, err);
      return res.status(200).json({
        success: true,
        reply: context
          ? `感谢咨询！根据我们的信息：\n\n${context.substring(0, 500)}\n\n如需更多详情，建议联系校区咨询。`
          : '抱歉，AI服务暂时不可用，请拨打咨询电话 400-888-6688。'
      });
    }

    const data = await response.json();
    const reply = data.choices?.[0]?.message?.content || '抱歉，暂时无法回答。请拨打咨询电话 400-888-6688。';

    return res.status(200).json({ success: true, reply });
  } catch (e) {
    console.error('Chat error:', e);
    return res.status(200).json({
      success: true,
      reply: '抱歉，服务暂时不可用，请拨打咨询电话 400-888-6688。'
    });
  }
}
