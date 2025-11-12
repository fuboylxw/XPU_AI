import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import control

# 定义传递函数
k = 1  # 令 k* = 1
num = [k, k]  # k*(s+1)
den = [1, -2, 2]  # s^2 - 2s + 2

# 创建系统
sys = signal.TransferFunction(num, den)

# 生成频率范围
omega = np.logspace(-2, 3, 1000)  # 从 0.01 到 1000
s = 1j * omega

# 计算频率响应
G = (k * (s + 1)) / (s**2 - 2*s + 2)
real_part = np.real(G)
imag_part = np.imag(G)

# 绘制奈奎斯特图
plt.figure(figsize=(10, 8))
plt.plot(real_part, imag_part, 'b-', linewidth=2, label='奈奎斯特曲线 (ω>0)')
plt.plot(real_part, -imag_part, 'r--', linewidth=1, label='奈奎斯特曲线 (ω<0)')

# 标记关键点
omega_points = [0, np.sqrt(2/3), 2]
colors = ['green', 'red', 'purple']
labels = ['ω=0', 'ω=√(2/3)', 'ω=2']

for i, w in enumerate(omega_points):
    G_val = (k * (1j*w + 1)) / ((1j*w)**2 - 2j*w + 2)
    plt.plot(np.real(G_val), np.imag(G_val), 'o', markersize=8, 
             color=colors[i], label=labels[i])
    plt.annotate(f'({np.real(G_val):.2f}, {np.imag(G_val):.2f})', 
                (np.real(G_val), np.imag(G_val)), 
                xytext=(10, 10), textcoords='offset points')

# 标记 (-1, 0) 点（稳定性参考点）
plt.plot(-1, 0, 'kx', markersize=10, markeredgewidth=2, label='(-1,0) 点')

# 设置图形属性
plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
plt.axvline(x=0, color='k', linestyle='-', alpha=0.3)
plt.grid(True, alpha=0.3)
plt.axis('equal')
plt.xlabel('实部 Re(G(jω))')
plt.ylabel('虚部 Im(G(jω))')
plt.title('传递函数 $G(s) = \\frac{k^*(s+1)}{s^2 - 2s + 2}$ 的奈奎斯特图')
plt.legend()
plt.xlim([-1.5, 1.5])
plt.ylim([-1.5, 1.5])

# 显示关键点数值
print("关键点坐标:")
print(f"ω=0: ({0.5:.3f}, {0:.3f})")
print(f"ω=√(2/3): ({0:.3f}, {0.612:.3f})")
print(f"ω=2: ({-0.5:.3f}, {0:.3f})")

plt.show()