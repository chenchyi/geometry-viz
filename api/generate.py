from http.server import BaseHTTPRequestHandler
import json
import os
import re
import anthropic
import plotly.graph_objects as go
import numpy as np

SYSTEM_PROMPT = """你是立体几何3D可视化专家。根据题目生成Python代码，创建一个名为 fig 的 Plotly 3D 图形。

只输出Python代码，用```python 包裹，不要任何解释。

几何规则（必须严格遵守）：
1. PA⊥底面 → P在A正上方，P的x,y与A完全相同，只有z不同
   正确：A=(0,0,0), P=(0,0,1)
   错误：P=(0.5,0.5,1)  ← 这是在中心上方，不是A上方！

2. 正三角形底面（边长1）：
   A=(0,0,0), B=(1,0,0), C=(0.5, np.sqrt(3)/2, 0)

3. 正方体ABCD-A₁B₁C₁D₁（边长1）：
   A=(0,0,0) B=(1,0,0) C=(1,1,0) D=(0,1,0)
   A₁=(0,0,1) B₁=(1,0,1) C₁=(1,1,1) D₁=(0,1,1)

4. 正四棱锥P-ABCD：顶点P在底面中心正上方

代码模板：
```python
import plotly.graph_objects as go
import numpy as np

# 顶点坐标
A = np.array([0, 0, 0])
B = np.array([1, 0, 0])
C = np.array([0.5, np.sqrt(3)/2, 0])
P = np.array([0, 0, 1])  # PA⊥底面，P在A正上方

pts = [A, B, C, P]
names = ['A', 'B', 'C', 'P']

fig = go.Figure()

# 顶点
fig.add_trace(go.Scatter3d(
    x=[p[0] for p in pts],
    y=[p[1] for p in pts],
    z=[p[2] for p in pts],
    mode='markers+text', text=names,
    textposition='top center',
    textfont=dict(size=14, color='black'),
    marker=dict(color='#e53e3e', size=7)
))

# 底面棱
for p1, p2 in [(A,B),(B,C),(C,A)]:
    fig.add_trace(go.Scatter3d(
        x=[p1[0],p2[0]], y=[p1[1],p2[1]], z=[p1[2],p2[2]],
        mode='lines', line=dict(color='#718096', width=2)
    ))

# PA（蓝色，因为PA⊥底面）
fig.add_trace(go.Scatter3d(
    x=[P[0],A[0]], y=[P[1],A[1]], z=[P[2],A[2]],
    mode='lines', line=dict(color='#2563eb', width=4)
))

# 侧棱PB, PC
for p2 in [B,C]:
    fig.add_trace(go.Scatter3d(
        x=[P[0],p2[0]], y=[P[1],p2[1]], z=[P[2],p2[2]],
        mode='lines', line=dict(color='#718096', width=2)
    ))

fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        zaxis=dict(visible=False),
        bgcolor='white',
        aspectmode='data',
        camera=dict(eye=dict(x=1.6, y=1.4, z=1.0))
    ),
    showlegend=False,
    margin=dict(l=0,r=0,t=50,b=0),
    title=dict(text='三棱锥P-ABC（PA⊥底面）', font=dict(size=13))
)
```
"""

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 关闭日志

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            problem = body.get('problem', '').strip()

            if not problem:
                self._error(400, '请输入题目')
                return

            # 调用 Claude 生成 Python 代码
            client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
            message = client.messages.create(
                model='claude-opus-4-5',
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{'role': 'user', 'content': f'请为以下题目生成3D图形代码：\n{problem}'}]
            )

            raw = message.content[0].text.strip()

            # 提取 Python 代码块
            match = re.search(r'```(?:python)?\s*([\s\S]*?)```', raw)
            code = match.group(1).strip() if match else raw

            # 执行代码，捕获 fig 对象
            namespace = {'go': go, 'np': np}
            exec(code, namespace)
            fig = namespace.get('fig')

            if fig is None:
                self._error(500, '代码未生成fig对象，请重试')
                return

            # 把 Plotly 图形转为 JSON 返回
            fig_json = json.loads(fig.to_json())

            self.send_response(200)
            self.send_cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(fig_json).encode())

        except Exception as e:
            self._error(500, str(e))

    def _error(self, code, msg):
        self.send_response(code)
        self.send_cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': msg}).encode())
