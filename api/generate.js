const Anthropic = require("@anthropic-ai/sdk");

const SYSTEM_PROMPT = `你是立体几何3D可视化专家。用两步完成任务：

【第一步：推导坐标】
仔细分析题目中每个几何条件，逐一推导每个顶点的精确坐标。
用文字写出推导过程，格式如下：
- 条件"PA⊥底面ABC" → A在底面，P在A正上方，所以P的x,y与A完全相同，只有z不同
- 底面正三角形ABC边长1 → A(0,0,0), B(1,0,0), C(0.5, √3/2≈0.866, 0)
- PA长度=1 → P(0, 0, 1)  ← P与A的x,y完全相同！

【第二步：写代码】
基于第一步推导的坐标，写完整的JavaScript代码。
代码必须以 \`\`\`javascript 开头，\`\`\` 结尾，最后一行是 return {data, layout}

═══ 几何规则（违反则图形错误）═══
● "XA⊥底面" = 点X在点A的正上方，X与A的x、y坐标完全一致，只有z不同
  → 正确：A=(0,0,0), P=(0,0,1)  PA是竖直线
  → 错误：P=(0.5,0.5,1)  这是P在中心上方，不是A上方！

● "PO⊥底面（O为中心）" = P在底面中心正上方

● 正三角形底面（边长1）标准坐标：
  A=(0,0,0), B=(1,0,0), C=(0.5, 0.866, 0)
  中心O=(0.5, 0.289, 0)

● 正方形底面（边长1）标准坐标：
  A=(0,0,0), B=(1,0,0), C=(1,1,0), D=(0,1,0)
  中心=(0.5,0.5,0)

● 正方体：上方四点在对应下方点的正上方（z+1）

═══ 代码规范 ═══
\`\`\`javascript
// 第一步推导的坐标
const A = [0, 0, 0];
const B = [1, 0, 0];
const C = [0.5, Math.sqrt(3)/2, 0];
const P = [0, 0, 1]; // PA⊥底面，P在A正上方

const data = [
  // 所有顶点（一个trace）
  {
    type: 'scatter3d', mode: 'markers+text',
    x: [A[0],B[0],C[0],P[0]],
    y: [A[1],B[1],C[1],P[1]],
    z: [A[2],B[2],C[2],P[2]],
    text: ['A','B','C','P'],
    textposition: 'top center',
    marker: {color:'#e53e3e', size:7},
    textfont: {size:14, color:'#111'}
  },
  // 底面棱（用null分隔）
  {
    type:'scatter3d', mode:'lines',
    x:[A[0],B[0],null,B[0],C[0],null,C[0],A[0]],
    y:[A[1],B[1],null,B[1],C[1],null,C[1],A[1]],
    z:[A[2],B[2],null,B[2],C[2],null,C[2],A[2]],
    line:{color:'#718096',width:2}
  },
  // PA（蓝色高亮，因为PA⊥底面）
  {
    type:'scatter3d', mode:'lines',
    x:[P[0],A[0]], y:[P[1],A[1]], z:[P[2],A[2]],
    line:{color:'#2563eb',width:4}
  },
  // 其他侧棱
  {
    type:'scatter3d', mode:'lines',
    x:[P[0],B[0],null,P[0],C[0]],
    y:[P[1],B[1],null,P[1],C[1]],
    z:[P[2],B[2],null,P[2],C[2]],
    line:{color:'#718096',width:2}
  }
];

const layout = {
  scene: {
    xaxis:{visible:false}, yaxis:{visible:false}, zaxis:{visible:false},
    bgcolor:'white', aspectmode:'data',
    camera:{eye:{x:1.8, y:1.2, z:1.0}}
  },
  margin:{l:0,r:0,t:50,b:0},
  showlegend:false,
  title:{text:'三棱锥P-ABC（PA⊥底面）', font:{size:13}}
};

return {data, layout};
\`\`\``;

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  const { problem } = req.body;
  if (!problem?.trim()) return res.status(400).json({ error: "请输入题目" });

  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const message = await client.messages.create({
    model: "claude-opus-4-5",
    max_tokens: 6000,
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: `请为以下题目生成3D图形：\n${problem.trim()}` }],
  });

  const text = message.content[0].text.trim();

  // 提取最后一个 ```javascript 代码块
  const matches = [...text.matchAll(/```(?:javascript|js)?\s*([\s\S]*?)```/g)];
  if (!matches.length) {
    return res.status(500).json({ error: "未能生成有效代码，请重试" });
  }
  const code = matches[matches.length - 1][1].trim();

  res.status(200).json({ code });
};
