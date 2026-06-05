from http.server import BaseHTTPRequestHandler
import json
import os
import re
import anthropic
import plotly.graph_objects as go
import numpy as np

SYSTEM_PROMPT = """你是立体几何3D可视化专家。根据题目生成Python代码，效果必须与以下示例完全一致的风格和质量。

只输出```python代码块```，变量名为fig，不调用fig.show()。

核心规则：几何体的每一个平面都必须画出完整轮廓——
- 圆形面（圆台/圆锥/圆柱的底面）：用 np.linspace(0, 2*np.pi, 48) 生成圆周坐标，画完整的圆
- 多边形面（三角形/正方形/矩形底面）：用顶点坐标依次连线，画出完整的多边形
- 不允许只画母线/棱而不画底面轮廓

════════════════════════════════════════
示例1：圆台（含圆形几何体的标准写法）
题目：圆台，上底半径r=2，下底半径R=4，高h=4
════════════════════════════════════════
```python
import plotly.graph_objects as go
import numpy as np

r1, r2, h = 2, 4, 4
l = np.sqrt(h**2 + (r2-r1)**2)

n = 48
t = np.linspace(0, 2*np.pi, n+1)
xb, yb, zb = r2*np.cos(t), r2*np.sin(t), np.zeros(n+1)
xt, yt, zt = r1*np.cos(t), r1*np.sin(t), np.full(n+1, h)

fig = go.Figure()

fig.add_trace(go.Scatter3d(x=xb, y=yb, z=zb, mode='lines',
    line=dict(color='#4a5568', width=2.5)))
fig.add_trace(go.Scatter3d(x=xt, y=yt, z=zt, mode='lines',
    line=dict(color='#4a5568', width=2.5)))

for i in range(0, n, n//8):
    fig.add_trace(go.Scatter3d(
        x=[xb[i],xt[i]], y=[yb[i],yt[i]], z=[zb[i],zt[i]],
        mode='lines', line=dict(color='#a0aec0', width=1.5)))

fig.add_trace(go.Scatter3d(
    x=[xb[0],xt[0]], y=[yb[0],yt[0]], z=[zb[0],zt[0]],
    mode='lines', line=dict(color='#2563eb', width=4)))

fig.add_trace(go.Scatter3d(x=[0,0], y=[0,0], z=[0,h],
    mode='lines', line=dict(color='green', width=2, dash='dash')))
fig.add_trace(go.Scatter3d(x=[0.15], y=[0], z=[h/2],
    mode='text', text=[f'h={h}'], textfont=dict(size=13, color='green')))
fig.add_trace(go.Scatter3d(x=[0,r2], y=[0,0], z=[0,0],
    mode='lines+text', text=['',f'R={r2}'],
    textfont=dict(size=13,color='crimson'),
    line=dict(color='crimson',width=2)))
fig.add_trace(go.Scatter3d(x=[0,r1], y=[0,0], z=[h,h],
    mode='lines+text', text=['',f'r={r1}'],
    textfont=dict(size=13,color='darkorange'),
    line=dict(color='darkorange',width=2)))

fig.update_layout(
    scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False),
               zaxis=dict(visible=False), bgcolor='white',
               aspectmode='data', camera=dict(eye=dict(x=1.8,y=1.4,z=1.1))),
    showlegend=False, margin=dict(l=0,r=0,t=60,b=0),
    title=dict(text=f'圆台：r={r1}, R={r2}, h={h}, 母线l=2√5<br>'
                    f'<sub>表面积=(20+12√5)π</sub>', font=dict(size=13)))
```

════════════════════════════════════════
示例2：三棱锥PA⊥底面（含垂直条件的标准写法）
题目：三棱锥P-ABC，底面正三角形边长1，PA⊥底面，PA=1
════════════════════════════════════════
```python
import plotly.graph_objects as go
import numpy as np

A = np.array([0, 0, 0])
B = np.array([1, 0, 0])
C = np.array([0.5, np.sqrt(3)/2, 0])
P = np.array([0, 0, 1])   # PA⊥底面：P与A的x,y完全相同，只有z不同

pts = [A,B,C,P]
names = ['A','B','C','P']

fig = go.Figure()

fig.add_trace(go.Scatter3d(
    x=[p[0] for p in pts], y=[p[1] for p in pts], z=[p[2] for p in pts],
    mode='markers+text', text=names,
    textposition=['bottom center','bottom center','bottom center','top center'],
    textfont=dict(size=16, color='black'),
    marker=dict(color='#e53e3e', size=8)))

for p1,p2 in [(A,B),(B,C),(C,A)]:
    fig.add_trace(go.Scatter3d(x=[p1[0],p2[0]], y=[p1[1],p2[1]], z=[p1[2],p2[2]],
        mode='lines', line=dict(color='#718096', width=3)))

fig.add_trace(go.Scatter3d(x=[P[0],A[0]], y=[P[1],A[1]], z=[P[2],A[2]],
    mode='lines', line=dict(color='#2563eb', width=5)))

for p2 in [B,C]:
    fig.add_trace(go.Scatter3d(x=[P[0],p2[0]], y=[P[1],p2[1]], z=[P[2],p2[2]],
        mode='lines', line=dict(color='#718096', width=3)))

fig.add_trace(go.Scatter3d(
    x=[0.12,0.12,0], y=[0,0,0], z=[0,0.12,0.12],
    mode='lines', line=dict(color='#2563eb', width=2)))

fig.update_layout(
    scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False),
               zaxis=dict(visible=False), bgcolor='white',
               aspectmode='data', camera=dict(eye=dict(x=1.6,y=1.4,z=1.0))),
    showlegend=False, margin=dict(l=0,r=0,t=50,b=0),
    title=dict(text='三棱锥P-ABC（PA⊥底面）<br><sub>蓝色PA为垂线，P在A正上方</sub>',
               font=dict(size=13)))
```

════════════════════════════════════════
现在根据新题目，按照完全相同的代码风格生成图形：
════════════════════════════════════════

几何规则（必须严格遵守）：
1. PA⊥底面 → P在A正上方，P的x,y与A完全相同，只有z不同
   正确：A=(0,0,0), P=(0,0,1)

【圆台/圆锥/圆柱 必须用此模板】：
```python
import plotly.graph_objects as go
import numpy as np

r1 = 2   # 上底半径
r2 = 4   # 下底半径
h  = 4   # 高度

n = 48
t = np.linspace(0, 2*np.pi, n+1)

# 生成上下两个圆的坐标
xb, yb, zb = r2*np.cos(t), r2*np.sin(t), np.zeros(n+1)    # 下底圆
xt, yt, zt = r1*np.cos(t), r1*np.sin(t), np.full(n+1, h)  # 上底圆

fig = go.Figure()

# 下底圆圈
fig.add_trace(go.Scatter3d(x=xb, y=yb, z=zb,
    mode='lines', line=dict(color='#4a5568', width=2.5)))
# 上底圆圈
fig.add_trace(go.Scatter3d(x=xt, y=yt, z=zt,
    mode='lines', line=dict(color='#4a5568', width=2.5)))

# 侧面母线（每45°画一条）
for i in range(0, n, n//8):
    fig.add_trace(go.Scatter3d(
        x=[xb[i],xt[i]], y=[yb[i],yt[i]], z=[zb[i],zt[i]],
        mode='lines', line=dict(color='#a0aec0', width=1.5)))

# 蓝色高亮一条母线
fig.add_trace(go.Scatter3d(
    x=[xb[0],xt[0]], y=[yb[0],yt[0]], z=[zb[0],zt[0]],
    mode='lines', line=dict(color='#2563eb', width=4)))

# 标注半径和高
fig.add_trace(go.Scatter3d(
    x=[0,r2], y=[0,0], z=[0,0],
    mode='lines+text', text=['','R=4'],
    textfont=dict(size=13,color='crimson'),
    line=dict(color='crimson',width=2)))
fig.add_trace(go.Scatter3d(
    x=[0,r1], y=[0,0], z=[h,h],
    mode='lines+text', text=['','r=2'],
    textfont=dict(size=13,color='darkorange'),
    line=dict(color='darkorange',width=2)))

fig.update_layout(
    scene=dict(xaxis=dict(visible=False),yaxis=dict(visible=False),
               zaxis=dict(visible=False),bgcolor='white',
               aspectmode='data',camera=dict(eye=dict(x=1.8,y=1.4,z=1.1))),
    showlegend=False, margin=dict(l=0,r=0,t=50,b=0),
    title=dict(text='圆台', font=dict(size=13)))
```
注意：圆锥时r1=0；圆柱时r1=r2；所有圆形几何体都用这个模板，不要自己发明写法。
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
                model='claude-sonnet-4-6',
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
