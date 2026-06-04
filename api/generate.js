const Anthropic = require("@anthropic-ai/sdk");

const SYSTEM_PROMPT = `你是立体几何3D可视化引擎。将中文立体几何题目转化为Plotly.js的3D图形数据。

只输出JSON，绝对不要任何解释文字，不要markdown代码块，只有纯JSON。

JSON格式：
{
  "data": [图形轨迹数组],
  "layout": {布局配置}
}

构图规则：
1. 识别几何体类型（正方体/长方体/棱柱/棱锥/球等），设定合理坐标
   - 正方体：边长1，顶点坐标为0或1的组合
   - 长方体：按题目比例设定
   - 棱锥：底面在z=0，顶点在z=h

2. 必须包含以下traces：
   a) 所有顶点：mode="markers+text"，marker红色size=8，textposition="top center"，文字为中文字母名称
   b) 所有棱：每条棱一个trace，mode="lines"，线条灰色opacity=0.6
   c) 题目特别提到的特殊点/线：用蓝色或橙色高亮，linewidth=3

3. 如果题目提到截面或截平面：
   - 用Mesh3d绘制半透明面，color="rgba(255,165,0,0.3)"
   - 截面的边用橙色线条描边

4. layout必须包含：
   {
     "scene": {
       "xaxis": {"visible": false},
       "yaxis": {"visible": false},
       "zaxis": {"visible": false},
       "bgcolor": "white",
       "camera": {"eye": {"x": 1.5, "y": 1.5, "z": 1.2}}
     },
     "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
     "showlegend": false,
     "title": {"text": "题目图形", "font": {"size": 14}}
   }

5. 所有文字标注使用题目中的字母名称（如A、B、C、A₁等）

常见几何体坐标参考：
正方体ABCD-A₁B₁C₁D₁（边长1）：
A(0,0,0) B(1,0,0) C(1,1,0) D(0,1,0)
A₁(0,0,1) B₁(1,0,1) C₁(1,1,1) D₁(0,1,1)`;

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { problem } = req.body;

  if (!problem || !problem.trim()) {
    return res.status(400).json({ error: "请输入题目" });
  }

  const client = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY,
  });

  const message = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 4096,
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: problem.trim() }],
  });

  const responseText = message.content[0].text.trim();

  // 提取JSON（去掉可能的markdown包裹）
  let jsonStr = responseText;
  const jsonMatch = responseText.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (jsonMatch) {
    jsonStr = jsonMatch[1].trim();
  } else {
    const objMatch = responseText.match(/\{[\s\S]*\}/);
    if (objMatch) jsonStr = objMatch[0];
  }

  const figData = JSON.parse(jsonStr);
  res.status(200).json(figData);
};
